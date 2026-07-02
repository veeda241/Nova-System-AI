# NOVA System AI - Master Technical Manual v2.0

## 1. SYSTEM INTRODUCTION
NOVA (Natural Operational Voice Assistant) is an advanced autonomous agent framework designed for deep integration with the Windows operating system. It represents a paradigm shift from simple chatbots to proactive, agentic entities capable of managing complexity, ensuring security, and self-optimizing over time.

### 1.1 Design Philosophy
- **Privacy-First Intelligence**: Support for local LLMs (Ollama) ensures sensitive data never leaves the host machine.
- **Resilient Architecture**: A decentralized neural bridge with automatic failover across multiple AI providers.
- **Agentic Autonomy**: Capable of decomposition, planning, execution, and self-correction without constant user oversight.
- **Human-Centric Interface**: A graphical HUD and voice system that mimics high-fidelity cinematic AI experience.

---

## 2. MULTI-MODEL BRAIN ARCHITECTURE
The brain of Nova is not a single model but a unified interface (the 'MultiModelBrain') that orchestrates multiple backends based on availability, speed, and capability context.

### 2.1 Backend Specification
| Backend Name | Tier | Primary Use-Case | Key Feature |
|--------------|------|------------------|-------------|
| Ollama | P1 (Local) |     Privacy & Offline | Local Llama-3/Mistral |
| Groq | P2 (Fast) | Real-time Voice/Chat | Llama-3.3 70B (Sub-sec) |
| Gemini | P3 (Deep) | Complex Coding/Doc | 1M+ Context Window |
| OpenAI | P4 (Legacy) | General Planning | GPT-4o Reliability |

### 2.2 Failover Logic Flow
When a prompt is received, the Brain executes the following sequence:
1.  **Backend Health Check**: Verifies local server status (11434) and Cloud API key validity.
2.  **Context Matching**: Selects model based on task complexity (e.g., Coding tasks prioritize Gemini).
3.  **Retries**: If an HTTP 429 (Rate Limit) occurs on Groq, the system falls back to Ollama.
4.  **Status Reporting**: Logs the current 'Active Brain' to the telemetry HUD.

---

## 3. NEURAL INTENT ENGINE (NIE)
The NIE is a specialized neural classification layer that handles critical system commands with ultra-low latency. It is built entirely in NumPy to avoid framework overhead.

### 3.1 hyperparameter Configuration
```json
{
    "model_type": "TinyTransformerClassifier",
    "embedding_dim": 64,
    "num_layers": 2,
    "attention_heads": 2,
    "feedforward_dim": 256,
    "vocab_size": 1000,
    "max_seq_len": 32,
    "num_classes": 9,
    "activation": "ReLU + Softmax"
}
```

### 3.2 Mathematical Framework
The NIE utilizes scaled dot-product attention to weight token importance:
- **Projections**: Q = XWq, K = XWk, V = XWv
- **Scored Weights**: W = softmax( (QK^T) / sqrt(64) )
- **Output**: Y = W V Wo

Training is performed via Stochastic Gradient Descent (SGD) with a momentum of 0.9, ensuring fast convergence on low-sample intent data.

---

## 4. AUTONOMOUS MCP AGENT SYSTEM
The Agent is Nova's action-oriented layer. It moves beyond conversation into task execution using the Model Context Protocol.

### 4.1 ReAct Control Loop
Nova's agent follows the ReAct (Reasoning + Acting) pattern:
- **Observe**: Inspects the current directory, OS status, and active processes.
- **Think**: The LLM generates a internal monologue explaining 'why' a tool is needed.
- **Act**: Selecting a tool from the ToolRegistry and generating the JSON parameters.
- **Evaluate**: Analyzing the result. If a FileNotFoundError occurs, the agent self-corrects.

### 4.2 The Tool Registry
| Tool Name | Module | Description |
|-----------|--------|-------------|
| WebSearch | nova_tools.py | DuckDuckGo/Wikipedia Scraping |
| AppFinder | interface/cli.py | Fuzzy-match local app launcher |
| ScreenAnalysis | interface/gui.py | OCR and Visual Scene Description |
| PythonExec | agent/tools.py | Sandboxed script execution |
| GitControl | nova_tools.py | Commit, Push, Log automation |
| DocManager | nova_pm.py | Project-level documentation |

---

## 5. UNIFIED CONTROL ENGINE (UCE)
The UCE is the automation core that translates high-level brain decisions into low-level Windows API calls.

### 5.1 App-Wide Control Layer (AWCL)
AWCL provides specific hooks for common applications:
- **Web Browsers**: URL navigation and search injection.
- **Media Players**: Playback, shuffle, and volume sync.
- **Code Editors**: File opening and syntax handling.

### 5.2 Human-Action Simulation (HASE)
HASE mimics human input using randomized bezier curves for mouse movement and jittery typing to ensure OS stability and compatibility with applications lacking official APIs.

---

## 6. NOVA OS INTERFACE v2.0
The Laptop Interface is a PyQt6-based HUD providing a premium visual experience with real-time telemetry.

### 6.1 Component Architecture
- **Neural Core**: A central animated ring indicating AI processing states.
- **Telemetry Bar**: Real-time graphs for CPU, RAM, and Battery.
- **Eye of Nova**: A vision port that captures and displays vision analysis results.

---

## 7. NEURAL EVOLUTION & LEARNING
Nova is a learning system. Every interaction contributes to a localized knowledge base.

### 7.1 Self-Programming Engine
Allows Nova to modify its own code:
- **Refactor**: existing functions based on performance logs.
- **Hotfixes**: Apply automated fixes to script errors.
- **Skill Acquisition**: Create new JSON templates for workflows.

---

## 8. MODULE REFERENCE
| File | Role |
|------|------|
| `interface/cli.py` | Master Controller & CLI UI |
| `interface/gui.py` | PyQt6 Master HUD Interface |
| `multi_model_brain.py` | AI Provider Orchestration |
| `enhanced_agent.py` | Task Planning & Execution Loop |
| `nova_tools.py` | Core Utility Suite |
| `self_programming.py` | Code Modification Logic |
| `nova_automation.py` | Windows API & UCE Wrapper |
