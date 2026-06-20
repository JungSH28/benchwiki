import base64
import datetime
import json
from importlib.metadata import version

import httpx

API_BASE = "https://benchwiki-api.benchwiki.workers.dev"
WEB_BASE = "https://benchwiki.pages.dev"  # prod; preview: 3097fa52.benchwiki.pages.dev


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


def build_submit_url(payload: dict, web_base: str = WEB_BASE) -> str:
    """Encode payload as base64url and return the /submit review URL."""
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode().rstrip("=")
    return f"{web_base.rstrip('/')}/submit#{encoded}"


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
