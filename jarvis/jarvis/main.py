"""Ponto de entrada do Jarvis.

Uso (a partir da pasta jarvis/):
    python -m jarvis.main --modo texto
    python -m jarvis.main --modo voz
    python -m jarvis.main --modo voz --sem-interface
    python -m jarvis.main --modo voz --sem-painel
"""
import argparse
import threading

from . import avisos, config
from .client import perguntar


def _anunciar_no_texto(texto: str) -> None:
    print(f"\n🔔 Lembrete: {texto}")


def modo_texto() -> None:
    print("Jarvis (modo texto). Digite 'sair' para encerrar.\n")
    historico: list[dict] = []
    avisos.iniciar(_anunciar_no_texto)
    while True:
        texto_usuario = input("Você: ").strip()
        if texto_usuario.lower() in ("sair", "exit", "quit"):
            break
        if not texto_usuario:
            continue
        resposta, historico = perguntar(historico, texto_usuario)
        print(f"Jarvis: {resposta}\n")


def _saudacao() -> str:
    if config.NOME_USUARIO:
        return f"Olá, senhor {config.NOME_USUARIO}! Em que vamos trabalhar hoje?"
    return "Olá! Em que posso ajudar?"


def modo_voz(estado=None) -> None:
    from . import voice

    print("Jarvis (modo voz). Bata palma para chamar. Pressione Ctrl+C para encerrar.\n")
    historico: list[dict] = []
    avisos.iniciar(lambda texto: voice.falar(f"Lembrete: {texto}"))
    primeira_palma = True

    if estado:
        estado.definir_status("online")

    while True:
        try:
            print("Aguardando palma...")
            if estado:
                estado.definir_status("aguardando")
            voice.esperar_palma()

            if primeira_palma:
                primeira_palma = False
                if estado:
                    estado.definir_status("falando")
                voice.falar(_saudacao())
            else:
                voice.bipe()

            if estado:
                estado.definir_status("ouvindo")
            texto_usuario = voice.ouvir()
            if not texto_usuario:
                if estado:
                    estado.definir_status("aguardando")
                continue
            if estado:
                estado.definir_ultimo_comando(texto_usuario)

            if texto_usuario.lower() in ("sair", "encerrar", "tchau"):
                voice.falar("Até mais!")
                break

            if estado:
                estado.definir_status("pensando")
            resposta, historico = perguntar(historico, texto_usuario)

            if estado:
                estado.definir_status("falando")
            voice.falar(resposta)
        except KeyboardInterrupt:
            break


def main() -> None:
    parser = argparse.ArgumentParser(description="Jarvis - assistente pessoal")
    parser.add_argument("--modo", choices=["texto", "voz"], default="texto")
    parser.add_argument(
        "--sem-interface", action="store_true", help="No modo voz, não abre a janela visual"
    )
    parser.add_argument(
        "--sem-painel", action="store_true", help="No modo voz, não abre o painel web de controle"
    )
    args = parser.parse_args()

    if not config.ANTHROPIC_API_KEY:
        print("ERRO: defina ANTHROPIC_API_KEY no arquivo .env antes de continuar.")
        return

    if args.modo == "voz":
        estado = None
        if not args.sem_interface:
            from . import interface

            estado = interface.Estado()

        if not args.sem_painel:
            from . import painel

            painel.iniciar(estado)
            print(f"Painel de controle: http://localhost:{painel.PORTA}")

        if estado:
            threading.Thread(target=modo_voz, args=(estado,), daemon=True).start()
            interface.Janela(estado).iniciar()
        else:
            modo_voz()
    else:
        modo_texto()


if __name__ == "__main__":
    main()
