from huggingface_hub import list_models
try:
    models = list_models(author="Qwen", sort="downloads", direction=-1, limit=50)
    print(f"{'Model ID':<50} | {'Downloads'}")
    print("-" * 65)
    for model in models:
        print(f"{model.modelId:<50} | {model.downloads}")
except Exception as e:
    print(f"Error: {e}")
