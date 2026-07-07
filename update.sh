#!/bin/bash
set -euo pipefail

INSTALL_DIR="/usr/share/hackingtool"
REPO_URL="https://github.com/dcooper94/hackingtool.git"
REPO_BRANCH="hacktool-gui-v2"

if [[ $EUID -ne 0 ]]; then
    echo "[ERROR] Run as root: sudo bash update.sh"
    exit 1
fi

if [[ ! -d "$INSTALL_DIR" ]]; then
    echo "[ERROR] Installation not found at $INSTALL_DIR. Run install.py first."
    exit 1
fi

echo "[*] Checking internet connection..."
if ! curl -sSf --max-time 10 https://github.com > /dev/null; then
    echo "[ERROR] No internet connection."
    exit 1
fi
echo "[✔] Internet OK"

echo "[*] Pulling latest changes from $REPO_URL ($REPO_BRANCH)..."
git -C "$INSTALL_DIR" config --local safe.directory "$INSTALL_DIR"
if git -C "$INSTALL_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git -C "$INSTALL_DIR" remote set-url origin "$REPO_URL" || true
    git -C "$INSTALL_DIR" fetch --depth 1 origin "$REPO_BRANCH"
    git -C "$INSTALL_DIR" checkout -B "$REPO_BRANCH" "origin/$REPO_BRANCH"
else
    echo "[ERROR] $INSTALL_DIR is not a git checkout. Re-run the one-liner installer."
    exit 1
fi

echo "[*] Updating Python dependencies..."
if [[ -f "$INSTALL_DIR/venv/bin/pip" ]]; then
    "$INSTALL_DIR/venv/bin/pip" install -q --upgrade -r "$INSTALL_DIR/requirements.txt"
else
    echo "[WARN] venv not found — skipping pip update. Run install.py to create it."
fi

echo "[✔] Hackingtool updated. Run 'hackingtool' to start."
