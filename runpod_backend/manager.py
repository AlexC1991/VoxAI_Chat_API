import os
import signal
import subprocess
import time
import httpx
from fastapi import FastAPI, Request, Response
from contextlib import asynccontextmanager

# --- CONFIGURATION ---
VLLM_PORT = 8001  # We run the heavy AI on this internal port
DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"

# Global process holder
vllm_process = None
current_model = None

def start_vllm(model_name):
    """Starts the vLLM subprocess on the internal port."""
    global vllm_process, current_model
    
    print(f"🚀 MANAGER: Launching model: {model_name}")
    
    # Command to launch vLLM
    cmd = [
        "python3", "-m", "vllm.entrypoints.openai.api_server",
        "--model", model_name,
        "--host", "127.0.0.1",
        "--port", str(VLLM_PORT),
        "--trust-remote-code",
        "--max-model-len", "8192" # Adjust based on GPU memory
    ]
    
    # Start the process in a new session so we can kill it cleanly later
    vllm_process = subprocess.Popen(cmd, start_new_session=True)
    current_model = model_name

def stop_vllm():
    """Kills the current vLLM subprocess."""
    global vllm_process
    if vllm_process:
        print("🛑 MANAGER: Stopping current model...")
        os.killpg(os.getpgid(vllm_process.pid), signal.SIGTERM)
        vllm_process.wait()
        vllm_process = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_vllm(DEFAULT_MODEL)
    yield
    # Shutdown
    stop_vllm()

app = FastAPI(lifespan=lifespan)

# --- ENDPOINTS ---

@app.post("/manager/load_model")
async def load_model_endpoint(request: Request):
    """The 'Translator' endpoint. Receives a model ID and hot-swaps it."""
    data = await request.json()
    new_model = data.get("model_id")
    
    if not new_model:
        return {"error": "No model_id provided"}
    
    if new_model == current_model:
        return {"status": "Model already loaded", "model": current_model}

    stop_vllm()
    start_vllm(new_model)
    
    return {"status": "Switched", "model": new_model, "message": "Model is loading... give it 30-60s."}

@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_all(path_name: str, request: Request):
    """Forward everything else (chat completions, models, etc.) to vLLM."""
    
    # Wait if vLLM isn't ready yet (Simple retry logic)
    client = httpx.AsyncClient(base_url=f"http://127.0.0.1:{VLLM_PORT}")
    
    try:
        # Forward the request to the internal vLLM server
        url = httpx.URL(path=path_name, query=request.url.query.encode("utf-8"))
        rp_req = client.build_request(
            request.method,
            url,
            headers=request.headers.raw,
            content=await request.body()
        )
        rp_resp = await client.send(rp_req)
        
        return Response(
            content=rp_resp.content,
            status_code=rp_resp.status_code,
            headers=rp_resp.headers
        )
    except httpx.ConnectError:
        return {"error": "Model is still loading. Please wait..."}
    finally:
        await client.aclose()

if __name__ == "__main__":
    import uvicorn
    # We listen on 0.0.0.0:8000 so RunPod can see us
    uvicorn.run(app, host="0.0.0.0", port=8000)