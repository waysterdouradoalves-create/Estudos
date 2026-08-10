"""Ferramentas que o Jarvis pode usar para controlar o PC e dispositivos inteligentes."""
import os
import subprocess

import psutil
import requests
from anthropic import beta_tool

from . import config


@beta_tool
def abrir_programa(nome: str) -> str:
    """Abre um programa ou aplicativo no Windows.

    Args:
        nome: Nome do programa (ex: "notepad", "calc", "chrome") ou caminho completo do executável.
    """
    try:
        os.startfile(nome)
        return f"Programa '{nome}' foi aberto."
    except OSError:
        try:
            subprocess.Popen(nome, shell=True)
            return f"Programa '{nome}' foi aberto."
        except Exception as erro:
            return f"Não consegui abrir '{nome}': {erro}"


@beta_tool
def executar_comando(comando: str) -> str:
    """Executa um comando no terminal do Windows (cmd) e retorna a saída.
    Não use para comandos destrutivos (apagar arquivos, formatar, desligar o PC) sem
    confirmação explícita do usuário no pedido dele.

    Args:
        comando: O comando a ser executado no cmd.
    """
    try:
        resultado = subprocess.run(
            comando, shell=True, capture_output=True, text=True, timeout=30
        )
        saida = (resultado.stdout or resultado.stderr or "(sem saída)").strip()
        return saida[:2000]
    except subprocess.TimeoutExpired:
        return "O comando demorou demais e foi cancelado."
    except Exception as erro:
        return f"Erro ao executar comando: {erro}"


@beta_tool
def listar_processos() -> str:
    """Lista os 15 processos que mais consomem memória no momento."""
    processos = sorted(
        psutil.process_iter(["pid", "name", "memory_info"]),
        key=lambda p: p.info["memory_info"].rss if p.info["memory_info"] else 0,
        reverse=True,
    )
    linhas = []
    for p in processos[:15]:
        mem_mb = (p.info["memory_info"].rss / 1024 / 1024) if p.info["memory_info"] else 0
        linhas.append(f"{p.info['pid']}: {p.info['name']} ({mem_mb:.0f} MB)")
    return "\n".join(linhas)


@beta_tool
def fechar_programa(nome: str) -> str:
    """Encerra todos os processos cujo nome contenha o texto informado.

    Args:
        nome: Nome (ou parte do nome) do processo a encerrar, ex: "notepad".
    """
    encerrados = 0
    for p in psutil.process_iter(["pid", "name"]):
        if nome.lower() in (p.info["name"] or "").lower():
            try:
                p.terminate()
                encerrados += 1
            except Exception:
                pass
    if encerrados:
        return f"{encerrados} processo(s) contendo '{nome}' foram encerrados."
    return f"Nenhum processo contendo '{nome}' foi encontrado."


@beta_tool
def controlar_dispositivo(entidade: str, acao: str) -> str:
    """Liga ou desliga um dispositivo inteligente (luz, tomada, etc.) via Home Assistant.
    Requer HOME_ASSISTANT_URL e HOME_ASSISTANT_TOKEN configurados no arquivo .env.

    Args:
        entidade: ID da entidade no Home Assistant, ex: "light.sala" ou "switch.tomada_quarto".
        acao: "ligar" ou "desligar".
    """
    if not config.HOME_ASSISTANT_URL or not config.HOME_ASSISTANT_TOKEN:
        return (
            "Integração com Home Assistant não configurada. "
            "Defina HOME_ASSISTANT_URL e HOME_ASSISTANT_TOKEN no arquivo .env."
        )

    dominio = entidade.split(".")[0]
    servico = "turn_on" if acao == "ligar" else "turn_off"
    url = f"{config.HOME_ASSISTANT_URL}/api/services/{dominio}/{servico}"
    headers = {
        "Authorization": f"Bearer {config.HOME_ASSISTANT_TOKEN}",
        "Content-Type": "application/json",
    }
    try:
        resposta = requests.post(url, headers=headers, json={"entity_id": entidade}, timeout=10)
        resposta.raise_for_status()
        return f"'{entidade}' foi {'ligado' if acao == 'ligar' else 'desligado'}."
    except Exception as erro:
        return f"Erro ao controlar '{entidade}': {erro}"


TOOLS = [abrir_programa, executar_comando, listar_processos, fechar_programa, controlar_dispositivo]
