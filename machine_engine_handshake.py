import os
import psutil
import ctypes

def get_hardware_config():
    """
    Probes the system hardware and prints status updates with [HANDSHAKE] tag.
    Returns: mode, physical_cores, config_dictionary
    """
    print("\n[HANDSHAKE] --- PROTOCOL STARTED ---")
    
    # ==========================================
    # 1. CPU AUTO-DETECTION
    # ==========================================
    print("[HANDSHAKE] Probing CPU Topology...")
    physical_cores = psutil.cpu_count(logical=False)
    if physical_cores is None: 
        physical_cores = 4 # Fallback
        print("[HANDSHAKE] !WARN! CPU count failed. Defaulting to 4.")
    else:
        print(f"[HANDSHAKE] Detected {physical_cores} Physical Cores.")

    # Calculate Threads
    optimal_threads = physical_cores
    optimal_batch_threads = max(2, physical_cores // 2)
    print(f"[HANDSHAKE] Calculated Optimal Threads: {optimal_threads} Gen / {optimal_batch_threads} Batch.")

    # ==========================================
    # 2. GPU BACKEND AUTO-DETECTION
    # ==========================================
    root_path = os.path.abspath(".")
    print(f"[HANDSHAKE] Scanning for High-Performance Backend in: {root_path}")
    
    # Default State
    mode = "APU (Vulkan)"
    
    # Base Config (The Golden Config)
    config = {
        "n_gpu_layers": 12,           
        "n_threads": optimal_threads, 
        "n_threads_batch": optimal_batch_threads, 
        "n_batch": 512,
        "flash_attn": True,
        "use_mlock": True,            
        "busy_wait": "1",             
        "cache_type_k": "f16",
        "cache_type_v": "f16"
    }

    # CHECK FOR CUDA / ZLUDA
    cuda_lib_path = os.path.join(root_path, "ggml-cuda.dll")
    
    if os.path.exists(cuda_lib_path):
        print("[HANDSHAKE] 'ggml-cuda.dll' found. Testing binary compatibility...")
        try:
            ctypes.CDLL(cuda_lib_path)
            print("[HANDSHAKE] Binary Test: PASSED. CUDA/ZLUDA is active.")
            
            mode = "UNLEASHED (CUDA/ZLUDA)"
            config.update({
                "n_gpu_layers": -1,       
                "n_threads": 4,           
                "n_threads_batch": 4,     
                "n_batch": 1024,          
                "use_mlock": False,       
                "busy_wait": "0"          
            })
        except:
            print("[HANDSHAKE] Binary Test: FAILED. Falling back to Vulkan.")
    else:
        print("[HANDSHAKE] No CUDA library found. Defaulting to APU/Vulkan.")

    print(f"[HANDSHAKE] Final Mode Decision: {mode}")
    print("[HANDSHAKE] --- PROTOCOL COMPLETE ---\n")
    return mode, physical_cores, config

if __name__ == "__main__":
    # Test run if executed directly
    get_hardware_config()
    input("Press Enter to exit...")