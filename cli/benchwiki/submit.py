import datetime
from importlib.metadata import version

import httpx

API_BASE = "https://benchwiki-api.workers.dev"


def build_payload(
    hardware: dict,
    runtime: dict,
    model: dict,
    results: dict,
    submitter_id: str = "anonymous",
) -> dict:
    return {
        "meta": {
            "submitted_at": datetime.datetime.utcnow().isoformat() + "Z",
            "submitter_id": submitter_id,
            "client_version": _client_version(),
        },
        "setup": {
            "type": "LOCAL",
            "hardware": hardware,
            "runtime": runtime,
            "model": model,
        },
        "benchmark": {
            "type": "LLM_INFERENCE",
            "config": {
                "context_tokens": results.pop("context_tokens", None),
                "batch_size": 1,
            },
            "results": {k: v for k, v in results.items() if k != "output_tokens"},
        },
    }


def submit(payload: dict, api_base: str = API_BASE) -> dict:
    url = f"{api_base.rstrip('/')}/api/submissions"
    resp = httpx.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _client_version() -> str:
    try:
        return version("benchwiki")
    except Exception:
        return "dev"
