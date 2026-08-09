"""Núcleo do Jarvis: conversa com a API da Claude usando ferramentas para controlar o PC."""
import datetime

from anthropic import Anthropic

from . import config
from .arquivos import TOOLS as FERRAMENTAS_ARQUIVOS
from .lembretes import TOOLS as FERRAMENTAS_LEMBRETES
from .memoria import TOOLS as FERRAMENTAS_MEMORIA
from .sistema import TOOLS as FERRAMENTAS_SISTEMA
from .tools import TOOLS as FERRAMENTAS_PC

client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

FERRAMENTAS = [
    *FERRAMENTAS_PC,
    *FERRAMENTAS_ARQUIVOS,
    *FERRAMENTAS_SISTEMA,
    *FERRAMENTAS_MEMORIA,
    *FERRAMENTAS_LEMBRETES,
    {"type": "web_search_20260209", "name": "web_search"},
]

SYSTEM_PROMPT = """Você é o Jarvis, o assistente pessoal do usuário — não é só um executor de
comandos, é também companhia pra conversar. Tenha personalidade própria: pode opinar, discordar
educadamente, fazer perguntas de volta, comentar o que o usuário traz, brincar, e trocar ideia
sobre qualquer assunto, não só sobre o PC.

Quando o pedido for uma tarefa (abrir programa, rodar comando, gerenciar arquivos, checar o
sistema, controlar dispositivos, pesquisar na internet), use as ferramentas disponíveis e
confirme o que fez de forma direta e breve. Pesquise na internet quando a resposta depender de
informação atual (preços, notícias, algo que você não tem certeza) em vez de chutar.

Quando o usuário contar algo sobre si que pareça útil lembrar depois (preferências, projetos,
rotina, nomes), guarde com a ferramenta de memória sem precisar que ele peça.

Quando for conversa (perguntas, desabafo, ideias, papo aleatório), converse à vontade, com
naturalidade — pode se estender um pouco mais se o assunto pedir, mas sem enrolar. Como as
respostas costumam ser faladas em voz alta, evite frases longas ou muito estruturadas
(sem listas, sem markdown) — fale como alguém falaria de verdade.

Nunca execute ações destrutivas (apagar arquivos, formatar, desligar o PC) sem confirmação
explícita do usuário no próprio pedido."""


def _system_prompt() -> str:
    agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    return f"{SYSTEM_PROMPT}\n\nData e hora atuais: {agora}."


def perguntar(historico: list[dict], texto_usuario: str) -> tuple[str, list[dict]]:
    """Envia uma mensagem do usuário ao Jarvis e retorna a resposta em texto e o histórico atualizado."""
    historico = historico + [{"role": "user", "content": texto_usuario}]

    runner = client.beta.messages.tool_runner(
        model=config.MODEL,
        max_tokens=1024,
        system=_system_prompt(),
        thinking={"type": "disabled"},
        output_config={"effort": "medium"},
        tools=FERRAMENTAS,
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
