CREATE TABLE IF NOT EXISTS submissions (
  id TEXT PRIMARY KEY,
  submitted_at TEXT NOT NULL,
  submitter_id TEXT NOT NULL DEFAULT 'anonymous',

  -- Setup
  setup_type TEXT NOT NULL CHECK (setup_type IN ('LOCAL', 'CLOUD')),

  -- LOCAL hardware (denormalized for query performance)
  topology TEXT CHECK (topology IN ('CPU_ONLY', 'GPU_SINGLE', 'GPU_MULTI', 'CPU_GPU_HYBRID', 'UNIFIED')),
  cpu_model TEXT,
  ram_gb REAL,
  gpu_model TEXT,
  vram_gb REAL,

  -- Runtime
  framework TEXT,
  framework_version TEXT,

  -- Model
  model_name TEXT,
  base_model TEXT,
  quant_format TEXT,
  quant_level TEXT,
  params_total_b REAL,
  params_active_b REAL,

  -- CLOUD
  provider TEXT,
  model_string TEXT,
  region TEXT,
  observed_at TEXT,

  -- Benchmark
  benchmark_type TEXT NOT NULL,
  ttft_ms REAL,
  decode_tps REAL,
  prefill_tps REAL,
  peak_memory_gb REAL,
  context_tokens INTEGER,
  accuracy REAL,
  benchmark_name TEXT,
  cost_per_1m_tokens REAL,

  -- Full payload for future schema expansion
  raw_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_topology        ON submissions(topology);
CREATE INDEX IF NOT EXISTS idx_framework       ON submissions(framework);
CREATE INDEX IF NOT EXISTS idx_benchmark_type  ON submissions(benchmark_type);
CREATE INDEX IF NOT EXISTS idx_setup_type      ON submissions(setup_type);
CREATE INDEX IF NOT EXISTS idx_quant_format    ON submissions(quant_format);
CREATE INDEX IF NOT EXISTS idx_decode_tps      ON submissions(decode_tps DESC);
CREATE INDEX IF NOT EXISTS idx_ttft_ms         ON submissions(ttft_ms ASC);
CREATE INDEX IF NOT EXISTS idx_accuracy        ON submissions(accuracy DESC);
CREATE INDEX IF NOT EXISTS idx_submitted_at    ON submissions(submitted_at DESC);
-- full-text on model_name handled by LIKE in queries for now
