#!/usr/bin/env python3
"""
HackingTool Touchscreen GUI
Designed for 3.5-inch Raspberry Pi displays (480 × 320 landscape).
Run with:  python3 gui.py

Requirements: python3-tk (apt install python3-tk)
"""

import math
import os
import pty
import re
import select
import signal
import sys
import time
import shutil
import threading
import subprocess
import tkinter as tk
from datetime import datetime
from pathlib import Path

# ── Bootstrap ──────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).parent
sys.path.insert(0, str(_ROOT))
os.chdir(_ROOT)

from tools.anonsurf              import AnonSurfTools
from tools.ddos                  import DDOSTools
from tools.exploit_frameworks    import ExploitFrameworkTools
from tools.forensics             import ForensicTools
from tools.information_gathering import InformationGatheringTools
from tools.other_tools           import OtherTools
from tools.payload_creator       import PayloadCreatorTools
from tools.phishing_attack       import PhishingAttackTools
from tools.post_exploitation     import PostExploitationTools
from tools.remote_administration import RemoteAdministrationTools
from tools.reverse_engineering   import ReverseEngineeringTools
from tools.sql_injection         import SqlInjectionTools
from tools.steganography         import SteganographyTools
from tools.tool_manager          import ToolManager
from tools.web_attack            import WebAttackTools
from tools.wireless_attack       import WirelessAttackTools
from tools.wordlist_generator    import WordlistGeneratorTools
from tools.xss_attack            import XSSAttackTools
from tools.active_directory      import ActiveDirectoryTools
from tools.cloud_security        import CloudSecurityTools
from tools.mobile_security       import MobileSecurityTools

# ── Palette ────────────────────────────────────────────────────────────────────
BG      = "#060810"
PANEL   = "#0d1117"
CARD    = "#161b22"
HOVER   = "#1c2535"
BORDER  = "#21262d"
FG      = "#e6edf3"
DIM     = "#6e7681"
GREEN   = "#3fb950"
CYAN    = "#58a6ff"
YELLOW  = "#d29922"
RED     = "#f85149"
MAGENTA = "#bc8cff"
BG_G    = "#0d2b0f"
BG_C    = "#0d1f33"
BG_R    = "#2b0f0d"
BG_M    = "#1f0d33"
TERM_FG = "#00ff41"

TAP_THRESHOLD = 50   # pixels
TAP_MAX_MS    = 280  # milliseconds


def F(size: int, bold: bool = False) -> tuple:
    return ("Courier", size, "bold" if bold else "normal")


# ── Category registry ──────────────────────────────────────────────────────────
CATEGORIES: list[tuple[str, str, object]] = [
    ("🛡",  "Anon Hiding",      AnonSurfTools()),
    ("🔍",  "Info Gather",      InformationGatheringTools()),
    ("📚",  "Wordlist Gen",     WordlistGeneratorTools()),
    ("📶",  "Wireless",         WirelessAttackTools()),
    ("🧩",  "SQL Inject",       SqlInjectionTools()),
    ("🎣",  "Phishing",         PhishingAttackTools()),
    ("🌐",  "Web Attack",       WebAttackTools()),
    ("🔧",  "Post Exploit",     PostExploitationTools()),
    ("🕵",  "Forensics",        ForensicTools()),
    ("📦",  "Payloads",         PayloadCreatorTools()),
    ("🧰",  "Exploit FW",       ExploitFrameworkTools()),
    ("🔁",  "Reverse Eng",      ReverseEngineeringTools()),
    ("⚡",  "DDOS",             DDOSTools()),
    ("🖥",  "Remote Admin",     RemoteAdministrationTools()),
    ("💥",  "XSS",              XSSAttackTools()),
    ("🖼",  "Stego",            SteganographyTools()),
    ("🏢",  "Active Dir",       ActiveDirectoryTools()),
    ("☁",   "Cloud Sec",        CloudSecurityTools()),
    ("📱",  "Mobile Sec",       MobileSecurityTools()),
    ("✨",  "Other Tools",      OtherTools()),
    ("♻",   "Update/Remove",    ToolManager()),
]


