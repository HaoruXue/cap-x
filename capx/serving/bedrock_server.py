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

import logging

import litellm
import tyro
import uvicorn
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
    # google/gemini and openai/* have no Bedrock equivalent — route them to a
    # sensible default so trials don't crash; adjust to taste.
    "google/gemini-2.5-pro-preview": "bedrock/us.amazon.nova-pro-v1:0",
    "google/gemini-3.1-pro-preview": "bedrock/us.amazon.nova-pro-v1:0",
}


def _resolve_model(model: str) -> str:
    if model.startswith("openrouter/"):
        model = model[len("openrouter/"):]
    if model in MODEL_MAP:
        return MODEL_MAP[model]
    if model.startswith("bedrock/"):
        return model
    # Bare Bedrock id (e.g. "us.anthropic.claude-sonnet-4-6") -> add prefix.
    return f"bedrock/{model}"


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
