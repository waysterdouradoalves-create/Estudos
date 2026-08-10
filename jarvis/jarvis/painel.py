"""Painel de controle do Jarvis: site local (Flask) com dashboard, chat, memória,
lembretes, rotinas e histórico — tudo pelo navegador, sem precisar de terminal."""
import os
import struct
import threading
import webbrowser
import zlib
from datetime import datetime

from flask import Flask, Response, jsonify, render_template_string, request

from . import banco

PORTA = 5000

_CACHE_ICONES: dict[int, bytes] = {}


def _gerar_icone_png(tamanho: int) -> bytes:
    """Desenha o ícone do app (reator central) direto em PNG, sem depender de Pillow."""
    cor_fundo = (3, 5, 9)
    cor_anel = (47, 212, 255)
    cor_nucleo = (255, 255, 255)
    centro = tamanho / 2
    raio_anel = tamanho * 0.34
    espessura = tamanho * 0.045
    raio_nucleo = tamanho * 0.09

    linhas = bytearray()
    for y in range(tamanho):
        linhas.append(0)  # sem filtro nesta linha
        for x in range(tamanho):
            dist = ((x - centro) ** 2 + (y - centro) ** 2) ** 0.5
            if dist <= raio_nucleo:
                cor = cor_nucleo
            elif raio_anel - espessura <= dist <= raio_anel + espessura:
                cor = cor_anel
            else:
                cor = cor_fundo
            linhas += bytes((*cor, 255))

    def _chunk(tipo: bytes, dados: bytes) -> bytes:
        return struct.pack(">I", len(dados)) + tipo + dados + struct.pack(">I", zlib.crc32(tipo + dados))

    ihdr = struct.pack(">IIBBBBB", tamanho, tamanho, 8, 6, 0, 0, 0)
    idat = zlib.compress(bytes(linhas), 9)
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


def _icone(tamanho: int) -> bytes:
    if tamanho not in _CACHE_ICONES:
        _CACHE_ICONES[tamanho] = _gerar_icone_png(tamanho)
    return _CACHE_ICONES[tamanho]

