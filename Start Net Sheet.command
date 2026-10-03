#!/bin/bash
# Double-click this file to start the Seller Net Sheet app.
# The first time, it downloads what it needs (a few minutes). After that it starts in seconds.
cd "$(dirname "$0")" || exit 1
export PATH="$HOME/.local/bin:$PATH"

if ! command -v uv >/dev/null 2>&1; then
  echo "First-time setup: installing the free 'uv' helper that runs this app..."
  curl -LsSf https://astral.sh/uv/install.sh | sh || {
    echo "Setup could not finish. Check your internet connection and try again."
    read -r -p "Press Return to close."
    exit 1
  }
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "Starting Seller Net Sheet... your web browser will open in a moment."
uv run --no-dev python -m netsheet
read -r -p "The app has stopped. Press Return to close this window."
