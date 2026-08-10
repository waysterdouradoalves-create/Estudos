"""Verificador em segundo plano de lembretes com horário marcado."""
import threading
import time
from typing import Callable

from . import lembretes

_INTERVALO_SEGUNDOS = 30


def iniciar(anunciar: Callable[[str], None]) -> None:
    """Inicia uma thread em segundo plano que checa lembretes vencidos periodicamente
    e chama anunciar(texto) para cada um encontrado."""

    def _loop() -> None:
        while True:
            for texto in lembretes.verificar_vencidos():
                anunciar(texto)
            time.sleep(_INTERVALO_SEGUNDOS)

    threading.Thread(target=_loop, daemon=True).start()
