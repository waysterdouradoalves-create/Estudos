"""Entrada e saída de voz do Jarvis (reconhecimento de fala e texto-para-fala)."""
import speech_recognition as sr
import pyttsx3

_reconhecedor = sr.Recognizer()
_motor_voz = pyttsx3.init()
_motor_voz.setProperty("rate", 175)


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
