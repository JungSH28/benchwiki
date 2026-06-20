export interface Env {
  DB: D1Database;
}

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

const VALID_TOPOLOGIES = new Set(["CPU_ONLY", "GPU_SINGLE", "GPU_MULTI", "CPU_GPU_HYBRID", "UNIFIED"]);
const VALID_BENCH_TYPES = new Set(["LLM_INFERENCE", "LLM_QUALITY", "IMAGE_GEN", "SPEECH_RECOGNITION", "EMBEDDING", "LLM_CLOUD_LATENCY"]);
const VALID_SORTS = new Set(["decode_tps", "ttft_ms", "accuracy", "submitted_at"]);

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    if (req.method === "OPTIONS") return new Response(null, { headers: CORS });

    const url = new URL(req.url);

    if (url.pathname === "/api/submissions") {
      if (req.method === "POST") return handleSubmit(req, env);
      if (req.method === "GET") return handleList(url, env);
    }

    const idMatch = url.pathname.match(/^\/api\/submissions\/([0-9a-f-]{36})$/);
    if (idMatch && req.method === "GET") return handleGet(idMatch[1], env);

    return json({ error: "Not Found" }, 404);
  },
};

async function handleSubmit(req: Request, env: Env): Promise<Response> {
  let body: any;
  try {
    body = await req.json();
  } catch {
    return json({ error: "Invalid JSON" }, 400);
  }

  const setup = body?.setup;
  const bench = body?.benchmark;

  if (!setup?.type || !bench?.type || !bench?.results) {
    return json({ error: "Missing required fields: setup.type, benchmark.type, benchmark.results" }, 400);
  }

  if (!["LOCAL", "CLOUD"].includes(setup.type)) {
    return json({ error: "setup.type must be LOCAL or CLOUD" }, 400);
  }

  if (!VALID_BENCH_TYPES.has(bench.type)) {
    return json({ error: `Unknown benchmark.type: ${bench.type}` }, 400);
  }

  const topology = setup.hardware?.topology ?? null;
  if (topology && !VALID_TOPOLOGIES.has(topology)) {
    return json({ error: `Unknown topology: ${topology}` }, 400);
  }

  const id = crypto.randomUUID();
  const submitted_at = new Date().toISOString();
  const r = bench.results;
  const hw = setup.hardware ?? {};
  const rt = setup.runtime ?? {};
  const m = setup.model ?? {};
  const cl = setup.cloud ?? {};

  await env.DB.prepare(`
    INSERT INTO submissions (
      id, submitted_at, submitter_id, setup_type,
      topology, cpu_model, ram_gb, gpu_model, vram_gb,
      framework, framework_version,
      model_name, base_model, quant_format, quant_level, params_total_b, params_active_b,
      provider, model_string, region, observed_at,
      benchmark_type, ttft_ms, decode_tps, prefill_tps, peak_memory_gb,
      context_tokens, accuracy, benchmark_name, cost_per_1m_tokens,
      raw_json
    ) VALUES (
      ?,?,?,?,  ?,?,?,?,?,  ?,?,  ?,?,?,?,?,?,  ?,?,?,?,  ?,?,?,?,?,  ?,?,?,?,  ?
    )
  `).bind(
    id, submitted_at, body.meta?.submitter_id ?? "anonymous", setup.type,
    topology, hw.cpu?.model ?? null, hw.memory?.ram_gb ?? null, hw.gpu?.[0]?.model ?? null, hw.gpu?.[0]?.vram_gb ?? null,
    rt.framework ?? null, rt.version ?? null,
    m.name ?? null, m.base_model ?? null, m.quant_format ?? null, m.quant_level ?? null, m.params_total_b ?? null, m.params_active_b ?? null,
    cl.provider ?? null, cl.model_string ?? null, cl.region_actual ?? cl.region_requested ?? null, cl.observed_at ?? null,
    bench.type, r.ttft_ms ?? null, r.decode_tps ?? null, r.prefill_tps ?? null, r.peak_memory_gb ?? null,
    bench.config?.context_tokens ?? null, r.accuracy ?? null, r.benchmark_name ?? null, r.cost_per_1m_tokens ?? null,
    JSON.stringify(body),
  ).run();

  return json({ id, submitted_at }, 201);
}

async function handleList(url: URL, env: Env): Promise<Response> {
  const p = url.searchParams;
  const conditions: string[] = [];
  const values: unknown[] = [];

  const addFilter = (col: string, param: string, op = "=") => {
    const val = p.get(param);
    if (val) {
      conditions.push(op === "LIKE" ? `${col} LIKE ?` : `${col} = ?`);
      values.push(op === "LIKE" ? `%${val}%` : val);
    }
  };

  addFilter("setup_type", "setup_type");
  addFilter("topology", "topology");
  addFilter("framework", "framework");
  addFilter("benchmark_type", "benchmark_type");
  addFilter("quant_format", "quant_format");
  addFilter("provider", "provider");
  addFilter("model_name", "model", "LIKE");

  const sortParam = p.get("sort") ?? "submitted_at";
  const sortCol = VALID_SORTS.has(sortParam) ? sortParam : "submitted_at";
  const dirParam = (p.get("dir") ?? "DESC").toUpperCase();
  const sortDir = dirParam === "ASC" ? "ASC" : "DESC";

  const limit = Math.min(parseInt(p.get("limit") ?? "50"), 200);
  const offset = Math.max(parseInt(p.get("offset") ?? "0"), 0);

  const where = conditions.length ? `WHERE ${conditions.join(" AND ")}` : "";

  const rows = await env.DB.prepare(
    `SELECT id, submitted_at, submitter_id, setup_type,
            topology, cpu_model, ram_gb, gpu_model, vram_gb,
            framework, model_name, quant_format, quant_level, params_total_b,
            provider, model_string, region, benchmark_type,
            ttft_ms, decode_tps, peak_memory_gb, context_tokens, accuracy, benchmark_name
     FROM submissions ${where}
     ORDER BY ${sortCol} ${sortDir}
     LIMIT ? OFFSET ?`
  ).bind(...values, limit, offset).all();

  return json({ results: rows.results, limit, offset });
}

async function handleGet(id: string, env: Env): Promise<Response> {
  const row = await env.DB.prepare("SELECT * FROM submissions WHERE id = ?").bind(id).first();
  if (!row) return json({ error: "Not Found" }, 404);
  return json(row);
}

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS, "Content-Type": "application/json" },
  });
}
