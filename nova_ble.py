#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA BLE Bridge Server (iPhone Friendly)
Premium mobile interface with full AI and system control integration.
"""

import os
import sys
import json
import threading
import time
from typing import Optional, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket
from datetime import datetime

# Add workspace to path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.join(SCRIPT_DIR, "workspace")
if WORKSPACE_DIR not in sys.path:
    sys.path.append(WORKSPACE_DIR)

# Standard UART Service UUIDs (Nordic UART Service) - for reference
UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

BLE_AVAILABLE = True
BLE_IMPORT_ERROR = None

# Try to import Groq for AI responses
try:
    from groq import Groq
    import dotenv
    dotenv.load_dotenv()
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_CLIENT = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
except:
    GROQ_CLIENT = None

# Premium Mobile UI HTML
MOBILE_UI_HTML = '''<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>Nova Remote</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0
        }

        :root {
            --bg: #020510;
            --accent: #00f5ff;
            --purple: #a855f7;
            --success: #3dffb0;
            --warning: #ffcc4d;
            --danger: #ff4d7f;
            --text: #fff;
            --text2: rgba(255, 255, 255, 0.6);
            --border: rgba(255, 255, 255, 0.12)
        }

        body {
            font-family: system-ui, -apple-system, sans-serif;
            min-height: 100vh;
            color: var(--text);
            background: radial-gradient(circle at 0% 0%, rgba(0, 255, 178, 0.06), transparent 55%), radial-gradient(circle at 100% 0%, rgba(80, 120, 255, 0.1), transparent 60%), linear-gradient(135deg, var(--bg), #050819);
            padding: 16px;
            padding-top: calc(env(safe-area-inset-top, 16px)+8px);
            padding-bottom: calc(env(safe-area-inset-bottom, 16px)+70px)
        }

        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 10px
        }

        .logo {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: conic-gradient(from 180deg, var(--accent), var(--purple), var(--accent));
            padding: 2px;
            box-shadow: 0 0 20px rgba(0, 245, 255, 0.3)
        }

        .logo-inner {
            width: 100%;
            height: 100%;
            border-radius: inherit;
            background: radial-gradient(circle at 30% 20%, rgba(255, 255, 255, 0.9), transparent 45%), radial-gradient(circle at 80% 80%, rgba(0, 0, 0, 0.9), transparent 55%)
        }

        h1 {
            font-size: 22px;
            font-weight: 700;
            letter-spacing: 0.1em;
            background: linear-gradient(120deg, #fff, var(--accent));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent
        }

        .subtitle {
            font-size: 10px;
            letter-spacing: 0.15em;
            color: var(--text2);
            text-transform: uppercase
        }

        .pill {
            padding: 6px 12px;
            border-radius: 999px;
            border: 1px solid rgba(0, 245, 255, 0.4);
            font-size: 10px;
            color: var(--accent);
            display: flex;
            align-items: center;
            gap: 6px
        }

        .dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--success);
            box-shadow: 0 0 8px rgba(61, 255, 176, 0.8)
        }

        .card {
            border-radius: 18px;
            padding: 14px;
            margin-bottom: 12px;
            background: linear-gradient(135deg, rgba(9, 14, 40, 0.95), rgba(15, 32, 68, 0.95));
            border: 1px solid rgba(0, 245, 255, 0.2);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
            position: relative
        }

        .card-title {
            position: absolute;
            right: 12px;
            top: 8px;
            font-size: 8px;
            letter-spacing: 0.12em;
            color: rgba(255, 255, 255, 0.2);
            text-transform: uppercase
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px
        }

        .stat {
            text-align: center
        }

        .stat-label {
            font-size: 9px;
            color: var(--text2);
            margin-bottom: 3px;
            text-transform: uppercase
        }

        .stat-value {
            font-size: 18px;
            font-weight: 600
        }

        .stat-unit {
            font-size: 9px;
            color: var(--text2)
        }

        .meter {
            margin-top: 4px;
            height: 3px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.08);
            overflow: hidden
        }

        .meter-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent), var(--purple));
            transform-origin: left;
            transform: scaleX(0);
            transition: transform 200ms
        }

        .section {
            font-size: 10px;
            color: var(--text2);
            text-transform: uppercase;
            letter-spacing: 0.18em;
            margin: 14px 0 8px;
            display: flex;
            align-items: center;
            gap: 8px
        }

        .section::after {
            content: "";
            flex: 1;
            height: 1px;
            background: linear-gradient(90deg, rgba(148, 163, 184, 0.3), transparent)
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px
        }

        .btn {
            border-radius: 14px;
            padding: 10px 4px;
            background: linear-gradient(145deg, rgba(17, 24, 56, 0.95), rgba(8, 14, 40, 0.98));
            border: 1px solid var(--border);
            text-align: center;
            cursor: pointer
        }

        .btn:active {
            transform: scale(0.95)
        }

        .btn .icon {
            font-size: 20px;
            display: block;
            margin-bottom: 3px
        }

        .btn .label {
            font-size: 8px;
            letter-spacing: 0.06em;
            color: var(--text2);
            text-transform: uppercase
        }

        .btn.danger {
            border-color: rgba(255, 77, 127, 0.5)
        }

        .btn.accent {
            border-color: rgba(0, 245, 255, 0.5);
            box-shadow: 0 6px 16px rgba(0, 245, 255, 0.2)
        }

        .chat {
            border-radius: 18px;
            padding: 12px;
            background: rgba(8, 11, 30, 0.95);
            border: 1px solid rgba(148, 163, 184, 0.3);
            height: 340px;
            display: flex;
            flex-direction: column
        }

        .chat-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px
        }

        .badge {
            padding: 4px 10px;
            border-radius: 99px;
            border: 1px solid rgba(0, 245, 255, 0.4);
            font-size: 9px;
            letter-spacing: 0.12em;
            text-transform: uppercase
        }

        .msgs {
            flex: 1;
            overflow-y: auto;
            padding: 4px
        }

        .msg {
            margin-bottom: 8px
        }

        .bubble {
            padding: 8px 12px;
            border-radius: 14px;
            font-size: 13px;
            line-height: 1.4;
            border: 1px solid rgba(148, 163, 184, 0.3)
        }

        .msg.nova .bubble {
            border-radius: 14px 14px 14px 4px;
            background: rgba(0, 245, 255, 0.1)
        }

        .msg.user {
            text-align: right
        }

        .msg.user .bubble {
            border-radius: 14px 14px 4px 14px;
            background: linear-gradient(135deg, var(--accent), var(--purple));
            color: #000;
            display: inline-block;
            border: none
        }

        .spinner {
            width: 14px;
            height: 14px;
            border-radius: 50%;
            border: 2px solid rgba(148, 163, 184, 0.3);
            border-top-color: var(--accent);
            animation: spin .7s linear infinite;
            display: inline-block
        }

        .input-row {
            display: flex;
            gap: 8px;
            margin-top: 8px
        }

        .input-row input {
            flex: 1;
            border-radius: 999px;
            border: 1px solid rgba(148, 163, 184, 0.5);
            background: rgba(15, 23, 42, 0.9);
            color: var(--text);
            font-size: 14px;
            padding: 10px 14px;
            outline: none
        }

        .input-row input:focus {
            border-color: var(--accent)
        }

        .send {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            border: none;
            background: conic-gradient(from 180deg, var(--accent), var(--purple), var(--accent));
            color: #000;
            font-size: 18px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center
        }

        .apps {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px
        }

        .app {
            border-radius: 14px;
            padding: 10px 4px;
            border: 1px solid rgba(148, 163, 184, 0.4);
            background: rgba(15, 23, 42, 0.9);
            text-align: center;
            cursor: pointer
        }

        .app:active {
            transform: scale(0.95)
        }

        .app .icon {
            font-size: 22px;
            display: block;
            margin-bottom: 3px
        }

        .app .label {
            font-size: 8px;
            color: var(--text2);
            text-transform: uppercase
        }

        .app.active {
            border-color: var(--accent);
            box-shadow: 0 6px 16px rgba(0, 245, 255, 0.3)
        }

        .page {
            display: none
        }

        .page.active {
            display: block
        }

        .nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(5, 8, 25, 0.98);
            border-top: 1px solid rgba(0, 245, 255, 0.15);
            padding: 8px 0;
            padding-bottom: calc(env(safe-area-inset-bottom, 8px)+8px);
            display: flex;
            justify-content: space-around;
            z-index: 100
        }

        .nav-btn {
            text-align: center;
            padding: 6px 14px;
            border-radius: 10px;
            cursor: pointer
        }

        .nav-btn .icon {
            font-size: 20px
        }

        .nav-btn .label {
            font-size: 8px;
            color: var(--text2);
            text-transform: uppercase
        }

        .nav-btn.active {
            background: rgba(0, 245, 255, 0.12)
        }

        .nav-btn.active .label {
            color: var(--accent)
        }

        #pin-overlay {
            position: fixed;
            inset: 0;
            z-index: 1000;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: rgba(0, 0, 0, 0.95);
            backdrop-filter: blur(20px)
        }

        #pin-overlay h2 {
            font-size: 16px;
            color: var(--accent);
            letter-spacing: 0.15em;
            margin-top: 8px
        }

        #pin-display {
            font-size: 28px;
            letter-spacing: 0.4em;
            color: var(--accent);
            margin: 20px 0
        }

        #pin-pad {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px
        }

        .pin-key {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            border: 1px solid rgba(148, 163, 184, 0.6);
            background: rgba(15, 23, 42, 0.9);
            color: var(--text);
            font-size: 22px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer
        }

        .pin-key:active {
            transform: scale(0.95)
        }

        .pin-key.confirm {
            background: var(--success);
            color: #000;
            border-color: var(--success)
        }

        .pin-key.back {
            background: var(--danger);
            border-color: var(--danger)
        }

        .pin-cancel {
            margin-top: 20px;
            padding: 8px 30px;
            border-radius: 999px;
            border: 1px solid rgba(148, 163, 184, 0.5);
            background: transparent;
            color: var(--text2);
            cursor: pointer
        }

        @keyframes spin {
            to {
                transform: rotate(360deg)
            }
        }
    </style>
</head>

<body>
    <div class="header">
        <div class="brand">
            <div class="logo">
                <div class="logo-inner"></div>
            </div>
            <div>
                <h1>NOVA</h1>
                <div class="subtitle">Remote Control</div>
            </div>
        </div>
        <div class="pill"><span class="dot"></span>{device_name}</div>
    </div>

    <div id="home" class="page active">
        <div class="card"><span class="card-title">System Diagnostics</span>
            <div class="stats">
                <div class="stat">
                    <div class="stat-label">CPU</div>
                    <div class="stat-value" id="cpu">0<span class="stat-unit">%</span></div>
                    <div class="meter">
                        <div class="meter-fill" id="cpuM"></div>
                    </div>
                </div>
                <div class="stat">
                    <div class="stat-label">RAM</div>
                    <div class="stat-value" id="mem">0<span class="stat-unit">%</span></div>
                    <div class="meter">
                        <div class="meter-fill" id="memM"></div>
                    </div>
                </div>
                <div class="stat">
                    <div class="stat-label">BAT</div>
                    <div class="stat-value" id="bat">--<span class="stat-unit">%</span></div>
                    <div class="meter">
                        <div class="meter-fill" id="batM"></div>
                    </div>
                </div>
                <div class="stat">
                    <div class="stat-label">DISK</div>
                    <div class="stat-value" id="disk">0<span class="stat-unit">%</span></div>
                    <div class="meter">
                        <div class="meter-fill" id="diskM"></div>
                    </div>
                </div>
            </div>
        </div>
        <div class="section">Controls</div>
        <div class="grid">
            <div class="btn" onclick="cmd('lock')"><span class="icon">🔒</span><span class="label">Lock</span></div>
            <div class="btn accent" onclick="showPin()"><span class="icon">🔓</span><span class="label">Unlock</span>
            </div>
            <div class="btn" onclick="cmd('sleep')"><span class="icon">😴</span><span class="label">Sleep</span></div>
            <div class="btn" onclick="cmd('mute')"><span class="icon">🔇</span><span class="label">Mute</span></div>
        </div>
        <div class="grid" style="margin-top:8px">
            <div class="btn" onclick="cmd('volume up')"><span class="icon">🔊</span><span class="label">Vol+</span>
            </div>
            <div class="btn" onclick="cmd('volume down')"><span class="icon">🔉</span><span class="label">Vol-</span>
            </div>
            <div class="btn" onclick="cmd('brightness up')"><span class="icon">☀️</span><span
                    class="label">Bright+</span></div>
            <div class="btn" onclick="cmd('brightness down')"><span class="icon">🌙</span><span
                    class="label">Bright-</span></div>
        </div>
        <div class="grid" style="margin-top:8px">
            <div class="btn" onclick="cmd('wake')"><span class="icon">⏰</span><span class="label">Wake</span></div>
            <div class="btn" onclick="cmd('clear temp')"><span class="icon">🧹</span><span class="label">Clean</span>
            </div>
            <div class="btn" onclick="confirm('Restart?')&&cmd('restart')"><span class="icon">🔄</span><span
                    class="label">Restart</span></div>
            <div class="btn danger" onclick="confirm('Shutdown?')&&cmd('shutdown')"><span class="icon">⏻</span><span
                    class="label">Power</span></div>
        </div>
    </div>

    <div id="chat" class="page">
        <div class="chat">
            <div class="chat-head">
                <div class="badge">Nova · Online</div>
                <div style="font-size:9px;color:var(--text2)">AI Chat</div>
            </div>
            <div class="msgs" id="msgs">
                <div class="msg nova">
                    <div class="bubble">Hello! How can I help? 🚀</div>
                </div>
            </div>
            <div class="input-row"><input id="inp" placeholder="Ask Nova..." autocomplete="off"><button class="send"
                    onclick="send()">➤</button></div>
        </div>
    </div>

    <div id="apps" class="page">
        <div class="section">App Launcher</div>
        <div class="apps">
            <div class="app" onclick="tap(this,'chrome')"><span class="icon">🌐</span><span class="label">Chrome</span>
            </div>
            <div class="app" onclick="tap(this,'spotify')"><span class="icon">🎵</span><span
                    class="label">Spotify</span></div>
            <div class="app" onclick="tap(this,'discord')"><span class="icon">💬</span><span
                    class="label">Discord</span></div>
            <div class="app" onclick="tap(this,'code')"><span class="icon">💻</span><span class="label">VS Code</span>
            </div>
            <div class="app" onclick="tap(this,'explorer')"><span class="icon">📁</span><span class="label">Files</span>
            </div>
            <div class="app" onclick="tap(this,'notepad')"><span class="icon">📝</span><span
                    class="label">Notepad</span></div>
            <div class="app" onclick="tap(this,'settings')"><span class="icon">⚙️</span><span
                    class="label">Settings</span></div>
            <div class="app" onclick="tap(this,'calc')"><span class="icon">🔢</span><span class="label">Calc</span>
            </div>
            <div class="app" onclick="tap(this,'whatsapp')"><span class="icon">📱</span><span
                    class="label">WhatsApp</span></div>
            <div class="app" onclick="tap(this,'youtube')"><span class="icon">▶️</span><span
                    class="label">YouTube</span></div>
            <div class="app" onclick="tap(this,'teams')"><span class="icon">👥</span><span class="label">Teams</span>
            </div>
            <div class="app" onclick="tap(this,'outlook')"><span class="icon">📧</span><span
                    class="label">Outlook</span></div>
            <div class="app" onclick="tap(this,'word')"><span class="icon">📄</span><span
                    class="label">Word</span></div>
            <div class="app" onclick="tap(this,'excel')"><span class="icon">📊</span><span
                    class="label">Excel</span></div>
            <div class="app" onclick="tap(this,'powerpoint')"><span class="icon">📽️</span><span
                    class="label">PPT</span></div>
            <div class="app" onclick="tap(this,'vlc media player')"><span class="icon">🎬</span><span
                    class="label">VLC</span></div>
            <div class="app" onclick="tap(this,'edge')"><span class="icon">🌐</span><span
                    class="label">Edge</span></div>
            <div class="app" onclick="tap(this,'terminal')"><span class="icon">💻</span><span
                    class="label">Terminal</span></div>
            <div class="app" onclick="tap(this,'git bash')"><span class="icon">🔧</span><span
                    class="label">Git Bash</span></div>
            <div class="app" onclick="tap(this,'mysql workbench')"><span class="icon">🗄️</span><span
                    class="label">MySQL</span></div>
            <div class="app" onclick="tap(this,'visual studio 2022')"><span class="icon">🟣</span><span
                    class="label">VS 2022</span></div>
            <div class="app" onclick="tap(this,'onenote')"><span class="icon">📔</span><span
                    class="label">OneNote</span></div>
            <div class="app" onclick="tap(this,'roblox player')"><span class="icon">🎮</span><span
                    class="label">Roblox</span></div>
            <div class="app" onclick="tap(this,'internet download manager')"><span class="icon">📥</span><span
                    class="label">IDM</span></div>
            <div class="app" onclick="tap(this,'task manager')"><span class="icon">📈</span><span
                    class="label">TaskMgr</span></div>
        </div>
        <p style="text-align:center;margin-top:12px;font-size:10px;color:var(--text2)">Tap=Open · Double-tap=Close</p>
    </div>

    <div id="set" class="page">
        <div class="section">Settings</div>
        <div class="card">
            <p style="font-size:13px;margin-bottom:6px">🔐 <b>Unlock PIN</b></p>
            <p style="font-size:11px;color:var(--text2)">Default: 1234</p>
        </div>
        <div class="card">
            <p style="font-size:13px;margin-bottom:6px">📊 <b>System</b></p>
            <p style="font-size:11px;color:var(--text2)">Device: {device_name}<br>Nova BLE v2.0</p>
        </div>
    </div>

    <nav class="nav">
        <div class="nav-btn active" onclick="go('home',this)">
            <div class="icon">🏠</div>
            <div class="label">Home</div>
        </div>
        <div class="nav-btn" onclick="go('chat',this)">
            <div class="icon">💬</div>
            <div class="label">Chat</div>
        </div>
        <div class="nav-btn" onclick="go('apps',this)">
            <div class="icon">📱</div>
            <div class="label">Apps</div>
        </div>
        <div class="nav-btn" onclick="go('set',this)">
            <div class="icon">⚙️</div>
            <div class="label">Settings</div>
        </div>
    </nav>

    <script>
        const msgs = document.getElementById('msgs'), inp = document.getElementById('inp'), taps = {};
        function go(p, e) { document.querySelectorAll('.page').forEach(x => x.classList.remove('active')); document.getElementById(p).classList.add('active'); document.querySelectorAll('.nav-btn').forEach(x => x.classList.remove('active')); e.classList.add('active') }
        function tap(e, a) { const n = Date.now(), t = taps[a] || 0; n - t < 300 ? (e.classList.remove('active'), cmd('close ' + a), taps[a] = 0) : (e.classList.add('active'), cmd('open ' + a), taps[a] = n) }
        function add(t, c) { const m = document.createElement('div'); m.className = 'msg ' + c; m.innerHTML = '<div class="bubble">' + t + '</div>'; msgs.appendChild(m); msgs.scrollTop = msgs.scrollHeight }
        function load() { const m = document.createElement('div'); m.className = 'msg nova'; m.id = 'ld'; m.innerHTML = '<div class="bubble"><span class="spinner"></span></div>'; msgs.appendChild(m); msgs.scrollTop = msgs.scrollHeight }
        function unload() { const e = document.getElementById('ld'); if (e) e.remove() }
        async function send() { const c = inp.value.trim(); if (!c) return; add(c, 'user'); inp.value = ''; load(); try { const r = await fetch('/send', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ command: c }) }); const d = await r.json(); unload(); add(d.response || 'Done.', 'nova') } catch (e) { unload(); add('Error.', 'nova') } }
        async function cmd(c) { try { await fetch('/send', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ command: c }) }) } catch (e) { } }
        let pin = '';
        function showPin() { const o = document.createElement('div'); o.id = 'pin-overlay'; o.innerHTML = '<div style="font-size:36px">🔐</div><h2>Enter PIN</h2><div id="pin-display">____</div><div id="pin-pad">' + [1, 2, 3, 4, 5, 6, 7, 8, 9, '⌫', 0, '✓'].map(n => '<button class="pin-key' + (n === '⌫' ? ' back' : n === '✓' ? ' confirm' : '') + '" onclick="' + (n === '⌫' ? 'pinBack()' : n === '✓' ? 'pinOk()' : "pinIn('" + n + "')") + '">' + n + '</button>').join('') + '</div><button class="pin-cancel" onclick="pinClose()">Cancel</button>'; document.body.appendChild(o); pin = '' }
        function pinDisp() { const d = document.getElementById('pin-display'); if (d) { let s = ''; for (let i = 0; i < 4; i++)s += i < pin.length ? '●' : '_'; d.textContent = s } }
        function pinIn(n) { if (pin.length < 4) { pin += n; pinDisp(); if (pin.length === 4) setTimeout(pinOk, 150) } }
        function pinBack() { pin = pin.slice(0, -1); pinDisp() }
        async function pinOk() { const d = document.getElementById('pin-display'); try { const r = await fetch('/send', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ command: 'pin_unlock:' + pin }) }); const data = await r.json(); if (data.response && data.response.toLowerCase().includes('unlocked')) { d.style.color = 'var(--success)'; d.textContent = '✓✓✓✓'; setTimeout(pinClose, 400) } else { d.style.color = 'var(--danger)'; d.textContent = '✗✗✗✗'; setTimeout(() => { pin = ''; d.style.color = 'var(--accent)'; pinDisp() }, 400) } } catch (e) { } }
        function pinClose() { const o = document.getElementById('pin-overlay'); if (o) o.remove(); pin = '' }
        async function stat() { try { const r = await fetch('/status'); const d = await r.json(); const c = d.cpu || 0, m = d.memory || 0, b = d.battery ?? 100, k = d.disk || 0; document.getElementById('cpu').innerHTML = c + '<span class="stat-unit">%</span>'; document.getElementById('mem').innerHTML = m + '<span class="stat-unit">%</span>'; document.getElementById('bat').innerHTML = b + '<span class="stat-unit">%</span>' + (d.charging ? '⚡' : ''); document.getElementById('disk').innerHTML = k + '<span class="stat-unit">%</span>'; document.getElementById('cpu').style.color = c < 50 ? 'var(--success)' : c < 80 ? 'var(--warning)' : 'var(--danger)'; document.getElementById('mem').style.color = m < 60 ? 'var(--success)' : m < 85 ? 'var(--warning)' : 'var(--danger)'; document.getElementById('bat').style.color = b < 20 ? 'var(--danger)' : b < 50 ? 'var(--warning)' : 'var(--success)'; document.getElementById('disk').style.color = k < 70 ? 'var(--success)' : k < 90 ? 'var(--warning)' : 'var(--danger)'; document.getElementById('cpuM').style.transform = 'scaleX(' + c / 100 + ')'; document.getElementById('memM').style.transform = 'scaleX(' + m / 100 + ')'; document.getElementById('batM').style.transform = 'scaleX(' + b / 100 + ')'; document.getElementById('diskM').style.transform = 'scaleX(' + k / 100 + ')' } catch (e) { } }
        inp.addEventListener('keypress', e => { if (e.key === 'Enter') send() }); stat(); setInterval(stat, 5000)
    </script>
</body>

</html>'''


class BleServer:
    """
    BLE-style Server for NOVA with premium mobile UI.
    Uses HTTP bridge for maximum compatibility.
    """
    
    def __init__(self, nova_instance=None):
        self.nova = nova_instance
        self.server = None
        self.thread = None
        self.running = False
        self.device_name = "Gigatron"
        self.port = 8888
        self.responses = []

    def start(self, name: str = "Nova-BLE"):
        """Start the BLE bridge server in a background thread."""
        import socket
        self.device_name = name
        self.running = True
        
        # Get local IP and print immediately
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
        except:
            local_ip = "localhost"
        
        print(f"\n✓ BLE Bridge Server '{self.device_name}' started!")
        print(f"  📱 iPhone Connection: http://{local_ip}:{self.port}")
        print(f"  🔗 Service UUID: {UART_SERVICE_UUID}")
        print("  Open this URL on your iPhone to connect!\n")
        
        # Start server in background
        self.thread = threading.Thread(target=self._run_server_silent, daemon=True)
        self.thread.start()
        return True

    def _run_server_silent(self):
        """Run HTTP server silently (message already printed)."""
        try:
            handler = self._create_handler()
            self.server = HTTPServer(('0.0.0.0', self.port), handler)
            
            while self.running:
                self.server.handle_request()
        except Exception as e:
            print(f"BLE Bridge Error: {e}")
            self.running = False

    def _run_server(self):
        """Run HTTP server as BLE bridge (with messages)."""
        try:
            handler = self._create_handler()
            self.server = HTTPServer(('0.0.0.0', self.port), handler)
            
            # Get local IP
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            print(f"\n✓ BLE Bridge Server '{self.device_name}' started!")
            print(f"  iPhone Connection: http://{local_ip}:{self.port}")
            print(f"  Service UUID: {UART_SERVICE_UUID}")
            print("  Use any HTTP client or browser on your iPhone to connect.\n")
            
            while self.running:
                self.server.handle_request()
        except Exception as e:
            print(f"BLE Bridge Error: {e}")
            self.running = False

    def _create_handler(self):
        """Create HTTP request handler with access to BleServer instance."""
        server_ref = self
        
        class BLEBridgeHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress HTTP logs
            
            def do_GET(self):
                """Handle GET requests."""
                if self.path == '/status':
                    try:
                        import psutil
                        battery = psutil.sensors_battery()
                        disk = psutil.disk_usage('/')
                        status = {
                            'device': server_ref.device_name,
                            'cpu': round(psutil.cpu_percent(interval=0.1), 1),
                            'memory': round(psutil.virtual_memory().percent, 1),
                            'battery': round(battery.percent) if battery else 100,
                            'charging': battery.power_plugged if battery else True,
                            'disk': round(disk.percent, 1),
                            'running': server_ref.running
                        }
                    except Exception as e:
                        status = {'device': server_ref.device_name, 'running': True, 'cpu': 0, 'memory': 0, 'battery': 100, 'disk': 0, 'error': str(e)}
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(status).encode())
                
                else:
                    # Serve premium mobile UI
                    html = MOBILE_UI_HTML.replace('{device_name}', server_ref.device_name)
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                    self.send_header('Pragma', 'no-cache')
                    self.send_header('Expires', '0')
                    self.end_headers()
                    self.wfile.write(html.encode('utf-8'))
            
            def do_POST(self):
                """Handle POST requests - commands from phone."""
                if self.path == '/send':
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    
                    try:
                        data = json.loads(post_data.decode('utf-8'))
                        command = data.get('command', '')
                        
                        # Process command
                        response = server_ref._process_command(command)
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({'response': response}).encode())
                    except Exception as e:
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': str(e)}).encode())
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def do_OPTIONS(self):
                """Handle CORS preflight."""
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
        
        return BLEBridgeHandler

    def _process_command(self, command: str) -> str:
        """Process incoming command from phone with full Nova integration."""
        try:
            lower_cmd = command.lower().strip()
            
            # PIN-based unlock (4-digit passcode)
            if lower_cmd.startswith('pin_unlock:'):
                entered_pin = command.split(':', 1)[1].strip() if ':' in command else ''
                correct_pin = getattr(self, 'unlock_pin', '1234')  # Default PIN is 1234
                
                if entered_pin == correct_pin:
                    import ctypes
                    import subprocess
                    import time
                    
                    # Wake PC
                    ctypes.windll.user32.mouse_event(0x0001, 1, 0, 0, 0)
                    time.sleep(0.3)
                    
                    # Type the Windows PIN/password if set
                    if hasattr(self, 'windows_pin') and self.windows_pin:
                        subprocess.run(['powershell', '-Command', 
                            f'(New-Object -ComObject WScript.Shell).SendKeys("{self.windows_pin}{{ENTER}}")'], 
                            capture_output=True)
                        return "🔓 PC unlocked successfully!"
                    else:
                        # Just wake and send Enter
                        subprocess.run(['powershell', '-Command', 
                            '(New-Object -ComObject WScript.Shell).SendKeys("{ENTER}")'], 
                            capture_output=True)
                        return "🔓 PC unlocked! (Set Windows PIN with /winpin XXXX)"
                else:
                    return "❌ Incorrect PIN. Try again."
            
            # Set app unlock PIN
            elif lower_cmd.startswith('/setpin ') or lower_cmd.startswith('setpin '):
                pin = command.split(' ', 1)[1].strip() if ' ' in command else ''
                if pin and len(pin) == 4 and pin.isdigit():
                    self.unlock_pin = pin
                    return f"🔐 App PIN changed to {pin}!"
                return "Usage: /setpin XXXX (4 digits)"
            
            # Set Windows login PIN  
            elif lower_cmd.startswith('/winpin ') or lower_cmd.startswith('winpin '):
                pin = command.split(' ', 1)[1].strip() if ' ' in command else ''
                if pin:
                    self.windows_pin = pin
                    return f"🔐 Windows PIN set! Unlock will now auto-type it."
                return "Usage: /winpin YOUR_WINDOWS_PIN"
            
            # Face ID Unlock - Wake PC and unlock (legacy)
            elif lower_cmd in ['faceid_unlock', 'unlock', '/unlock']:
                import ctypes
                import subprocess
                import time
                
                ctypes.windll.user32.mouse_event(0x0001, 1, 0, 0, 0)
                time.sleep(0.3)
                subprocess.run(['powershell', '-Command', 
                    '(New-Object -ComObject WScript.Shell).SendKeys("{ENTER}")'], 
                    capture_output=True)
                return "🔓 PC woken up!"
            
            # Wake PC from sleep
            elif lower_cmd in ['wake', '/wake', 'wake up', 'wakeup']:
                import ctypes
                ctypes.windll.user32.mouse_event(0x0001, 1, 0, 0, 0)
                return "☀️ PC is awake!"
            
            # Brightness Up
            elif lower_cmd in ['brightness up', 'bright up', 'brighter', '/brightup']:
                import subprocess
                subprocess.run(['powershell', '-Command', 
                    '''$brightness = (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness;
                    $new = [Math]::Min(100, $brightness + 10);
                    (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, $new)'''], 
                    capture_output=True)
                return "🔆 Brightness increased!"
            
            # Brightness Down
            elif lower_cmd in ['brightness down', 'bright down', 'dimmer', '/brightdown']:
                import subprocess
                subprocess.run(['powershell', '-Command', 
                    '''$brightness = (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness;
                    $new = [Math]::Max(0, $brightness - 10);
                    (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, $new)'''], 
                    capture_output=True)
                return "🔅 Brightness decreased!"
            
            # Volume Up
            elif lower_cmd in ['volume up', 'vol up', 'louder', '/volup']:
                import subprocess
                subprocess.run(['powershell', '-Command', 
                    '(New-Object -ComObject WScript.Shell).SendKeys([char]175)'], 
                    capture_output=True)
                return "🔊 Volume increased!"
            
            # Volume Down
            elif lower_cmd in ['volume down', 'vol down', 'quieter', '/voldown']:
                import subprocess
                subprocess.run(['powershell', '-Command', 
                    '(New-Object -ComObject WScript.Shell).SendKeys([char]174)'], 
                    capture_output=True)
                return "🔈 Volume decreased!"
            
            # Clear Temp Files
            elif lower_cmd in ['clear temp', 'clean temp', 'clear cache', 'clean', '/clean', '/cleartemp']:
                import subprocess
                import shutil
                import tempfile
                
                cleaned_mb = 0
                temp_dirs = [
                    tempfile.gettempdir(),
                    os.path.expandvars(r'%LOCALAPPDATA%\Temp'),
                    os.path.expandvars(r'%WINDIR%\Temp'),
                ]
                
                for temp_dir in temp_dirs:
                    try:
                        if os.path.exists(temp_dir):
                            for item in os.listdir(temp_dir):
                                item_path = os.path.join(temp_dir, item)
                                try:
                                    if os.path.isfile(item_path):
                                        size = os.path.getsize(item_path)
                                        os.remove(item_path)
                                        cleaned_mb += size
                                    elif os.path.isdir(item_path):
                                        size = sum(os.path.getsize(os.path.join(dp, f)) 
                                                   for dp, dn, fn in os.walk(item_path) for f in fn)
                                        shutil.rmtree(item_path, ignore_errors=True)
                                        cleaned_mb += size
                                except:
                                    pass
                    except:
                        pass
                
                # Also clean Windows prefetch and recent
                try:
                    subprocess.run(['powershell', '-Command', 
                        'Remove-Item -Path "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue'],
                        capture_output=True)
                except:
                    pass
                
                mb_freed = round(cleaned_mb / (1024 * 1024), 1)
                return f"🧹 Cleaned! Freed {mb_freed} MB of temp files."
            
            # System Control Commands
            elif lower_cmd in ['lock', '/lock', 'lock screen', 'lock pc']:
                import ctypes
                ctypes.windll.user32.LockWorkStation()
                return "🔒 System locked successfully!"
            
            elif lower_cmd in ['sleep', '/sleep', 'sleep mode', 'go to sleep']:
                os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
                return "😴 System entering sleep mode..."
            
            elif lower_cmd in ['shutdown', '/shutdown', 'shut down', 'turn off']:
                os.system('shutdown /s /t 5')
                return "⏻ Shutting down in 5 seconds... (Run 'shutdown /a' to cancel)"
            
            elif lower_cmd in ['restart', '/restart', 'reboot']:
                os.system('shutdown /r /t 5')
                return "🔄 Restarting in 5 seconds..."
            
            elif lower_cmd in ['mute', '/mute', 'silence', 'quiet']:
                try:
                    from ctypes import cast, POINTER
                    from comtypes import CLSCTX_ALL
                    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                    devices = AudioUtilities.GetSpeakers()
                    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    volume = cast(interface, POINTER(IAudioEndpointVolume))
                    volume.SetMute(1, None)
                    return "🔇 System muted!"
                except:
                    # Fallback using PowerShell
                    import subprocess
                    subprocess.run(['powershell', '-Command', 
                        '(New-Object -ComObject WScript.Shell).SendKeys([char]173)'], 
                        capture_output=True)
                    return "🔇 Mute toggled!"
            
            elif lower_cmd in ['/status', 'status']:
                import psutil
                cpu = psutil.cpu_percent()
                mem = psutil.virtual_memory().percent
                battery = psutil.sensors_battery()
                bat_str = f"{round(battery.percent)}%" if battery else "N/A"
                return f"📊 System Status:\n• CPU: {cpu}%\n• Memory: {mem}%\n• Battery: {bat_str}"
            
            # App Launch Commands
            elif lower_cmd.startswith('open '):
                app = lower_cmd.replace('open ', '').strip()
                app_map = {
                    'chrome': 'chrome', 'browser': 'chrome', 'google': 'chrome',
                    'spotify': 'spotify:', 'music': 'spotify:',
                    'discord': 'discord:',
                    'code': 'code', 'vscode': 'code', 'vs code': 'code',
                    'explorer': 'explorer', 'files': 'explorer',
                    'notepad': 'notepad', 'notes': 'notepad',
                    'settings': 'ms-settings:', 'calc': 'calc', 'calculator': 'calc',
                    'terminal': 'wt', 'cmd': 'cmd', 'powershell': 'powershell',
                    'whatsapp': 'whatsapp:', 'youtube': 'https://youtube.com',
                    'teams': 'msteams:', 'outlook': 'outlook', 'mail': 'outlook',
                    'edge': 'msedge', 'word': 'winword', 'excel': 'excel',
                    'powerpoint': 'powerpnt', 'ppt': 'powerpnt',
                    'onenote': 'onenote', 'slack': 'slack:',
                    'zoom': 'zoommtg:', 'telegram': 'telegram:',
                    'notion': 'notion:', 'figma': 'figma:',
                    'photoshop': 'photoshop', 'premiere': 'premiere',
                    'obs': 'obs64', 'steam': 'steam:', 'epic': 'com.epicgames.launcher:',
                }
                
                # First try app_cache.json for all installed apps
                try:
                    cache_path = os.path.join(SCRIPT_DIR, 'app_cache.json')
                    if os.path.exists(cache_path):
                        with open(cache_path, 'r', encoding='utf-8') as f:
                            app_cache = json.load(f)
                        # Check if app is in cache
                        if app in app_cache:
                            os.system(f'start "" "{app_cache[app]}"')
                            return f"🚀 Opening {app.title()}..."
                        # Try partial match
                        for cached_name, path in app_cache.items():
                            if app in cached_name or cached_name in app:
                                os.system(f'start "" "{path}"')
                                return f"🚀 Opening {cached_name.title()}..."
                except:
                    pass
                
                # Fall back to app_map
                cmd = app_map.get(app, app)
                os.system(f'start {cmd}')
                return f"🚀 Opening {app.title()}..."
            
            elif lower_cmd.startswith('close '):
                app = lower_cmd.replace('close ', '').strip()
                process_map = {
                    'chrome': 'chrome.exe', 'spotify': 'Spotify.exe',
                    'discord': 'Discord.exe', 'code': 'Code.exe',
                    'notepad': 'notepad.exe', 'explorer': 'explorer.exe',
                    'whatsapp': 'WhatsApp.exe', 'teams': 'Teams.exe',
                    'outlook': 'OUTLOOK.EXE', 'edge': 'msedge.exe',
                    'word': 'WINWORD.EXE', 'excel': 'EXCEL.EXE',
                    'powerpoint': 'POWERPNT.EXE', 'onenote': 'ONENOTE.EXE',
                    'slack': 'slack.exe', 'zoom': 'Zoom.exe',
                    'telegram': 'Telegram.exe', 'notion': 'Notion.exe',
                    'figma': 'Figma.exe', 'obs': 'obs64.exe',
                    'steam': 'steam.exe',
                    # New apps added
                    'vlc': 'vlc.exe', 'vlc media player': 'vlc.exe',
                    'terminal': 'WindowsTerminal.exe', 'wt': 'WindowsTerminal.exe',
                    'git bash': 'git-bash.exe', 'git': 'git-bash.exe',
                    'mysql': 'MySQLWorkbench.exe', 'mysql workbench': 'MySQLWorkbench.exe',
                    'visual studio': 'devenv.exe', 'visual studio 2022': 'devenv.exe', 'vs 2022': 'devenv.exe',
                    'roblox': 'RobloxPlayerBeta.exe', 'roblox player': 'RobloxPlayerBeta.exe',
                    'roblox studio': 'RobloxStudioBeta.exe',
                    'idm': 'IDMan.exe', 'internet download manager': 'IDMan.exe',
                    'task manager': 'Taskmgr.exe', 'taskmgr': 'Taskmgr.exe',
                    'youtube': 'chrome.exe',  # YouTube runs in browser
                    'settings': 'SystemSettings.exe',
                    'calc': 'Calculator.exe', 'calculator': 'Calculator.exe',
                }
                proc = process_map.get(app, f'{app}.exe')
                os.system(f'taskkill /f /im {proc} 2>nul')
                return f"❌ Closed {app.title()}"
            
            # Time/Date
            elif lower_cmd in ['time', 'what time', "what's the time", 'current time']:
                now = datetime.now().strftime('%I:%M %p')
                return f"🕐 Current time: {now}"
            
            elif lower_cmd in ['date', "what's the date", 'current date', 'today']:
                today = datetime.now().strftime('%A, %B %d, %Y')
                return f"📅 Today is {today}"
            
            # AI Chat - Use Groq if available, otherwise use Nova's processor
            else:
                # Try Groq AI first
                if GROQ_CLIENT:
                    try:
                        completion = GROQ_CLIENT.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[
                                {"role": "system", "content": "You are Nova, a helpful AI assistant. Keep responses concise but friendly. Use emojis occasionally."},
                                {"role": "user", "content": command}
                            ],
                            max_tokens=500,
                            temperature=0.7
                        )
                        return completion.choices[0].message.content
                    except Exception as e:
                        pass
                
                # Fallback to Nova's processor
                if self.nova:
                    return self.nova.process(command)
                
                # Final fallback
                return f"I received: '{command}'. For AI responses, please ensure Groq API is configured."
                
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def stop(self):
        """Stop the BLE bridge server."""
        self.running = False
        if self.server:
            self.server.shutdown()
        print("BLE Bridge server stopped.")


if __name__ == "__main__":
    # Standalone test
    server = BleServer()
    if server.start():
        try:
            print("Server running. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            server.stop()