_PAGINA = r"""
<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>JARVIS · Painel de Controle</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="manifest" href="/manifest.json">
<link rel="icon" href="/icone-192.png">
<meta name="theme-color" content="#030509">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    color-scheme: dark;
    --bg: #030509; --panel: rgba(10, 15, 26, 0.66); --border: rgba(120, 200, 255, 0.14);
    --border-forte: rgba(120, 200, 255, 0.45); --acento: #2fd4ff; --acento-2: #4f7dff;
    --texto: #eaf2ff; --texto-fraco: #7688a6; --sucesso: #1fe0a0; --aviso: #ffb020; --perigo: #ff4d6d;
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; }
  body {
    margin: 0; min-height: 100vh; display: flex; position: relative; overflow-x: hidden;
    background: var(--bg); color: var(--texto);
    font-family: 'Rajdhani', 'Segoe UI', sans-serif; font-size: 16px;
  }
  body::before {
    content: ''; position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background:
      radial-gradient(circle at 15% 20%, rgba(34,211,238,0.11), transparent 40%),
      radial-gradient(circle at 85% 75%, rgba(124,92,255,0.13), transparent 45%),
      radial-gradient(circle at 50% 100%, rgba(31,224,160,0.05), transparent 40%);
    animation: flutuar 18s ease-in-out infinite alternate;
  }
  body::after {
    content: ''; position: fixed; inset: 0; z-index: 0; pointer-events: none; opacity: .35;
    background-image:
      linear-gradient(rgba(110,231,255,0.035) 1px, transparent 1px),
      linear-gradient(90deg, rgba(110,231,255,0.035) 1px, transparent 1px);
    background-size: 42px 42px;
    mask-image: radial-gradient(circle at 30% 20%, black, transparent 75%);
    -webkit-mask-image: radial-gradient(circle at 30% 20%, black, transparent 75%);
  }
  @keyframes flutuar { from { transform: translate(0,0) scale(1); } to { transform: translate(-2%,2%) scale(1.05); } }
  .mono { font-family: 'Consolas', 'Courier New', monospace; }
  ::-webkit-scrollbar { width: 8px; height: 8px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: rgba(110,231,255,0.2); border-radius: 4px; }
  ::-webkit-scrollbar-thumb:hover { background: rgba(110,231,255,0.4); }

  /* ---------- Sidebar ---------- */
  #sidebar {
    width: 240px; flex-shrink: 0; position: sticky; top: 0; height: 100vh; z-index: 2;
    background: var(--panel); backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
    border-right: 1px solid var(--border); padding: 24px 0; display: flex; flex-direction: column;
  }
  #sidebar .logo {
    font-family: 'Orbitron', sans-serif; font-size: 22px; font-weight: 900; letter-spacing: 6px;
    padding: 0 24px 22px; margin-bottom: 14px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 10px;
    background: linear-gradient(90deg, var(--acento), var(--acento-2));
    -webkit-background-clip: text; background-clip: text; color: transparent;
    text-shadow: 0 0 30px rgba(34,211,238,0.25);
  }
  #sidebar .logo .nucleo {
    width: 9px; height: 9px; border-radius: 50%; background: var(--acento); flex-shrink: 0;
    box-shadow: 0 0 8px 2px var(--acento), 0 0 16px 4px rgba(34,211,238,0.5);
    animation: nucleo-pulsar 2.4s ease-in-out infinite;
  }
  @keyframes nucleo-pulsar { 0%,100% { opacity: 1; transform: scale(1); } 50% { opacity: .5; transform: scale(1.4); } }
  #sidebar nav { display: flex; flex-direction: column; gap: 4px; padding: 0 14px; flex: 1; }
  #sidebar .item {
    display: flex; align-items: center; gap: 11px; padding: 11px 14px; border-radius: 10px;
    color: var(--texto-fraco); cursor: pointer; font-size: 15px; font-weight: 500; user-select: none;
    border: 1px solid transparent; position: relative; transition: all .2s ease;
  }
  #sidebar .item:hover { background: rgba(110,231,255,0.06); color: var(--texto); border-color: var(--border); }
  #sidebar .item.ativo {
    background: linear-gradient(90deg, rgba(34,211,238,0.14), rgba(124,92,255,0.05));
    color: var(--acento); font-weight: 700; border-color: var(--border-forte);
    box-shadow: inset 0 0 14px rgba(34,211,238,0.08);
  }
  #sidebar .item.ativo::before {
    content: ''; position: absolute; left: -14px; top: 8px; bottom: 8px; width: 3px; border-radius: 3px;
    background: linear-gradient(180deg, var(--acento), var(--acento-2)); box-shadow: 0 0 8px var(--acento);
  }
  #sidebar .rodape { padding: 14px 24px 0; font-size: 11px; color: var(--texto-fraco); border-top: 1px solid var(--border); margin-top: 12px; letter-spacing: 1px; }

  /* ---------- Conteúdo ---------- */
  #conteudo { flex: 1; padding: 32px 40px; max-width: 1180px; position: relative; z-index: 1; }
  .secao { display: none; }
  .secao.ativa { display: block; animation: aparecer .3s ease; }
  @keyframes aparecer { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }

  h1.titulo {
    font-family: 'Orbitron', sans-serif; font-size: 21px; margin: 0 0 26px; font-weight: 700;
    letter-spacing: 2px; text-transform: uppercase; color: var(--texto); display: flex; align-items: center; gap: 12px;
  }
  h1.titulo::after { content: ''; flex: 1; height: 1px; background: linear-gradient(90deg, var(--border-forte), transparent); }

  /* ---------- Status hero: reator central ---------- */
  .status-hero {
    display: flex; align-items: center; gap: 48px; background:
      radial-gradient(circle at 15% 50%, rgba(47,212,255,0.07), transparent 55%), var(--panel);
    backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); position: relative; overflow: hidden;
    border: 1px solid var(--border); border-radius: 20px; padding: 46px 50px; margin-bottom: 24px;
    min-height: 220px;
  }
  .status-hero::before {
    content: ''; position: absolute; top: 0; left: -30%; width: 30%; height: 2px;
    background: linear-gradient(90deg, transparent, currentColor, transparent); opacity: .5;
    animation: varrer 3.2s linear infinite;
  }
  @keyframes varrer { from { left: -30%; } to { left: 100%; } }

  /* Núcleo estilo "arc reactor": anéis concêntricos girando + centro pulsante */
  .ponto {
    width: 130px; height: 130px; border-radius: 50%; flex-shrink: 0; position: relative;
    display: flex; align-items: center; justify-content: center;
  }
  .anel-extra { position: absolute; border-radius: 50%; border: 1px dashed currentColor; pointer-events: none; }
  .anel-extra.a1 { inset: -16px; opacity: .28; animation: girar 7s linear infinite reverse; }
  .anel-extra.a2 { inset: -34px; opacity: .14; animation: girar 12s linear infinite; border-style: solid; border-width: 1px; }
  .ponto::before {
    content: ''; position: absolute; inset: 0; border-radius: 50%;
    background: conic-gradient(currentColor 0deg, transparent 100deg, currentColor 180deg, transparent 280deg);
    opacity: .7; animation: girar 3s linear infinite;
    -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 7px), #000 calc(100% - 7px));
    mask: radial-gradient(farthest-side, transparent calc(100% - 7px), #000 calc(100% - 7px));
  }
  @keyframes girar { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
  .ponto::after {
    content: ''; width: 34px; height: 34px; border-radius: 50%; background: currentColor; position: relative; z-index: 1;
    box-shadow: 0 0 22px 6px currentColor, 0 0 50px 16px currentColor;
  }
  .ponto.pulsar::after { animation: respirar 1.8s ease-in-out infinite; }
  @keyframes respirar {
    0%, 100% { box-shadow: 0 0 22px 6px currentColor, 0 0 50px 16px currentColor; }
    50% { box-shadow: 0 0 30px 9px currentColor, 0 0 68px 22px currentColor; }
  }
  .status-hero-info { position: relative; z-index: 1; }
  .status-hero .texto {
    font-family: 'Orbitron', sans-serif; font-size: 24px; font-weight: 700; letter-spacing: 3px; text-transform: uppercase;
  }
  .status-hero .sub { font-size: 14px; color: var(--texto-fraco); margin-top: 6px; letter-spacing: .5px; }
  .cor-online, .cor-aguardando { color: var(--sucesso); }
  .cor-ouvindo, .cor-pensando { color: var(--aviso); }
  .cor-falando { color: var(--acento-2); }
  .cor-ligando { color: var(--acento); }

  .botao-ativar {
    margin-top: 18px; background: linear-gradient(135deg, var(--acento), var(--acento-2)); color: #04101a;
    border: none; border-radius: 999px; padding: 12px 26px; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; font-size: 12px; cursor: pointer; font-family: 'Rajdhani', inherit;
    box-shadow: 0 0 20px rgba(47,212,255,.35); transition: transform .15s ease, box-shadow .15s ease;
  }
  .botao-ativar:hover { transform: translateY(-1px); box-shadow: 0 0 28px rgba(47,212,255,.55); }
  .botao-ativar:disabled { opacity: .45; cursor: default; transform: none; }

  /* ---------- Cards / grade ---------- */
  .grade { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 18px; margin-bottom: 24px; }
  .cartao {
    background: var(--panel); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
    border: 1px solid var(--border); border-radius: 14px; padding: 20px; position: relative;
    transition: border-color .2s ease, transform .2s ease;
  }
  /* Cantos estilo HUD/mira */
  .cartao::before, .cartao::after {
    content: ''; position: absolute; width: 14px; height: 14px; border: 2px solid var(--acento);
    opacity: .3; transition: opacity .2s ease; pointer-events: none;
  }
  .cartao::before { top: -1px; left: -1px; border-right: none; border-bottom: none; border-radius: 6px 0 0 0; }
  .cartao::after { bottom: -1px; right: -1px; border-left: none; border-top: none; border-radius: 0 0 6px 0; }
  .cartao:hover { border-color: var(--border-forte); transform: translateY(-2px); }
  .cartao:hover::before, .cartao:hover::after { opacity: .9; }
  .cartao h2 {
    font-family: 'Orbitron', sans-serif; font-size: 11px; color: var(--acento); text-transform: uppercase;
    letter-spacing: 2px; margin: 0 0 16px; font-weight: 700;
  }
  .estat-num {
    font-family: 'Orbitron', sans-serif; font-size: 28px; font-weight: 700;
    background: linear-gradient(90deg, var(--texto), var(--acento)); -webkit-background-clip: text;
    background-clip: text; color: transparent;
  }
  .estat-legenda { font-size: 12px; color: var(--texto-fraco); margin-top: 4px; letter-spacing: .5px; }

  /* Medidor circular (CPU / RAM) */
  .dial-cartao { display: flex; flex-direction: column; align-items: center; text-align: center; }
  .dial {
    --pct: 0; --cor: var(--acento); width: 92px; height: 92px; border-radius: 50%; position: relative;
    display: flex; align-items: center; justify-content: center;
    background: conic-gradient(var(--cor) calc(var(--pct) * 1%), rgba(255,255,255,0.07) 0);
    box-shadow: 0 0 18px -4px var(--cor); transition: background .5s ease;
  }
  .dial::before { content: ''; position: absolute; inset: 8px; border-radius: 50%; background: var(--bg); }
  .dial-valor { position: relative; font-family: 'Orbitron', sans-serif; font-weight: 700; font-size: 16px; z-index: 1; }
  .dial.roxo { --cor: var(--acento-2); }

  /* ---------- Listas ---------- */
  .lista { list-style: none; padding: 0; margin: 0; }
  .lista li {
    display: flex; justify-content: space-between; align-items: center; gap: 10px;
    padding: 12px 0; border-bottom: 1px solid var(--border); font-size: 14px;
  }
  .lista li:last-child { border-bottom: none; }
  .lista .vazio { color: var(--texto-fraco); font-style: italic; }
  .item-texto { flex: 1; }
  .item-sub { font-size: 11px; color: var(--texto-fraco); margin-top: 3px; letter-spacing: .3px; }

  /* ---------- Formulários / botões ---------- */
  form.form-linha { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px; }
  input[type=text], input[type=datetime-local], textarea {
    background: rgba(255,255,255,0.03); border: 1px solid var(--border); color: var(--texto);
    padding: 11px 14px; border-radius: 10px; font-family: 'Rajdhani', inherit; font-size: 14px;
    transition: border-color .2s ease;
  }
  input:focus, textarea:focus { outline: none; border-color: var(--border-forte); box-shadow: 0 0 0 3px rgba(34,211,238,0.08); }
  input[type=text] { flex: 1; min-width: 160px; }
  textarea { width: 100%; min-height: 60px; resize: vertical; }
  button {
    background: linear-gradient(135deg, var(--acento), var(--acento-2)); color: #04101a; border: none; border-radius: 10px;
    padding: 11px 22px; font-weight: 700; cursor: pointer; font-family: 'Rajdhani', inherit; font-size: 14px;
    letter-spacing: .5px; text-transform: uppercase; box-shadow: 0 0 16px rgba(34,211,238,.25);
    transition: transform .15s ease, box-shadow .15s ease;
  }
  button:hover { transform: translateY(-1px); box-shadow: 0 0 22px rgba(34,211,238,.4); }
  button:disabled { opacity: 0.4; cursor: default; transform: none; box-shadow: none; }
  button.secundario { background: rgba(255,255,255,0.06); color: var(--texto); box-shadow: none; }
  button.perigo { background: rgba(255,77,109,0.12); color: var(--perigo); box-shadow: none; padding: 7px 12px; font-size: 12px; border: 1px solid rgba(255,77,109,0.3); }
  button.pequeno { padding: 7px 12px; font-size: 12px; }

  /* ---------- Chat ---------- */
  #chat-log { max-height: 420px; overflow-y: auto; margin-bottom: 14px; padding-right: 4px; }
  #chat-log .bolha { margin: 10px 0; font-size: 14px; line-height: 1.5; padding: 12px 16px; border-radius: 12px; max-width: 80%; border: 1px solid var(--border); }
  #chat-log .voce { background: rgba(34,211,238,0.08); border-color: rgba(34,211,238,0.25); margin-left: auto; }
  #chat-log .jarvis { background: rgba(124,92,255,0.06); border-color: rgba(124,92,255,0.2); }
  #chat-log .rotulo { font-family: 'Orbitron', sans-serif; font-size: 10px; text-transform: uppercase; letter-spacing: 1.5px; opacity: .7; display: block; margin-bottom: 4px; }

  /* ---------- Responsivo ---------- */
  @media (max-width: 760px) {
    body { flex-direction: column; }
    #sidebar { width: 100%; height: auto; position: relative; flex-direction: row; overflow-x: auto; padding: 14px; }
    #sidebar .logo { display: none; }
    #sidebar nav { flex-direction: row; padding: 0; }
    #sidebar .item.ativo::before { display: none; }
    #sidebar .rodape, #sidebar .rodape-parar { display: none; }
    #conteudo { padding: 20px; }
  }
</style>
</head>
<body>

<div id="sidebar">
  <div class="logo"><span class="nucleo"></span>JARVIS</div>
  <nav id="nav">
    <div class="item ativo" data-secao="dashboard">📊 Dashboard</div>
    <div class="item" data-secao="chat">💬 Chat</div>
    <div class="item" data-secao="memoria">🧠 Memória</div>
    <div class="item" data-secao="lembretes">⏰ Lembretes</div>
    <div class="item" data-secao="rotinas">🔁 Rotinas</div>
    <div class="item" data-secao="historico">📜 Histórico</div>
  </nav>
  <div class="rodape mono">painel local · localhost:5000</div>
  <div class="rodape-parar" style="padding: 14px 24px 0;">
    <button id="btn-parar" class="perigo" style="width:100%; padding:10px 0; font-size:12px; letter-spacing:1px;">⏻ Encerrar Jarvis</button>
  </div>
</div>

<div id="conteudo">

  <!-- Dashboard -->
  <section class="secao ativa" id="secao-dashboard">
    <h1 class="titulo">Dashboard</h1>
    <div class="status-hero cor-ligando" id="status-hero">
      <div class="ponto pulsar" id="status-ponto">
        <span class="anel-extra a1"></span>
        <span class="anel-extra a2"></span>
      </div>
      <div class="status-hero-info">
        <div class="texto" id="status-texto">Carregando...</div>
        <div class="sub">Modelo: claude-sonnet-5</div>
        <button type="button" id="btn-ativar" class="botao-ativar">🎙️ Ativar agora</button>
      </div>
    </div>
    <div class="grade">
      <div class="cartao dial-cartao">
        <h2>CPU</h2>
        <div class="dial" id="cpu-dial"><span class="dial-valor" id="cpu-txt">-</span></div>
      </div>
      <div class="cartao dial-cartao">
        <h2>Memória RAM</h2>
        <div class="dial roxo" id="ram-dial"><span class="dial-valor" id="ram-txt">-</span></div>
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
    document.getElementById('cpu-dial').style.setProperty('--pct', d.cpu);
    document.getElementById('ram-txt').textContent = d.ram.toFixed(0) + '%';
    document.getElementById('ram-dial').style.setProperty('--pct', d.ram);
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

// ---------- Ativar manualmente (sem bater palma) ----------
const btnAtivar = document.getElementById('btn-ativar');
btnAtivar.addEventListener('click', async () => {
  btnAtivar.disabled = true;
  btnAtivar.textContent = 'Ativando...';
  try { await fetch('/api/ativar', { method: 'POST' }); } catch (e) { /* ignora */ }
  setTimeout(() => { btnAtivar.disabled = false; btnAtivar.textContent = '🎙️ Ativar agora'; }, 2500);
});

// ---------- Encerrar ----------
document.getElementById('btn-parar').addEventListener('click', async () => {
  if (!confirm('Tem certeza que quer encerrar o Jarvis?')) return;
  try { await fetch('/api/parar', { method: 'POST' }); } catch (e) { /* processo já pode ter caído */ }
  document.body.innerHTML = '<div style="padding:60px;font-family:Orbitron,sans-serif;color:#7c8aa8;font-size:18px;letter-spacing:1px">Jarvis encerrado. Pode fechar esta aba.</div>';
});

// ---------- App instalável (PWA) ----------
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => { /* segue sem PWA */ });
}

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

    # ---------- App instalável (PWA) ----------
    @app.route("/manifest.json")
    def manifest():
        return jsonify(
            {
                "name": "JARVIS",
                "short_name": "Jarvis",
                "start_url": "/",
                "display": "standalone",
                "background_color": "#030509",
                "theme_color": "#030509",
                "icons": [
                    {"src": "/icone-192.png", "sizes": "192x192", "type": "image/png"},
                    {"src": "/icone-512.png", "sizes": "512x512", "type": "image/png"},
                ],
            }
        )

    @app.route("/sw.js")
    def service_worker():
        return Response("self.addEventListener('fetch', () => {});", mimetype="application/javascript")

    @app.route("/icone-<int:tamanho>.png")
    def icone(tamanho):
        return Response(_icone(tamanho), mimetype="image/png")

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

    # ---------- Ativação manual ----------
    @app.route("/api/ativar", methods=["POST"])
    def api_ativar():
        from . import voice

        voice.evento_ativacao_manual.set()
        return jsonify(ok=True)

    # ---------- Encerrar ----------
    @app.route("/api/parar", methods=["POST"])
    def api_parar():
        threading.Timer(0.4, lambda: os._exit(0)).start()
        return jsonify(ok=True)

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
