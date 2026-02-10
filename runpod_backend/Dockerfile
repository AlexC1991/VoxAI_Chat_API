FROM vllm/vllm-openai:latest

# Install the manager dependencies
RUN pip install fastapi uvicorn httpx

WORKDIR /app

# Copy the manager script
COPY manager.py /app/manager.py

# Expose the API port
EXPOSE 8000

# Start the Manager (which starts vLLM)
ENTRYPOINT ["python3", "/app/manager.py"]