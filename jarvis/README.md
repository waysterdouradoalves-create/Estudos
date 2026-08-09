# Jarvis

Assistente pessoal para Windows, com voz, chat de texto e automação do PC, usando a API da
Claude (Anthropic) como "cérebro".

## O que ele já faz

- **Conversa** por texto ou por voz (fala em português).
- **Abre e fecha programas** (`abrir_programa`, `fechar_programa`).
- **Executa comandos** no terminal do Windows (`executar_comando`).
- **Lista processos** em execução (`listar_processos`).
- **Controla dispositivos inteligentes** (luzes, tomadas, etc.) via
  [Home Assistant](https://www.home-assistant.io/) — opcional.

## Instalação (Windows)

1. Instale o [Python 3.11+](https://www.python.org/downloads/).
2. Abra um terminal na pasta `jarvis/` e crie um ambiente virtual:

   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Instale as dependências:

   ```bat
   pip install -r requirements.txt
   ```

   > Se `pyaudio` falhar ao instalar (comum no Windows), use:
   > `pip install pipwin && pipwin install pyaudio`

4. Copie `.env.example` para `.env` e preencha sua chave da API:

   ```bat
   copy .env.example .env
   ```

   Edite o `.env` e defina `ANTHROPIC_API_KEY` com sua chave (veja como gerar uma em
   https://console.anthropic.com/settings/keys).

## Uso

A partir da pasta `jarvis/`, com o ambiente virtual ativado:

```bat
python -m jarvis.main --modo texto
```

ou, para conversar por voz (precisa de microfone e internet, usa o reconhecimento de voz do
Google):

```bat
python -m jarvis.main --modo voz
```

Diga "sair" (texto) ou "sair"/"tchau" (voz) para encerrar.

## Controlando dispositivos inteligentes (opcional)

Se você tem um [Home Assistant](https://www.home-assistant.io/) rodando na sua rede, preencha
no `.env`:

```
HOME_ASSISTANT_URL=http://homeassistant.local:8123
HOME_ASSISTANT_TOKEN=<token de acesso de longa duração, gerado no seu perfil do Home Assistant>
```

Depois é só pedir, por exemplo: "Jarvis, liga a luz da sala" (a entidade precisa existir no
Home Assistant, ex: `light.sala`).

## Custo

O Jarvis usa `claude-sonnet-5` por padrão (bom equilíbrio custo/qualidade). Para uso leve
(dezenas de comandos por dia), o custo fica na faixa de alguns dólares por mês. Para reduzir
ainda mais, troque `JARVIS_MODEL` no `.env` para `claude-haiku-4-5` (mais rápido e barato, ótimo
para comandos simples).

## Próximos passos possíveis

- Palavra de ativação ("Jarvis, ...") para não precisar apertar nada.
- Rodar como serviço/inicializar com o Windows.
- Mais ferramentas: controle de volume, brilho, buscas na web, agenda, etc.
