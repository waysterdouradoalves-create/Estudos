"""Ferramentas de gerenciamento de arquivos e pastas."""
import os
import shutil
from pathlib import Path

from anthropic import beta_tool


def _resolver_caminho(caminho: str) -> str:
    """Expande ~, variáveis de ambiente e atalhos como 'Área de Trabalho' e 'Documentos'."""
    caminho = os.path.expandvars(os.path.expanduser(caminho))
    partes = caminho.replace("\\", "/").split("/", 1)
    primeiro = partes[0].strip().lower()
    resto = partes[1] if len(partes) > 1 else ""

    if primeiro in ("área de trabalho", "area de trabalho", "desktop"):
        base = os.path.join(os.path.expanduser("~"), "Desktop")
        return os.path.join(base, resto) if resto else base
    if primeiro in ("documentos", "documents"):
        base = os.path.join(os.path.expanduser("~"), "Documents")
        return os.path.join(base, resto) if resto else base
    return caminho


@beta_tool
def criar_pasta(caminho: str) -> str:
    """Cria uma pasta (e as pastas pai necessárias, se não existirem).

    Args:
        caminho: Caminho da pasta a criar. Pode começar com "Área de Trabalho\\" ou
            "Documentos\\" para ser relativo a essas pastas, ou ser um caminho completo.
    """
    caminho = _resolver_caminho(caminho)
    try:
        os.makedirs(caminho, exist_ok=True)
        return f"Pasta criada: {caminho}"
    except Exception as erro:
        return f"Não consegui criar a pasta: {erro}"


@beta_tool
def criar_arquivo(caminho: str, conteudo: str = "") -> str:
    """Cria um arquivo de texto com o conteúdo informado (sobrescreve se já existir).

    Args:
        caminho: Caminho do arquivo a criar.
        conteudo: Texto a colocar dentro do arquivo (pode ser vazio).
    """
    caminho = _resolver_caminho(caminho)
    try:
        pasta = os.path.dirname(caminho)
        if pasta:
            os.makedirs(pasta, exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(conteudo)
        return f"Arquivo criado: {caminho}"
    except Exception as erro:
        return f"Não consegui criar o arquivo: {erro}"


@beta_tool
def ler_arquivo(caminho: str) -> str:
    """Lê e retorna o conteúdo de um arquivo de texto.

    Args:
        caminho: Caminho do arquivo a ler.
    """
    caminho = _resolver_caminho(caminho)
    try:
        with open(caminho, "r", encoding="utf-8", errors="replace") as f:
            conteudo = f.read()
        return conteudo[:4000]
    except Exception as erro:
        return f"Não consegui ler o arquivo: {erro}"


@beta_tool
def renomear_ou_mover(origem: str, destino: str) -> str:
    """Renomeia ou move um arquivo/pasta de origem para destino.

    Args:
        origem: Caminho atual do arquivo ou pasta.
        destino: Novo caminho/nome.
    """
    origem = _resolver_caminho(origem)
    destino = _resolver_caminho(destino)
    try:
        shutil.move(origem, destino)
        return f"Movido/renomeado de '{origem}' para '{destino}'."
    except Exception as erro:
        return f"Não consegui mover/renomear: {erro}"


@beta_tool
def copiar_item(origem: str, destino: str) -> str:
    """Copia um arquivo ou pasta de origem para destino.

    Args:
        origem: Caminho do arquivo/pasta a copiar.
        destino: Caminho de destino.
    """
    origem = _resolver_caminho(origem)
    destino = _resolver_caminho(destino)
    try:
        if os.path.isdir(origem):
            shutil.copytree(origem, destino)
        else:
            pasta = os.path.dirname(destino)
            if pasta:
                os.makedirs(pasta, exist_ok=True)
            shutil.copy2(origem, destino)
        return f"Copiado de '{origem}' para '{destino}'."
    except Exception as erro:
        return f"Não consegui copiar: {erro}"


@beta_tool
def apagar_item(caminho: str) -> str:
    """Apaga permanentemente um arquivo ou pasta. NUNCA chame esta ferramenta sem o
    usuário ter confirmado explicitamente que quer apagar — pergunte antes se não tiver
    certeza absoluta de que ele já confirmou.

    Args:
        caminho: Caminho do arquivo ou pasta a apagar.
    """
    caminho = _resolver_caminho(caminho)
    try:
        if os.path.isdir(caminho):
            shutil.rmtree(caminho)
        else:
            os.remove(caminho)
        return f"Apagado: {caminho}"
    except Exception as erro:
        return f"Não consegui apagar: {erro}"


@beta_tool
def procurar_arquivos(pasta: str, padrao: str = "*") -> str:
    """Procura arquivos dentro de uma pasta (e subpastas) por nome/padrão.

    Args:
        pasta: Pasta onde procurar (ex: "Área de Trabalho", "Documentos").
        padrao: Padrão de busca no estilo glob, ex: "*.pdf", "relatorio*", "*" para tudo.
    """
    pasta = _resolver_caminho(pasta)
    try:
        encontrados = list(Path(pasta).rglob(padrao))
        if not encontrados:
            return "Nenhum arquivo encontrado."
        return "\n".join(str(p) for p in encontrados[:30])
    except Exception as erro:
        return f"Não consegui procurar: {erro}"


TOOLS = [
    criar_pasta,
    criar_arquivo,
    ler_arquivo,
    renomear_ou_mover,
    copiar_item,
    apagar_item,
    procurar_arquivos,
]
