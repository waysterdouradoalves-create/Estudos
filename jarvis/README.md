# Jarvis

Assistente pessoal para Windows, com voz, chat de texto e automação do PC, usando a API da
Claude (Anthropic) como "cérebro".

## O que ele já faz

- **Conversa** por texto ou por voz (fala em português) — no modo voz, você **bate palma**
  para chamar o Jarvis, ele avisa "Pode falar" e escuta seu comando.
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

3. Instale as dependências principais (modo texto, automação do PC):

   ```bat
   pip install -r requirements.txt
   ```

   Se você também quer o **modo voz**, instale as dependências extras:

   ```bat
   pip install -r requirements-voz.txt
   ```

   > `pyaudio` costuma falhar ao compilar em versões muito novas do Python (ex: 3.14), porque
   > ainda não existe um pacote pré-compilado pra elas — o pip tenta compilar do zero e pede
   > o `portaudio.h`, que não vem instalado. Se isso acontecer, o jeito mais simples é criar
   > o ambiente virtual com o Python 3.12 só pra este projeto:
   >
   > ```bat
   > choco install python312 -y
   > py -3.12 -m venv .venv
   > .venv\Scripts\activate
   > pip install -r requirements.txt -r requirements-voz.txt
   > ```
   >
   > O modo texto funciona normalmente sem essas dependências de voz.

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

No modo voz, **bata palma** para chamar o Jarvis — ele responde "Pode falar" e aí é só falar o
comando. Se ele não estiver detectando suas palmas (ou estiver disparando sozinho com barulho
do ambiente), ajuste `JARVIS_LIMIAR_PALMA` no `.env` (menor = mais sensível).

Diga "sair" (texto) ou "sair"/"tchau" (voz) para encerrar.

### A palma não está sendo detectada?

Rode a ferramenta de calibração, que mostra o volume captado pelo microfone em tempo real:

```bat
python -m jarvis.calibrar
```

- Se o número **nunca se mexer** (fica sempre perto de 0), o problema não é sensibilidade —
  é o Windows bloqueando o acesso ao microfone, ou o microfone errado selecionado como padrão.
  Confira em **Configurações → Privacidade e segurança → Microfone** se "Permitir que os apps
  acessem seu microfone" está ativado, e em **Configurações → Sistema → Som → Entrada** se o
  dispositivo certo está selecionado.
- Se o número **se mexer**, anote o valor mais alto que aparece quando você bate palma, e
  coloque um pouco abaixo disso em `JARVIS_LIMIAR_PALMA` no `.env` (ex: se a palma bate uns
  8000, use 5000 ou 6000).

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

- Palavra de ativação por voz ("Jarvis, ...") além da palma.
- Rodar como serviço/inicializar com o Windows.
- Mais ferramentas: controle de volume, brilho, buscas na web, agenda, etc.
