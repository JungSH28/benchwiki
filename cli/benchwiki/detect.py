import json
import platform
import subprocess
import psutil


def detect_hardware() -> dict:
    gpu = _detect_gpu()
    topology = _detect_topology(gpu)
    return {
        "os": _detect_os(),
        "cpu": _detect_cpu(),
        "memory": _detect_memory(),
        "topology": topology,
        "gpu": gpu,
    }


def _detect_os() -> dict:
    return {
        "name": platform.system(),
        "version": platform.version(),
        "kernel": platform.release(),
    }


def _detect_cpu() -> dict:
    info: dict = {
        "cores_physical": psutil.cpu_count(logical=False),
        "cores_logical": psutil.cpu_count(logical=True),
        "architecture": platform.machine(),
    }

    if platform.system() == "Darwin":
        try:
            raw = subprocess.run(
                ["system_profiler", "SPHardwareDataType", "-json"],
                capture_output=True, text=True, timeout=10
            ).stdout
            hw = json.loads(raw)["SPHardwareDataType"][0]
            info["model"] = hw.get("chip_type") or hw.get("cpu_type", "Unknown")
        except Exception:
            info["model"] = platform.processor() or "Unknown"
    elif platform.system() == "Linux":
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        info["model"] = line.split(":", 1)[1].strip()
                        break
        except OSError:
            info["model"] = platform.processor() or "Unknown"
    else:
        info["model"] = platform.processor() or "Unknown"

    freq = psutil.cpu_freq()
    if freq:
        if freq.min:
            info["base_ghz"] = round(freq.min / 1000, 2)
        if freq.max:
            info["boost_ghz"] = round(freq.max / 1000, 2)

    return info


def _detect_memory() -> dict:
    vm = psutil.virtual_memory()
    ram_gb = round(vm.total / (1024 ** 3), 1)
    # Heuristic: Apple Silicon uses LPDDR5, x86 desktops typically DDR5/DDR4
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        mem_type = "LPDDR5"
    else:
        mem_type = "DDR5"
    return {"ram_gb": ram_gb, "type": mem_type}


def _detect_gpu() -> list[dict]:
    gpus: list[dict] = []

    # NVIDIA via pynvml
    try:
        import pynvml  # type: ignore
        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        for i in range(count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            gpus.append({
                "model": pynvml.nvmlDeviceGetName(handle),
                "vram_gb": round(mem.total / (1024 ** 3), 1),
            })
        pynvml.nvmlShutdown()
    except Exception:
        pass

    # AMD / Apple — no pynvml; detect via system_profiler on macOS
    if not gpus and platform.system() == "Darwin":
        try:
            raw = subprocess.run(
                ["system_profiler", "SPDisplaysDataType", "-json"],
                capture_output=True, text=True, timeout=10
            ).stdout
            displays = json.loads(raw).get("SPDisplaysDataType", [])
            for d in displays:
                name = d.get("spdisplays_vendor") or d.get("_name", "")
                vram_raw = d.get("spdisplays_vram") or d.get("spdisplays_vram_shared", "")
                vram_gb: float | None = None
                if vram_raw:
                    parts = vram_raw.split()
                    try:
                        val = float(parts[0])
                        unit = parts[1].upper() if len(parts) > 1 else "MB"
                        vram_gb = val / 1024 if unit == "MB" else val
                    except (ValueError, IndexError):
                        pass
                if name:
                    entry: dict = {"model": name}
                    if vram_gb is not None:
                        entry["vram_gb"] = round(vram_gb, 1)
                    gpus.append(entry)
        except Exception:
            pass

    return gpus


def _detect_topology(gpu: list[dict]) -> str:
    if not gpu:
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            return "UNIFIED"
        return "CPU_ONLY"
    if len(gpu) == 1:
        return "GPU_SINGLE"
    return "GPU_MULTI"
