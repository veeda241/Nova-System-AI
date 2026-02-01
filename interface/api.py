#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nova API
========
Flask-based REST API for Nova System.
Provides /query endpoint for the SimpliSmart UI.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from nova_system.workflow import NovaOrchestrator
import threading

app = Flask(__name__)
CORS(app) # Enable CORS for UI cross-origin requests

orchestrator = NovaOrchestrator()

@app.route('/query', methods=['POST'])
def query():
    data = request.json
    if not data or 'query' not in data:
        return jsonify({"error": "Missing 'query' field"}), 400
    
    user_query = data['query']
    result = orchestrator.process_query(user_query)
    
    return jsonify(result)

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "status": "online",
        "name": "Nova OS API",
        "version": "2.1"
    })

def run_api(port=5000):
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    print("🚀 Nova API starting on port 5000...")
    run_api()
