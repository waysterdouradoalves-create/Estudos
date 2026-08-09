"""Lista de lembretes que o usuário pode guardar e consultar depois.

Isto NÃO avisa sozinho na hora certa (não há um alarme automático) — é uma lista
guardada num arquivo local que o Jarvis consulta quando perguntado."""
import json
import os

from anthropic import beta_tool

_ARQUIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dados", "lembretes.json")


def _carregar() -> list[str]:
    if not os.path.exists(_ARQUIVO):
        return []
    with open(_ARQUIVO, "r", encoding="utf-8") as f:
        return json.load(f)


def _salvar(lista: list[str]) -> None:
    os.makedirs(os.path.dirname(_ARQUIVO), exist_ok=True)
    with open(_ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)


@beta_tool
def criar_lembrete(texto: str) -> str:
    """Adiciona um lembrete à lista.

    Args:
        texto: O que deve ser lembrado, incluindo horário/data se for relevante
            (ex: "reunião às 15h", "comprar leite", "ligar pro dentista amanhã").
    """
    lembretes = _carregar()
    lembretes.append(texto)
    _salvar(lembretes)
    return f"Lembrete adicionado: {texto}"


@beta_tool
def listar_lembretes() -> str:
    """Lista todos os lembretes guardados."""
    lembretes = _carregar()
    if not lembretes:
        return "Você não tem nenhum lembrete guardado."
    return "\n".join(f"{i + 1}. {texto}" for i, texto in enumerate(lembretes))


@beta_tool
def remover_lembrete(numero: int) -> str:
    """Remove um lembrete da lista pelo número (use listar_lembretes primeiro para
    ver os números).

    Args:
        numero: O número do lembrete a remover, como aparece em listar_lembretes.
    """
    lembretes = _carregar()
    indice = numero - 1
    if 0 <= indice < len(lembretes):
        removido = lembretes.pop(indice)
        _salvar(lembretes)
        return f"Lembrete removido: {removido}"
    return "Não encontrei um lembrete com esse número."


TOOLS = [criar_lembrete, listar_lembretes, remover_lembrete]
