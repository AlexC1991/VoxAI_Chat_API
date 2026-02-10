# Walkthrough - Loading openai/gpt-oss-20b on RunPod

I have successfully loaded the `openai/gpt-oss-20b` model on RunPod using vLLM.

## Problem
The `openai/gpt-oss-20b` model requires a very recent version of the `transformers` library to recognize its custom `gpt_oss` architecture.
- **Issue 1:** The default RunPod vLLM images (e.g., v0.6.3) were too old and lacked this support.
- **Issue 2:** The `latest` vLLM image (v0.7.0+) required CUDA 12.9 drivers, which are not yet available on standard RunPod instances (which use CUDA 12.1/12.4), causing container startup failures.

## Solution
I implemented a **Runtime Installation Strategy**:
1.  **Base Image:** Switched to a standard, compatible `runpod/pytorch:2.2.0-py3.10-cuda12.1.1-devel-ubuntu22.04` image. This ensures the container creates successfully on the host.
2.  **Runtime Setup:** Modified the startup command to install the latest `vllm` and `transformers` libraries *inside* the container before starting the server.
    ```bash
    pip install --upgrade pip && pip install vllm transformers && python3 -m vllm.entrypoints.openai.api_server ...
    ```
3.  **Robust Command Passing:** Refactored `runpod_interface.py` to correctly pass this complex command string to `runpodctl` using the `--args` flag, ensuring it is executed properly by the container's entrypoint.

## Results
- The pod now creates successfully.
- It automatically updates to the latest vLLM (v0.15.1+).
- The logs confirm: `Resolved architecture: GptOssForCausalLM`.
- The model loads and the API server starts.

## Verified Logs
```
INFO 02-10 03:24:20 [model.py:541] Resolved architecture: GptOssForCausalLM
INFO 02-10 03:24:26 [vllm.py:624] Asynchronous scheduling is enabled.
```
