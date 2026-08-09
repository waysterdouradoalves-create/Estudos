"""Entrada e saída de voz do Jarvis (reconhecimento de fala, texto-para-fala e palma)."""
import pyaudio
import speech_recognition as sr
import pyttsx3

try:
    import audioop
except ImportError:  # Python 3.13+ removeu o módulo audioop da biblioteca padrão
    import audioop_lts as audioop

from . import config

_reconhecedor = sr.Recognizer()
_motor_voz = pyttsx3.init()
_motor_voz.setProperty("rate", 175)


def esperar_palma() -> None:
    """Fica escutando o microfone em segundo plano até detectar uma palma (som curto e alto)."""
    p = pyaudio.PyAudio()
    fluxo = p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)
    try:
        while True:
            dados = fluxo.read(1024, exception_on_overflow=False)
            volume = audioop.rms(dados, 2)
            if volume > config.LIMIAR_PALMA:
                return
    finally:
        fluxo.stop_stream()
        fluxo.close()
        p.terminate()


def ouvir() -> str | None:
    """Escuta o microfone e retorna o texto reconhecido (ou None se não entendeu)."""
    with sr.Microphone() as fonte:
        print("Ouvindo...")
        _reconhecedor.adjust_for_ambient_noise(fonte, duration=0.5)
        audio = _reconhecedor.listen(fonte)

    try:
        texto = _reconhecedor.recognize_google(audio, language="pt-BR")
        print(f"Você disse: {texto}")
        return texto
    except sr.UnknownValueError:
        print("Não entendi o que você disse.")
        return None
    except sr.RequestError as erro:
        print(f"Erro no reconhecimento de voz: {erro}")
        return None


def falar(texto: str) -> None:
    """Fala o texto em voz alta."""
    print(f"Jarvis: {texto}")
    _motor_voz.say(texto)
    _motor_voz.runAndWait()
