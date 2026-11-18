#!/usr/bin/env bash
# d1-2B (LiquidAI, LFM3-VL-2B lineage) Q4_K_M decision-model server.
# Decision-only model: serves /v1/systemone (typed answers, one forward pass, no
# generation); /v1/chat/completions returns 501. Requires llama.cpp >= b11960 (v0.8.0).
# Swap models by editing -m, then: systemctl --user restart decide
exec "$HOME/.local/bin/llama-server" \
  -m "$HOME/models/d1-2B-Q4_K_M.gguf" \
  -b 8192 -ub 8192 \
  --host 127.0.0.1 --port 9931
