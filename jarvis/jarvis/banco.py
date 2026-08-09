"""Banco de dados local do Jarvis (SQLite) — memórias, lembretes, rotinas e histórico."""
import os
import sqlite3
from contextlib import contextmanager

_ARQUIVO_BD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dados", "jarvis.db")


def _conectar() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(_ARQUIVO_BD), exist_ok=True)
    conexao = sqlite3.connect(_ARQUIVO_BD)
    conexao.row_factory = sqlite3.Row
    return conexao


def inicializar() -> None:
    """Cria as tabelas do banco de dados, se ainda não existirem."""
    with _conectar() as conexao:
        conexao.executescript(
            """
            CREATE TABLE IF NOT EXISTS memorias (
                chave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS lembretes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                texto TEXT NOT NULL,
                quando TEXT,
                avisado INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS rotinas (
                nome TEXT PRIMARY KEY,
                passos TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quando TEXT NOT NULL,
                comando TEXT,
                resposta TEXT
            );
            """
        )


@contextmanager
def conexao():
    """Context manager que devolve uma conexão já com o banco inicializado
    (commit automático ao sair do bloco, sem erro)."""
    inicializar()
    con = _conectar()
    try:
        yield con
        con.commit()
    finally:
        con.close()
