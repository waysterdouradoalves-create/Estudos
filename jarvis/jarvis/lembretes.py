"""Lista de lembretes que o usuário pode guardar e consultar depois.

Lembretes com data/hora marcada são avisados automaticamente quando chega a hora
(veja jarvis.avisos); lembretes sem data ficam só na lista, pra consulta."""
import json
import os
from datetime import datetime

from anthropic import beta_tool

_ARQUIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dados", "lembretes.json")


def _carregar() -> list[dict]:
    if not os.path.exists(_ARQUIVO):
        return []
    with open(_ARQUIVO, "r", encoding="utf-8") as f:
        return json.load(f)


def _salvar(lista: list[dict]) -> None:
    os.makedirs(os.path.dirname(_ARQUIVO), exist_ok=True)
    with open(_ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)


def _pendentes(lista: list[dict]) -> list[dict]:
    return [item for item in lista if not item.get("avisado")]


@beta_tool
def criar_lembrete(texto: str, quando: str = "") -> str:
    """Adiciona um lembrete à lista. Se tiver data/hora, o Jarvis avisa sozinho na hora
    certa (falando em voz alta, no modo voz).

    Args:
        texto: O que deve ser lembrado (ex: "reunião com o time", "comprar leite").
        quando: Data e hora do lembrete, no formato "AAAA-MM-DD HH:MM" (24h). Calcule a
            partir da data/hora atual informada no contexto da conversa. Deixe vazio se
            o usuário não especificou horário — nesse caso é só um item de lista, sem
            aviso automático.
    """
    lembretes = _carregar()
    lembretes.append({"texto": texto, "quando": quando or None, "avisado": False})
    _salvar(lembretes)
    if quando:
        return f"Lembrete adicionado: {texto} (aviso em {quando})"
    return f"Lembrete adicionado: {texto}"


@beta_tool
def listar_lembretes() -> str:
    """Lista todos os lembretes pendentes."""
    lembretes = _pendentes(_carregar())
    if not lembretes:
        return "Você não tem nenhum lembrete guardado."
    linhas = []
    for i, item in enumerate(lembretes):
        if item.get("quando"):
            linhas.append(f"{i + 1}. {item['texto']} — {item['quando']}")
        else:
            linhas.append(f"{i + 1}. {item['texto']}")
    return "\n".join(linhas)


@beta_tool
def remover_lembrete(numero: int) -> str:
    """Remove um lembrete da lista pelo número (use listar_lembretes primeiro para
    ver os números).

    Args:
        numero: O número do lembrete a remover, como aparece em listar_lembretes.
    """
    todos = _carregar()
    pendentes = _pendentes(todos)
    indice = numero - 1
    if 0 <= indice < len(pendentes):
        alvo = pendentes[indice]
        todos.remove(alvo)
        _salvar(todos)
        return f"Lembrete removido: {alvo['texto']}"
    return "Não encontrei um lembrete com esse número."


def verificar_vencidos() -> list[str]:
    """Retorna os textos dos lembretes cuja hora já chegou e marca como avisados.

    Não é uma ferramenta do Claude — usada internamente pelo verificador em segundo
    plano (jarvis.avisos)."""
    lembretes = _carregar()
    agora = datetime.now()
    vencidos = []
    mudou = False
    for item in lembretes:
        if item.get("avisado") or not item.get("quando"):
            continue
        try:
            quando = datetime.strptime(item["quando"], "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        if quando <= agora:
            vencidos.append(item["texto"])
            item["avisado"] = True
            mudou = True
    if mudou:
        _salvar(lembretes)
    return vencidos


TOOLS = [criar_lembrete, listar_lembretes, remover_lembrete]
