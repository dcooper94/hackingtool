#!/usr/bin/env python3
"""
PiSugar2 / PiSugar2 Pro battery reader.

Talks to the pisugar-server daemon (unix socket preferred, TCP fallback).
Install the daemon once on the Pi with:
    curl http://cdn.pisugar.com/release/pisugar-server.sh | sudo bash
    sudo systemctl enable --now pisugar-server

If the daemon is not running, read() returns (None, False) silently.
"""

import socket
from typing import Optional

_SOCK = "/tmp/pisugar-server.sock"
_TCP  = ("127.0.0.1", 8423)
_TIMEOUT = 1.5


def _query(cmd: str) -> Optional[str]:
    """Send one command to pisugar-server, return the trimmed response."""
    for family, addr in ((socket.AF_UNIX, _SOCK), (socket.AF_INET, _TCP)):
        try:
            with socket.socket(family, socket.SOCK_STREAM) as s:
                s.settimeout(_TIMEOUT)
                s.connect(addr)
                s.sendall((cmd + "\n").encode())
                return s.recv(256).decode().strip()
        except Exception:
            continue
    return None


def read() -> tuple[Optional[float], bool]:
    """
    Return (percent, is_charging).
    percent is None when the pisugar-server daemon is unreachable.
    """
    pct: Optional[float] = None
    charging = False

    r = _query("get battery")
    if r and r.startswith("battery:"):
        try:
            pct = float(r.split(":", 1)[1].strip())
        except ValueError:
            pass

    r2 = _query("get battery_charging")
    if r2 and "true" in r2.lower():
        charging = True

    return pct, charging
