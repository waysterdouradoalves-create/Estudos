"""Entrada e saída de voz do Jarvis (reconhecimento de fala, texto-para-fala e palma)."""
import threading

import pyaudio
import speech_recognition as sr
import pyttsx3

try:
    import winsound
except ImportError:  # não estamos no Windows (ex: rodando testes em outro SO)
    winsound = None

try:
    import audioop
except ImportError:  # Python 3.13+ removeu o módulo audioop da biblioteca padrão
    import audioop_lts as audioop

from . import config

_reconhecedor = sr.Recognizer()
# Trava compartilhada entre ouvir() e falar(): evita que um lembrete fale por cima
# enquanto o usuário está sendo gravado (a voz vazaria pro microfone e atrapalharia o
# reconhecimento), e também que duas falas se sobreponham.
_trava_audio = threading.Lock()
# Permite ativar a escuta pelo painel web, sem precisar bater palma: o botão "Ativar
# agora" seta este evento, e esperar_palma() o observa a cada volta do laço.
evento_ativacao_manual = threading.Event()


def _medir_ruido_ambiente(fluxo, chunk: int = 1024, amostras: int = 20) -> float:
    """Mede o volume médio do ambiente por um instante, para calibrar a detecção de palma."""
    valores = [audioop.rms(fluxo.read(chunk, exception_on_overflow=False), 2) for _ in range(amostras)]
    return sum(valores) / len(valores)


def esperar_palma() -> None:
    """Fica escutando o microfone em segundo plano até detectar uma palma (som curto e alto).

    Se auto-calibra: mede o barulho do ambiente por um instante e considera "palma"
    qualquer pico bem acima disso, então funciona sem ajuste manual em qualquer microfone.
    """
    p = pyaudio.PyAudio()
    fluxo = p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)
    try:
        ruido_ambiente = _medir_ruido_ambiente(fluxo)
        limiar = max(ruido_ambiente * config.MULTIPLICADOR_PALMA, config.LIMIAR_PALMA_MINIMO)
        print(f"(ruído ambiente: {ruido_ambiente:.0f} | limiar da palma: {limiar:.0f})")
        while True:
            if evento_ativacao_manual.is_set():
                evento_ativacao_manual.clear()
                print("Ativado pelo painel web.")
                return
            dados = fluxo.read(1024, exception_on_overflow=False)
            volume = audioop.rms(dados, 2)
            print(f"\rnível: {volume:5d} / limiar: {limiar:.0f}".ljust(40), end="", flush=True)
            if volume > limiar:
                # Confirma que é um pico curto (palma) e não barulho contínuo (conversa,
                # TV, música): checa se o volume já caiu de novo logo em seguida.
                dados2 = fluxo.read(1024, exception_on_overflow=False)
                volume2 = audioop.rms(dados2, 2)
                if volume2 < limiar:
                    print("  <- PALMA DETECTADA")
                    return
                print("  (som alto contínuo, ignorando)")
    finally:
        fluxo.stop_stream()
        fluxo.close()
        p.terminate()


def bipe() -> None:
    """Toca um bipe curto (quase instantâneo) para avisar que o Jarvis já está ouvindo."""
    if winsound is not None:
        winsound.Beep(880, 120)


def ouvir() -> str | None:
    """Escuta o microfone e retorna o texto reconhecido (ou None se não entendeu)."""
    with _trava_audio:
        with sr.Microphone() as fonte:
            print("Ouvindo...")
            _reconhecedor.adjust_for_ambient_noise(fonte, duration=0.5)
            # Em ambientes muito silenciosos, a calibração automática deixa o
            # reconhecedor sensível demais e ele capta qualquer ruidinho (não a fala)
            # como "início da frase" — resultando em áudio vazio/curto que o Google não
            # consegue entender. Um piso mínimo evita isso.
            if _reconhecedor.energy_threshold < 300:
                _reconhecedor.energy_threshold = 300
            # Tempo de silêncio para considerar que a frase terminou (padrão é 0.8s, curto
            # demais — cortava no meio se a pessoa pausasse um instante pra pensar).
            _reconhecedor.pause_threshold = 1.5
            audio = _reconhecedor.listen(fonte, phrase_time_limit=15)

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
    """Fala o texto em voz alta.

    Cria um motor de voz novo a cada chamada: o pyttsx3/SAPI5 no Windows só funciona de
    forma confiável na mesma thread em que foi criado, e falar() pode ser chamada tanto
    da thread principal quanto da thread de verificação de lembretes.
    """
    with _trava_audio:
        print(f"Jarvis: {texto}")
        motor = pyttsx3.init()
        motor.setProperty("rate", 175)
        motor.say(texto)
        motor.runAndWait()
        motor.stop()
