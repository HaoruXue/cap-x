"""Drop-in Amazon Bedrock proxy.

Exposes the SAME OpenAI-compatible ``/chat/completions`` contract as
``openrouter_server.py`` so that nothing in CaP-X needs to change: point
``LaunchArgs.server_url`` at this server and existing clients keep working.

It uses LiteLLM under the hood, which translates OpenAI-format chat messages
(including image_url content blocks and streaming) into Bedrock's Converse API
and handles the cross-region inference-profile ids for you.

Usage::

    uv run capx/serving/bedrock_server.py --port 8110 --region us-west-2

Then run CaP-X exactly as before; e.g. keep --server_url http://127.0.0.1:8110/...
and pass a model that maps below, or an explicit bedrock/ id.

Credentials come from the machine's default AWS config (AWS_PROFILE / ~/.aws),
the same setup used elsewhere on this box.
"""

import json as _json
import logging
import time as _time
import uuid as _uuid

import boto3
import httpx
import litellm
import tyro
import uvicorn
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# --- Identical request/response schema to openrouter_server.py --------------

class ImageUrl(BaseModel):
    url: str


class ContentItem(BaseModel):
    type: str
    text: str | None = None
    image_url: ImageUrl | None = None


class Message(BaseModel):
    role: str
    content: str | list[ContentItem] | None = None
    # Surfaced for Anthropic-on-Bedrock adaptive thinking — summary of the
    # model's chain-of-thought when display="summarized" is requested.
    # Field name matches the OpenRouter / DeepSeek convention so existing
    # callers (e.g. capx.llm.client.query_model) read it without changes.
    reasoning: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str = "openrouter/anthropic/claude-sonnet-4"
    messages: list[Message]
    temperature: float | None = 0.2
    max_tokens: int | None = 256
    stream: bool = False
    top_p: float | None = None
    reasoning_effort: str | None = None
    max_completion_tokens: int | None = None


class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: Message
    finish_reason: str | None = None


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionResponseChoice]


# --- Map existing CaP-X / OpenRouter model strings to Bedrock ids -----------
# Keys are matched after stripping the leading "openrouter/". Anything not in
# the map is passed through with a "bedrock/" prefix so you can also send
# e.g. "us.anthropic.claude-opus-4-8" directly.
MODEL_MAP = {
    "anthropic/claude-sonnet-4": "bedrock/us.anthropic.claude-sonnet-4-6",
    "anthropic/claude-opus-4": "bedrock/us.anthropic.claude-opus-4-8",
    "deepseek/deepseek-r1": "bedrock/us.deepseek.r1-v1:0",
    "deepseek/deepseek-chat-v3-0324": "bedrock/deepseek.v3-v1:0",
    "qwen/qwen3-235b-a22b": "bedrock/qwen.qwen3-235b-a22b-2507-v1:0",
    "meta-llama/llama-4-maverick": "bedrock/us.meta.llama3-3-70b-instruct-v1:0",
    # OpenAI GPT-5.x — served via Bedrock Mantle endpoint, NOT bedrock-runtime.
    # The string-prefixed `mantle/` form tells the proxy to take the
    # bedrock-mantle code path (SigV4 → /openai/v1/responses) instead of
    # litellm's Converse-API path. Region-pinned to us-east-2 since
    # bedrock-mantle for GPT-5.x is only in us-east-1/us-east-2.
    "openai/gpt-5.5": "mantle/openai.gpt-5.5",
    "openai/gpt-5.4": "mantle/openai.gpt-5.4",
    # google/gemini have no Bedrock equivalent — route them to a sensible
    # default so trials don't crash; adjust to taste.
    "google/gemini-2.5-pro-preview": "bedrock/us.amazon.nova-pro-v1:0",
    "google/gemini-3.1-pro-preview": "bedrock/us.amazon.nova-pro-v1:0",
}


def _resolve_model(model: str) -> str:
    if model.startswith("openrouter/"):
        model = model[len("openrouter/"):]
    if model in MODEL_MAP:
        return MODEL_MAP[model]
    if model.startswith("bedrock/") or model.startswith("mantle/"):
        return model
    # Bare Bedrock id (e.g. "us.anthropic.claude-sonnet-4-6") -> add prefix.
    return f"bedrock/{model}"


