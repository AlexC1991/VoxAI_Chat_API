from huggingface_hub import model_info
import sys

models_to_check = [
    "dranger003/Midnight-Miqu-70B-v1.5-AWQ",
    "cecibas/Midnight-Miqu-70B-v1.5-4bit",
    "Qwen/Qwen2.5-72B-Instruct-AWQ"
]

print(f"{'Model ID':<50} | {'Status'}")
print("-" * 65)

for model_id in models_to_check:
    try:
        info = model_info(model_id)
        status = "Public"
        if info.private:
            status = "Private (Locked)"
        elif info.gated:
            status = "Gated (Requires Token)"
        
        print(f"{model_id:<50} | {status}")
    except Exception as e:
        print(f"{model_id:<50} | ERROR: {e}")
