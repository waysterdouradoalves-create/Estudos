"""Memória de longo prazo do Jarvis: preferências e informações sobre o usuário,
guardadas no banco de dados local (SQLite)."""
from anthropic import beta_tool

from . import banco


@beta_tool
def lembrar_disso(chave: str, valor: str) -> str:
    """Guarda uma informação sobre o usuário para lembrar em conversas futuras
    (preferências, nomes, rotinas, projetos, gostos, etc.). Use quando o usuário contar
    algo que pareça valer a pena lembrar depois.

    Args:
        chave: Um nome curto para essa informação, ex: "comida favorita", "projeto atual".
        valor: A informação em si.
    """
    with banco.conexao() as conexao:
        conexao.execute(
            "INSERT INTO memorias (chave, valor) VALUES (?, ?) "
            "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
            (chave, valor),
        )
    return f"Guardado: {chave} = {valor}"


@beta_tool
def o_que_voce_lembra() -> str:
    """Lista tudo que o Jarvis guardou sobre o usuário até agora."""
    with banco.conexao() as conexao:
        linhas = conexao.execute("SELECT chave, valor FROM memorias ORDER BY chave").fetchall()
    if not linhas:
        return "Ainda não tenho nada guardado sobre você."
    return "\n".join(f"{linha['chave']}: {linha['valor']}" for linha in linhas)


@beta_tool
def esquecer(chave: str) -> str:
    """Remove uma informação guardada sobre o usuário.

    Args:
        chave: O nome da informação a esquecer (o mesmo usado quando foi guardada).
    """
    with banco.conexao() as conexao:
        cursor = conexao.execute("DELETE FROM memorias WHERE chave = ?", (chave,))
        removeu = cursor.rowcount > 0
    if removeu:
        return f"Esqueci: {chave}"
    return f"Não tinha nada guardado com o nome '{chave}'."


TOOLS = [lembrar_disso, o_que_voce_lembra, esquecer]