# ── Tap helper ─────────────────────────────────────────────────────────────────
def _bind_tap(widgets: list[tk.Widget], on_tap,
              hl_target: tk.Widget | None = None, hl_color: str = HOVER):
    """
    Tap = press + release within TAP_THRESHOLD px and TAP_MAX_MS.
    Displacement checked in both B1-Motion and ButtonRelease so drivers that
    skip motion events (common on RPi resistive screens) are handled correctly.
    Highlight is delayed 80 ms so scroll-flicks don't flash every item.
    """
    state: dict = {"x": 0, "y": 0, "t": 0.0, "dragging": False, "hl_id": None}

    def _hl(bg: str):
        if hl_target is None:
            return
        try:
            hl_target.config(bg=bg)
            for k in hl_target.winfo_children():
                k.config(bg=bg)
        except tk.TclError:
            pass

    def _cancel_hl_pending():
        aid = state["hl_id"]
        if aid is not None:
            state["hl_id"] = None
            try:
                hl_target.after_cancel(aid)
            except Exception:
                pass

    def _press(e):
        state["x"] = e.x_root
        state["y"] = e.y_root
        state["t"] = time.monotonic()
        state["dragging"] = False
        _cancel_hl_pending()
        if hl_target is not None:
            state["hl_id"] = hl_target.after(
                80, lambda: (None if state["dragging"] else _hl(hl_color))
            )

    def _motion(e):
        dy = abs(e.y_root - state["y"])
        dx = abs(e.x_root - state["x"])
        if not state["dragging"] and (dy > TAP_THRESHOLD or dx > TAP_THRESHOLD):
            state["dragging"] = True
            _cancel_hl_pending()
            _hl(CARD)

    def _release(e):
        _cancel_hl_pending()
        _hl(CARD)
        elapsed_ms = (time.monotonic() - state["t"]) * 1000
        dy = abs(e.y_root - state["y"])
        dx = abs(e.x_root - state["x"])
        moved = dy > TAP_THRESHOLD or dx > TAP_THRESHOLD
        if not state["dragging"] and not moved and elapsed_ms < TAP_MAX_MS:
            on_tap()

    for w in widgets:
        try:
            w.bind("<ButtonPress-1>",   _press,   add="+")
            w.bind("<B1-Motion>",       _motion,  add="+")
            w.bind("<ButtonRelease-1>", _release, add="+")
        except tk.TclError:
            pass


# ── ANSI stripper ──────────────────────────────────────────────────────────────
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mABCDEFGHJKSTfnsu]|\x1b\][^\x07]*\x07|\r")

def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


# ── pip → uv rewriter ──────────────────────────────────────────────────────────
UV_BIN  = shutil.which("uv")
_PIP_RE = re.compile(r"\b(?:python3?\s+-m\s+)?pip3?\s+install\b")

def _preprocess_cmd(cmd: str) -> str:
    if not _PIP_RE.search(cmd):
        return cmd
    if "--system" in cmd or "--break-system-packages" in cmd:
        return cmd
    if UV_BIN:
        return _PIP_RE.sub("uv pip install --system", cmd)
    return _PIP_RE.sub(lambda m: m.group(0) + " --break-system-packages", cmd)


# ── Update-command builder ─────────────────────────────────────────────────────
def _build_update_cmds(tool) -> list[str]:
    cmds: list[str] = []
    for ic in getattr(tool, "INSTALL_COMMANDS", []) or []:
        if "git clone" in ic:
            parts = ic.split()
            urls  = [p for p in parts if p.startswith("http")]
            if urls:
                dn  = urls[0].rstrip("/").rsplit("/", 1)[-1].replace(".git", "")
                idx = parts.index(urls[0])
                if idx + 1 < len(parts) and not parts[idx + 1].startswith("-"):
                    dn = parts[idx + 1]
                cmds.append(f"git -C {dn} pull")
        elif "pip install" in ic:
            cmds.append(_preprocess_cmd(ic.replace("pip install",
                                                    "pip install --upgrade")))
        elif "go install" in ic:
            cmds.append(ic)
        elif "gem install" in ic:
            cmds.append(ic.replace("gem install", "gem update"))
    return cmds or ["echo 'No automatic update method found for this tool.'"]


