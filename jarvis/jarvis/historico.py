"""Histórico de comandos: cada pergunta/resposta trocada com o Jarvis é registrada no
banco de dados local, e pode ser consultada depois."""
from anthropic import beta_tool

from . import banco


def registrar(quando: str, comando: str, resposta: str) -> None:
    """Grava uma interação no histórico. Não é uma ferramenta do Claude — chamada
    internamente pelo núcleo (jarvis.client) a cada pergunta respondida."""
    with banco.conexao() as conexao:
        conexao.execute(
            "INSERT INTO logs (quando, comando, resposta) VALUES (?, ?, ?)",
            (quando, comando, resposta),
        )


@beta_tool
def consultar_historico(quantidade: int = 10) -> str:
    """Mostra os últimos comandos e respostas trocados com o Jarvis.

    Args:
        quantidade: Quantos itens do histórico mostrar (padrão 10).
    """
    with banco.conexao() as conexao:
        linhas = conexao.execute(
            "SELECT quando, comando, resposta FROM logs ORDER BY id DESC LIMIT ?",
            (quantidade,),
        ).fetchall()
    if not linhas:
        return "Ainda não há histórico registrado."
    itens = [f"[{linha['quando']}] Você: {linha['comando']} | Jarvis: {linha['resposta']}" for linha in reversed(linhas)]
    return "\n".join(itens)


TOOLS = [consultar_historico]
