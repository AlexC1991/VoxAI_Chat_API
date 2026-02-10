import requests
import config
import time

def sync_remote_model(local_filename):
    """
    The 'Translator' Function.
    1. Looks up the local filename in config.py
    2. Finds the matching Remote ID.
    3. Tells the RunPod Manager to load it.
    """
    if not config.USE_RUNPOD:
        print("[REMOTE] Remote mode is DISABLED in config.")
        return False

    # 1. Translate
    remote_id = config.MODEL_MAP.get(local_filename)
    if not remote_id:
        print(f"[REMOTE] ⚠️ No translation found for '{local_filename}'.")
        print(f"         Using default: {config.DEFAULT_REMOTE_MODEL}")
        remote_id = config.DEFAULT_REMOTE_MODEL

    print(f"\n[REMOTE] 📡 Connecting to RunPod...")
    print(f"[REMOTE] 🔄 Requesting Switch: {local_filename} -> {remote_id}")

    # 2. Send Command to Manager
    manager_url = f"{config.RUNPOD_BASE_URL}/manager/load_model"
    
    try:
        # We start by checking if the server is even there
        response = requests.post(
            manager_url, 
            json={"model_id": remote_id}, 
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"[REMOTE] ✅ SUCCESS: {data.get('message')}")
            print(f"[REMOTE] ⏳ Waiting for model to load (approx 30s)...")
            _wait_for_server_ready()
            return True
        else:
            print(f"[REMOTE] ❌ ERROR: Server returned {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"[REMOTE] ❌ CONNECTION FAILED: Is the Pod running?")
        print(f"         URL: {manager_url}")
        return False

def _wait_for_server_ready():
    """Pings the chat endpoint until it replies, confirming model is loaded."""
    url = f"{config.RUNPOD_BASE_URL}/v1/models"
    for i in range(12): # Try for 60 seconds
        try:
            requests.get(url, timeout=2)
            print("[REMOTE] 🚀 Server is READY!")
            return
        except:
            time.sleep(5)
            print(".", end="", flush=True)
    print("\n[REMOTE] ⚠️ Server is taking a long time. Proceeding anyway...")

# Test block
if __name__ == "__main__":
    test_model = "Qwen3-8B-Q5_K_M.gguf"
    sync_remote_model(test_model)