# ── Main application ───────────────────────────────────────────────────────────
class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("HackingTool")
        self.configure(bg=BG)

        self.attributes("-fullscreen", True)
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))

        self._stack: list[tuple] = []
        self._proc:      subprocess.Popen | None = None
        self._master_fd: int | None = None   # PTY master fd for stdin forwarding
        self._term_gen:  int = 0

        self._build_chrome()
        self._push(self._page_main)
        self.after(800, self._poll_battery)
        self._tick_clock()

    # ── Chrome ────────────────────────────────────────────────────────────────

    def _build_chrome(self):
        hdr = tk.Frame(self, bg=PANEL, height=40)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)

        self._back_btn = tk.Button(
            hdr, text=" ◄ ", font=F(10, bold=True),
            bg=PANEL, fg=CYAN,
            activebackground=CARD, activeforeground=CYAN,
            relief=tk.FLAT, bd=0, padx=10,
            state=tk.DISABLED,
            command=self._go_back,
        )
        self._back_btn.pack(side=tk.LEFT, fill=tk.Y)

        self._title_lbl = tk.Label(
            hdr, text="[ HACKINGTOOL ]", font=F(11, bold=True),
            bg=PANEL, fg=GREEN,
        )
        self._title_lbl.pack(side=tk.LEFT, fill=tk.Y, padx=4)

        tk.Button(
            hdr, text=" ✕ ", font=F(11, bold=True),
            bg=PANEL, fg=RED,
            activebackground=BG_R, activeforeground=RED,
            relief=tk.FLAT, bd=0, padx=10,
            command=self.destroy,
        ).pack(side=tk.RIGHT, fill=tk.Y)

        self._bat_lbl = tk.Label(hdr, text="", font=F(8, bold=True),
                                 bg=PANEL, fg=GREEN)
        self._bat_lbl.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 4))

        self._clock_lbl = tk.Label(hdr, text="", font=F(8), bg=PANEL, fg=DIM)
        self._clock_lbl.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8))

        self._area = tk.Frame(self, bg=BG)
        self._area.pack(fill=tk.BOTH, expand=True)

    def _tick_clock(self):
        now = datetime.now()
        self._clock_lbl.config(text=now.strftime("%H:%M  %d %b"))
        self.after(1000, self._tick_clock)

    def _poll_battery(self):
        """Spawn a background thread to read battery, then update header label."""
        def _do_read():
            try:
                from battery import read as _bat_read
                pct, charging = _bat_read()
            except Exception:
                pct, charging = None, False

            def _update():
                try:
                    if pct is not None:
                        icon  = "⚡" if charging else "🔋"
                        color = GREEN if pct > 50 else (YELLOW if pct > 20 else RED)
                        self._bat_lbl.config(text=f"{icon}{pct:.0f}%", fg=color)
                    else:
                        self._bat_lbl.config(text="")
                except tk.TclError:
                    pass

            self.after(0, _update)

        threading.Thread(target=_do_read, daemon=True).start()
        self.after(30_000, self._poll_battery)

    def _set_header(self, text: str, back: bool = False):
        self._title_lbl.config(text=text[:28])
        self._back_btn.config(
            state=tk.NORMAL if back else tk.DISABLED,
            fg=CYAN if back else DIM,
        )

    # ── Navigation ────────────────────────────────────────────────────────────

    def _clear(self):
        for w in self._area.winfo_children():
            w.destroy()

    def _push(self, page_fn, *args):
        self._stack.append((page_fn, args))
        self._clear()
        page_fn(*args)

    def _go_back(self):
        self._term_gen += 1
        self._kill_proc()
        if len(self._stack) > 1:
            self._stack.pop()
            fn, args = self._stack[-1]
            self._clear()
            fn(*args)

    def _kill_proc(self):
        """Kill the running subprocess and close the PTY master fd."""
        if self._proc and self._proc.poll() is None:
            try:
                os.killpg(os.getpgid(self._proc.pid), signal.SIGTERM)
            except Exception:
                try:
                    self._proc.terminate()
                except Exception:
                    pass
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
            self._master_fd = None

    # ── Paged view ────────────────────────────────────────────────────────────

    def _show_paged(self, container: tk.Frame, items: list,
                    build_fn, per_page: int):
        """
        Paginate *items* inside *container* with ◄ / ► arrow buttons.
        build_fn(page_frame, page_items) populates each page.
        No scrolling — eliminates drag-vs-tap ambiguity completely.
        """
        n_pages = max(1, math.ceil(len(items) / per_page))
        state = {"p": 0}

        # nav must be packed BEFORE content so expand=True doesn't steal its space
        nav = tk.Frame(container, bg=PANEL, height=46)
        nav.pack(side=tk.BOTTOM, fill=tk.X)
        nav.pack_propagate(False)

        content = tk.Frame(container, bg=BG)
        content.pack(fill=tk.BOTH, expand=True)

        def _prev():
            if state["p"] > 0:
                state["p"] -= 1
                _render()

        def _next():
            if state["p"] < n_pages - 1:
                state["p"] += 1
                _render()

        btn_prev = tk.Button(
            nav, text="   ◄   ", font=F(13, bold=True),
            bg=PANEL, fg=CYAN, relief=tk.FLAT, bd=0,
            activebackground=CARD, activeforeground=CYAN,
            command=_prev,
        )
        btn_prev.pack(side=tk.LEFT, fill=tk.Y, padx=4)

        page_lbl = tk.Label(nav, text="", font=F(9), bg=PANEL, fg=DIM)
        page_lbl.pack(side=tk.LEFT, expand=True)

        btn_next = tk.Button(
            nav, text="   ►   ", font=F(13, bold=True),
            bg=PANEL, fg=CYAN, relief=tk.FLAT, bd=0,
            activebackground=CARD, activeforeground=CYAN,
            command=_next,
        )
        btn_next.pack(side=tk.RIGHT, fill=tk.Y, padx=4)

        def _render():
            for w in content.winfo_children():
                w.destroy()
            p = state["p"]
            build_fn(content, items[p * per_page:(p + 1) * per_page])
            page_lbl.config(
                text=f"page {p + 1} of {n_pages}" if n_pages > 1 else ""
            )
            btn_prev.config(
                state=tk.NORMAL if p > 0         else tk.DISABLED,
                fg   =CYAN       if p > 0         else DIM,
            )
            btn_next.config(
                state=tk.NORMAL if p < n_pages-1 else tk.DISABLED,
                fg   =CYAN       if p < n_pages-1 else DIM,
            )

        _render()

    # ── Page: category grid ───────────────────────────────────────────────────

    def _page_main(self):
        self._stack = [(self._page_main, ())]
        self._set_header("[ HACKINGTOOL ]", back=False)

        COLS = 2  # 2 cols × 3 rows = 6 per page → 4 pages for 21 categories

        def _build(frame, page_items):
            for i, (icon, label, coll) in enumerate(page_items):
                r, c = divmod(i, COLS)
                card = tk.Frame(
                    frame, bg=CARD,
                    highlightbackground=BORDER, highlightthickness=1,
                )
                card.grid(row=r, column=c, padx=3, pady=2, sticky="nsew")
                frame.rowconfigure(r, weight=1, minsize=70)

                icon_lbl = tk.Label(card, text=icon, font=("", 18),
                                    bg=CARD, fg=FG, pady=4)
                icon_lbl.pack()
                text_lbl = tk.Label(card, text=label, font=F(8, bold=True),
                                    bg=CARD, fg=CYAN, justify=tk.CENTER, pady=1)
                text_lbl.pack()

                def _go(col=coll):
                    self._push(self._page_category, col)

                _bind_tap([card, icon_lbl, text_lbl], _go,
                          hl_target=card, hl_color=HOVER)

            for c in range(COLS):
                frame.columnconfigure(c, weight=1, minsize=130)

        self._show_paged(self._area, CATEGORIES, _build, per_page=6)

    # ── Page: tool list ───────────────────────────────────────────────────────

    def _page_category(self, collection):
        self._set_header(collection.TITLE[:28], back=True)

        tools = (
            collection._active_tools()
            if hasattr(collection, "_active_tools")
            else list(getattr(collection, "TOOLS", []))
        )

        total = len(tools)
        n_ok  = sum(1 for t in tools
                    if hasattr(t, "is_installed") and t.is_installed)

        bar = tk.Frame(self._area, bg=PANEL, pady=4, padx=8)
        bar.pack(fill=tk.X)
        tk.Label(bar, text=f"{total} tools", font=F(9, bold=True),
                 bg=PANEL, fg=FG).pack(side=tk.LEFT)
        tk.Label(bar, text=f"   ✔ {n_ok}",
                 font=F(9), bg=PANEL, fg=GREEN).pack(side=tk.LEFT)
        tk.Label(bar, text=f"  ✘ {total - n_ok}",
                 font=F(9), bg=PANEL, fg=DIM).pack(side=tk.LEFT)
        tk.Frame(self._area, bg=BORDER, height=1).pack(fill=tk.X)

        def _build(frame, page_items):
            for tool in page_items:
                is_sub = hasattr(tool, "_active_tools")

                row = tk.Frame(frame, bg=CARD,
                               highlightbackground=BORDER, highlightthickness=1)
                row.pack(fill=tk.X, padx=4, pady=1)

                if is_sub:
                    s_txt, s_fg = "▶", CYAN
                elif hasattr(tool, "is_installed"):
                    s_txt = "✔" if tool.is_installed else "✘"
                    s_fg  = GREEN if tool.is_installed else DIM
                else:
                    s_txt, s_fg = "•", DIM

                stat = tk.Label(row, text=s_txt, font=F(12),
                                bg=CARD, fg=s_fg, width=3, pady=14)
                stat.pack(side=tk.LEFT)

                mid = tk.Frame(row, bg=CARD)
                mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=6)

                name = tk.Label(mid, text=tool.TITLE, font=F(10, bold=True),
                                bg=CARD, fg=FG, anchor="w")
                name.pack(fill=tk.X)

                desc_str = (getattr(tool, "DESCRIPTION", "") or "").strip()
                sub_widgets: list[tk.Widget] = [stat, mid, name]
                if desc_str:
                    short = desc_str[:60] + ("…" if len(desc_str) > 60 else "")
                    desc = tk.Label(mid, text=short, font=F(8),
                                    bg=CARD, fg=DIM, anchor="w")
                    desc.pack(fill=tk.X)
                    sub_widgets.append(desc)

                arrow = tk.Label(row, text="›", font=F(15, bold=True),
                                 bg=CARD, fg=CYAN, padx=10)
                arrow.pack(side=tk.RIGHT)
                sub_widgets.append(arrow)

                def _go(t=tool):
                    if hasattr(t, "_active_tools"):
                        self._push(self._page_category, t)
                    else:
                        self._push(self._page_tool, t)

                _bind_tap([row] + sub_widgets, _go,
                          hl_target=row, hl_color=HOVER)

        self._show_paged(self._area, tools, _build, per_page=4)

    # ── Page: tool detail + actions ───────────────────────────────────────────

    def _page_tool(self, tool):
        self._set_header(tool.TITLE[:28], back=True)

        p = tk.Frame(self._area, bg=BG)
        p.pack(fill=tk.BOTH, expand=True)

        installed = hasattr(tool, "is_installed") and tool.is_installed

        # Status + description row
        top = tk.Frame(p, bg=PANEL, padx=10, pady=6)
        top.pack(fill=tk.X, padx=4, pady=(4, 2))

        sb_fg  = GREEN if installed else DIM
        sb_txt = "✔  INSTALLED" if installed else "✘  NOT INSTALLED"
        tk.Label(top, text=sb_txt, font=F(10, bold=True),
                 bg=PANEL, fg=sb_fg).pack(anchor="w")

        raw = (getattr(tool, "DESCRIPTION", "") or "No description.").strip()
        tk.Label(top, text=raw[:160], font=F(8), bg=PANEL, fg=DIM,
                 wraplength=450, justify=tk.LEFT, anchor="nw").pack(fill=tk.X, pady=(4, 0))

        url = getattr(tool, "PROJECT_URL", "")
        if url:
            import webbrowser
            lnk = tk.Label(top, text=f"🔗 {url[:52]}", font=F(8),
                           bg=PANEL, fg=CYAN, cursor="hand2", anchor="w")
            lnk.pack(fill=tk.X)
            lnk.bind("<Button-1>", lambda e: webbrowser.open_new_tab(url))

        tk.Frame(p, bg=BORDER, height=1).pack(fill=tk.X, padx=4, pady=4)

        # ── Action buttons — stacked vertically for large touch targets ───────
        install_cmds = list(getattr(tool, "INSTALL_COMMANDS", []) or [])
        run_cmds     = list(getattr(tool, "RUN_COMMANDS",     []) or [])
        update_cmds  = _build_update_cmds(tool)

        for label, cmds, bg_col, fg_col, title_prefix in [
            ("⬇  INSTALL",  install_cmds, BG_G, GREEN,   "Installing"),
            ("▶  RUN",       run_cmds,     BG_C, CYAN,    "Running"),
            ("↑  UPDATE",    update_cmds,  BG_M, MAGENTA, "Updating"),
        ]:
            has = bool(cmds)
            tk.Button(
                p, text=label, font=F(10, bold=True),
                bg=bg_col if has else CARD,
                fg=fg_col if has else DIM,
                activebackground=HOVER, activeforeground=fg_col,
                relief=tk.FLAT, bd=0, pady=15,
                disabledforeground=DIM,
                state=tk.NORMAL if has else tk.DISABLED,
                command=lambda c=cmds, t=title_prefix: self._push(
                    self._page_terminal, c, f"{t}: {tool.TITLE}"
                ),
            ).pack(fill=tk.X, padx=4, pady=2)

        # Extra OPTIONS defined by the tool
        std = {"Install", "Run", "Update", "Open Folder"}
        extra = [o for o in getattr(tool, "OPTIONS", []) if o[0] not in std]
        if extra:
            tk.Frame(p, bg=BORDER, height=1).pack(fill=tk.X, padx=4, pady=4)
            for opt_name, opt_fn in extra:
                tk.Button(
                    p, text=opt_name, font=F(9, bold=True),
                    bg=PANEL, fg=YELLOW,
                    activebackground=HOVER, activeforeground=YELLOW,
                    relief=tk.FLAT, bd=0, pady=12,
                    command=opt_fn,
                ).pack(fill=tk.X, padx=4, pady=2)

    # ── Page: in-app terminal (PTY-backed, with stdin input bar) ─────────────

    def _page_terminal(self, commands: list[str], title: str = "Terminal"):
        """
        Runs *commands* inside a PTY so interactive programs (prompts, curses,
        colour output) work correctly.  A text entry + SEND button at the
        bottom lets the user type answers / commands into the running process.
        """
        self._term_gen += 1
        my_gen = self._term_gen
        self._set_header(title[:28], back=True)

        outer = tk.Frame(self._area, bg=BG)
        outer.pack(fill=tk.BOTH, expand=True)

        # ── control bar (pack bottom-up so expand=True on txt_wrap doesn't hide them)
        ctrl = tk.Frame(outer, bg=PANEL, height=36)
        ctrl.pack(side=tk.BOTTOM, fill=tk.X)
        ctrl.pack_propagate(False)

        inp_frame = tk.Frame(outer, bg="#000000", height=40)
        inp_frame.pack(side=tk.BOTTOM, fill=tk.X)
        inp_frame.pack_propagate(False)

        # ── output area (fills remaining space above the two bottom bars) ──
        txt_wrap = tk.Frame(outer, bg="#000000")
        txt_wrap.pack(fill=tk.BOTH, expand=True)

        txt = tk.Text(
            txt_wrap,
            bg="#000000", fg=TERM_FG,
            font=("Courier", 10),
            selectbackground="#003300",
            insertbackground=TERM_FG,
            relief=tk.FLAT, bd=4, wrap=tk.WORD,
            spacing1=2,
            state=tk.DISABLED,
        )
        vsb = tk.Scrollbar(
            txt_wrap, command=txt.yview,
            bg="#0a0a0a", troughcolor="#000000", activebackground="#1a1a1a",
        )
        txt.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        txt.pack(fill=tk.BOTH, expand=True)

        txt.tag_configure("cmd",  foreground=CYAN)
        txt.tag_configure("ok",   foreground=GREEN)
        txt.tag_configure("err",  foreground=RED)
        txt.tag_configure("info", foreground=YELLOW)

        # ── stdin input bar ───────────────────────────────────────────────────
        inp_var = tk.StringVar()
        inp_entry = tk.Entry(
            inp_frame, textvariable=inp_var,
            font=("Courier", 10), bg="#0a0a0a", fg=TERM_FG,
            insertbackground=TERM_FG, relief=tk.FLAT, bd=4,
            selectbackground="#003300",
        )
        inp_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _send_input(*_):
            text = inp_var.get()
            inp_var.set("")
            if self._master_fd is not None:
                try:
                    os.write(self._master_fd, (text + "\n").encode())
                except OSError:
                    pass

        inp_entry.bind("<Return>", _send_input)

        tk.Button(
            inp_frame, text=" ↵ SEND ", font=F(9, bold=True),
            bg=BG_C, fg=CYAN, relief=tk.FLAT, bd=0,
            activebackground=HOVER, activeforeground=CYAN,
            command=_send_input,
        ).pack(side=tk.RIGHT, fill=tk.Y, pady=2, padx=2)

        # ── control bar ───────────────────────────────────────────────────────
        status_lbl = tk.Label(ctrl, text="● RUNNING", font=F(8, bold=True),
                              bg=PANEL, fg=GREEN)
        status_lbl.pack(side=tk.RIGHT, padx=10)

        def _write(s: str, tag: str = ""):
            if self._term_gen != my_gen:
                return
            try:
                txt.config(state=tk.NORMAL)
                txt.insert(tk.END, s, tag)
                txt.see(tk.END)
                txt.config(state=tk.DISABLED)
            except tk.TclError:
                pass

        def _kill():
            self._term_gen += 1   # stop the runner thread
            self._kill_proc()
            try:
                status_lbl.config(text="● STOPPED", fg=RED)
            except tk.TclError:
                pass

        def _clear_txt():
            try:
                txt.config(state=tk.NORMAL)
                txt.delete("1.0", tk.END)
                txt.config(state=tk.DISABLED)
            except tk.TclError:
                pass

        tk.Button(
            ctrl, text="■ STOP", font=F(9, bold=True),
            bg=BG_R, fg=RED, activebackground=RED, activeforeground=FG,
            relief=tk.FLAT, bd=0, padx=10, pady=0,
            command=_kill,
        ).pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=4)

        tk.Button(
            ctrl, text="CLEAR", font=F(9),
            bg=CARD, fg=DIM, activebackground=BORDER, activeforeground=FG,
            relief=tk.FLAT, bd=0, padx=8, pady=0,
            command=_clear_txt,
        ).pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=4)

        if not commands:
            self.after(10, _write, "No commands to run.\n", "err")
            return

        if UV_BIN:
            self.after(10, _write,
                       f"[uv detected — pip installs rewritten to: uv pip install --system]\n",
                       "info")
        else:
            self.after(10, _write,
                       "[uv not found — pip installs will use --break-system-packages]\n",
                       "info")

        # ── PTY runner thread ─────────────────────────────────────────────────
        def _runner():
            for raw_cmd in commands:
                if self._term_gen != my_gen:
                    break

                cmd = _preprocess_cmd(raw_cmd.strip())
                if not cmd:
                    continue

                self.after(0, _write, f"$ {cmd}\n", "cmd")

                try:
                    master_fd, slave_fd = pty.openpty()
                    self._master_fd = master_fd

                    self._proc = subprocess.Popen(
                        cmd, shell=True,
                        stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
                        close_fds=True,
                        preexec_fn=os.setsid,
                    )
                    os.close(slave_fd)

                    # Read PTY output until process exits
                    while True:
                        if self._term_gen != my_gen:
                            self._kill_proc()
                            break
                        try:
                            r, _, _ = select.select([master_fd], [], [], 0.05)
                            if r:
                                try:
                                    data = os.read(master_fd, 1024)
                                    if data:
                                        text = _strip_ansi(
                                            data.decode("utf-8", errors="replace")
                                        )
                                        self.after(0, _write, text)
                                except OSError:
                                    break
                            elif self._proc.poll() is not None:
                                # Drain any remaining buffered output
                                try:
                                    while True:
                                        r2, _, _ = select.select(
                                            [master_fd], [], [], 0.02
                                        )
                                        if not r2:
                                            break
                                        data = os.read(master_fd, 1024)
                                        if not data:
                                            break
                                        text = _strip_ansi(
                                            data.decode("utf-8", errors="replace")
                                        )
                                        self.after(0, _write, text)
                                except OSError:
                                    pass
                                break
                        except (OSError, ValueError):
                            break

                    try:
                        os.close(master_fd)
                    except OSError:
                        pass
                    self._master_fd = None

                    self._proc.wait()
                    if self._term_gen == my_gen:
                        rc  = self._proc.returncode
                        tag = "ok" if rc == 0 else "err"
                        msg = "\n✔  Done (exit 0)\n\n" if rc == 0 \
                            else f"\n✘  Exit {rc}\n\n"
                        self.after(0, _write, msg, tag)

                except Exception as ex:
                    if self._term_gen == my_gen:
                        self.after(0, _write, f"Error: {ex}\n", "err")

            if self._term_gen == my_gen:
                self.after(0, status_lbl.config, {"text": "● DONE", "fg": CYAN})

        threading.Thread(target=_runner, daemon=True).start()


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    App().mainloop()


if __name__ == "__main__":
    main()
