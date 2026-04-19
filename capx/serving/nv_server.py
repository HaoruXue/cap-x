import itertools
import logging
import time
from pathlib import Path
from typing import Literal

import tyro
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)
MAX_KEY_ROTATION_PASSES = 3
RATE_LIMIT_BACKOFF_SECONDS = 5.0


class ImageUrl(BaseModel):
    url: str


class ContentItem(BaseModel):
    type: Literal["text", "image_url"]
    text: str | None = None
    image_url: ImageUrl | None = None


class Message(BaseModel):
    role: str
    content: str | list[ContentItem] | None = None


class ChatCompletionRequest(BaseModel):
    model: str = "gcp/google/gemini-3.1-pro-preview"
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


def _load_api_keys(key_file: str) -> list[str]:
    """Load API keys from a file, one key per line. Ignores blank lines and comments."""
    path = Path(key_file)
    if not path.exists():
        raise FileNotFoundError(f"Key file not found: {key_file}")

    keys: list[str] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            keys.append(line)

    if not keys:
        raise ValueError(f"No API keys found in {key_file}")
    return keys


def _is_retryable_key_error(exc: Exception) -> bool:
    text = str(exc).lower()
    markers = (
        "403",
        "401",
        "429",
        "rate limit",
        "quota",
        "daily limit",
        "insufficient",
        "billing",
        "credit",
        "forbidden",
        "unauthorized",
    )
    return any(marker in text for marker in markers)


def _is_rate_limit_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "429" in text or "rate limit" in text


def create_app(
    api_keys: list[str],
    base_url: str,
    async_client: bool = True,
) -> FastAPI:
    if async_client:
        clients = [AsyncOpenAI(api_key=key, base_url=base_url) for key in api_keys]
    else:
        clients = [OpenAI(api_key=key, base_url=base_url) for key in api_keys]

    # Stateless round-robin selection across requests.
    key_cycle = itertools.count()

    app = FastAPI(title="NV Inference Proxy", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def iter_clients():
        start = next(key_cycle) % len(clients)
        for offset in range(len(clients)):
            idx = (start + offset) % len(clients)
            yield idx, clients[idx]

    if async_client:

        @app.post("/chat/completions")
        async def chat_completions(request: ChatCompletionRequest):
            last_error: Exception | None = None
            client_kwargs = request.model_dump(exclude_none=True)

            for attempt in range(MAX_KEY_ROTATION_PASSES):
                saw_rate_limit = False
                for idx, client in iter_clients():
                    try:
                        if request.stream:
                            client_kwargs["stream"] = True
                            response = await client.chat.completions.create(**client_kwargs)

                            async def event_stream():
                                async for chunk in response:
                                    yield f"data: {chunk.model_dump_json()}\n\n"
                                yield "data: [DONE]\n\n"

                            return StreamingResponse(event_stream(), media_type="text/event-stream")

                        client_kwargs["stream"] = False
                        response = await client.chat.completions.create(**client_kwargs)

                        choices = [
                            ChatCompletionResponseChoice(
                                index=c.index,
                                message=Message(role=c.message.role, content=c.message.content),
                                finish_reason=c.finish_reason,
                            )
                            for c in response.choices
                        ]

                        if idx != 0:
                            logger.info("NV proxy served request with rotated key index %s", idx)

                        return ChatCompletionResponse(
                            id=response.id,
                            created=response.created,
                            model=response.model,
                            choices=choices,
                        )
                    except Exception as exc:
                        last_error = exc
                        if _is_retryable_key_error(exc):
                            if _is_rate_limit_error(exc):
                                saw_rate_limit = True
                            logger.warning("NV proxy key index %s failed; rotating key: %s", idx, exc)
                            continue
                        raise HTTPException(status_code=500, detail=str(exc))

                if saw_rate_limit and attempt < MAX_KEY_ROTATION_PASSES - 1:
                    backoff_s = RATE_LIMIT_BACKOFF_SECONDS * (attempt + 1)
                    logger.warning("All NV keys rate-limited; backing off for %.1fs before retry", backoff_s)
                    import asyncio

                    await asyncio.sleep(backoff_s)

            raise HTTPException(status_code=500, detail=str(last_error) if last_error else "All NV keys failed")

    else:

        @app.post("/chat/completions", response_model=ChatCompletionResponse)
        def chat_completions(request: ChatCompletionRequest):
            last_error: Exception | None = None
            client_kwargs = request.model_dump(exclude_none=True)
            client_kwargs["stream"] = False

            for attempt in range(MAX_KEY_ROTATION_PASSES):
                saw_rate_limit = False
                for idx, client in iter_clients():
                    try:
                        response = client.chat.completions.create(**client_kwargs)

                        choices = [
                            ChatCompletionResponseChoice(
                                index=c.index,
                                message=Message(role=c.message.role, content=c.message.content),
                                finish_reason=c.finish_reason,
                            )
                            for c in response.choices
                        ]

                        if idx != 0:
                            logger.info("NV proxy served request with rotated key index %s", idx)

                        return ChatCompletionResponse(
                            id=response.id,
                            created=response.created,
                            model=response.model,
                            choices=choices,
                        )
                    except Exception as exc:
                        last_error = exc
                        if _is_retryable_key_error(exc):
                            if _is_rate_limit_error(exc):
                                saw_rate_limit = True
                            logger.warning("NV proxy key index %s failed; rotating key: %s", idx, exc)
                            continue
                        raise HTTPException(status_code=500, detail=str(exc))

                if saw_rate_limit and attempt < MAX_KEY_ROTATION_PASSES - 1:
                    backoff_s = RATE_LIMIT_BACKOFF_SECONDS * (attempt + 1)
                    logger.warning("All NV keys rate-limited; backing off for %.1fs before retry", backoff_s)
                    time.sleep(backoff_s)

            raise HTTPException(status_code=500, detail=str(last_error) if last_error else "All NV keys failed")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


def main(
    key_file: str = ".nvinferencekey",
    api_key: str | None = None,
    host: str = "0.0.0.0",
    port: int = 8110,
    base_url: str = "https://inference-api.nvidia.com/v1/",
    async_client: bool = True,
):
    """Start the NV Inference Proxy Server with optional key rotation."""
    if api_key is None:
        api_keys = _load_api_keys(key_file)
        logger.info("Loaded %s NV inference key(s) from %s", len(api_keys), key_file)
    else:
        api_keys = [api_key]

    app = create_app(api_keys=api_keys, base_url=base_url, async_client=async_client)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    tyro.cli(main)
