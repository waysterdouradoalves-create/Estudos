# Jarvis

Assistente pessoal para Windows, com voz, chat de texto e automação do PC, usando a API da
Claude (Anthropic) como "cérebro".

## O que ele já faz

- **Conversa de verdade** por texto ou por voz (fala em português) — não só executa comando,
  também opina, pergunta, brinca e troca ideia sobre qualquer assunto. No modo voz, você
  **bate palma** para chamar o Jarvis, ele toca um bipe e já escuta seu comando.
- **Abre e fecha programas** (`abrir_programa`, `fechar_programa`) e **executa comandos** no
  terminal do Windows.
- **Gerencia arquivos e pastas**: cria, lê, renomeia, move, copia, apaga e procura arquivos.
- **Pesquisa na internet** quando a resposta depender de informação atual.
- **Monitora o sistema**: uso de CPU, RAM, disco e GPU (placas NVIDIA).
- **Lembra de você**: guarda preferências e informações que você conta, e você pode perguntar
  "o que você lembra sobre mim" ou pedir pra esquecer algo.
- **Guarda lembretes** numa lista que você consulta quando quiser (não avisa sozinho na hora
  certa ainda).
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

No modo voz, **bata palma** para chamar o Jarvis — ele toca um bipe curto e já escuta o
comando. A detecção se ajusta sozinha ao barulho do ambiente (mede o ruído de fundo por um
instante antes de esperar a palma), então normalmente não precisa configurar nada.

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
- Se o número **se mexer mas a palma ainda não é detectada**, ajuste no `.env`:
  `JARVIS_MULTIPLICADOR_PALMA` (padrão 2) — diminua se as palmas continuarem ignoradas, ou
  aumente se ele disparar sozinho com barulho do ambiente.

## Rodando sem precisar abrir terminal

Dê **duplo clique** em `iniciar_jarvis.vbs` (na pasta `jarvis/`) — ele liga o Jarvis em modo
voz em segundo plano, sem nenhuma janela aparecendo. É só bater palma normalmente depois.

Para **encerrar**, abra o Gerenciador de Tarefas (Ctrl+Shift+Esc), procure por `pythonw.exe`
na lista de processos e clique em "Finalizar tarefa".

### Ligar automaticamente com o Windows

1. Aperta **Win+R**, digita `shell:startup` e aperta Enter (abre a pasta de Inicialização).
2. Copia o arquivo `iniciar_jarvis.vbs` pra dentro dessa pasta (pode ser cópia, ou um atalho
   dele — os dois funcionam).

Pronto — toda vez que você ligar o PC e entrar no Windows, o Jarvis já vai estar rodando em
segundo plano, esperando você bater palma.

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
- Lembretes que avisam sozinhos na hora certa (hoje é só uma lista consultável).
- Mais ferramentas: controle de volume, brilho, agenda, etc.
