import json
import sys

import click
from rich.console import Console
from rich.table import Table

from .benchmark import run_inference
from .detect import detect_hardware
from .submit import API_BASE, build_payload, submit

console = Console()


@click.group()
def main():
    """BenchWiki CLI — benchmark AI inference and submit results."""


@main.command()
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
def detect(as_json: bool):
    """Detect and display local hardware."""
    hw = detect_hardware()
    if as_json:
        click.echo(json.dumps(hw, indent=2))
        return

    table = Table(title="Detected Hardware")
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("OS", f"{hw['os']['name']} {hw['os']['version']}")
    table.add_row("CPU", hw["cpu"].get("model", "Unknown"))
    table.add_row("Cores", f"{hw['cpu']['cores_physical']}P / {hw['cpu']['cores_logical']}L")
    table.add_row("RAM", f"{hw['memory']['ram_gb']} GB ({hw['memory']['type']})")
    table.add_row("Topology", hw["topology"])
    for i, g in enumerate(hw["gpu"]):
        vram = f"{g['vram_gb']} GB" if "vram_gb" in g else "N/A"
        table.add_row(f"GPU[{i}]", f"{g['model']}  VRAM={vram}")

    console.print(table)


@main.command()
@click.option("--model", required=True, help="Model name as the endpoint expects it")
@click.option("--endpoint", default="http://localhost:11434/v1", show_default=True)
@click.option("--api-key", default="dummy", show_default=True)
@click.option("--framework", default="Ollama", show_default=True)
@click.option("--framework-version", default="")
@click.option("--quant-format", default="")
@click.option("--quant-level", default="")
@click.option("--params-b", type=float, default=None, help="Total parameters in billions")
@click.option("--context-tokens", type=int, default=512, show_default=True)
@click.option("--max-tokens", type=int, default=256, show_default=True)
@click.option("--no-submit", is_flag=True, help="Run benchmark but skip submission")
@click.option("--api-base", default=API_BASE, show_default=True)
def run(
    model, endpoint, api_key, framework, framework_version,
    quant_format, quant_level, params_b, context_tokens, max_tokens,
    no_submit, api_base,
):
    """Detect hardware, run LLM_INFERENCE benchmark, and optionally submit."""
    console.print("[bold]Detecting hardware...[/bold]")
    hw = detect_hardware()
    console.print(f"  Topology: [cyan]{hw['topology']}[/cyan]  "
                  f"CPU: [cyan]{hw['cpu'].get('model', '?')}[/cyan]  "
                  f"RAM: [cyan]{hw['memory']['ram_gb']} GB[/cyan]")

    console.print(f"\n[bold]Running benchmark[/bold] — model=[cyan]{model}[/cyan]  "
                  f"endpoint=[cyan]{endpoint}[/cyan]")
    console.print("  (This may take a minute...)\n")

    try:
        results = run_inference(
            endpoint=endpoint,
            model=model,
            api_key=api_key,
            context_tokens=context_tokens,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        console.print(f"[red]Benchmark failed:[/red] {exc}")
        sys.exit(1)

    _print_results(results)

    if no_submit:
        return

    runtime = {
        "framework": framework,
        "version": framework_version or None,
    }
    model_meta = {
        "name": model,
        "quant_format": quant_format or None,
        "quant_level": quant_level or None,
        "params_total_b": params_b,
    }

    payload = build_payload(hw, runtime, model_meta, results)

    if not click.confirm("\nSubmit to BenchWiki?"):
        return

    try:
        resp = submit(payload, api_base=api_base)
        console.print(f"\n[green]Submitted![/green]  id={resp.get('id')}")
    except Exception as exc:
        console.print(f"[red]Submission failed:[/red] {exc}")
        sys.exit(1)


def _print_results(results: dict):
    table = Table(title="Benchmark Results")
    table.add_column("Metric", style="bold")
    table.add_column("Value")

    ttft = results.get("ttft_ms")
    tps = results.get("decode_tps")
    mem = results.get("peak_memory_gb")

    table.add_row("TTFT", f"{ttft} ms" if ttft is not None else "N/A")
    table.add_row("Decode TPS", f"{tps} tok/s" if tps is not None else "N/A")
    table.add_row("Peak Memory", f"{mem} GB" if mem is not None else "N/A")
    table.add_row("Output Tokens", str(results.get("output_tokens", "?")))

    console.print(table)
