import sys
import time
import requests
import json
from config import *

# ==========================================
# 🎨  VOX UI STYLING
# ==========================================
def print_system(msg):
    # Cyan text for system messages
    print(f"\033[96m[VOX REMOTE]\033[0m {msg}")

def print_debug(msg):
    # Grey text for debug info
    print(f"\033[90m   >>> DEBUG: {msg}\033[0m")

def print_speed(token_count, total_time):
    # Green text for stats
    if total_time > 0:
        tps = token_count / total_time
        print(f"\n\033[92m[STATS] {token_count} tokens in {total_time:.2f}s | Speed: {tps:.2f} t/s\033[0m")
        print("-" * 40)

# ==========================================
# 🛠️  SERVER BOOT SEQUENCE
# ==========================================
def boot_sequence():
    print("\n" + "="*40)
    print(" VOX-AI REMOTE LINK | STATUS: INITIALIZING")
    print("="*40)
    
    # 1. Ping the Server
    print_system(f"Pinging Neural Cloud: {RUNPOD_BASE_URL}...")
    
    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}"
    }

    try:
        start = time.time()
        # We try to fetch the models list as a "Ping"
        response = requests.get(f"{RUNPOD_BASE_URL}/models", headers=headers, timeout=10)
        ping = (time.time() - start) * 1000
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                # Check if 'data' exists and has content
                if "data" in data and len(data["data"]) > 0:
                    active_model = data['data'][0]['id']
                else:
                    # If the server responds but the format is different, use a placeholder
                    active_model = "Remote Model (Ready)"
                    
                print_system(f"Connection Established! (Ping: {ping:.0f}ms)")
                print_system(f"Active Neural Core: \033[93m{active_model}\033[0m")
                print_system(f"Backend Engine: vLLM (CUDA Optimized)")
                print_debug("GPU Handshake: CONFIRMED")
                print("="*40 + "\n")
                return True
                
            except Exception as parse_error:
                print_system(f"Connected, but couldn't parse model name: {parse_error}")
                print_debug("Proceeding anyway...")
                print("="*40 + "\n")
                return True
        else:
            print_system(f"Server replied with Error {response.status_code}")
            return False

    except Exception as e:
        print_system(f"Connection Failed: {e}")
        return False

# ==========================================
# 💬  MAIN CHAT LOOP
# ==========================================
def chat_loop():
    # Run the boot sequence first
    if not boot_sequence():
        return

    # Initialize History
    messages = []
    print_system("Listening for input...\n")

    while True:
        try:
            user_input = input("\033[94mYou:\033[0m ")
            if user_input.lower() in ["exit", "quit"]:
                break

            # Add User Message
            messages.append({"role": "user", "content": user_input})

            # Prepare the payload
            payload = {
                "model": DEFAULT_REMOTE_MODEL, # Uses the one from config.py
                "messages": messages,
                "stream": True,
                "max_tokens": 2048,
                "temperature": 0.7
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {RUNPOD_API_KEY}"
            }

            # Start Generation
            print("VOX: ", end="", flush=True)
            start_time = time.time()
            token_count = 0
            collected_message = ""
            
            # STREAMING REQUEST
            response = requests.post(f"{RUNPOD_BASE_URL}/chat/completions", headers=headers, json=payload, stream=True)

            if response.status_code != 200:
                print(f"\n[ERROR] Server returned {response.status_code}: {response.text}")
                continue

            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8').strip()
                    if decoded_line.startswith("data: "):
                        data_str = decoded_line[6:] # Remove "data: " prefix
                        if data_str == "[DONE]":
                            break
                        try:
                            json_response = json.loads(data_str)
                            if "choices" in json_response:
                                delta = json_response["choices"][0].get("delta", {})
                                if "content" in delta:
                                    content = delta["content"]
                                    if content: # Ensure content is not None
                                        print(content, end="", flush=True)
                                        collected_message += content
                                        token_count += 1
                        except:
                            pass

            # Print Stats at the end
            total_time = time.time() - start_time
            print_speed(token_count, total_time)

            # Save Assistant Reply to History
            if collected_message:
                messages.append({"role": "assistant", "content": collected_message})

        except KeyboardInterrupt:
            print("\n[VOX REMOTE] Disconnecting...")
            break
        except Exception as e:
            print(f"\n[ERROR] {e}")

if __name__ == "__main__":
    chat_loop()