#!/usr/bin/env python3
"""
PiSugar2 Pro battery reader — two backends, tried in order:

1. pisugar-server daemon  (unix socket / TCP)
   Install from GitHub releases:
     https://github.com/PiSugar/pisugar-server-rs/releases
   Download the ARM64 .deb, then:
     sudo dpkg -i pisugar-power-manager_*_arm64.deb
     sudo systemctl enable --now pisugar-server

2. Direct I2C via smbus2  (works without the daemon)
   Requires I2C enabled on the Pi:
     sudo raspi-config  →  Interface Options  →  I2C  →  Enable
   And the smbus2 library:
     pip install smbus2   OR   sudo apt install python3-smbus2

Either backend failing is handled silently — read() returns (None, False).
"""

import socket
from typing import Optional

# ── Backend 1: pisugar-server daemon ──────────────────────────────────────────
_SOCK    = "/tmp/pisugar-server.sock"
_TCP     = ("127.0.0.1", 8423)
_TIMEOUT = 1.5


def _daemon_query(cmd: str) -> Optional[str]:
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


def _read_daemon() -> tuple[Optional[float], bool]:
    pct: Optional[float] = None
    charging = False

    r = _daemon_query("get battery")
    if r and r.startswith("battery:"):
        try:
            pct = float(r.split(":", 1)[1].strip())
        except ValueError:
            pass

    r2 = _daemon_query("get battery_charging")
    if r2 and "true" in r2.lower():
        charging = True

    return pct, charging


# ── Backend 2: direct I2C (PiSugar2 Pro — IP5312 chip, address 0x75) ─────────
_I2C_BUS  = 1
_I2C_ADDR = 0x75

# Voltage register pair (14-bit ADC split across two bytes)
_REG_VBAT_H = 0x22
_REG_VBAT_L = 0x23
# Charging status register (bit 5 = input power detected / charging)
_REG_STATUS = 0x71

# LiPo discharge curve endpoints used for % estimation
_V_MIN_MV = 3000.0   # ~0 %
_V_MAX_MV = 4200.0   # ~100 %


def _read_i2c() -> tuple[Optional[float], bool]:
    try:
        import smbus2
        bus = smbus2.SMBus(_I2C_BUS)
        v_hi = bus.read_byte_data(_I2C_ADDR, _REG_VBAT_H)
        v_lo = bus.read_byte_data(_I2C_ADDR, _REG_VBAT_L)
        status = bus.read_byte_data(_I2C_ADDR, _REG_STATUS)
        bus.close()

        # 14-bit ADC: upper 6 bits in v_hi, lower 8 bits in v_lo
        raw     = ((v_hi & 0x3F) << 8) | v_lo
        # Empirical calibration for IP5312 (2600 mV offset, 26.855 mV/LSB scaling)
        voltage = raw * 26.855 + 2600.0
        pct     = max(0.0, min(100.0,
                       (voltage - _V_MIN_MV) / (_V_MAX_MV - _V_MIN_MV) * 100.0))
        charging = bool(status & 0x20)
        return pct, charging

    except Exception:
        return None, False


# ── Public API ────────────────────────────────────────────────────────────────

def read() -> tuple[Optional[float], bool]:
    """
    Return (battery_percent, is_charging).
    percent is None when neither backend is available.
    """
    pct, charging = _read_daemon()
    if pct is not None:
        return pct, charging
    return _read_i2c()
