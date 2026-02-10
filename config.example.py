# config.example.py
# RENAMED from config.py -> config.example.py
# INSTRUCTIONS: Rename this file to 'config.py' and add your API keys.

# =====================================================
# 1. CLOUD SETTINGS (RunPod Integration)
# =====================================================
USE_RUNPOD = True  # Set to False to force Offline Only Mode
API_KEY = "YOUR_RUNPOD_API_KEY_HERE" 
POD_ID = "YOUR_POD_ID_HERE" 

# Base URL constructed from Pod ID
RUNPOD_BASE_URL = f"https://{POD_ID}-8000.proxy.runpod.net/v1"

# =====================================================
# 2. THE HYBRID MAP (Model selection menu)
# =====================================================
# FORMAT: "Menu Display Name": "Local Filename"
# 1. The Key is what you see in the boot menu.
# 2. The Value is the filename in your 'models/' folder.
# NOTE: For Cloud Mode, the system will try to resolve a HuggingFace ID from this filename.
MODEL_MAP = {
    "sophosympatheia/Midnight-Miqu-70B": "Midnight-Miqu-70B.awq",
    "Qwen/Qwen2.5-72B-Instruct-AWQ": "Qwen2.5-72B-Instruct.awq",
    "openai/gpt-oss-20b": "gpt-oss-20b-Q2_K.gguf",
    "Qwen/Qwen3-VL-8B-Instruct": "Qwen3-VL-8B-Instruct.gguf",
    "Qwen/Qwen2.5-14B-Instruct": "Qwen2.5-14B-Q4_K_M.gguf",
    "dphn/Dolphin-Mistral-24B-Venice-Edition": "Dolphin-Mistral-24B-Venice-Edition-q4_k_m.gguf",
    "meta-llama/Meta-Llama-3-8B-Instruct": "Llama-3-8B-Q5.gguf",
    "mistralai/Mistral-7B-Instruct-v0.3": "Mistral-7B-v0.3.gguf"
}

# =====================================================
# 3. GPU HARDWARE PROFILES (Smart Cloud Selection)
# =====================================================
# Define which GPUs are suitable for which models.
GPU_TIERS = {
    "tier_standard": [ # 48GB Cards (Good for <40B models)
        "NVIDIA A40",
        "NVIDIA RTX A6000",
        "NVIDIA RTX 6000 Ada",
        "NVIDIA A100 80GB PCIe" # Overflow option
    ],
    "tier_ultra": [    # 80GB+ Cards (Required for 70B+ models)
        "NVIDIA A100 80GB PCIe",
        "NVIDIA A100-SXM4-80GB",
        "NVIDIA H100 80GB HBM3"
    ]
}

MODEL_SPECIFIC_TIERS = {
    "cecibas/Midnight-Miqu-70B-v1.5-4bit": "tier_ultra",
    "Qwen/Qwen2.5-72B-Instruct-AWQ": "tier_ultra",
}

KEYWORD_TIERS = [
    ("70b", "tier_ultra"),
    ("72b", "tier_ultra"),
    ("miqu", "tier_ultra"),
]
