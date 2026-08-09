"""Ponto de entrada do Jarvis.

Uso (a partir da pasta jarvis/):
    python -m jarvis.main --modo texto
    python -m jarvis.main --modo voz
"""
import argparse

from . import config
from .client import perguntar


def modo_texto() -> None:
    print("Jarvis (modo texto). Digite 'sair' para encerrar.\n")
    historico: list[dict] = []
    while True:
        texto_usuario = input("Você: ").strip()
        if texto_usuario.lower() in ("sair", "exit", "quit"):
            break
        if not texto_usuario:
            continue
        resposta, historico = perguntar(historico, texto_usuario)
        print(f"Jarvis: {resposta}\n")


def modo_voz() -> None:
    from . import voice

    print("Jarvis (modo voz). Bata palma para chamar. Pressione Ctrl+C para encerrar.\n")
    historico: list[dict] = []
    voice.falar("Jarvis ligado. Bata palma para me chamar.")
    while True:
        try:
            print("Aguardando palma...")
            voice.esperar_palma()
            voice.falar("Pode falar.")

            texto_usuario = voice.ouvir()
            if not texto_usuario:
                continue
            if texto_usuario.lower() in ("sair", "encerrar", "tchau"):
                voice.falar("Até mais!")
                break
            resposta, historico = perguntar(historico, texto_usuario)
            voice.falar(resposta)
        except KeyboardInterrupt:
            break


def main() -> None:
    parser = argparse.ArgumentParser(description="Jarvis - assistente pessoal")
    parser.add_argument("--modo", choices=["texto", "voz"], default="texto")
    args = parser.parse_args()

    if not config.ANTHROPIC_API_KEY:
        print("ERRO: defina ANTHROPIC_API_KEY no arquivo .env antes de continuar.")
        return

    if args.modo == "voz":
        modo_voz()
    else:
        modo_texto()


if __name__ == "__main__":
    main()