# --- Bedrock Mantle (GPT-5.x via Responses API) helpers ---------------------

# Bedrock Mantle for GPT-5.x is currently only available in us-east-1 and
# us-east-2. Pinned to us-east-2 by default; override with $BEDROCK_MANTLE_REGION.
_MANTLE_REGION = "us-east-2"


def _messages_to_responses_input(messages: list) -> list:
    """Convert OpenAI Chat Completions messages to Responses-API ``input``.

    The Responses API on Bedrock Mantle accepts a list of {role, content}
    dicts directly (verified empirically). Multimodal content_items map
    1:1 except that image_url with data: URLs become {type:"input_image",
    image_url:"..."}.
    """
    out: list = []
    for m in messages:
        role = m.get("role", "user") if isinstance(m, dict) else m.role
        content = m.get("content") if isinstance(m, dict) else m.content
        if isinstance(content, str):
            out.append({"role": role, "content": content})
            continue
        # Content is a list of items
        items_in: list = []
        for item in content or []:
            if isinstance(item, dict):
                t = item.get("type")
                if t == "text":
                    items_in.append({"type": "input_text", "text": item.get("text", "")})
                elif t == "image_url":
                    url = item.get("image_url", {}).get("url") if isinstance(item.get("image_url"), dict) else item.get("image_url")
                    items_in.append({"type": "input_image", "image_url": url})
                else:
                    items_in.append(item)
            else:
                # Pydantic ContentItem
                t = getattr(item, "type", None)
                if t == "text":
                    items_in.append({"type": "input_text", "text": getattr(item, "text", "")})
                elif t == "image_url":
                    iu = getattr(item, "image_url", None)
                    url = iu.url if iu is not None else None
                    items_in.append({"type": "input_image", "image_url": url})
        out.append({"role": role, "content": items_in})
    return out


def _mantle_request(model_id: str, request: "ChatCompletionRequest", region: str) -> dict:
    """Call Bedrock Mantle /openai/v1/responses via SigV4 and return the JSON."""
    body = {
        "model": model_id,
        "input": _messages_to_responses_input([m.model_dump() for m in request.messages]),
    }
    if request.max_tokens is not None:
        body["max_output_tokens"] = request.max_tokens
    if request.max_completion_tokens is not None:
        body["max_output_tokens"] = request.max_completion_tokens
    if request.reasoning_effort:
        body["reasoning"] = {"effort": request.reasoning_effort}

    session = boto3.Session(region_name=region)
    creds = session.get_credentials()
    if creds is None:
        raise RuntimeError("No AWS credentials available for bedrock-mantle SigV4")
    url = f"https://bedrock-mantle.{region}.api.aws/openai/v1/responses"
    payload = _json.dumps(body)
    aws_req = AWSRequest(method="POST", url=url, data=payload, headers={"Content-Type": "application/json"})
    SigV4Auth(creds, "bedrock-mantle", region).add_auth(aws_req)
    headers = dict(aws_req.headers)
    with httpx.Client(timeout=300) as client:
        resp = client.post(url, content=payload, headers=headers)
    if resp.status_code >= 400:
        raise RuntimeError(f"bedrock-mantle {resp.status_code}: {resp.text[:500]}")
    return resp.json()


def _responses_to_chat_completion(resp_json: dict, model_id: str) -> "ChatCompletionResponse":
    """Convert a Responses-API response into a Chat-Completions response.

    The visible assistant text lives in output[*].content[*].text where
    output[*].type=="message". Reasoning summary (if any) lives in
    output[*].summary[*].text where type=="reasoning".
    """
    text_chunks: list[str] = []
    reasoning_chunks: list[str] = []
    finish_reason = "stop"
    for item in resp_json.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []) or []:
                if c.get("type") == "output_text":
                    text_chunks.append(c.get("text", ""))
        elif item.get("type") == "reasoning":
            for s in item.get("summary", []) or []:
                if isinstance(s, dict) and s.get("text"):
                    reasoning_chunks.append(s["text"])
                elif isinstance(s, str):
                    reasoning_chunks.append(s)
    content = "\n".join(text_chunks)
    reasoning = "\n".join(reasoning_chunks) if reasoning_chunks else None
    return ChatCompletionResponse(
        id=resp_json.get("id", f"chatcmpl-{_uuid.uuid4()}"),
        created=int(resp_json.get("created_at", _time.time())),
        model=resp_json.get("model", model_id),
        choices=[
            ChatCompletionResponseChoice(
                index=0,
                message=Message(role="assistant", content=content, reasoning=reasoning),
                finish_reason=finish_reason,
            )
        ],
    )


