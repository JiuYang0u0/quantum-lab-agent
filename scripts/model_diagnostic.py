"""One tiny completion diagnostic, no tools; does not claim tool support."""
import asyncio
import json
import time
from pathlib import Path

import httpx

from quantum_lab_agent.provider import Provider, Settings


async def main():
    settings = Settings.load().model_copy(update={"max_tokens": 16})
    start = time.monotonic()
    result = {"model": settings.model, "max_tokens": 16, "kind": "basic_completion_not_tool_test"}
    async with httpx.AsyncClient(trust_env=False) as client:
        try:
            result["response"] = await Provider(client, settings).complete(
                [{"role": "user", "content": "Reply only OK."}], [], start + 30)
            result["status"] = "responded"
        except (TimeoutError, httpx.HTTPError, ValueError, KeyError) as exc:
            result["status"] = type(exc).__name__
    result["elapsed_seconds"] = time.monotonic() - start
    target = Path(".qla/live/model-diagnostic.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
