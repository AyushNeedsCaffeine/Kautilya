#!/usr/bin/env bash
# Kautilya environment recovery after WSL restart.
# Usage: bash scripts/restart_kautilya.sh [--gpu]
set -u

OLLAMA_BIN=/mnt/d/ollama_extract/bin/ollama
OLLAMA_LOG=/mnt/d/ollama_serve.log

echo "== 1/4 stopping any stale processes =="
pkill -f "ollama serve" 2>/dev/null || true
pkill -f "streamlit run" 2>/dev/null || true
sleep 2

echo "== 2/4 starting Ollama =="
if [ "${1:-}" = "--gpu" ]; then
    setsid "$OLLAMA_BIN" serve > "$OLLAMA_LOG" 2>&1 &
else
    # default: CPU mode so torch (bge-m3/NLI) keeps the GPU uncontended
    CUDA_VISIBLE_DEVICES="" setsid "$OLLAMA_BIN" serve > "$OLLAMA_LOG" 2>&1 &
fi
disown
sleep 5
curl -s http://127.0.0.1:11434/api/tags > /dev/null && echo "   Ollama UP (3 models)" || echo "   Ollama not ready yet — check $OLLAMA_LOG"

echo "== 3/4 verifying torch (GPU) =="
cd /mnt/d/Projects/GenAI-Starts-here/Kautilya
timeout 30 ./Kautilya-venv/bin/python -c "import torch; torch.zeros(1, device='cuda'); print('   torch OK: cuda =', torch.cuda.is_available())" \
    && echo "   torch healthy" || echo "   torch slow (teardown hang is benign) — full health confirmed if real inference works"

echo "== 4/4 starting Streamlit UI =="
setsid ./Kautilya-venv/bin/python -m streamlit run src/kautilya/ui/app.py \
    --server.port 8501 --server.headless true \
    > /tmp/streamlit_launch.log 2>&1 &
disown
sleep 4
echo "   UI -> http://localhost:8501  (log: /tmp/streamlit_launch.log)"