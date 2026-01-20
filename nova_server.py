#!/usr/bin/env python3
"""
NOVA GUI Server
================
A Flask-based web server that provides a sleek GUI for the Nova Core Assistant.
Run with: python nova_server.py
Then visit: http://127.0.0.1:5000
"""

from flask import Flask, render_template, request, jsonify
import os
import sys

# Add script directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nova_lite import NovaCoreAssistant

app = Flask(__name__)
assistant = NovaCoreAssistant(user_name="Vyas")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_input = data.get('message', '') if data else ''
    
    if not user_input:
        return jsonify({'response': "I didn't catch that. Please try again."})
    
    response = assistant.process(user_input)
    return jsonify({'response': response})

@app.route('/status', methods=['GET'])
def status():
    """Get system status for dashboard."""
    return jsonify({
        'brain': 'connected' if assistant.brain else 'offline',
        'user': assistant.user_name,
        'plugins': list(assistant.plugins.keys())
    })

if __name__ == '__main__':
    print("""
    ╔═══════════════════════════════════════════════════╗
    ║            NOVA GUI SERVER                        ║
    ║   Starting at http://127.0.0.1:5000               ║
    ╚═══════════════════════════════════════════════════╝
    """)
    app.run(debug=True, port=5000, host='127.0.0.1')

