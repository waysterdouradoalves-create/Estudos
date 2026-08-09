"""Rotinas: sequências de tarefas salvas que podem ser executadas de uma vez com um
comando curto — ex: "Jarvis, prepara meu PC pra trabalhar" abrindo vários programas.

Não guarda uma lista rígida de cliques/comandos: guarda uma descrição em texto dos
passos, e o próprio Claude decide como executá-los usando as ferramentas disponíveis
toda vez que a rotina é chamada (mais flexível que gravar uma macro fixa)."""
from anthropic import beta_tool

from . import banco


@beta_tool
def criar_rotina(nome: str, passos: str) -> str:
    """Salva uma rotina: uma sequência de tarefas que pode ser executada de uma vez só
    depois, com um comando curto.

    Args:
        nome: Nome curto pra chamar a rotina depois (ex: "trabalhar", "modo jogo").
        passos: Descrição do que fazer, em ordem (ex: "abrir o navegador, abrir o VS
            Code, abrir a calculadora").
    """
    with banco.conexao() as conexao:
        conexao.execute(
            "INSERT INTO rotinas (nome, passos) VALUES (?, ?) "
            "ON CONFLICT(nome) DO UPDATE SET passos = excluded.passos",
            (nome.lower(), passos),
        )
    return f"Rotina '{nome}' salva: {passos}"


@beta_tool
def listar_rotinas() -> str:
    """Lista todas as rotinas salvas."""
    with banco.conexao() as conexao:
        linhas = conexao.execute("SELECT nome, passos FROM rotinas ORDER BY nome").fetchall()
    if not linhas:
        return "Nenhuma rotina salva ainda."
    return "\n".join(f"{linha['nome']}: {linha['passos']}" for linha in linhas)


@beta_tool
def executar_rotina(nome: str) -> str:
    """Busca os passos de uma rotina salva. Depois de chamar esta ferramenta, execute
    cada passo descrito usando as outras ferramentas disponíveis (abrir_programa, etc.)
    até terminar a rotina inteira.

    Args:
        nome: Nome da rotina a executar.
    """
    with banco.conexao() as conexao:
        linha = conexao.execute("SELECT passos FROM rotinas WHERE nome = ?", (nome.lower(),)).fetchone()
        if not linha:
            nomes = conexao.execute("SELECT nome FROM rotinas").fetchall()
            disponiveis = ", ".join(item["nome"] for item in nomes) or "nenhuma"
            return f"Não encontrei uma rotina chamada '{nome}'. Rotinas disponíveis: {disponiveis}"
    return f"Passos da rotina '{nome}': {linha['passos']}. Execute cada passo agora usando as ferramentas disponíveis."


@beta_tool
def remover_rotina(nome: str) -> str:
    """Remove uma rotina salva.

    Args:
        nome: Nome da rotina a remover.
    """
    with banco.conexao() as conexao:
        cursor = conexao.execute("DELETE FROM rotinas WHERE nome = ?", (nome.lower(),))
        removeu = cursor.rowcount > 0
    if removeu:
        return f"Rotina '{nome}' removida."
    return f"Não encontrei uma rotina chamada '{nome}'."


TOOLS = [criar_rotina, listar_rotinas, executar_rotina, remover_rotina]
