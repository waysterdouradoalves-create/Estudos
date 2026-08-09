"""Configurações do Jarvis, carregadas do arquivo .env."""
import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("JARVIS_MODEL", "claude-sonnet-5")

# Detecção de palma no modo voz: o Jarvis mede o barulho do ambiente por um instante e
# considera "palma" qualquer som MULTIPLICADOR_PALMA vezes mais alto que isso (se ajusta
# sozinho a cada microfone, sem precisar de um número fixo). LIMIAR_PALMA_MINIMO evita
# falsos positivos em ambientes muito silenciosos, onde o ruído de fundo é quase zero.
MULTIPLICADOR_PALMA = float(os.getenv("JARVIS_MULTIPLICADOR_PALMA", "2"))
LIMIAR_PALMA_MINIMO = int(os.getenv("JARVIS_LIMIAR_PALMA_MINIMO", "300"))

# Opcional: integração com Home Assistant para controlar dispositivos (luzes, tomadas, etc.)
HOME_ASSISTANT_URL = os.getenv("HOME_ASSISTANT_URL", "").rstrip("/")
HOME_ASSISTANT_TOKEN = os.getenv("HOME_ASSISTANT_TOKEN", "")
