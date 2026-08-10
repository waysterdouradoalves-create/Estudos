"""Lista de lembretes, guardada no banco de dados local (SQLite).

Lembretes com data/hora marcada são avisados automaticamente quando chega a hora
(veja jarvis.avisos); lembretes sem data ficam só na lista, pra consulta."""
from datetime import datetime

from anthropic import beta_tool

from . import banco


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
    with banco.conexao() as conexao:
        conexao.execute(
            "INSERT INTO lembretes (texto, quando, avisado) VALUES (?, ?, 0)",
            (texto, quando or None),
        )
    if quando:
        return f"Lembrete adicionado: {texto} (aviso em {quando})"
    return f"Lembrete adicionado: {texto}"


@beta_tool
def listar_lembretes() -> str:
    """Lista todos os lembretes pendentes."""
    with banco.conexao() as conexao:
        linhas = conexao.execute(
            "SELECT texto, quando FROM lembretes WHERE avisado = 0 ORDER BY id"
        ).fetchall()
    if not linhas:
        return "Você não tem nenhum lembrete guardado."
    resultado = []
    for i, linha in enumerate(linhas):
        if linha["quando"]:
            resultado.append(f"{i + 1}. {linha['texto']} — {linha['quando']}")
        else:
            resultado.append(f"{i + 1}. {linha['texto']}")
    return "\n".join(resultado)


@beta_tool
def remover_lembrete(numero: int) -> str:
    """Remove um lembrete da lista pelo número (use listar_lembretes primeiro para
    ver os números).

    Args:
        numero: O número do lembrete a remover, como aparece em listar_lembretes.
    """
    with banco.conexao() as conexao:
        linhas = conexao.execute(
            "SELECT id, texto FROM lembretes WHERE avisado = 0 ORDER BY id"
        ).fetchall()
        indice = numero - 1
        if 0 <= indice < len(linhas):
            alvo = linhas[indice]
            conexao.execute("DELETE FROM lembretes WHERE id = ?", (alvo["id"],))
            return f"Lembrete removido: {alvo['texto']}"
        return "Não encontrei um lembrete com esse número."


def verificar_vencidos() -> list[str]:
    """Retorna os textos dos lembretes cuja hora já chegou e marca como avisados.

    Não é uma ferramenta do Claude — usada internamente pelo verificador em segundo
    plano (jarvis.avisos)."""
    agora = datetime.now()
    vencidos = []
    with banco.conexao() as conexao:
        linhas = conexao.execute(
            "SELECT id, texto, quando FROM lembretes WHERE avisado = 0 AND quando IS NOT NULL"
        ).fetchall()
        for linha in linhas:
            try:
                quando = datetime.strptime(linha["quando"], "%Y-%m-%d %H:%M")
            except ValueError:
                continue
            if quando <= agora:
                vencidos.append(linha["texto"])
                conexao.execute("UPDATE lembretes SET avisado = 1 WHERE id = ?", (linha["id"],))
    return vencidos


TOOLS = [criar_lembrete, listar_lembretes, remover_lembrete]
