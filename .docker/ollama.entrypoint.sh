#!/bin/bash

# Start Ollama serverß
ollama serve &

# Pull Ollama models
ollama pull nomic-embed-text:latest
ollama pull llama3:latest

# Wait for Ollama server to be ready
ATTEMPT=0
until ollama list > /dev/null; do
  echo "Waiting for Ollama server to be ready..."
  ATTEMPT=$((ATTEMPT + 1))
  if [ "$ATTEMPT" -ge "$MAX_ATTEMPTS" ]; then
    echo "Error: Ollama server did not become ready after $MAX_ATTEMPTS attempts. Exiting."
    exit 1
  fi
  sleep 2
done

echo "Ollama server is ready. Models pulled successfully."
# Keep the container running
tail -f /dev/null