def create_app(region: str) -> FastAPI:
    app = FastAPI(title="Bedrock Proxy", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _kwargs(request: ChatCompletionRequest) -> dict:
        kw = request.model_dump(exclude_none=True)
        kw["model"] = _resolve_model(kw.get("model", ""))
        kw["aws_region_name"] = region
        # Claude Opus 4.x on Bedrock rejects `temperature` and `top_p`.
        if "claude-opus-4" in kw["model"]:
            kw.pop("temperature", None)
            kw.pop("top_p", None)
        # Translate OpenAI-style `reasoning_effort` to Bedrock's adaptive
        # thinking + output_config.effort. Default effort=high; request
        # summarized display so we capture plaintext reasoning instead of
        # only an opaque signature.
        effort = kw.pop("reasoning_effort", None)
        if "claude-opus-4" in kw["model"] or "claude-sonnet-4" in kw["model"]:
            valid = {"low", "medium", "high", "xhigh", "max"}
            effort = effort if effort in valid else "high"
            kw["thinking"] = {"type": "adaptive", "display": "summarized"}
            kw["output_config"] = {"effort": effort}
        return kw

    @app.post("/chat/completions")
    async def chat_completions(request: ChatCompletionRequest):
        try:
            resolved = _resolve_model(request.model or "")
            # Bedrock Mantle (GPT-5.x) — separate code path, NOT litellm.
            if resolved.startswith("mantle/"):
                model_id = resolved[len("mantle/"):]
                mantle_region = _MANTLE_REGION
                resp_json = _mantle_request(model_id, request, mantle_region)
                return _responses_to_chat_completion(resp_json, model_id)

            kw = _kwargs(request)

            if request.stream:
                kw["stream"] = True
                response = await litellm.acompletion(**kw)

                async def event_stream():
                    async for chunk in response:
                        yield f"data: {chunk.model_dump_json()}\n\n"
                    yield "data: [DONE]\n\n"

                return StreamingResponse(event_stream(), media_type="text/event-stream")

            kw["stream"] = False
            response = await litellm.acompletion(**kw)

            choices = []
            for c in response.choices:
                # litellm exposes Anthropic adaptive-thinking summaries on
                # the message as `reasoning_content` and/or in
                # `thinking_blocks[*].thinking`. Fall back through both.
                reasoning = getattr(c.message, "reasoning_content", None) or None
                if not reasoning:
                    blocks = getattr(c.message, "thinking_blocks", None) or []
                    chunks = [
                        b.get("thinking") if isinstance(b, dict) else getattr(b, "thinking", None)
                        for b in blocks
                    ]
                    chunks = [s for s in chunks if s]
                    reasoning = "\n".join(chunks) if chunks else None
                choices.append(
                    ChatCompletionResponseChoice(
                        index=c.index,
                        message=Message(
                            role=c.message.role,
                            content=c.message.content,
                            reasoning=reasoning,
                        ),
                        finish_reason=c.finish_reason,
                    )
                )
            return ChatCompletionResponse(
                id=response.id,
                created=response.created,
                model=response.model,
                choices=choices,
            )
        except Exception as e:
            logger.exception("Bedrock completion failed")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


def main(
    host: str = "0.0.0.0",
    port: int = 8110,
    region: str = "us-west-2",
):
    """Start the Bedrock proxy on the same port CaP-X already targets."""
    app = create_app(region=region)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    tyro.cli(main)
