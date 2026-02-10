# VoxAI_Chat_API

```text
██╗   ██╗ ██████╗ ██╗  ██╗       █████╗ ██╗
██║   ██║██╔═══██╗╚██╗██╔╝      ██╔══██╗██║
██║   ██║██║   ██║ ╚███╔╝ █████╗███████║██║
╚██╗ ██╔╝██║   ██║ ██╔██╗ ╚════╝██╔══██║██║
 ╚████╔╝ ╚██████╔╝██╔╝ ██╗      ██║  ██║██║
  ╚═══╝   ╚═════╝ ╚═╝  ╚═╝      ╚═╝  ╚═╝╚═╝
```
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![RunPod Ready](https://img.shields.io/badge/RunPod-Serverless-purple)](https://docs.runpod.io/serverless/overview)
[![Status: Stable](https://img.shields.io/badge/Status-Stable-green)](https://github.com/)

**A Hybrid Local/Cloud Architecture for Large Language Models.**

VoxAI is a specialized Python-based interface designed to seamlessly bridge the gap between local hardware (APUs/Consumer GPUs) and high-performance cloud infrastructure (RunPod). It allows users to run efficient models locally while instantly "bursting" to the cloud for massive 70B+ parameter models, all within a single, unified chat interface.

## 📋 Table of Contents
- [Key Features](#-key-features)
- [Quick Start](#-quick-start)
- [Customization](#-customization)
- [Usage Examples](#-usage-examples)
- [Project Structure](#-project-structure)

## 🌟 Key Features

### 🛡️ Hybrid Engine (Local + Cloud)
*   **Local Mode**: Optimized for consumer hardware (e.g., AMD RX 6600, NVIDIA RTX 3060). Uses `llama-cpp-python` with Vulkan/CUDA acceleration for standard models like `Qwen 7B` and `Llama 3`.
*   **Cloud Mode**: Instant uplink to RunPod serverless GPUs (A40, A6000, A100) for running heavyweights like `Midnight-Miqu 70B` and `Qwen2.5 72B`.

### 🔄 Smart Swapping & Auto-Healing
*   **In-Pod Swapping**: Hot-swaps models *inside* the running container to reuse the GPU, reducing switch time from ~5 minutes to seconds.
*   **Zombie Process Protection**: If an in-pod swap fails (e.g., library mismatch), the system automatically detects the failure, kills the "zombie" pod, and spins up a fresh compatible instance.

### 💰 Cost Efficiency
*   **Tiered GPU Selection**: Automatically selects the cheapest viable GPU.
    *   *Small Models (<30B)*: Rents an RTX A40/A6000 (~$0.30/hr).
    *   *Ultra Models (70B+)*: Rents an A100 80GB (~$1.79/hr).
*   **Auto-Shutdown**: Prevents billing accidents by terminating cloud resources on exit.

## 🚀 Quick Start

### 1. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/yourusername/VoxAI_Chat_API.git
cd VoxAI_Chat_API
pip install python==3.10
pip install -r requirements.txt
```

### 2. Configuration
Rename the template and add your API keys:
```bash
mv config.example.py config.py
```
Edit `config.py`:
```python
API_KEY = "YOUR_RUNPOD_API_KEY"
POD_ID = "YOUR_POD_ID" # Optional: Initial Pod ID
```

### 3. Usage
Launch the unified start script:
```bash
start.bat
```
You will be prompted to select your environment:
```text
[1] LOCAL (RX 6600) | [2] CLOUD (RunPod)
```

## 🛠️ Customization

### Adding Your Own Models
To add a new model to the menu, simply edit the `MODEL_MAP` in your `config.py` file.

**Format:** `"Menu Display Name": "Local Filename"`

```python
MODEL_MAP = {
    # ... existing models ...
    "My New Cool Model": "my-model-v1.gguf",
}
```
*Note: Ensure the `.gguf` file is placed inside the `models/` directory.*

## 🎮 Usage Examples

### Local GGUF Loading (Hardware Handshake)
VoxAI performs a hardware handshake on boot to determine optimal thread counts and GPU layers.
*Performance: Local 14B models typically respond in <15s on mid-range hardware.*

```text
[LOCAL] 🛡️ Loading GGUF: models/Qwen3-VL-8B-Instruct.gguf...
[HANDSHAKE] Detected 4 Physical Cores. Mode: APU (Hybrid/Vulkan)
[LOCAL] 🟢 Backend drivers loaded manually.
[LOCAL] ✅ Engine Online.
```

### The "Zombie" Recovery (Self-Healing)
During testing, swapping from a 70B model (A100) to a 14B model (A40) caused a library mismatch. VoxAI self-corrected in <45s.

```text
[PHOENIX] 🔥 Initiating Swap...
[PHOENIX] ♻️  Optimizing: Reusing active GPU...
[DEBUG] Valid Endpoint, but ID mismatch (1/5): 'openai/gpt-oss-20b' != 'Qwen/Qwen3-14B'
[PHOENIX] ❌ Swap Verification Failed: Persistent Old Model Detected.
[PHOENIX] ⚠️ In-Pod Swap failed. Retrying with fresh pod...
[PHOENIX] ☠️ Terminating old pod...
[PHOENIX] 🐣 Renting NVIDIA A40...
[PHOENIX] ✅ Online! Serving: Qwen/Qwen3-14B
```

### Creative Generation
**User**: "Can u write me a song Like AJR kinda song?"
**VoxAI (Qwen 14B)**: 
> *Title: "Echoes in the Static"*
> *Verse 1: Driving through the city, dashboard lights are glowing...*
> *Chorus: I hear echoes in the static, whispers in the noise...*

## 📂 Project Structure
*   `start.bat` - Main entry point.
*   `vox_core_chat.py` - The brain. Handles input, local inference, and cloud orchestration.
*   `runpod_interface.py` - The driver. Manages RunPod API, renting, and swapping.
*   `machine_engine_handshake.py` - Hardware detection logic for local optimization.
*   `config.py` - User settings (GitIgnored).

## 📄 License
This project is open-source. Feel free to fork and modify!
