# BenchWiki

Community-driven benchmark platform for AI inference performance across hardware × model × framework combinations. Supports both local and cloud models.

## The Gap

No single platform covers:
- Local LLM inference speed **and** quality, across arbitrary hardware/framework combos
- Community-submitted results with structured, filterable metadata
- Fine-tuned model benchmarks (e.g. Qwopus, custom GGUF variants)
- Cloud API latency with time-stamped observations

Existing alternatives are partial: llmcheck.net (Apple Silicon speed only), mac-llm-bench (manual GitHub PRs), HuggingFace Leaderboard (standardized server only).

## How It Works

### Submit

A Python CLI (`pip install benchwiki`) auto-detects your hardware, runs the benchmark against an OpenAI-compatible endpoint, and submits a signed result packet.

```json
{
  "meta": { "submitted_at": "...", "submitter_id": "...", "client_version": "0.1.0" },
  "setup": {
    "type": "LOCAL",
    "hardware": { "os": {}, "cpu": {}, "memory": {}, "topology": "UNIFIED", "gpu": [] },
    "runtime": { "framework": "MLX", "version": "0.24.0", "driver_version": "Metal 3.2" },
    "model": { "name": "Qwopus3.6-27B-v2", "quant_format": "MLX", "quant_level": "4bit", "params_total_b": 27 }
  },
  "benchmark": {
    "type": "LLM_INFERENCE",
    "config": { "context_tokens": 4096, "batch_size": 1 },
    "results": { "ttft_ms": 32800, "decode_tps": 14.9, "peak_memory_gb": 17.3 }
  }
}
```

For cloud submissions, `setup.hardware` is replaced by `setup.cloud` (provider, model string, region, `observed_at`).

### Explore

Faceted search UI with filters across:

| Dimension | Options |
|-----------|---------|
| Topology | `CPU_ONLY` / `GPU_SINGLE` / `GPU_MULTI` / `CPU_GPU_HYBRID` / `UNIFIED` |
| Model | name, base model, params, quant format/level, MoE/Dense |
| Runtime | framework, version, context length |
| Cloud | provider, model string, date range, region |

Results are shareable via URL: `/explore?topology=UNIFIED&model=Qwen3.6-27B&quant=Q4&sort=decode_tps`

### Benchmark Types

| Type | Key Metrics |
|------|-------------|
| `LLM_INFERENCE` | `ttft_ms`, `decode_tps`, `prefill_tps`, `peak_memory_gb` |
| `LLM_QUALITY` | `benchmark_name`, `accuracy`, `samples`, `think_mode` |
| `LLM_CLOUD_LATENCY` | `ttft_ms`, `decode_tps`, `cost_per_1m_tokens`, `observed_at` |
| `IMAGE_GEN` | `steps_per_sec`, `resolution`, `peak_memory_gb` |
| `SPEECH_RECOGNITION` | `realtime_factor`, `wer` |
| `EMBEDDING` | `encode_tps`, `dimensions` |

## Editing Model

Measurements are **immutable**. Metadata is **wiki-editable**.

| Field | Editable | Reason |
|-------|----------|--------|
| `gpu_model`, `cpu_model` | ✓ | Typo / wrong model name |
| `framework`, `quant_format` | ✓ | Wrong selection |
| `decode_tps`, `ttft_ms` | ✗ | Measurement — immutable |
| `peak_memory_gb` | ✗ | Measurement — immutable |

Suspicious measurements are flagged, not edited. Re-measurement → new submission.

Permission tiers (OpenStreetMap-inspired): new users propose edits → trusted users apply directly → veteran users handle rollbacks and flags.

Custom fields via `extended: {}` can be promoted to core schema fields through community vote when N+ users adopt the same field.

## Architecture

```
Python CLI (pip install benchwiki)
  → auto-detect hardware (psutil, pynvml, system_profiler)
  → run benchmark against OpenAI-compatible endpoint
  → submit signed result packet

Cloudflare Workers + D1 (or PostgreSQL)
  → GitHub OAuth
  → result validation + outlier flagging
  → edit history versioning

Cloudflare Pages
  → faceted search UI
  → speed + quality results side by side
```

## Status

Early development. Schema and API are not stable.
