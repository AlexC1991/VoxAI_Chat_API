import os
import psutil
import ctypes

def get_hardware_config():
    """
    VOX-AI Hardware Handshake
    Status: GOLDEN CONFIGURATION (Ryzen APU Optimized)
    """
    print("\n[HANDSHAKE] --- PROTOCOL STARTED ---")
    
    # 1. CPU DETECTION
    print("[HANDSHAKE] Probing CPU Topology...")
    physical_cores = psutil.cpu_count(logical=False) or 4
    print(f"[HANDSHAKE] Detected {physical_cores} Physical Cores.")

    # 2. CALCULATE THREADS
    # 8 Threads was proven stable and fastest for Vulkan Mode
    optimal_threads = physical_cores
    optimal_batch_threads = max(2, physical_cores // 2)

    # 3. BACKEND DETECTION
    root_path = os.path.abspath(".")
    print(f"[HANDSHAKE] Scanning for High-Performance Backend in: {root_path}")
    
    # === DEFAULT MODE: APU (Vulkan Hybrid) ===
    # This was the winner at ~7.5 t/s
    mode = "APU (Hybrid/Vulkan)"
    config = {
        "n_gpu_layers": 26,           # The Bandwidth Sweet Spot
        "n_threads": optimal_threads, 
        "n_threads_batch": optimal_batch_threads, 
        "n_batch": 512,
        "flash_attn": True,
        "use_mlock": True,            # Keep RAM locked for stability
        "busy_wait": "1",             # Force driver performance
        "cache_type_k": "f16",
        "cache_type_v": "f16"
    }

    # === FUTURE MODE: UNLEASHED (CUDA/ZLUDA) ===
    # Automatically activates if you install ZLUDA or upgrade to NVIDIA
    cuda_lib_path = os.path.join(root_path, "ggml-cuda.dll")
    
    if os.path.exists(cuda_lib_path):
        print("[HANDSHAKE] High-Performance Driver Found.")
        try:
            ctypes.CDLL(cuda_lib_path)
            mode = "UNLEASHED (CUDA/ZLUDA)"
            config.update({
                "n_gpu_layers": -1,       # MAX GPU
                "n_threads": 4,           
                "n_threads_batch": 4,     
                "n_batch": 1024,          
                "use_mlock": False,       
                "busy_wait": "0"          
            })
        except:
            print("[HANDSHAKE] Driver check failed. Staying on APU.")

    print(f"[HANDSHAKE] Final Mode Decision: {mode}")
    print("[HANDSHAKE] --- PROTOCOL COMPLETE ---\n")
    return mode, physical_cores, config

if __name__ == "__main__":
    get_hardware_config()