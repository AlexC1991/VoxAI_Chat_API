import sys
import os
import time
import requests
import json
from config import API_KEY, POD_ID, MODEL_MAP

# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

def launch_chat():
    print(f"{CYAN}Starting VoxAI Initialization...{RESET}\n")
    
    # [SECTION] Environment Selection
    print(f"{CYAN}")
    print(r"""
██╗   ██╗ ██████╗ ██╗  ██╗       █████╗ ██╗
██║   ██║██╔═══██╗╚██╗██╔╝      ██╔══██╗██║
██║   ██║██║   ██║ ╚███╔╝ █████╗███████║██║
╚██╗ ██╔╝██║   ██║ ██╔██╗ ╚════╝██╔══██║██║
 ╚████╔╝ ╚██████╔╝██╔╝ ██╗      ██║  ██║██║
  ╚═══╝   ╚═════╝ ╚═╝  ╚═╝      ╚═╝  ╚═╝╚═╝
    """)
    print(f"     VOX-AI UNIVERSAL ENGINE | {YELLOW}BOOT{CYAN}")
    print(f"============================================{RESET}")
    print(" [1] LOCAL (GPU/CPU) | [2] CLOUD (RunPod)")
    
    choice = input("Select Environment: ").strip()
    use_cloud = choice == "2"

    # [SECTION] Model Selection
    print("\n--- Available Brains ---")
    keys = list(MODEL_MAP.keys())
    for i, key in enumerate(keys):
        print(f" [{i+1}] {key}")
    
    try:
        m_choice = int(input("\nSelect Model: ")) - 1
        selected_model = keys[m_choice]
    except:
        print(f"{RED}[ERROR] Invalid selection.{RESET}")
        sys.exit(1)

    # [SECTION] Engine Logic
    llm = None
    cloud_driver = None
    target_cloud_id = None # Variable to store resolved ID
    
    if use_cloud:
        try:
            from runpod_interface import RunPodDriver
            cloud_driver = RunPodDriver(API_KEY, POD_ID)
            
            # Resolve the specific Cloud ID using the "Phone Book"
            local_filename_for_mapping = MODEL_MAP[selected_model]
            target_cloud_id = get_cloud_model_id(local_filename_for_mapping)
            
            if not target_cloud_id:
                print(f"{RED}[ABORT] No valid Cloud ID provided.{RESET}")
                sys.exit(1)
            
            # Try to switch/boot the cloud pod with resolved ID
            if cloud_driver.switch_model(target_cloud_id):
                print(f"\n[SYSTEM] ☁️  {GREEN}Cloud Link Established.{RESET}")
            else:
                print(f"\n[FALLBACK] ⚠️ {YELLOW}Cloud failed. Engaging Local Hardware...{RESET}")
                use_cloud = False # Trigger fallback
        except Exception as e:
            print(f"[ERROR] Cloud init failed: {e}")
            use_cloud = False

    # [SECTION] Local Fallback
    if not use_cloud:
        # Define the local filename from the map
        local_file = MODEL_MAP[selected_model]
        
        # 1. Construct Absolute Path to avoid relative path errors
        base_dir = os.path.dirname(os.path.abspath(__file__))
        models_dir = os.path.join(base_dir, "models")
        
        # 2. Normalize Slashes for Windows compatibility
        model_path = os.path.join(models_dir, local_file).replace("\\", "/")
        
        print(f"\n[LOCAL] 🛡️ {CYAN}Loading GGUF: {model_path}...{RESET}")
        
        if not os.path.exists(model_path):
            print(f"{RED}[ERROR] ❌ File not found: {model_path}{RESET}")
            print("[HINT] Check if the file is in the 'models' folder and named correctly.")
            sys.exit(1)

        try:
            # [HANDSHAKE] Import and Run Hardware Check
            import machine_engine_handshake
            import ctypes # Required for manual backend loading
            mode, phys_cores, cfg = machine_engine_handshake.get_hardware_config()
            
            # Apply Environment Overrides from Handshake
            root_path = os.path.abspath(".")
            os.environ["GGML_VK_FORCE_BUSY_WAIT"] = cfg["busy_wait"]
            os.environ["GGML_BACKEND_SEARCH_PATH"] = root_path
            
            # [CRITICAL] Manually Load GGML Backend (Fixes 'no backends loaded' error)
            try:
                # Try loading ggml.dll to register backends (Vulkan/CPU)
                ggml = ctypes.CDLL(os.path.join(root_path, "ggml.dll"))
                if hasattr(ggml, 'ggml_backend_load_all'): 
                    ggml.ggml_backend_load_all()
                print(f"[LOCAL] 🟢 Backend drivers loaded manually.")
            except Exception as e:
                print(f"[LOCAL] ⚠️ Backend load warning: {e}")
            
            # Standard Llama Initialization with Handshake Config
            print(f"[LOCAL] 🛠️ Initializing Llama Engine ({mode})...")
            from llama_cpp import Llama
            llm = Llama(
                model_path=model_path,
                n_ctx=4096,
                verbose=True,
                
                # INJECTING CONFIG FROM HANDSHAKE
                n_gpu_layers=cfg['n_gpu_layers'],
                n_threads=cfg['n_threads'],
                n_threads_batch=cfg['n_threads_batch'],
                n_batch=cfg['n_batch'],
                flash_attn=cfg['flash_attn'],
                use_mlock=cfg['use_mlock'],
                cache_type_k=cfg['cache_type_k'],
                cache_type_v=cfg['cache_type_v']
            )
            print(f"[LOCAL] {GREEN}✅ Engine Online.{RESET}")
        except Exception as e:
            print(f"{RED}[ERROR] Failed to load local model: {e}{RESET}")
            sys.exit(1)

    # [SECTION] The Chat Loop
    print("\n" + "="*40)
    print(f"VoxAI Online. Model: {selected_model}")
    print("Commands: 'exit', 'swap' (Cloud Only)")
    print("="*40 + "\n")

    messages = []

    while True:
        try:
            user_input = input(f"{CYAN}You:{RESET} ").strip()
            if user_input.lower() == "exit":
                if use_cloud and cloud_driver:
                    print(f"{YELLOW}[SYSTEM] Shutting down Cloud Resources...{RESET}")
                    cloud_driver.terminate_pod()
                else:
                    print(f"{YELLOW}[LOCAL] Shutting down Engine...{RESET}")
                break
            
            # Hotkey logic for swapping could go here, or just checking input
            # Hotkey logic for swapping could go here, or just checking input
            if user_input.lower() == "swap":
                print(f"{YELLOW}[SYSTEM] Triggering Model Swap...{RESET}")
                
                # 1. Show Menu
                print("\n--- Available Brains ---")
                keys = list(MODEL_MAP.keys())
                for i, key in enumerate(keys):
                    print(f" [{i+1}] {key}")
                
                try:
                    selection = input("\nSelect Model (0 to cancel): ").strip()
                    if selection == "0": continue
                    
                    m_choice = int(selection) - 1
                    if 0 <= m_choice < len(keys):
                        new_model_key = keys[m_choice]
                        
                        # --- CLOUD SWAP LOGIC ---
                        if use_cloud and cloud_driver:
                            local_filename = MODEL_MAP[new_model_key]
                            new_cloud_id = get_cloud_model_id(local_filename)
                            
                            if new_cloud_id:
                                if cloud_driver.switch_model(new_cloud_id):
                                    target_cloud_id = new_cloud_id
                                    selected_model = new_model_key
                                    print(f"\n[SYSTEM] ☁️  {GREEN}Swap Complete. Now running: {selected_model}{RESET}")
                                    print("="*40 + "\n")
                                else:
                                     print(f"{RED}[ERROR] Swap failed. Staying on current pool.{RESET}")
                        
                        # --- LOCAL SWAP LOGIC ---
                        else:
                            model_filename = MODEL_MAP[new_model_key]
                            new_path = os.path.join(models_dir, model_filename)
                            
                            if not os.path.exists(new_path):
                                print(f"{RED}[ERROR] File not found: {new_path}{RESET}")
                                continue

                            print(f"\n[LOCAL] 🔄 Unloading current model...")
                            if 'llm' in locals():
                                del llm
                                import gc
                                gc.collect()
                            
                            print(f"[LOCAL] 🛡️ Loading New GGUF: {new_model_key}...")
                            
                            # Re-run handshake to be safe (or reuse cfg)
                            import machine_engine_handshake
                            _, _, cfg = machine_engine_handshake.get_hardware_config()

                            print(f"[LOCAL] 🛠️ Initializing Llama Engine...")
                            from llama_cpp import Llama
                            llm = Llama(
                                model_path=new_path,
                                n_ctx=4096,
                                verbose=True,
                                n_gpu_layers=cfg['n_gpu_layers'],
                                n_threads=cfg['n_threads'],
                                n_threads_batch=cfg['n_threads_batch'],
                                n_batch=cfg['n_batch'],
                                flash_attn=cfg['flash_attn'],
                                use_mlock=cfg['use_mlock'],
                                cache_type_k=cfg['cache_type_k'],
                                cache_type_v=cfg['cache_type_v']
                            )
                            selected_model = new_model_key
                            print(f"[LOCAL] {GREEN}✅ Swap Complete. Engine Online.{RESET}")
                            print("="*40 + "\n")

                    else:
                        print(f"{RED}[ERROR] Invalid selection.{RESET}")

                except Exception as e:
                    print(f"{RED}[ERROR] Selection error: {e}{RESET}")
                
                continue

            messages.append({"role": "user", "content": user_input})

            print(f"{GREEN}VoxAI:{RESET} ", end="", flush=True)

            if use_cloud and cloud_driver and cloud_driver.new_pod_id:
                # CLOUD GENERATION
                url = f"https://{cloud_driver.new_pod_id}-8000.proxy.runpod.net/v1/chat/completions"
                payload = {
                    "model": target_cloud_id, 
                    "messages": messages,
                    "max_tokens": 512,
                    "stream": True # CRITICAL: Enable streaming response
                }
                headers = {"Authorization": f"Bearer {API_KEY}"}
                
                try:
                    response = requests.post(url, json=payload, headers=headers, stream=True)
                    full_response = ""
                    
                    # Timing
                    t0 = time.time()
                    token_count = 0
                    
                    for chunk in response.iter_lines():
                        if chunk:
                            try:
                                decoded = chunk.decode('utf-8')
                                if decoded.startswith("data: "):
                                    decoded = decoded[6:] # Robust stripping
                                
                                if decoded.strip() == "[DONE]":
                                    continue
                                
                                j = json.loads(decoded)
                                if 'choices' in j and len(j['choices']) > 0:
                                    delta = j['choices'][0].get('delta', {})
                                    token = delta.get('content', '')
                                    if token:
                                        print(token, end="", flush=True)
                                        full_response += token
                                        token_count += 1
                            except: pass # Silent fail on bad chunks is fine for stream
                    
                    dt = time.time() - t0
                    if token_count > 0 and dt > 0:
                        speed = token_count / dt
                        balance = cloud_driver.get_balance() or 0.0
                        cost = cloud_driver.pod_cost or 0.0
                        print(f"\n{YELLOW}({speed:.2f} t/s) | Balance: ${float(balance):.2f} | Cost: ${float(cost):.3f}/hr{RESET}")
                    else:
                         print() # Newline

                    messages.append({"role": "assistant", "content": full_response})
                except Exception as e:
                    print(f"\n{RED}[Cloud Error] {e}{RESET}")

            elif llm:
                # LOCAL GENERATION
                try:
                    stream = llm.create_chat_completion(
                        messages=messages,
                        max_tokens=512,
                        stream=True
                    )
                    full_response = ""
                    
                    # Timing
                    t0 = time.time()
                    token_count = 0
                    
                    for chunk in stream:
                        if 'content' in chunk['choices'][0]['delta']:
                            token = chunk['choices'][0]['delta']['content']
                            print(token, end="", flush=True)
                            full_response += token
                            token_count += 1
                    
                    dt = time.time() - t0
                    if token_count > 0 and dt > 0:
                         print(f"\n{YELLOW}({token_count / dt:.2f} t/s){RESET}")
                    else:
                         print() # Newline

                    messages.append({"role": "assistant", "content": full_response})
                except Exception as e:
                    print(f"\n{RED}[Local Error] {e}{RESET}")

        except KeyboardInterrupt:
            print("\n[SYSTEM] Interrupted. Exiting...")
            if use_cloud and cloud_driver:
                print(f"{YELLOW}[SYSTEM] Shutting down Cloud Resources...{RESET}")
                # Use a small try-except to ensure we don't hang if network is down
                try:
                    cloud_driver.terminate_pod()
                except Exception as e:
                    print(f"{RED}[ERROR] Failed to terminate pod on exit: {e}{RESET}")
            break

# [SECTION] Helper Functions
def get_cloud_model_id(local_filename):
    """
    Resolves the Hugging Face ID from the local filename using known_models.json.
    If not found, prompts the user and saves the new mapping.
    """
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "known_models.json")
    
    known_models = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r') as f:
                known_models = json.load(f)
        except:
            pass # Start fresh if corrupt
            
    if local_filename in known_models:
        return known_models[local_filename]
        
    # Not found, ask user
    print(f"\n{YELLOW}[SYSTEM] This model has not been mapped to a Cloud ID yet.{RESET}")
    print(f"File: {local_filename}")
    new_id = input(f"Enter the Hugging Face Hub ID (e.g. 'organization/model-name'): ").strip()
    
    if not new_id:
        print(f"{RED}[ERROR] Invalid ID. Aborting.{RESET}")
        return None
        
    # Save back to JSON
    known_models[local_filename] = new_id
    try:
        with open(json_path, 'w') as f:
            json.dump(known_models, f, indent=4)
        print(f"[SYSTEM] Saved mapping to phone book.")
    except Exception as e:
        print(f"{RED}[ERROR] Could not save mapping: {e}{RESET}")
        
    return new_id

if __name__ == "__main__":
    launch_chat()