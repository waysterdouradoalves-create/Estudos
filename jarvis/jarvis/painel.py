"""Painel de controle do Jarvis: site local (Flask) com dashboard, chat, memória,
lembretes, rotinas e histórico — tudo pelo navegador, sem precisar de terminal."""
import threading
import webbrowser
from datetime import datetime

from flask import Flask, jsonify, render_template_string, request

from . import banco

PORTA = 5000

_PAGINA = r"""
<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>JARVIS · Painel de Controle</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; min-height: 100vh; display: flex;
    background: #0b0f17; color: #e6ebf5;
    font-family: 'Segoe UI', Inter, system-ui, sans-serif;
  }
  .mono { font-family: 'Consolas', 'Courier New', monospace; }

  /* ---------- Sidebar ---------- */
  #sidebar {
    width: 220px; flex-shrink: 0; background: #0f1420; border-right: 1px solid #1c2432;
    padding: 22px 0; display: flex; flex-direction: column; height: 100vh; position: sticky; top: 0;
  }
  #sidebar .logo {
    font-family: 'Consolas', monospace; font-size: 22px; font-weight: 700; letter-spacing: 5px;
    color: #6ea8fe; padding: 0 24px 22px; border-bottom: 1px solid #1c2432; margin-bottom: 12px;
  }
  #sidebar nav { display: flex; flex-direction: column; gap: 2px; padding: 0 12px; flex: 1; }
  #sidebar .item {
    display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 8px;
    color: #9aa5b8; cursor: pointer; font-size: 14px; user-select: none; transition: background .15s, color .15s;
  }
  #sidebar .item:hover { background: #161d2b; color: #e6ebf5; }
  #sidebar .item.ativo { background: #17233b; color: #6ea8fe; font-weight: 600; }
  #sidebar .rodape { padding: 12px 24px 0; font-size: 11px; color: #566073; border-top: 1px solid #1c2432; margin-top: 12px; }

  /* ---------- Conteúdo ---------- */
  #conteudo { flex: 1; padding: 28px 34px; max-width: 1100px; }
  .secao { display: none; }
  .secao.ativa { display: block; animation: aparecer .25s ease; }
  @keyframes aparecer { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }

  h1.titulo { font-size: 22px; margin: 0 0 22px; font-weight: 700; }

  /* ---------- Status hero ---------- */
  .status-hero {
    display: flex; align-items: center; gap: 14px; background: #10151f;
    border: 1px solid #1c2432; border-radius: 14px; padding: 20px 24px; margin-bottom: 22px;
  }
  .ponto { width: 14px; height: 14px; border-radius: 50%; flex-shrink: 0; background: #6ea8fe; }
  .ponto.pulsar { animation: pulsar 1.6s ease-in-out infinite; }
  @keyframes pulsar { 0%,100% { box-shadow: 0 0 0 0 currentColor; opacity: 1; } 50% { box-shadow: 0 0 0 8px transparent; opacity: .7; } }
  .status-hero .texto { font-size: 17px; font-weight: 700; }
  .status-hero .sub { font-size: 12px; color: #8891a3; margin-top: 2px; }
  .cor-online, .cor-aguardando { color: #35d68a; } .cor-online .ponto, .cor-aguardando .ponto { background: #35d68a; }
  .cor-ouvindo, .cor-pensando { color: #f5c451; } .cor-ouvindo .ponto, .cor-pensando .ponto { background: #f5c451; }
  .cor-falando { color: #a78bfa; } .cor-falando .ponto { background: #a78bfa; }
  .cor-ligando { color: #6ea8fe; }

  /* ---------- Cards / grade ---------- */
  .grade { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 22px; }
  .cartao {
    background: #10151f; border: 1px solid #1c2432; border-radius: 12px; padding: 18px;
  }
  .cartao h2 {
    font-size: 11px; color: #6ea8fe; text-transform: uppercase; letter-spacing: 1.5px;
    margin: 0 0 14px; font-weight: 700;
  }
  .estat-num { font-size: 26px; font-weight: 700; }
  .estat-legenda { font-size: 12px; color: #8891a3; margin-top: 2px; }

  .barra-fundo { background: #1c2530; border-radius: 6px; height: 12px; overflow: hidden; margin-bottom: 12px; }
  .barra { height: 100%; background: #35d68a; transition: width .5s ease; }
  .barra-linha { display: flex; justify-content: space-between; font-size: 12px; color: #b7c0d1; margin-bottom: 4px; }

  /* ---------- Listas ---------- */
  .lista { list-style: none; padding: 0; margin: 0; }
  .lista li {
    display: flex; justify-content: space-between; align-items: center; gap: 10px;
    padding: 10px 0; border-bottom: 1px solid #1c2432; font-size: 13px;
  }
  .lista li:last-child { border-bottom: none; }
  .lista .vazio { color: #566073; font-style: italic; }
  .item-texto { flex: 1; }
  .item-sub { font-size: 11px; color: #8891a3; margin-top: 2px; }

  /* ---------- Formulários / botões ---------- */
  form.form-linha { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 18px; }
  input[type=text], input[type=datetime-local], textarea {
    background: #161d2b; border: 1px solid #2a3346; color: #e6ebf5;
    padding: 10px 12px; border-radius: 8px; font-family: inherit; font-size: 13px;
  }
  input[type=text] { flex: 1; min-width: 160px; }
  textarea { width: 100%; min-height: 60px; resize: vertical; }
  button {
    background: #6ea8fe; color: #0b0f17; border: none; border-radius: 8px;
    padding: 10px 18px; font-weight: 700; cursor: pointer; font-family: inherit; font-size: 13px;
  }
  button:hover { filter: brightness(1.08); }
  button:disabled { opacity: 0.5; cursor: default; }
  button.secundario { background: #1c2530; color: #e6ebf5; }
  button.perigo { background: #2a1620; color: #ff7a90; padding: 6px 10px; font-size: 12px; }
  button.pequeno { padding: 6px 10px; font-size: 12px; }

  /* ---------- Chat ---------- */
  #chat-log { max-height: 420px; overflow-y: auto; margin-bottom: 14px; padding-right: 4px; }
  #chat-log .bolha { margin: 8px 0; font-size: 13px; line-height: 1.5; padding: 10px 14px; border-radius: 10px; max-width: 80%; }
  #chat-log .voce { background: #17233b; color: #cfe0ff; margin-left: auto; }
  #chat-log .jarvis { background: #161d2b; color: #e6ebf5; }
  #chat-log .rotulo { font-size: 10px; text-transform: uppercase; letter-spacing: 1px; opacity: .6; display: block; margin-bottom: 3px; }

  /* ---------- Responsivo ---------- */
  @media (max-width: 760px) {
    body { flex-direction: column; }
    #sidebar { width: 100%; height: auto; position: relative; flex-direction: row; overflow-x: auto; padding: 12px; }
    #sidebar .logo { display: none; }
    #sidebar nav { flex-direction: row; padding: 0; }
    #sidebar .rodape { display: none; }
    #conteudo { padding: 18px; }
  }
</style>
</head>
<body>

<div id="sidebar">
  <div class="logo">JARVIS</div>
  <nav id="nav">
    <div class="item ativo" data-secao="dashboard">📊 Dashboard</div>
    <div class="item" data-secao="chat">💬 Chat</div>
    <div class="item" data-secao="memoria">🧠 Memória</div>
    <div class="item" data-secao="lembretes">⏰ Lembretes</div>
    <div class="item" data-secao="rotinas">🔁 Rotinas</div>
    <div class="item" data-secao="historico">📜 Histórico</div>
  </nav>
  <div class="rodape mono">painel local · localhost:5000</div>
</div>

<div id="conteudo">

  <!-- Dashboard -->
  <section class="secao ativa" id="secao-dashboard">
    <h1 class="titulo">Dashboard</h1>
    <div class="status-hero cor-ligando" id="status-hero">
      <div class="ponto pulsar" id="status-ponto"></div>
      <div>
        <div class="texto" id="status-texto">Carregando...</div>
        <div class="sub">Modelo: claude-sonnet-5</div>
      </div>
    </div>
    <div class="grade">
      <div class="cartao">
        <h2>CPU</h2>
        <div class="barra-linha"><span>Uso</span><span id="cpu-txt">-</span></div>
        <div class="barra-fundo"><div class="barra" id="cpu-barra" style="width:0%"></div></div>
      </div>
      <div class="cartao">
        <h2>Memória RAM</h2>
        <div class="barra-linha"><span>Uso</span><span id="ram-txt">-</span></div>
        <div class="barra-fundo"><div class="barra" id="ram-barra" style="width:0%;background:#a78bfa"></div></div>
      </div>
      <div class="cartao">
        <h2>Comandos hoje</h2>
        <div class="estat-num" id="stat-comandos">-</div>
        <div class="estat-legenda">perguntas respondidas</div>
      </div>
      <div class="cartao">
        <h2>Lembretes</h2>
        <div class="estat-num" id="stat-lembretes">-</div>
        <div class="estat-legenda">pendentes</div>
      </div>
      <div class="cartao">
        <h2>Rotinas</h2>
        <div class="estat-num" id="stat-rotinas">-</div>
        <div class="estat-legenda">salvas</div>
      </div>
    </div>
  </section>

  <!-- Chat -->
  <section class="secao" id="secao-chat">
    <h1 class="titulo">Conversar com o Jarvis</h1>
    <div class="cartao">
      <div id="chat-log"></div>
      <form class="form-linha" id="chat-form" style="margin-bottom:0">
        <input type="text" id="chat-texto" placeholder="Digite algo pro Jarvis..." autocomplete="off">
        <button type="submit" id="chat-botao">Enviar</button>
      </form>
    </div>
  </section>

  <!-- Memória -->
  <section class="secao" id="secao-memoria">
    <h1 class="titulo">Memória</h1>
    <div class="cartao" style="margin-bottom:18px">
      <h2>Adicionar</h2>
      <form class="form-linha" id="memoria-form">
        <input type="text" id="memoria-chave" placeholder="Nome (ex: comida favorita)">
        <input type="text" id="memoria-valor" placeholder="Valor (ex: pizza)">
        <button type="submit">Guardar</button>
      </form>
    </div>
    <div class="cartao">
      <h2>O que o Jarvis lembra</h2>
      <ul class="lista" id="memoria-lista"><li class="vazio">Carregando...</li></ul>
    </div>
  </section>

  <!-- Lembretes -->
  <section class="secao" id="secao-lembretes">
    <h1 class="titulo">Lembretes</h1>
    <div class="cartao" style="margin-bottom:18px">
      <h2>Novo lembrete</h2>
      <form class="form-linha" id="lembrete-form">
        <input type="text" id="lembrete-texto" placeholder="O que lembrar?" style="flex:2">
        <input type="datetime-local" id="lembrete-quando">
        <button type="submit">Adicionar</button>
      </form>
    </div>
    <div class="cartao">
      <h2>Pendentes</h2>
      <ul class="lista" id="lembretes-lista"><li class="vazio">Carregando...</li></ul>
    </div>
  </section>

  <!-- Rotinas -->
  <section class="secao" id="secao-rotinas">
    <h1 class="titulo">Rotinas</h1>
    <div class="cartao" style="margin-bottom:18px">
      <h2>Nova rotina</h2>
      <form id="rotina-form">
        <input type="text" id="rotina-nome" placeholder="Nome (ex: trabalhar)" style="margin-bottom:8px;width:100%">
        <textarea id="rotina-passos" placeholder="Passos (ex: abrir o navegador, abrir o VS Code)"></textarea>
        <div style="margin-top:10px"><button type="submit">Salvar rotina</button></div>
      </form>
    </div>
    <div class="cartao">
      <h2>Rotinas salvas</h2>
      <ul class="lista" id="rotinas-lista"><li class="vazio">Carregando...</li></ul>
    </div>
  </section>

  <!-- Histórico -->
  <section class="secao" id="secao-historico">
    <h1 class="titulo">Histórico de comandos</h1>
    <div class="cartao">
      <ul class="lista" id="historico-lista"><li class="vazio">Carregando...</li></ul>
    </div>
  </section>

</div>

<script>
// ---------- Navegação ----------
document.querySelectorAll('#nav .item').forEach(item => {
  item.addEventListener('click', () => {
    document.querySelectorAll('#nav .item').forEach(i => i.classList.remove('ativo'));
    document.querySelectorAll('.secao').forEach(s => s.classList.remove('ativa'));
    item.classList.add('ativo');
    document.getElementById('secao-' + item.dataset.secao).classList.add('ativa');
  });
});

// ---------- Status / Dashboard ----------
async function atualizarStatus() {
  try {
    const r = await fetch('/api/status');
    const d = await r.json();
    const hero = document.getElementById('status-hero');
    hero.className = 'status-hero cor-' + d.status;
    document.getElementById('status-texto').textContent = d.status.toUpperCase().replace('_', ' ');
    document.getElementById('cpu-txt').textContent = d.cpu.toFixed(0) + '%';
    document.getElementById('cpu-barra').style.width = d.cpu + '%';
    document.getElementById('ram-txt').textContent = d.ram.toFixed(0) + '%';
    document.getElementById('ram-barra').style.width = d.ram + '%';
    document.getElementById('stat-comandos').textContent = d.comandos_hoje;
    document.getElementById('stat-lembretes').textContent = d.lembretes_pendentes;
    document.getElementById('stat-rotinas').textContent = d.total_rotinas;
  } catch (e) { /* servidor ainda subindo */ }
}

// ---------- Memória ----------
async function atualizarMemoria() {
  const r = await fetch('/api/memorias');
  const d = await r.json();
  const ul = document.getElementById('memoria-lista');
  ul.innerHTML = d.length ? d.map(m => `
    <li><span class="item-texto"><b>${m.chave}</b>: ${m.valor}</span>
    <button class="perigo" onclick="removerMemoria('${m.chave.replace(/'/g, "\\'")}')">Esquecer</button></li>
  `).join('') : '<li class="vazio">Nada guardado ainda.</li>';
}
async function removerMemoria(chave) {
  await fetch('/api/memorias/' + encodeURIComponent(chave), { method: 'DELETE' });
  atualizarMemoria();
}
document.getElementById('memoria-form').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const chave = document.getElementById('memoria-chave').value.trim();
  const valor = document.getElementById('memoria-valor').value.trim();
  if (!chave || !valor) return;
  await fetch('/api/memorias', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({chave, valor}),
  });
  document.getElementById('memoria-chave').value = '';
  document.getElementById('memoria-valor').value = '';
  atualizarMemoria();
});

// ---------- Lembretes ----------
async function atualizarLembretes() {
  const r = await fetch('/api/lembretes');
  const d = await r.json();
  const ul = document.getElementById('lembretes-lista');
  ul.innerHTML = d.length ? d.map(l => `
    <li><span class="item-texto">${l.texto}${l.quando ? `<div class="item-sub">⏰ ${l.quando}</div>` : ''}</span>
    <button class="perigo" onclick="removerLembrete(${l.id})">Remover</button></li>
  `).join('') : '<li class="vazio">Nenhum lembrete.</li>';
}
async function removerLembrete(id) {
  await fetch('/api/lembretes/' + id, { method: 'DELETE' });
  atualizarLembretes();
  atualizarStatus();
}
document.getElementById('lembrete-form').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const texto = document.getElementById('lembrete-texto').value.trim();
  const quandoCampo = document.getElementById('lembrete-quando').value;
  const quando = quandoCampo ? quandoCampo.replace('T', ' ') : '';
  if (!texto) return;
  await fetch('/api/lembretes', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({texto, quando}),
  });
  document.getElementById('lembrete-texto').value = '';
  document.getElementById('lembrete-quando').value = '';
  atualizarLembretes();
  atualizarStatus();
});

// ---------- Rotinas ----------
async function atualizarRotinas() {
  const r = await fetch('/api/rotinas');
  const d = await r.json();
  const ul = document.getElementById('rotinas-lista');
  ul.innerHTML = d.length ? d.map(rt => `
    <li><span class="item-texto"><b>${rt.nome}</b><div class="item-sub">${rt.passos}</div></span>
    <span style="display:flex;gap:6px">
      <button class="secundario pequeno" onclick="executarRotina('${rt.nome.replace(/'/g, "\\'")}')">Executar</button>
      <button class="perigo" onclick="removerRotina('${rt.nome.replace(/'/g, "\\'")}')">Remover</button>
    </span></li>
  `).join('') : '<li class="vazio">Nenhuma rotina salva.</li>';
}
async function removerRotina(nome) {
  await fetch('/api/rotinas/' + encodeURIComponent(nome), { method: 'DELETE' });
  atualizarRotinas();
  atualizarStatus();
}
async function executarRotina(nome) {
  document.querySelector('[data-secao="chat"]').click();
  const log = document.getElementById('chat-log');
  log.innerHTML += `<div class="bolha jarvis"><span class="rotulo">Jarvis</span>Executando a rotina "${nome}"...</div>`;
  log.scrollTop = log.scrollHeight;
  const r = await fetch('/api/rotinas/' + encodeURIComponent(nome) + '/executar', { method: 'POST' });
  const d = await r.json();
  log.innerHTML += `<div class="bolha jarvis"><span class="rotulo">Jarvis</span>${d.resposta}</div>`;
  log.scrollTop = log.scrollHeight;
}
document.getElementById('rotina-form').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const nome = document.getElementById('rotina-nome').value.trim();
  const passos = document.getElementById('rotina-passos').value.trim();
  if (!nome || !passos) return;
  await fetch('/api/rotinas', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({nome, passos}),
  });
  document.getElementById('rotina-nome').value = '';
  document.getElementById('rotina-passos').value = '';
  atualizarRotinas();
  atualizarStatus();
});

// ---------- Histórico ----------
async function atualizarHistorico() {
  const r = await fetch('/api/historico');
  const d = await r.json();
  const ul = document.getElementById('historico-lista');
  ul.innerHTML = d.length ? d.map(h => `
    <li><span class="item-texto"><div class="item-sub">${h.quando}</div>
    <b>Você:</b> ${h.comando}<br><b>Jarvis:</b> ${h.resposta}</span></li>
  `).join('') : '<li class="vazio">Sem histórico ainda.</li>';
}

// ---------- Chat ----------
const chatLog = document.getElementById('chat-log');
const chatBotao = document.getElementById('chat-botao');
document.getElementById('chat-form').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const campo = document.getElementById('chat-texto');
  const texto = campo.value.trim();
  if (!texto) return;
  chatLog.innerHTML += `<div class="bolha voce"><span class="rotulo">Você</span>${texto}</div>`;
  campo.value = '';
  chatBotao.disabled = true;
  chatLog.scrollTop = chatLog.scrollHeight;
  try {
    const r = await fetch('/api/perguntar', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({texto}),
    });
    const d = await r.json();
    chatLog.innerHTML += `<div class="bolha jarvis"><span class="rotulo">Jarvis</span>${d.resposta}</div>`;
  } catch (e) {
    chatLog.innerHTML += `<div class="bolha jarvis"><span class="rotulo">Jarvis</span>(erro ao responder, tenta de novo)</div>`;
  }
  chatBotao.disabled = false;
  chatLog.scrollTop = chatLog.scrollHeight;
  atualizarStatus();
  atualizarHistorico();
});

// ---------- Inicialização ----------
atualizarStatus();
atualizarMemoria();
atualizarLembretes();
atualizarRotinas();
atualizarHistorico();
setInterval(atualizarStatus, 1500);
setInterval(atualizarLembretes, 8000);
</script>
</body>
</html>
"""


