"""Memória de longo prazo do Jarvis: preferências e informações sobre o usuário,
guardadas entre uma conversa e outra num arquivo local."""
import json
import os

from anthropic import beta_tool

_ARQUIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dados", "memoria.json")


def _carregar() -> dict:
    if not os.path.exists(_ARQUIVO):
        return {}
    with open(_ARQUIVO, "r", encoding="utf-8") as f:
        return json.load(f)


def _salvar(dados: dict) -> None:
    os.makedirs(os.path.dirname(_ARQUIVO), exist_ok=True)
    with open(_ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


@beta_tool
def lembrar_disso(chave: str, valor: str) -> str:
    """Guarda uma informação sobre o usuário para lembrar em conversas futuras
    (preferências, nomes, rotinas, projetos, gostos, etc.). Use quando o usuário contar
    algo que pareça valer a pena lembrar depois.

    Args:
        chave: Um nome curto para essa informação, ex: "comida favorita", "projeto atual".
        valor: A informação em si.
    """
    dados = _carregar()
    dados[chave] = valor
    _salvar(dados)
    return f"Guardado: {chave} = {valor}"


@beta_tool
def o_que_voce_lembra() -> str:
    """Lista tudo que o Jarvis guardou sobre o usuário até agora."""
    dados = _carregar()
    if not dados:
        return "Ainda não tenho nada guardado sobre você."
    return "\n".join(f"{chave}: {valor}" for chave, valor in dados.items())


@beta_tool
def esquecer(chave: str) -> str:
    """Remove uma informação guardada sobre o usuário.

    Args:
        chave: O nome da informação a esquecer (o mesmo usado quando foi guardada).
    """
    dados = _carregar()
    if chave in dados:
        del dados[chave]
        _salvar(dados)
        return f"Esqueci: {chave}"
    return f"Não tinha nada guardado com o nome '{chave}'."


TOOLS = [lembrar_disso, o_que_voce_lembra, esquecer]
