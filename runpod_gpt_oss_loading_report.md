# RunPod gpt-oss-20b Loading Investigation Report

## 1. Objective
Successfully load the `openai/gpt-oss-20b` model on a RunPod cloud GPU instance using the vLLM inference engine, ensuring that the custom `gpt_oss` architecture is recognized and fully functional.

## 2. The Core Challenge: "The Goldilocks Problem"
We encountered a significant conflict between software requirements and hardware compatibility:
- **Software Requirement:** The `gpt-oss-20b` model uses a custom architecture (`gpt_oss`) that is only supported in very recent versions of the `transformers` library (v4.39+) and `vllm`.
- **Hardware Constraint:** Most standard RunPod cloud GPU instances run on host machines with **CUDA 12.1** or **CUDA 12.4** drivers.
- **Image Conflict:**
    - **Too Old:** Standard vLLM images (e.g., `v0.6.3`) support the hardware (CUDA 12.1) but are too old to recognize the model architecture.
    - **Too New:** The `vllm/vllm-openai:latest` image supports the model but is built against **CUDA 12.9**, causing it to fail immediately on startup on standard hosts (`unsatisfied condition: cuda>=12.9`).

## 3. Investigation & Attempts

### Attempt 1: Standard vLLM Image
- **Configuration:** `vllm/vllm-openai:v0.6.3.post1`
- **Result:** **FAILURE**
- **Error:** `ValueError: The checkpoint you are trying to load has model type 'gpt_oss' but Transformers does not recognize this architecture.`
- **Reason:** The `transformers` library inside this image was outdated and lacked the necessary code registration for `gpt_oss`.

### Attempt 2: Latest vLLM Image
- **Configuration:** `vllm/vllm-openai:latest`
- **Result:** **FAILURE** (Container Crash)
- **Error:** `nvidia-container-cli: requirement error: unsatisfied condition: cuda>=12.9`
- **Reason:** The `latest` tag pulled an image built for the absolute newest NVIDIA drivers, which were not present on the host machine. The container refused to start.

### Attempt 3: Runtime Installation (The Winner)
- **Strategy:** Instead of relying on a pre-built vLLM image, use a **generic, compatible PyTorch image** and install the software stack dynamically at boot time.
- **Base Image:** `runpod/pytorch:2.2.0-py3.10-cuda12.1.1-devel-ubuntu22.04` (Guaranteed to work on RunPod hosts).
- **Command:**
    ```bash
    pip install --upgrade pip && \
    pip install vllm transformers && \
    python3 -m vllm.entrypoints.openai.api_server ...
    ```
- **Hurdles:**
    - **Syntax Errors:** Initial attempts to chain commands failed because `runpodctl` and the container's `nvidia_entrypoint.sh` mishandled arguments passed via `--args`.
    - **"Disappearing Pods":** Malformed commands caused the container to exit immediately, making it hard to debug.
- **Fix:** Refactoring `runpod_interface.py` to:
    1.  Use the proper `runpodctl` argument format (`--args "string"`).
    2.  Wrap the entire command in `/bin/sh -c "..."` to properly handle the `&&` operators.
    3.  Append `|| sleep infinity` to keep the container alive for debugging if the installation failed.

## 4. Final Solution Configuration

The working configuration in `runpod_interface.py` is:

```python
start_cmd = (
    "/bin/sh -c \""
    "pip install --upgrade pip && "
    "pip install vllm transformers && "
    "python3 -m vllm.entrypoints.openai.api_server "
    f"--model {target_model} "
    "--gpu-memory-utilization 0.95 "
    "--max-model-len 8192 "
    "--dtype auto "
    "--trust-remote-code "
    "|| sleep infinity"
    "\""
)

args = [
    # ... standard runpodctl args ...
    "--imageName", "runpod/pytorch:2.2.0-py3.10-cuda12.1.1-devel-ubuntu22.04",
    "--args", start_cmd
]
```

## 5. Verification Results
- **Pod Status:** Created and Running (Stable).
- **Logs:** confirmed successful installation of vLLM (v0.15.1+) and model loading.
    ```
    INFO [model.py:541] Resolved architecture: GptOssForCausalLM
    ```
- **API:** The vLLM server is now listening on port 8000 and ready for inference requests.

## 6. Conclusion
The **Runtime Installation Strategy** is the robust solution for running cutting-edge models on standard cloud infrastructure. It bypasses the "dependency hell" of pre-built Docker images by decoupling the **OS/Driver layer** (handled by the base image) from the **Application layer** (installed at runtime). This creates a slightly longer boot time (approx. 60-90s) but guarantees compatibility.
