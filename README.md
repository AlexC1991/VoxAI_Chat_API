# VOX-AI Chat Engine

A lightweight, high-performance LLM chat engine optimized for local hardware (APUs/CPUs/GPUs).

## Features

- **Hardware Optimized**: Automatically detects your hardware (APU, CUDA, CPU) and configures the fastest settings.
- **Portable**: Works with `llama.cpp` shared libraries mostly out of the box (requires DLLs in root).
- **Dual Mode**:
  - **CLI Mode**: Run `start.bat` for an interactive chat terminal.
  - **API Mode**: Import `vox_api` to use in your own Python applications.

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Interactive Chat**:
   Double-click `start.bat` or run:
   ```bash
   python main.py
   ```

## Integration (For Developers)

To use VOX-AI in your own software, use the `vox_api` module.

```python
from vox_api import VoxAPI

# 1. Initialize (Auto-detects model and hardware)
engine = VoxAPI()

# 2. Chat (Streaming)
print("Bot: ", end="")
for token in engine.chat("Hello!", stream=True):
    print(token, end="", flush=True)

# 3. Chat (Non-Streaming)
response = engine.chat("Tell me a fact.", stream=False)
print(response)

# 4. Clear Context
engine.clear_history()
```

## Hardware Support

- **APU (Ryzen/Radeon)**: Full support via Vulkan backend (default).
- **NVIDIA GPU**: Supports CUDA if `ggml-cuda.dll` is present.
- **CPU**: Falls back to optimized CPU inference if no GPU found.

## Project Structure

- `main.py`: The launcher script. Checks environment and verifying files.
- `vox_api.py`: The integration layer. Use this for your apps.
- `vox_core_chat.py`: The interactive CLI chat interface.
- `machine_engine_handshake.py`: Hardware detection logic.
- `debug_engine.py`: Benchmarking tool to test performance.
