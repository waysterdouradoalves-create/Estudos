"""Painel de controle do Jarvis: site local para acompanhar o status, ver lembretes e
conversar por texto pelo navegador (sem precisar de terminal)."""
import threading
import webbrowser

from flask import Flask, jsonify, render_template_string, request

from . import banco

PORTA = 5000

_PAGINA = """
<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Painel do Jarvis</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 24px; min-height: 100vh;
    background: #0a0e14; color: #e8eef7;
    font-family: 'Consolas', 'Courier New', monospace;
  }
  h1 { color: #8ab4f8; letter-spacing: 6px; font-size: 28px; margin: 0 0 4px; }
  .status { font-weight: bold; margin-bottom: 24px; font-size: 14px; }
  .status.online, .status.aguardando { color: #3ddc84; }
  .status.ouvindo, .status.pensando { color: #f5c451; }
  .status.falando { color: #7c5cff; }
  .status.ligando { color: #8ab4f8; }
  .grade { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
  .painel { background: #111722; border-radius: 10px; padding: 16px; }
  .painel h2 { font-size: 12px; color: #8ab4f8; text-transform: uppercase; letter-spacing: 2px; margin: 0 0 12px; }
  .barra-fundo { background: #1c2530; border-radius: 6px; height: 14px; overflow: hidden; margin-bottom: 10px; }
  .barra { height: 100%; background: #3ddc84; transition: width .4s; }
  ul { list-style: none; padding: 0; margin: 0; max-height: 150px; overflow-y: auto; }
  li { padding: 5px 0; border-bottom: 1px solid #1c2530; font-size: 12px; }
  #chat-log { max-height: 260px; overflow-y: auto; margin-bottom: 12px; }
  #chat-log p { margin: 5px 0; font-size: 13px; line-height: 1.4; }
  #chat-log .voce { color: #8ab4f8; }
  #chat-log .jarvis { color: #e8eef7; }
  form { display: flex; gap: 8px; }
  input[type=text] {
    flex: 1; background: #1c2530; border: 1px solid #2a3346; color: #e8eef7;
    padding: 10px; border-radius: 6px; font-family: inherit; font-size: 14px;
  }
  button {
    background: #8ab4f8; color: #0a0e14; border: none; border-radius: 6px;
    padding: 10px 18px; font-weight: bold; cursor: pointer; font-family: inherit;
  }
  button:hover { opacity: 0.9; }
  button:disabled { opacity: 0.5; cursor: default; }
</style>
</head>
<body>
  <h1>JARVIS</h1>
  <div class="status" id="status">● carregando...</div>

  <div class="grade">
    <div class="painel">
      <h2>Sistema</h2>
      <div style="font-size:12px;margin-bottom:4px">CPU <span id="cpu-txt"></span></div>
      <div class="barra-fundo"><div class="barra" id="cpu-barra"></div></div>
      <div style="font-size:12px;margin-bottom:4px">RAM <span id="ram-txt"></span></div>
      <div class="barra-fundo"><div class="barra" id="ram-barra" style="background:#7c5cff"></div></div>
    </div>
    <div class="painel">
      <h2>Lembretes</h2>
      <ul id="lembretes"><li>Carregando...</li></ul>
    </div>
  </div>

  <div class="painel">
    <h2>Conversar</h2>
    <div id="chat-log"></div>
    <form id="chat-form">
      <input type="text" id="chat-texto" placeholder="Digite algo pro Jarvis..." autocomplete="off">
      <button type="submit" id="chat-botao">Enviar</button>
    </form>
  </div>

<script>
async function atualizarStatus() {
  try {
    const r = await fetch('/api/status');
    const d = await r.json();
    const el = document.getElementById('status');
    el.textContent = '● ' + d.status.toUpperCase();
    el.className = 'status ' + d.status;
    document.getElementById('cpu-txt').textContent = d.cpu.toFixed(0) + '%';
    document.getElementById('cpu-barra').style.width = d.cpu + '%';
    document.getElementById('ram-txt').textContent = d.ram.toFixed(0) + '%';
    document.getElementById('ram-barra').style.width = d.ram + '%';
  } catch (e) { /* servidor ainda subindo, ignora */ }
}

async function atualizarLembretes() {
  try {
    const r = await fetch('/api/lembretes');
    const d = await r.json();
    const ul = document.getElementById('lembretes');
    ul.innerHTML = d.length ? d.map(l => `<li>${l}</li>`).join('') : '<li>Nenhum lembrete.</li>';
  } catch (e) { /* ignora */ }
}

const log = document.getElementById('chat-log');
const botao = document.getElementById('chat-botao');
document.getElementById('chat-form').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const campo = document.getElementById('chat-texto');
  const texto = campo.value.trim();
  if (!texto) return;
  log.innerHTML += `<p class="voce"><b>Você:</b> ${texto}</p>`;
  campo.value = '';
  botao.disabled = true;
  log.scrollTop = log.scrollHeight;
  try {
    const r = await fetch('/api/perguntar', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({texto}),
    });
    const d = await r.json();
    log.innerHTML += `<p class="jarvis"><b>Jarvis:</b> ${d.resposta}</p>`;
  } catch (e) {
    log.innerHTML += `<p class="jarvis"><b>Jarvis:</b> (erro ao responder, tenta de novo)</p>`;
  }
  botao.disabled = false;
  log.scrollTop = log.scrollHeight;
});

atualizarStatus();
atualizarLembretes();
setInterval(atualizarStatus, 1500);
setInterval(atualizarLembretes, 5000);
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

    @app.route("/api/status")
    def api_status():
        status = estado.ler()[0] if estado else "online"
        return jsonify(
            status=status,
            cpu=psutil.cpu_percent(interval=None),
            ram=psutil.virtual_memory().percent,
        )

    @app.route("/api/lembretes")
    def api_lembretes():
        with banco.conexao() as conexao:
            linhas = conexao.execute(
                "SELECT texto, quando FROM lembretes WHERE avisado = 0 ORDER BY id"
            ).fetchall()
        return jsonify(
            [f"{linha['texto']} — {linha['quando']}" if linha["quando"] else linha["texto"] for linha in linhas]
        )

    @app.route("/api/perguntar", methods=["POST"])
    def api_perguntar():
        nonlocal historico_web
        texto = (request.get_json(silent=True) or {}).get("texto", "").strip()
        if not texto:
            return jsonify(resposta="(mensagem vazia)")
        resposta, historico_web = perguntar(historico_web, texto)
        return jsonify(resposta=resposta)

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
