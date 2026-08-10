"""Ferramenta de calibração: mostra o volume captado pelo microfone em tempo real,
para descobrir o valor ideal de JARVIS_LIMIAR_PALMA.

Uso: python -m jarvis.calibrar
"""
import pyaudio

try:
    import audioop
except ImportError:  # Python 3.13+ removeu o módulo audioop da biblioteca padrão
    import audioop_lts as audioop


def main() -> None:
    p = pyaudio.PyAudio()
    fluxo = p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)

    print("Fale, bata palma ou faça barulho perto do microfone. Ctrl+C para sair.\n")
    print("- Se o número NÃO se mexer nunca (fica sempre perto de 0), o problema é o")
    print("  microfone/permissão do Windows, não a sensibilidade.")
    print("- Se ele se mexer, anote o valor mais alto que aparece numa palma e use um")
    print("  pouco abaixo disso como JARVIS_LIMIAR_PALMA no .env (ex: palma bate 8000 ->")
    print("  use 5000 ou 6000).\n")

    try:
        while True:
            dados = fluxo.read(1024, exception_on_overflow=False)
            volume = audioop.rms(dados, 2)
            barra = "#" * min(volume // 200, 80)
            print(f"\rVolume: {volume:6d} {barra}".ljust(100), end="", flush=True)
    except KeyboardInterrupt:
        print("\nEncerrado.")
    finally:
        fluxo.stop_stream()
        fluxo.close()
        p.terminate()


if __name__ == "__main__":
    main()
