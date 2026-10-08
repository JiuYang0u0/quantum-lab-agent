"""OpenAI-compatible HTTP protocol, without automatic request retries."""
import asyncio
import os
import time
from urllib.parse import urlsplit

import httpx
from pydantic import Field, model_validator

from .schemas import Config


class Settings(Config):
    base_url: str = "http://127.0.0.1:1234/v1"
    model: str = "google/gemma-4-e2b"
    api_key: str = Field(default="", repr=False, exclude=True)
    qec_url: str = "http://127.0.0.1:8000"
    max_tokens: int = Field(default=512, ge=16, le=2048)

    @model_validator(mode="after")
    def valid(self):
        for url in (self.base_url, self.qec_url):
            parsed = urlsplit(url)
            if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError("URLs must be HTTP(S), without embedded credentials or query")
        if not self.model.strip():
            raise ValueError("explicit model ID required")
        return self

    @classmethod
    def load(cls, profile="lmstudio"):
        if profile not in ("lmstudio", "nvidia"):
            raise ValueError("unknown provider profile")
        return cls(
            base_url=os.getenv("QLA_BASE_URL", "http://127.0.0.1:1234/v1" if profile == "lmstudio" else "https://integrate.api.nvidia.com/v1"),
            model=os.getenv("QLA_MODEL", "google/gemma-4-e2b" if profile == "lmstudio" else ""),
            api_key=os.getenv("QLA_API_KEY", ""),
            qec_url=os.getenv("QLA_QEC_URL", "http://127.0.0.1:8000"),
            max_tokens=int(os.getenv("QLA_MAX_TOKENS", "512")),
        )


class Provider:
    def __init__(self, client: httpx.AsyncClient, settings: Settings):
        self.client, self.settings = client, settings
        self.last_metadata = {}

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.settings.api_key}"} if self.settings.api_key else {}

    async def models(self):
        response = await self.client.get(self.settings.base_url.rstrip("/") + "/models",
                                         headers=self.headers, timeout=10)
        response.raise_for_status()
        return [item["id"] for item in response.json()["data"]]

    async def complete(self, messages, tools, deadline):
        return await self._complete(messages, tools, deadline, self.settings.max_tokens)

    async def interpret(self, messages, deadline, max_tokens):
        if not 16 <= max_tokens <= 256:
            raise ValueError("invalid interpretation token budget")
        return await self._complete(messages, [], deadline, max_tokens)

    async def _complete(self, messages, tools, deadline, max_tokens):
        self.last_metadata = {}
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("provider time budget")
        payload = {"model": self.settings.model, "messages": messages, "temperature": 0,
                   "max_tokens": max_tokens, "stream": False}
        if tools:
            payload.update(tools=tools, tool_choice="auto")
        async with asyncio.timeout(remaining):
            response = await self.client.post(self.settings.base_url.rstrip("/") + "/chat/completions",
                                              json=payload, headers=self.headers, timeout=remaining)
        response.raise_for_status()
        envelope = response.json()
        choices = envelope.get("choices") if isinstance(envelope, dict) else None
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise ValueError("invalid completion choices")
        choice = choices[0]
        message = choice.get("message")
        if not isinstance(message, dict) or message.get("role") != "assistant":
            raise ValueError("invalid completion message")
        if message.get("content") is not None and not isinstance(message["content"], str):
            raise ValueError("invalid completion content")
        calls = message.get("tool_calls")
        if calls is not None:
            if not isinstance(calls, list):
                raise ValueError("invalid tool calls")
            for call in calls:
                if not isinstance(call, dict) or not isinstance(call.get("id"), str) or not call["id"] or call.get("type") != "function":
                    raise ValueError("invalid tool call")
                function = call.get("function")
                if not isinstance(function, dict) or not isinstance(function.get("name"), str) or not isinstance(function.get("arguments"), str):
                    raise TypeError("invalid function call")
        usage = envelope.get("usage")
        clean_usage = {}
        if isinstance(usage, dict):
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                if type(usage.get(key)) is int:
                    clean_usage[key] = usage[key]
            for key in ("prompt_tokens_details", "completion_tokens_details"):
                if isinstance(usage.get(key), dict):
                    clean_usage[key] = {k: v for k, v in usage[key].items()
                                        if k.endswith("_tokens") and type(v) is int}
        self.last_metadata = {"finish_reason": choice.get("finish_reason") if isinstance(
            choice.get("finish_reason"), str) else None, "usage": clean_usage}
        # Never retain reasoning text, including extra fields nested in tool calls.
        result = {k: v for k, v in message.items() if k in ("role", "content")}
        if calls is not None:
            result["tool_calls"] = [{"id": c["id"], "type": "function", "function": {
                "name": c["function"]["name"], "arguments": c["function"]["arguments"]}} for c in calls]
        return result
