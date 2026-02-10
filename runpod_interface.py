import subprocess
import time
import requests
import sys
import re
try:
    from config import GPU_TIERS, MODEL_SPECIFIC_TIERS, KEYWORD_TIERS
except ImportError:
    # Fallback if config is missing (for safety)
    GPU_TIERS, MODEL_SPECIFIC_TIERS, KEYWORD_TIERS = {}, {}, []

class RunPodDriver:
    def __init__(self, api_key, pod_id):
        self.api_key = api_key
        self.pod_id = pod_id 
        self.new_pod_id = None
        self.current_gpu_type = None
        self.pod_cost = 0.0

    def _run_cmd(self, cmd_list):
        """Executes shell commands via subprocess."""
        try:
            # On Windows, shell=False with a list of args is usually safest for runpodctl
            result = subprocess.run(cmd_list, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"ERROR: {e.stderr}"

    def get_balance(self):
        """Fetches RunPod balance via GraphQL."""
        query = "query { myself { balance } }"
        try:
            resp = requests.post(
                f"https://api.runpod.io/graphql?api_key={self.api_key}",
                json={'query': query}, timeout=5
            )
            # print(f"[DEBUG] Balance Resp: {resp.status_code} | {resp.text}") 
            if resp.status_code == 200:
                data = resp.json()
                if 'errors' in data:
                    print(f"\n[PHOENIX] ⚠️ Balance Error: {data['errors'][0]['message']}")
                    return 0.0
                return data['data']['myself']['balance']
        except Exception as e:
            print(f"\n[PHOENIX] ⚠️ Balance Fetch Failed: {e}")
            return 0.0

    def _refresh_cost(self):
        """Updates pod_cost based on current_gpu_type."""
        if self.current_gpu_type:
            avail = self.get_available_gpus()
            # print(f"[DEBUG] Refreshing Cost for {self.current_gpu_type}. Found {len(avail)} GPUs.")
            for g in avail:
                if g['name'] == self.current_gpu_type:
                    self.pod_cost = g['price']
                    # print(f"[DEBUG] Found Price: ${self.pod_cost}")
                    break
            else:
                # Fallback: Scrape exact string match failed, try partial?
                pass

    def get_available_gpus(self):
        """Scrapes cloud stock and pricing."""
        output = self._run_cmd(["runpodctl", "get", "cloud"])
        # print(f"[DEBUG] Cloud Raw: {output[:100]}...") # Peek
        lines = output.strip().split('\n')
        gpus = []
        # Regex to capture: Name, VRAM (int), Price (float)
        # Expected format: "1x NVIDIA A40  48 GB  0.34"
        regex = r'^(1x\s.*?)\s+(\d+)\s*GB\s+([\d\.]+)$'
        
        for line in lines:
            match = re.search(regex, line)
            if match:
                name = match.group(1).replace('1x ', '').strip()
                vram = int(match.group(2))
                price = float(match.group(3))
                gpus.append({"name": name, "vram": vram, "price": price})
        return gpus

    def create_pod_on_gpu(self, gpu_type, target_model):
        """Rents GPU with verified Image and Token handling."""
        print(f"[PHOENIX] 🐣 Renting {gpu_type}...")
        
        # 1. Clean Command (No quotes, no 'vllm serve')
        start_cmd = (
            "/bin/sh -c \""
            "pip install --upgrade pip --cache-dir /root/.cache/huggingface/pip_cache && "
            "pip install vllm transformers --cache-dir /root/.cache/huggingface/pip_cache && "
            "python3 -m vllm.entrypoints.openai.api_server "
            f"--model {target_model} "
            "--gpu-memory-utilization 0.95 "
            "--max-model-len 8192 "
            "--dtype auto "
            "--trust-remote-code "
            "--disable-frontend-multiprocessing "  # Fix for Engine Core Init failures
        )
        
        # Auto-detect AWQ
        if "awq" in target_model.lower() or "4bit" in target_model.lower():
            start_cmd += " --quantization awq"
            
        start_cmd += " || sleep infinity\""
        
        args = [
            "runpodctl", "create", "pod",
            "--name", "VoxAI_Cloud",
            "--imageName", "runpod/pytorch:2.2.0-py3.10-cuda12.1.1-devel-ubuntu22.04", 
            "--gpuType", gpu_type,
            "--volumeSize", "100",
            "--volumePath", "/root/.cache/huggingface",
            "--ports", "8000/http",
            "--env", "HF_TOKEN=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",
            "--env", f"MODEL={target_model}",
            "--args", start_cmd 
        ]

        output = self._run_cmd(args)
        # print(f"[DEBUG] Raw RunPod Output: {output}") # Reduce noise
        
        pod_id = None
        if "created" in output.lower():
            import re
            match = re.search(r'pod\s+"([^"]+)"\s+created', output.lower())
            if match: pod_id = match.group(1)
            else:
                match = re.search(r'"([a-zA-Z0-9-]+)"', output)
                if match: pod_id = match.group(1)
        
        if pod_id:
            self.current_gpu_type = gpu_type
            # Try to update cost if possible, or do it later
            # For now, we set it to 0 and let switch_model update it or get_balace
            # Actually, to get cost, we need to know the price of the GPU we just rented.
            # We can lookup from available GPUs or just assume the user saw it.
            # Let's try to find it in get_available_gpus if available.
            avail = self.get_available_gpus()
            for g in avail:
                if g['name'] == gpu_type:
                    self.pod_cost = g['price']
                    break
            
            return pod_id
        return None

    def restart_server(self, target_model):
        """Hot-swaps the model inside the existing pod."""
        print(f"[PHOENIX] ♻️  Optimizing: Reusing active GPU ({self.current_gpu_type})...")
        self._refresh_cost() # Ensure we have the price
        active_id = self.new_pod_id if self.new_pod_id else self.pod_id
        
        # 1. Kill existing vLLM
        print("[PHOENIX] 🛑 Stopping current model...")
        self._run_cmd(["runpodctl", "exec", "pod", active_id, "--", "pkill -f vllm"])
        
        # 2. Wait for Death (Crucial!)
        print("[PHOENIX] 💀 Verifying shutdown...")
        url = f"https://{active_id}-8000.proxy.runpod.net/v1/models"
        for _ in range(15):
            try:
                requests.get(url, timeout=2) # If this succeeds, it's still alive
                time.sleep(1)
            except:
                break # Connection failed = Logic Success (Server is dead)
        else:
             # Force Kill if pkill failed
             self._run_cmd(["runpodctl", "exec", "pod", active_id, "--", "killall -9 python3"])
        
        # 2. Start new vLLM (Background)
        print(f"[PHOENIX] 🚀 Starting {target_model}...")
        # Use nohup to keep it running after exec returns
        start_cmd = (
            f"nohup python3 -m vllm.entrypoints.openai.api_server "
            f"--model {target_model} "
            "--gpu-memory-utilization 0.95 "
            "--max-model-len 8192 "
            "--dtype auto "
            "--trust-remote-code "
            "--disable-frontend-multiprocessing "
        )
        
        # Auto-detect AWQ
        if "awq" in target_model.lower() or "4bit" in target_model.lower():
            start_cmd += " --quantization awq"
            
        start_cmd += " > /var/log/vllm.log 2>&1 &"
        self._run_cmd(["runpodctl", "exec", "pod", active_id, "--", "bash", "-c", start_cmd])
        return True

    def _get_model_tier(self, target_model):
        """Resolves the required GPU Tier for a model."""
        if target_model in MODEL_SPECIFIC_TIERS:
            return MODEL_SPECIFIC_TIERS[target_model]
        for keywords, tier_name in KEYWORD_TIERS:
            for kw in keywords:
                if kw == "*" or kw.lower() in target_model.lower():
                    return tier_name
        return "tier_standard"

    def _get_gpu_tier(self, gpu_name):
        """Identifies which tier the current GPU belongs to."""
        if not gpu_name: return None
        for tier, gpus in GPU_TIERS.items():
            if gpu_name in gpus:
                return tier
        return None

    def switch_model(self, target_model):
        """Priority: Defined List -> Scrape 48GB+ -> User Pick -> Retry 3x."""
        print(f"\n[PHOENIX] 🔥 Initiating Swap...")
        active_id = self.new_pod_id if self.new_pod_id else self.pod_id
        
        # Resolve Tiers
        target_tier = self._get_model_tier(target_model)
        current_tier = self._get_gpu_tier(self.current_gpu_type)
        
        print(f"[PHOENIX] 📊 Swap Analysis: Target={target_tier} | Current={current_tier} ({self.current_gpu_type})")

        # --- PHASE 1: Try In-Pod Swap (Reuse) ---
        can_reuse = False
        if active_id and current_tier:
            if current_tier == target_tier: can_reuse = True
            elif current_tier == "tier_ultra" and target_tier == "tier_standard": can_reuse = True
            
        if can_reuse:
            if self.restart_server(target_model):
                if self.wait_for_boot(target_model, is_swap=True):
                    return True
                else:
                    print("[PHOENIX] ⚠️ In-Pod Swap failed (Container likely reset). Retrying with fresh pod...")
        
        # --- PHASE 2: Terminate Old Pod ---
        if active_id:
            print(f"[PHOENIX] ☠️ Terminating old pod {active_id}...")
            self._run_cmd(["runpodctl", "remove", "pod", active_id])
            time.sleep(2)

        # --- PHASE 3: Automatic Priority List ---
        # 3.1 Tier Selection
        selected_tier = None
        
        # A. Check Specific Model ID (High Priority)
        if target_model in MODEL_SPECIFIC_TIERS:
            selected_tier = MODEL_SPECIFIC_TIERS[target_model]
            print(f"[PHOENIX] 🎯 Exact Match: '{target_model}' -> {selected_tier}")
            
        # B. Check Keywords (Fallback)
        if not selected_tier:
            for keywords, tier_name in KEYWORD_TIERS:
                for kw in keywords:
                    if kw == "*" or kw.lower() in target_model.lower():
                        selected_tier = tier_name
                        print(f"[PHOENIX] 🔍 Keyword Match: '{kw}' -> {selected_tier}")
                        break
                if selected_tier: break
        
        # 3.2 Resolve GPU List
        priority_list = GPU_TIERS.get(selected_tier, [])
            
        # Hardcoded fallback just in case config is weird
        if not priority_list:
            print("[PHOENIX] ⚠️ No Tier matched, using safe fallback.")
            priority_list = ["NVIDIA A40", "NVIDIA RTX A6000"]
        
        print(f"[PHOENIX] 🕵️ Checking Priority List: {priority_list}")
        for gpu in priority_list:
            new_id = self.create_pod_on_gpu(gpu, target_model)
            if new_id:
                self.new_pod_id = new_id
                print(f"[PHOENIX] ✅ Successfully secured {gpu}.")
                return self.wait_for_boot(target_model)
            # print(f"[PHOENIX] ⚠️ {gpu} unavailable...")

        # --- PHASE 4: Manual Selection from Available 48GB+ ---
        print("\n[PHOENIX] ⚠️ Priority GPUs unavailable. Scanning cloud for options...")
        all_gpus = self.get_available_gpus()
        
        # Filter for >= 48GB (or >= 24GB if desperate? User said sorted from 48GB and up)
        # Let's show everything 24GB+ just in case, but sort by VRAM desc
        candidates = [g for g in all_gpus if g['vram'] >= 24]
        candidates.sort(key=lambda x: (-x['vram'], x['price']))
        
        if not candidates:
            print("[PHOENIX] ❌ No High-VRAM GPUs available.")
            return False

        print("\n=== ☁️ Available High-VRAM GPUs ===")
        print(f"{'#':<3} {'GPU Name':<25} {'VRAM':<8} {'Price/Hr':<10}")
        print("-" * 50)
        for i, g in enumerate(candidates):
            print(f"{i+1:<3} {g['name']:<25} {g['vram']}GB    ${g['price']:.2f}")

        try:
            choice_idx = int(input("\nSelect GPU # (0 to cancel): ")) - 1
            if choice_idx < 0: return False
            selected_gpu_name = candidates[choice_idx]['name']
            
            # --- PHASE 5: Retry Loop (3x) ---
            print(f"[PHOENIX] 🎯 Targeting: {selected_gpu_name}. Attempting to rent (Max 3 retries)...")
            for attempt in range(3):
                new_id = self.create_pod_on_gpu(selected_gpu_name, target_model)
                if new_id:
                    self.new_pod_id = new_id
                    print(f"[PHOENIX] ✅ Successfully secured {selected_gpu_name}.")
                    return self.wait_for_boot(target_model)
                
                print(f"[PHOENIX] ⚠️ Attempt {attempt+1}/3 failed. Retrying in 2s...")
                time.sleep(2)

            print("[PHOENIX] ❌ Failed to rent selected GPU after 3 attempts.")
            return False
            
        except: return False

    def wait_for_boot(self, target_model, is_swap=False):
        """Monitors boot status and verifies the pod actually exists."""
        print(f"[PHOENIX] ⏳ Waiting for Engine...")
        
        mismatch_count = 0
        max_mismatch = 5 if is_swap else 20 # Fail faster on swaps
        
        # Wait up to 10 mins (600s) because large models take time to download/load
        for i in range(100): 
            # 1. Verify Pod Exists
            pod_list = self._run_cmd(["runpodctl", "get", "pod"])
            if self.new_pod_id not in pod_list:
                print(f"\n[PHOENIX] ❌ CRITICAL: Pod {self.new_pod_id} disappeared from server!")
                print("[PHOENIX] This usually means it crashed on boot (Driver/Backend mismatch).")
                return False

            # 2. Check HTTP Endpoint AND Model ID
            try:
                url = f"https://{self.new_pod_id}-8000.proxy.runpod.net/v1/models"
                resp = requests.get(url, timeout=3)
                if resp.status_code == 200:
                    data = resp.json()
                    # Check if the LOADED model matches the TARGET model
                    # This prevents connecting to the OLD server process if it refused to die
                    if 'data' in data and len(data['data']) > 0:
                        loaded_id = data['data'][0]['id']
                        # Flexible matching (case-insensitive for safety)
                        if target_model.lower() in loaded_id.lower() or loaded_id.lower() in target_model.lower():
                            print(f"\n[PHOENIX] ✅ Online! Serving: {loaded_id}")
                            return True
                        else:
                            mismatch_count += 1
                            print(f"\n[DEBUG] Valid Endpoint, but ID mismatch ({mismatch_count}/{max_mismatch}): '{loaded_id}' != '{target_model}'")
                            if mismatch_count >= max_mismatch:
                                print(f"[PHOENIX] ❌ Swap Verification Failed: Persistent Old Model Detected.")
                                return False
            except: 
                pass

            # 3. Stream Logs
            self.stream_container_logs(self.new_pod_id)

            sys.stdout.write(f"\r[PHOENIX] ⏳ Booting... ({i*6}s)")
            sys.stdout.flush()
            time.sleep(6)
            
        print("\n[PHOENIX] ❌ Boot Timed Out.")
        return False


        print("\n[PHOENIX] ❌ Boot Timed Out.")
        return False

    def stream_container_logs(self, pod_id):
        """Fetches and displays new logs from the container."""
        try:
            output = self._run_cmd(["runpodctl", "logs", "pod", pod_id, "--tail", "5"])
            if output and "ERROR" not in output:
                lines = output.strip().split('\n')
                for line in lines:
                    # Simple de-duplication could be added here if needed
                    # For now, just printing the tail gives a sense of activity
                    if line.strip():
                        print(f"\n[POD LOG] {line.strip()}")
        except: pass

    def terminate_pod(self):
        """Terminates the active pod to save costs."""
        pod_id = self.new_pod_id if self.new_pod_id else self.pod_id
        if pod_id:
            print(f"\n[PHOENIX] ☠️ Terminating pod {pod_id}...")
            self._run_cmd(["runpodctl", "remove", "pod", pod_id])
            self.new_pod_id = None
            self.pod_id = None
            print(f"[PHOENIX] ✅ Pod terminated successfully.")
        else:
            print("\n[PHOENIX] No active pod to terminate.")