"""Núcleo do Jarvis: conversa com a API da Claude usando ferramentas para controlar o PC."""
from anthropic import Anthropic

from . import config
from .tools import TOOLS

client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Você é o Jarvis, um assistente pessoal de voz e texto rodando no PC do usuário.
Seja direto e breve nas respostas, como convém a um assistente falado em voz alta.
Use as ferramentas disponíveis para abrir programas, executar comandos, listar/fechar processos
e controlar dispositivos inteligentes quando o usuário pedir.
Nunca execute comandos destrutivos (apagar arquivos, formatar, desligar o PC) sem confirmação
explícita do usuário no próprio pedido."""


def perguntar(historico: list[dict], texto_usuario: str) -> tuple[str, list[dict]]:
    """Envia uma mensagem do usuário ao Jarvis e retorna a resposta em texto e o histórico atualizado."""
    historico = historico + [{"role": "user", "content": texto_usuario}]

    runner = client.beta.messages.tool_runner(
        model=config.MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        thinking={"type": "disabled"},
        output_config={"effort": "low"},
        tools=TOOLS,
        messages=historico,
    )

    ultima_mensagem = None
    for mensagem in runner:
        ultima_mensagem = mensagem

    resposta_texto = "".join(
        bloco.text for bloco in ultima_mensagem.content if bloco.type == "text"
    ).strip()
    historico = historico + [{"role": "assistant", "content": ultima_mensagem.content}]
    return resposta_texto, historico
