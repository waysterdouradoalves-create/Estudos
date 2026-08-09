"""Monitoramento de recursos do sistema (CPU, RAM, disco, GPU)."""
import os
import subprocess

import psutil
from anthropic import beta_tool


def _consultar_gpu() -> str:
    """Tenta consultar uma GPU NVIDIA via nvidia-smi (retorna aviso se não disponível)."""
    try:
        resultado = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if resultado.returncode == 0 and resultado.stdout.strip():
            uso, mem_usada, mem_total, temp = [v.strip() for v in resultado.stdout.strip().split(",")]
            return f"GPU: {uso}% de uso, {mem_usada} MB de {mem_total} MB de memória, {temp}°C"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return "GPU: informação não disponível (funciona apenas com placas NVIDIA e o driver instalado)."


@beta_tool
def informar_sistema() -> str:
    """Informa o uso atual de CPU, memória RAM, disco e GPU (quando disponível)."""
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    disco = psutil.disk_usage("C:\\" if os.name == "nt" else "/")

    linhas = [
        f"CPU: {cpu:.0f}%",
        f"RAM: {ram.percent:.0f}% usada ({ram.used / 1e9:.1f} GB de {ram.total / 1e9:.1f} GB)",
        f"Disco: {disco.percent:.0f}% usado ({disco.used / 1e9:.1f} GB de {disco.total / 1e9:.1f} GB)",
        _consultar_gpu(),
    ]
    return "\n".join(linhas)


TOOLS = [informar_sistema]
