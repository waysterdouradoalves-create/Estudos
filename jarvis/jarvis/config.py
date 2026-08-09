"""Configurações do Jarvis, carregadas do arquivo .env."""
import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("JARVIS_MODEL", "claude-sonnet-5")

# Sensibilidade da detecção de palma no modo voz (menor número = mais sensível).
# Se o Jarvis não detectar suas palmas, diminua esse valor; se ele disparar sozinho
# com barulhos do ambiente, aumente.
LIMIAR_PALMA = int(os.getenv("JARVIS_LIMIAR_PALMA", "4000"))

# Opcional: integração com Home Assistant para controlar dispositivos (luzes, tomadas, etc.)
HOME_ASSISTANT_URL = os.getenv("HOME_ASSISTANT_URL", "").rstrip("/")
HOME_ASSISTANT_TOKEN = os.getenv("HOME_ASSISTANT_TOKEN", "")
