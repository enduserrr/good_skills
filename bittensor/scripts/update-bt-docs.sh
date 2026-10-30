#!/usr/bin/env bash
# Keep a local sparse clone of RaoFoundation/subtensor docs fresh.
# Docs land in ~/.hermes/cache/subtensor-docs/docs/ — grep them directly.
set -e
DIR="$HOME/.hermes/cache/subtensor-docs"
if [ ! -d "$DIR/.git" ]; then
  git clone --depth 1 --filter=blob:none --sparse \
    https://github.com/RaoFoundation/subtensor.git "$DIR"
  git -C "$DIR" sparse-checkout set docs
else
  git -C "$DIR" pull --ff-only
fi
git -C "$DIR" log -1 --format="subtensor docs @ %h %ci"
