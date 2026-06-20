import threading
import time

import psutil
from openai import OpenAI

# ~512 tokens worth of context filler
_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer concisely and accurately."
)
_USER_PROMPT = (
    "Explain in detail how the transformer architecture works, including "
    "self-attention, positional encoding, feed-forward layers, and why "
    "transformers replaced recurrent networks for most NLP tasks."
)


def run_inference(
    endpoint: str,
    model: str,
    api_key: str = "dummy",
    context_tokens: int = 512,
    max_tokens: int = 256,
) -> dict:
    client = OpenAI(base_url=endpoint, api_key=api_key)

    proc = psutil.Process()
    peak_mem_bytes = proc.memory_info().rss

    stop_event = threading.Event()

    def _poll_mem():
        nonlocal peak_mem_bytes
        while not stop_event.is_set():
            try:
                current = proc.memory_info().rss
                if current > peak_mem_bytes:
                    peak_mem_bytes = current
            except psutil.NoSuchProcess:
                break
            time.sleep(0.1)

    mem_thread = threading.Thread(target=_poll_mem, daemon=True)
    mem_thread.start()

    try:
        baseline_mem = proc.memory_info().rss
        start = time.perf_counter()
        first_token_at: float | None = None
        output_tokens = 0

        stream = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _USER_PROMPT},
            ],
            max_tokens=max_tokens,
            stream=True,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                if first_token_at is None:
                    first_token_at = time.perf_counter()
                output_tokens += 1

        end = time.perf_counter()
    finally:
        stop_event.set()
        mem_thread.join(timeout=1)

    ttft_ms: int | None = None
    decode_tps: float | None = None

    if first_token_at is not None:
        ttft_ms = round((first_token_at - start) * 1000)
        decode_time = end - first_token_at
        if decode_time > 0 and output_tokens > 1:
            decode_tps = round((output_tokens - 1) / decode_time, 2)

    peak_delta_gb = round((peak_mem_bytes - baseline_mem) / (1024 ** 3), 3)

    return {
        "ttft_ms": ttft_ms,
        "decode_tps": decode_tps,
        "peak_memory_gb": max(peak_delta_gb, 0.0),
        "context_tokens": context_tokens,
        "output_tokens": output_tokens,
    }
