import sys
import os
import time
import ctypes
import psutil
from llama_cpp import Llama

# Fix encoding for Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ==========================================
# 0. SYSTEM OVERRIDE
# ==========================================
try:
    p = psutil.Process(os.getpid())
    p.nice(psutil.HIGH_PRIORITY_CLASS)
    print("[SYSTEM] Priority: HIGH")
except: pass

os.environ["GGML_VK_FORCE_BUSY_WAIT"] = "1"
os.environ["GGML_NUMA"] = "0"

# ==========================================
# 1. SETUP
# ==========================================
ROOT_DIR = os.path.abspath(".")
os.environ["PATH"] += os.pathsep + ROOT_DIR
if hasattr(os, 'add_dll_directory'): os.add_dll_directory(ROOT_DIR)
os.environ["GGML_BACKEND_SEARCH_PATH"] = ROOT_DIR
os.environ["LLAMA_CPP_LIB"] = os.path.join(ROOT_DIR, "llama.dll")

try:
    ggml = ctypes.CDLL(os.path.join(ROOT_DIR, "ggml.dll"))
    if hasattr(ggml, 'ggml_backend_load_all'): ggml.ggml_backend_load_all()
except: pass

MODEL_FILENAME = "llama-3.2-3b-instruct-q4_k_m.gguf"
model_path = os.path.join("models", MODEL_FILENAME)

# ==========================================
# 2. OPTIMIZED CONFIGURATION
# Based on comprehensive benchmarking results:
# - 12 GPU layers is optimal for this APU (more layers = memory bandwidth bottleneck)
# - FP16 cache provides best performance (Q8/Q4 compression doesn't help on this hardware)
# - 8 generation threads / 2 batch threads prevents CPU contention
# - 512 batch size is optimal
# - 2048 context is sufficient (4096 adds minimal benefit)
# ==========================================
CONFIG = {
    "gpu_layers": 12,
    "cache_k": "f16",
    "cache_v": "f16", 
    "threads": 8,
    "threads_batch": 2,
    "batch": 512,
    "ctx": 2048
}

PROMPT = "Write a 250 word short story about time travel."
GEN_TOKENS = 250

print("\n" + "="*60)
print(" VOX-AI DEBUG ENGINE (Optimized)")
print("="*60)
print(f" Config: {CONFIG['gpu_layers']}L GPU | {CONFIG['cache_k']}/{CONFIG['cache_v']} Cache")
print(f"         {CONFIG['threads']}/{CONFIG['threads_batch']} Threads | {CONFIG['batch']} Batch | {CONFIG['ctx']} Ctx")
print("="*60)

try:
    llm = Llama(
        model_path=model_path,
        n_ctx=CONFIG['ctx'],
        n_gpu_layers=CONFIG['gpu_layers'],
        cache_type_k=CONFIG['cache_k'],
        cache_type_v=CONFIG['cache_v'],
        n_threads=CONFIG['threads'],
        n_threads_batch=CONFIG['threads_batch'],
        n_batch=CONFIG['batch'],
        flash_attn=True,
        use_mlock=True,
        use_mmap=True,
        verbose=False
    )
    
    # WARMUP (Critical for consistent timing)
    print("\n[Warming up...]")
    for _ in range(3):
        llm.create_chat_completion(messages=[{"role":"user","content":"."}], max_tokens=1)
    
    # THE REAL TEST - Using streaming to count ACTUAL tokens
    print(f"\n>> Prompt: {PROMPT[:50]}...")
    print(">> Generating (streaming)...\n")
    
    start = time.time()
    first_token_time = None
    token_count = 0
    response_text = ""
    
    stream = llm.create_chat_completion(
        messages=[{"role": "user", "content": PROMPT}],
        max_tokens=GEN_TOKENS,
        stream=True
    )
    
    for chunk in stream:
        if "content" in chunk["choices"][0]["delta"]:
            token = chunk["choices"][0]["delta"]["content"]
            if first_token_time is None:
                first_token_time = time.time() - start
            token_count += 1
            response_text += token
            print(token, end="", flush=True)
    
    total_time = time.time() - start
    gen_time = total_time - first_token_time
    
    # Calculate ACTUAL t/s (based on real tokens generated)
    actual_tps = token_count / total_time
    gen_tps = (token_count - 1) / gen_time if gen_time > 0 and token_count > 1 else 0
    
    print("\n\n" + "="*60)
    print(" RESULTS")
    print("="*60)
    print(f" Time to First Token (TTFT): {first_token_time*1000:.0f}ms")
    print(f" Tokens Generated: {token_count}")
    print(f" Total Time: {total_time:.2f}s")
    print(f" ")
    print(f" ACTUAL Speed (including TTFT): {actual_tps:.2f} t/s")
    print(f" GENERATION Speed (after TTFT): {gen_tps:.2f} t/s")
    print("="*60)
    
except Exception as e:
    print(f"\n[ERROR] {e}")

input("\nPress Enter to exit...")