def criar_app(estado=None) -> Flask:
    import psutil

    from .client import perguntar

    app = Flask(__name__)
    historico_web: list[dict] = []

    @app.route("/")
    def pagina_principal():
        return render_template_string(_PAGINA)

    # ---------- Status ----------
    @app.route("/api/status")
    def api_status():
        status = estado.ler()[0] if estado else "online"
        with banco.conexao() as conexao:
            hoje = datetime.now().strftime("%Y-%m-%d")
            comandos_hoje = conexao.execute(
                "SELECT COUNT(*) AS c FROM logs WHERE quando LIKE ?", (hoje + "%",)
            ).fetchone()["c"]
            lembretes_pendentes = conexao.execute(
                "SELECT COUNT(*) AS c FROM lembretes WHERE avisado = 0"
            ).fetchone()["c"]
            total_rotinas = conexao.execute("SELECT COUNT(*) AS c FROM rotinas").fetchone()["c"]
        return jsonify(
            status=status,
            cpu=psutil.cpu_percent(interval=None),
            ram=psutil.virtual_memory().percent,
            comandos_hoje=comandos_hoje,
            lembretes_pendentes=lembretes_pendentes,
            total_rotinas=total_rotinas,
        )

    # ---------- Chat ----------
    @app.route("/api/perguntar", methods=["POST"])
    def api_perguntar():
        nonlocal historico_web
        texto = (request.get_json(silent=True) or {}).get("texto", "").strip()
        if not texto:
            return jsonify(resposta="(mensagem vazia)")
        resposta, historico_web = perguntar(historico_web, texto)
        return jsonify(resposta=resposta)

    # ---------- Memória ----------
    @app.route("/api/memorias", methods=["GET"])
    def api_memorias_listar():
        with banco.conexao() as conexao:
            linhas = conexao.execute("SELECT chave, valor FROM memorias ORDER BY chave").fetchall()
        return jsonify([{"chave": linha["chave"], "valor": linha["valor"]} for linha in linhas])

    @app.route("/api/memorias", methods=["POST"])
    def api_memorias_salvar():
        dados = request.get_json(silent=True) or {}
        chave, valor = dados.get("chave", "").strip(), dados.get("valor", "").strip()
        if not chave or not valor:
            return jsonify(erro="chave e valor são obrigatórios"), 400
        with banco.conexao() as conexao:
            conexao.execute(
                "INSERT INTO memorias (chave, valor) VALUES (?, ?) "
                "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
                (chave, valor),
            )
        return jsonify(ok=True)

    @app.route("/api/memorias/<chave>", methods=["DELETE"])
    def api_memorias_remover(chave):
        with banco.conexao() as conexao:
            conexao.execute("DELETE FROM memorias WHERE chave = ?", (chave,))
        return jsonify(ok=True)

    # ---------- Lembretes ----------
    @app.route("/api/lembretes", methods=["GET"])
    def api_lembretes_listar():
        with banco.conexao() as conexao:
            linhas = conexao.execute(
                "SELECT id, texto, quando FROM lembretes WHERE avisado = 0 ORDER BY id"
            ).fetchall()
        return jsonify(
            [{"id": linha["id"], "texto": linha["texto"], "quando": linha["quando"]} for linha in linhas]
        )

    @app.route("/api/lembretes", methods=["POST"])
    def api_lembretes_criar():
        dados = request.get_json(silent=True) or {}
        texto = dados.get("texto", "").strip()
        quando = dados.get("quando", "").strip() or None
        if not texto:
            return jsonify(erro="texto é obrigatório"), 400
        with banco.conexao() as conexao:
            conexao.execute("INSERT INTO lembretes (texto, quando, avisado) VALUES (?, ?, 0)", (texto, quando))
        return jsonify(ok=True)

    @app.route("/api/lembretes/<int:id_lembrete>", methods=["DELETE"])
    def api_lembretes_remover(id_lembrete):
        with banco.conexao() as conexao:
            conexao.execute("DELETE FROM lembretes WHERE id = ?", (id_lembrete,))
        return jsonify(ok=True)

    # ---------- Rotinas ----------
    @app.route("/api/rotinas", methods=["GET"])
    def api_rotinas_listar():
        with banco.conexao() as conexao:
            linhas = conexao.execute("SELECT nome, passos FROM rotinas ORDER BY nome").fetchall()
        return jsonify([{"nome": linha["nome"], "passos": linha["passos"]} for linha in linhas])

    @app.route("/api/rotinas", methods=["POST"])
    def api_rotinas_salvar():
        dados = request.get_json(silent=True) or {}
        nome, passos = dados.get("nome", "").strip(), dados.get("passos", "").strip()
        if not nome or not passos:
            return jsonify(erro="nome e passos são obrigatórios"), 400
        with banco.conexao() as conexao:
            conexao.execute(
                "INSERT INTO rotinas (nome, passos) VALUES (?, ?) "
                "ON CONFLICT(nome) DO UPDATE SET passos = excluded.passos",
                (nome.lower(), passos),
            )
        return jsonify(ok=True)

    @app.route("/api/rotinas/<nome>", methods=["DELETE"])
    def api_rotinas_remover(nome):
        with banco.conexao() as conexao:
            conexao.execute("DELETE FROM rotinas WHERE nome = ?", (nome.lower(),))
        return jsonify(ok=True)

    @app.route("/api/rotinas/<nome>/executar", methods=["POST"])
    def api_rotinas_executar(nome):
        nonlocal historico_web
        resposta, historico_web = perguntar(historico_web, f"executa a rotina {nome}")
        return jsonify(resposta=resposta)

    # ---------- Histórico ----------
    @app.route("/api/historico")
    def api_historico():
        quantidade = request.args.get("quantidade", 50, type=int)
        with banco.conexao() as conexao:
            linhas = conexao.execute(
                "SELECT quando, comando, resposta FROM logs ORDER BY id DESC LIMIT ?", (quantidade,)
            ).fetchall()
        return jsonify(
            [{"quando": linha["quando"], "comando": linha["comando"], "resposta": linha["resposta"]} for linha in linhas]
        )

    return app


def iniciar(estado=None, abrir_navegador: bool = True) -> None:
    """Inicia o painel web em segundo plano, em http://localhost:5000."""
    app = criar_app(estado)
    threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=PORTA, debug=False, use_reloader=False),
        daemon=True,
    ).start()
    if abrir_navegador:
        threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{PORTA}")).start()
