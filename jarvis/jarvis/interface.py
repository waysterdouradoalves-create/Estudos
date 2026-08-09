"""Interface visual do Jarvis: janela mostrando status e uso do sistema em tempo real."""
import threading
import tkinter as tk
from datetime import datetime

import psutil

_COR_FUNDO = "#0a0e14"
_COR_PAINEL = "#111722"
_COR_TEXTO = "#8ab4f8"
_COR_TEXTO_CLARO = "#e8eef7"
_COR_VERDE = "#3ddc84"
_COR_AMARELO = "#f5c451"
_COR_BARRA_FUNDO = "#1c2530"

_CORES_STATUS = {
    "online": _COR_VERDE,
    "aguardando": _COR_VERDE,
    "ouvindo": _COR_AMARELO,
    "pensando": _COR_AMARELO,
    "falando": "#7c5cff",
}


class Estado:
    """Estado compartilhado entre a thread de voz e a interface (protegido por trava)."""

    def __init__(self) -> None:
        self._trava = threading.Lock()
        self.status = "ligando"
        self.ultimo_comando = "-"

    def definir_status(self, texto: str) -> None:
        with self._trava:
            self.status = texto

    def definir_ultimo_comando(self, texto: str) -> None:
        with self._trava:
            self.ultimo_comando = texto

    def ler(self) -> tuple[str, str]:
        with self._trava:
            return self.status, self.ultimo_comando


class Janela:
    """Janela principal do Jarvis (Tkinter). Deve rodar na thread principal."""

    def __init__(self, estado: Estado) -> None:
        self.estado = estado
        self.root = tk.Tk()
        self.root.title("JARVIS")
        self.root.configure(bg=_COR_FUNDO)
        self.root.geometry("360x480")
        self.root.resizable(False, False)

        tk.Label(
            self.root, text="JARVIS", font=("Consolas", 24, "bold"), fg=_COR_TEXTO, bg=_COR_FUNDO
        ).pack(pady=(20, 4))

        self.label_status = tk.Label(
            self.root, text="● LIGANDO", font=("Consolas", 12, "bold"), fg=_COR_VERDE, bg=_COR_FUNDO
        )
        self.label_status.pack()

        tk.Label(self.root, text="Sistema", font=("Consolas", 10), fg=_COR_TEXTO, bg=_COR_FUNDO).pack(
            pady=(20, 4)
        )
        self.canvas = tk.Canvas(self.root, width=320, height=90, bg=_COR_PAINEL, highlightthickness=0)
        self.canvas.pack()

        tk.Label(self.root, text="Último comando", font=("Consolas", 10), fg=_COR_TEXTO, bg=_COR_FUNDO).pack(
            pady=(20, 2)
        )
        self.label_comando = tk.Label(
            self.root,
            text="-",
            font=("Consolas", 10),
            fg=_COR_TEXTO_CLARO,
            bg=_COR_FUNDO,
            wraplength=320,
            justify="center",
        )
        self.label_comando.pack(padx=16)

        self.label_relogio = tk.Label(self.root, text="", font=("Consolas", 11), fg=_COR_TEXTO, bg=_COR_FUNDO)
        self.label_relogio.pack(pady=(24, 0), side="bottom")

        self._atualizar()

    def _barra(self, y: int, rotulo: str, fracao: float) -> None:
        largura, altura = 200, 18
        x = 20
        cor = _COR_VERDE if fracao < 0.7 else (_COR_AMARELO if fracao < 0.9 else "#ff5c5c")
        self.canvas.create_rectangle(x, y, x + largura, y + altura, fill=_COR_BARRA_FUNDO, outline="")
        self.canvas.create_rectangle(
            x, y, x + largura * max(0.0, min(fracao, 1.0)), y + altura, fill=cor, outline=""
        )
        self.canvas.create_text(
            x + largura + 10, y + altura / 2, text=f"{rotulo} {fracao * 100:.0f}%",
            fill=_COR_TEXTO_CLARO, font=("Consolas", 9), anchor="w",
        )

    def _atualizar(self) -> None:
        status, comando = self.estado.ler()
        cor = _CORES_STATUS.get(status, _COR_TEXTO)
        self.label_status.config(text=f"● {status.upper()}", fg=cor)
        self.label_comando.config(text=comando)
        self.label_relogio.config(text=datetime.now().strftime("%d/%m/%Y  %H:%M:%S"))

        self.canvas.delete("all")
        # cpu_percent(interval=None) não bloqueia — usa a leitura desde a última chamada
        cpu = psutil.cpu_percent(interval=None) / 100
        ram = psutil.virtual_memory().percent / 100
        self._barra(15, "CPU", cpu)
        self._barra(50, "RAM", ram)

        self.root.after(1000, self._atualizar)

    def iniciar(self) -> None:
        self.root.mainloop()
