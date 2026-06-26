#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# HackingTool — boot setup
#
# Usage (from anywhere inside the repo):
#   sudo bash setup-boot.sh
#
# What it does:
#   1. Creates /usr/bin/hackingtool-gui  (global command)
#   2. Creates /etc/xdg/autostart entry  (starts GUI on desktop login/boot)
#   3. Creates /usr/share/applications entry (shows in app menu)
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# Resolve repo root (directory that contains this script)
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BIN=/usr/bin/hackingtool-gui
AUTOSTART_FILE=/etc/xdg/autostart/hackingtool-gui.desktop
APPENTRY=/usr/share/applications/hackingtool-gui.desktop

GREEN='\033[0;32m'; CYAN='\033[0;36m'; RED='\033[0;31m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}[✔]${RESET} $1"; }
info() { echo -e "${CYAN}[*]${RESET} $1"; }
fail() { echo -e "${RED}[✘]${RESET} $1"; exit 1; }

[ "$(id -u)" -eq 0 ] || fail "Run as root:  sudo bash \"${BASH_SOURCE[0]}\""

echo ""
echo -e "${CYAN}  HackingTool — boot setup${RESET}"
echo -e "  Repo: $REPO"
echo ""

# ── 1. Global command (/usr/bin/hackingtool-gui) ──────────────────────────────
info "Installing global command..."
cat > "$BIN" <<LAUNCHER
#!/bin/bash
REPO="$REPO"
[ -f "\$REPO/venv/bin/activate" ] && source "\$REPO/venv/bin/activate"
cd "\$REPO"
exec python3 "\$REPO/gui.py" "\$@"
LAUNCHER
chmod 755 "$BIN"
ok "Global command: $BIN"

# ── 2. Autostart on desktop login (/etc/xdg/autostart) ───────────────────────
info "Installing autostart entry..."
mkdir -p /etc/xdg/autostart
cat > "$AUTOSTART_FILE" <<DESKTOP
[Desktop Entry]
Type=Application
Name=HackingTool
Comment=Touchscreen penetration testing suite
Exec=$BIN
Terminal=false
X-GNOME-Autostart-enabled=true
DESKTOP
ok "Autostart: $AUTOSTART_FILE"

# ── 3. Application menu entry (/usr/share/applications) ──────────────────────
info "Installing app menu entry..."
mkdir -p /usr/share/applications
cat > "$APPENTRY" <<DESKTOP
[Desktop Entry]
Type=Application
Name=HackingTool GUI
Comment=Touchscreen penetration testing suite
Exec=$BIN
Terminal=false
Categories=Security;
DESKTOP
ok "App menu: $APPENTRY"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}  Done!${RESET}"
echo -e "  • Run now:    ${CYAN}hackingtool-gui${RESET}"
echo -e "  • On reboot:  GUI starts automatically when the desktop loads"
echo ""
