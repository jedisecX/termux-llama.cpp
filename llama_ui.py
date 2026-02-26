#!/usr/bin/env python3
# =============================================================================
#  TERMUX LLAMA.CPP  —  PYTHON UI
#  A full-featured, curses-based terminal interface for llama.cpp on Termux
#
#  Modules:
#    • Matrix-rain GGUF boot screen
#    • GGUF file browser & loader (llama-cpp-python)
#    • Mood-driven dynamic colour engine
#    • RSS headline reader
#    • Network tools (ping, DNS, port-scan, traceroute, whois)
#    • Self-programming module (generate, edit, save & run Python)
#    • PDF import (text extraction) & export (save conversations / output)
#
#  Requirements (installed by install.sh):
#    llama-cpp-python, feedparser, requests, fpdf2, pdfplumber,
#    rich, prompt_toolkit, pygments, psutil, dnspython
# =============================================================================

import curses
import curses.panel
import os
import sys
import time
import random
import threading
import json
import re
import subprocess
import socket
import struct
import textwrap
import queue
import math
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any

# ── Optional imports (graceful degradation) ───────────────────────────────────
try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    from urllib.parse import urljoin, urlparse, urlunparse
    URLLIB_AVAILABLE = True
except ImportError:
    URLLIB_AVAILABLE = False

# ── Constants ─────────────────────────────────────────────────────────────────
APP_NAME    = "TERMUX LLAMA.CPP UI"
APP_VERSION = "1.0.0"
MODELS_DIR  = os.environ.get("LLAMA_MODELS_DIR",
                             os.path.expanduser("~/llama-cpp-termux/models"))

# Matrix rain character sets
MATRIX_CHARS = (
    "ﾊﾋｼﾂｳｦﾅﾐﾋﾍｽﾒｯｽﾀ0123456789ABCDEF"
    "GGUFLLAMA█▓▒░╔╗╚╝║═┌┐└┘│─"
    "αβγδεζηθλμπρστφψω∑∏∫√∞≈≠±"
)

# RSS feeds (default)
DEFAULT_RSS_FEEDS = [
    ("BBC World",    "http://feeds.bbci.co.uk/news/rss.xml"),
    ("HackerNews",   "https://hnrss.org/frontpage"),
    ("Reuters Tech", "https://feeds.reuters.com/reuters/technologyNews"),
    ("Wired",        "https://www.wired.com/feed/rss"),
    ("ArsTechnica",  "https://feeds.arstechnica.com/arstechnica/index"),
    ("AI News",      "https://www.artificialintelligence-news.com/feed/"),
]

# ── Mood definitions ──────────────────────────────────────────────────────────
MOODS = {
    "neutral":       {"label": "Neutral",       "emoji": "◈",  "pair": 1},
    "happy":         {"label": "Happy",         "emoji": "◉",  "pair": 2},
    "curious":       {"label": "Curious",       "emoji": "◈",  "pair": 3},
    "philosophical": {"label": "Philosophical", "emoji": "◈",  "pair": 4},
    "technical":     {"label": "Technical",     "emoji": "◈",  "pair": 5},
    "creative":      {"label": "Creative",      "emoji": "◈",  "pair": 6},
    "concerned":     {"label": "Concerned",     "emoji": "◈",  "pair": 7},
    "excited":       {"label": "Excited",       "emoji": "◉",  "pair": 8},
}

MOOD_KEYWORDS = {
    "happy":         ["happy","glad","delight","wonderful","great","love","joy","fantastic"],
    "curious":       ["wonder","curious","interesting","fascinating","how","why","explore"],
    "philosophical": ["meaning","purpose","existence","consciousness","reality","truth","wisdom"],
    "technical":     ["algorithm","function","code","system","data","process","compute","binary"],
    "creative":      ["imagine","create","design","art","story","build","invent","inspire"],
    "concerned":     ["worry","caution","danger","risk","problem","issue","concern","careful"],
    "excited":       ["amazing","incredible","wow","awesome","extraordinary","thrilling","exciting"],
}

# =============================================================================
#  COLOUR ENGINE
# =============================================================================
class ColourEngine:
    """Manages curses colour pairs and dynamic mood-based theming."""

    # (foreground, background) for each colour pair index
    THEMES: Dict[str, Dict[str, Tuple[int, int]]] = {
        "neutral":       {"main": (curses.COLOR_CYAN,    curses.COLOR_BLACK),
                          "accent":(curses.COLOR_WHITE,   curses.COLOR_BLACK),
                          "border":(curses.COLOR_CYAN,    curses.COLOR_BLACK),
                          "input": (curses.COLOR_WHITE,   curses.COLOR_BLACK)},
        "happy":         {"main": (curses.COLOR_GREEN,   curses.COLOR_BLACK),
                          "accent":(curses.COLOR_YELLOW,  curses.COLOR_BLACK),
                          "border":(curses.COLOR_GREEN,   curses.COLOR_BLACK),
                          "input": (curses.COLOR_WHITE,   curses.COLOR_BLACK)},
        "curious":       {"main": (curses.COLOR_YELLOW,  curses.COLOR_BLACK),
                          "accent":(curses.COLOR_CYAN,    curses.COLOR_BLACK),
                          "border":(curses.COLOR_YELLOW,  curses.COLOR_BLACK),
                          "input": (curses.COLOR_WHITE,   curses.COLOR_BLACK)},
        "philosophical": {"main": (curses.COLOR_MAGENTA, curses.COLOR_BLACK),
                          "accent":(curses.COLOR_WHITE,   curses.COLOR_BLACK),
                          "border":(curses.COLOR_MAGENTA, curses.COLOR_BLACK),
                          "input": (curses.COLOR_WHITE,   curses.COLOR_BLACK)},
        "technical":     {"main": (curses.COLOR_WHITE,   curses.COLOR_BLACK),
                          "accent":(curses.COLOR_CYAN,    curses.COLOR_BLACK),
                          "border":(curses.COLOR_WHITE,   curses.COLOR_BLACK),
                          "input": (curses.COLOR_WHITE,   curses.COLOR_BLACK)},
        "creative":      {"main": (curses.COLOR_MAGENTA, curses.COLOR_BLACK),
                          "accent":(curses.COLOR_YELLOW,  curses.COLOR_BLACK),
                          "border":(curses.COLOR_MAGENTA, curses.COLOR_BLACK),
                          "input": (curses.COLOR_WHITE,   curses.COLOR_BLACK)},
        "concerned":     {"main": (curses.COLOR_RED,     curses.COLOR_BLACK),
                          "accent":(curses.COLOR_YELLOW,  curses.COLOR_BLACK),
                          "border":(curses.COLOR_RED,     curses.COLOR_BLACK),
                          "input": (curses.COLOR_WHITE,   curses.COLOR_BLACK)},
        "excited":       {"main": (curses.COLOR_YELLOW,  curses.COLOR_BLACK),
                          "accent":(curses.COLOR_GREEN,   curses.COLOR_BLACK),
                          "border":(curses.COLOR_YELLOW,  curses.COLOR_BLACK),
                          "input": (curses.COLOR_WHITE,   curses.COLOR_BLACK)},
    }

    # Pair indices: 1=main 2=accent 3=border 4=input 5=header 6=matrix 7=error 8=info
    def init_pairs(self):
        curses.start_color()
        curses.use_default_colors()
        # static pairs
        curses.init_pair(10, curses.COLOR_GREEN,   curses.COLOR_BLACK)  # matrix
        curses.init_pair(11, curses.COLOR_RED,     curses.COLOR_BLACK)  # error
        curses.init_pair(12, curses.COLOR_CYAN,    curses.COLOR_BLACK)  # info
        curses.init_pair(13, curses.COLOR_YELLOW,  curses.COLOR_BLACK)  # warning
        curses.init_pair(14, curses.COLOR_WHITE,   curses.COLOR_BLACK)  # plain
        curses.init_pair(15, curses.COLOR_MAGENTA, curses.COLOR_BLACK)  # purple
        curses.init_pair(16, curses.COLOR_BLACK,   curses.COLOR_WHITE)  # reversed
        self.set_mood("neutral")

    def set_mood(self, mood: str):
        self.mood = mood
        theme = self.THEMES.get(mood, self.THEMES["neutral"])
        curses.init_pair(1, *theme["main"])    # main text
        curses.init_pair(2, *theme["accent"])  # accent
        curses.init_pair(3, *theme["border"])  # borders
        curses.init_pair(4, *theme["input"])   # input area
        curses.init_pair(5, curses.COLOR_BLACK, theme["main"][0])  # header (inverted)

    @staticmethod
    def pair(n: int, bold: bool = False) -> int:
        attr = curses.color_pair(n)
        if bold:
            attr |= curses.A_BOLD
        return attr


CE = ColourEngine()


# =============================================================================
#  MOOD ENGINE
# =============================================================================
class MoodEngine:
    """Detects the mood of an AI response and updates the colour theme."""

    def __init__(self, colour_engine: ColourEngine, on_change=None):
        self.ce = colour_engine
        self.current_mood = "neutral"
        self.on_change = on_change

    def detect(self, text: str) -> str:
        text_lower = text.lower()
        scores: Dict[str, int] = {}
        for mood, keywords in MOOD_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[mood] = score
        if not scores:
            return "neutral"
        return max(scores, key=scores.get)

    def update(self, text: str):
        new_mood = self.detect(text)
        if new_mood != self.current_mood:
            self.current_mood = new_mood
            self.ce.set_mood(new_mood)
            if self.on_change:
                self.on_change(new_mood)


# =============================================================================
#  MATRIX RAIN
# =============================================================================
class MatrixRain:
    """Full-screen matrix rain effect with GGUF-themed characters."""

    def __init__(self, stdscr, duration: float = 4.0, title: str = ""):
        self.stdscr = stdscr
        self.duration = duration
        self.title = title

    def run(self):
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        h, w = self.stdscr.getmaxyx()

        # Each column: (y_position, speed, char_list, trail_len)
        cols = []
        for x in range(w):
            speed     = random.uniform(0.05, 0.25)
            trail_len = random.randint(4, min(h, 20))
            cols.append({
                "x": x, "y": random.uniform(0, -h),
                "speed": speed, "trail": trail_len,
                "chars": [random.choice(MATRIX_CHARS) for _ in range(trail_len)],
            })

        start = time.time()
        frame = 0

        while time.time() - start < self.duration:
            ch = self.stdscr.getch()
            if ch in (ord('q'), ord(' '), 27):   # q / space / ESC exits early
                break

            self.stdscr.erase()
            h, w = self.stdscr.getmaxyx()

            for col in cols:
                col["y"] += col["speed"] * (1 + frame * 0.002)
                if col["y"] - col["trail"] > h:
                    col["y"] = random.uniform(-h * 0.5, 0)
                    col["speed"] = random.uniform(0.05, 0.25)
                    col["chars"] = [random.choice(MATRIX_CHARS)
                                    for _ in range(col["trail"])]

                # Occasionally mutate a character
                if random.random() < 0.1:
                    idx = random.randint(0, col["trail"] - 1)
                    col["chars"][idx] = random.choice(MATRIX_CHARS)

                for i in range(col["trail"]):
                    ry = int(col["y"]) - i
                    if ry < 0 or ry >= h - 1:
                        continue
                    rx = col["x"]
                    if rx >= w:
                        continue
                    char = col["chars"][i % len(col["chars"])]
                    if i == 0:
                        attr = CE.pair(10, bold=True)    # bright green head
                    elif i < 3:
                        attr = CE.pair(10) | curses.A_BOLD
                    else:
                        fade = max(1, col["trail"] - i)
                        attr = (CE.pair(14) if fade < 3 else CE.pair(10))
                    try:
                        self.stdscr.addch(ry, rx, ord(char[0]), attr)
                    except curses.error:
                        pass

            # Overlay title in the centre
            if self.title:
                box_w = min(len(self.title) + 8, w - 2)
                bx    = max(0, (w - box_w) // 2)
                by    = h // 2 - 1
                label = f"  {self.title}  "
                try:
                    self.stdscr.addstr(by, bx, label.center(box_w),
                                       CE.pair(10, bold=True) | curses.A_REVERSE)
                except curses.error:
                    pass

            # Loading bar at bottom
            elapsed  = time.time() - start
            progress = min(1.0, elapsed / self.duration)
            bar_w    = max(10, w - 20)
            filled   = int(bar_w * progress)
            bar_str  = f" Loading: [{'█' * filled}{'░' * (bar_w - filled)}] {int(progress*100)}% "
            try:
                self.stdscr.addstr(h - 1, 0, bar_str[:w], CE.pair(10, bold=True))
            except curses.error:
                pass

            self.stdscr.refresh()
            time.sleep(0.04)
            frame += 1

        self.stdscr.nodelay(False)
        curses.curs_set(1)


# =============================================================================
#  GGUF FILE BROWSER
# =============================================================================
class GGUFBrowser:
    """Interactive curses file browser to select a .gguf model."""

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.start_dir = Path(MODELS_DIR) if Path(MODELS_DIR).exists() else Path.home()

    def browse(self) -> Optional[str]:
        curdir = self.start_dir
        selected = 0
        offset   = 0

        while True:
            h, w = self.stdscr.getmaxyx()
            self.stdscr.erase()

            entries = self._list(curdir)
            visible = h - 6

            # Header
            hdr = f" GGUF File Browser — {curdir} "
            try:
                self.stdscr.addstr(0, 0, hdr[:w].ljust(w), CE.pair(5, bold=True))
            except curses.error:
                pass
            try:
                self.stdscr.addstr(1, 0, " [↑↓] navigate  [Enter] open/select  [Backspace] up  [q] cancel ",
                                   CE.pair(12))
            except curses.error:
                pass

            # Border
            try:
                self.stdscr.addstr(2, 0, "─" * w, CE.pair(3))
            except curses.error:
                pass

            if not entries:
                try:
                    self.stdscr.addstr(3, 2, "(empty directory)", CE.pair(13))
                except curses.error:
                    pass
            else:
                if selected >= len(entries):
                    selected = len(entries) - 1
                if selected < offset:
                    offset = selected
                if selected >= offset + visible:
                    offset = selected - visible + 1

                for i, (name, is_dir, is_gguf) in enumerate(entries[offset:offset + visible]):
                    row = 3 + i
                    prefix = "📁 " if is_dir else ("◈ " if is_gguf else "  ")
                    line   = f" {prefix}{name}"
                    if offset + i == selected:
                        attr = CE.pair(16) | curses.A_BOLD
                    elif is_gguf:
                        attr = CE.pair(2, bold=True)
                    elif is_dir:
                        attr = CE.pair(1)
                    else:
                        attr = CE.pair(14)
                    try:
                        self.stdscr.addstr(row, 0, line[:w].ljust(w), attr)
                    except curses.error:
                        pass

            try:
                self.stdscr.addstr(h - 2, 0, "─" * w, CE.pair(3))
            except curses.error:
                pass
            if entries and selected < len(entries):
                name, is_dir, is_gguf = entries[selected]
                sz = ""
                try:
                    p = curdir / name
                    if p.is_file():
                        sz = f"  ({p.stat().st_size / 1024**3:.2f} GB)" if p.stat().st_size > 1e9 \
                             else f"  ({p.stat().st_size / 1024**2:.1f} MB)"
                except Exception:
                    pass
                status = f" {'DIR' if is_dir else 'GGUF' if is_gguf else 'FILE'}: {name}{sz} "
                try:
                    self.stdscr.addstr(h - 1, 0, status[:w], CE.pair(12))
                except curses.error:
                    pass

            self.stdscr.refresh()
            key = self.stdscr.getch()

            if key == curses.KEY_UP:
                if selected > 0:
                    selected -= 1
            elif key == curses.KEY_DOWN:
                if selected < len(entries) - 1:
                    selected += 1
            elif key in (curses.KEY_ENTER, 10, 13):
                if entries:
                    name, is_dir, is_gguf = entries[selected]
                    target = curdir / name
                    if is_dir:
                        curdir   = target
                        selected = 0
                        offset   = 0
                    elif is_gguf:
                        return str(target)
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                parent = curdir.parent
                if parent != curdir:
                    curdir   = parent
                    selected = 0
                    offset   = 0
            elif key in (ord('q'), 27):
                return None

    @staticmethod
    def _list(path: Path):
        items = []
        try:
            for p in sorted(path.iterdir()):
                is_dir  = p.is_dir()
                is_gguf = p.suffix.lower() == ".gguf" and p.is_file()
                if is_dir or is_gguf or p.is_file():
                    items.append((p.name, is_dir, is_gguf))
        except PermissionError:
            pass
        # dirs first, then gguf, then others
        return sorted(items, key=lambda x: (not x[1], not x[2], x[0]))


# =============================================================================
#  RSS MODULE
# =============================================================================
class RSSModule:
    """Fetches and displays RSS headlines."""

    def __init__(self):
        self.feeds  = list(DEFAULT_RSS_FEEDS)
        self.cache: Dict[str, List[str]] = {}

    def fetch(self, url: str) -> List[str]:
        if url in self.cache:
            return self.cache[url]
        if not FEEDPARSER_AVAILABLE:
            return ["[feedparser not installed – run: pip install feedparser]"]
        if not REQUESTS_AVAILABLE:
            return ["[requests not installed]"]
        try:
            feed = feedparser.parse(url)
            headlines = []
            for entry in feed.entries[:15]:
                title   = entry.get("title", "(no title)")
                summary = entry.get("summary", "")
                summary = re.sub(r"<[^>]+>", "", summary)[:120]
                pub     = entry.get("published", "")
                headlines.append(f"• {title}\n  {summary}\n  {pub}")
            self.cache[url] = headlines or ["(no entries)"]
            return self.cache[url]
        except Exception as e:
            return [f"[Error: {e}]"]

    def add_feed(self, name: str, url: str):
        self.feeds.append((name, url))


# =============================================================================
#  NETWORK TOOLS
# =============================================================================
class NetworkTools:
    """Basic network diagnostic utilities."""

    @staticmethod
    def ping(host: str, count: int = 4) -> str:
        try:
            result = subprocess.run(
                ["ping", "-c", str(count), host],
                capture_output=True, text=True, timeout=15
            )
            return result.stdout or result.stderr
        except FileNotFoundError:
            return "[ping not available]"
        except subprocess.TimeoutExpired:
            return "[ping timed out]"

    @staticmethod
    def traceroute(host: str) -> str:
        for cmd in [["traceroute", host], ["tracepath", host]]:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                return result.stdout or result.stderr
            except FileNotFoundError:
                continue
            except subprocess.TimeoutExpired:
                return "[traceroute timed out]"
        return "[traceroute/tracepath not available]"

    @staticmethod
    def dns_lookup(host: str) -> str:
        lines = []
        if DNS_AVAILABLE:
            try:
                for rtype in ("A", "AAAA", "MX", "NS", "TXT"):
                    try:
                        answers = dns.resolver.resolve(host, rtype)
                        lines.append(f"{rtype}:")
                        for r in answers:
                            lines.append(f"  {r}")
                    except Exception:
                        pass
            except Exception as e:
                lines.append(f"[dnspython error: {e}]")
        else:
            try:
                ip = socket.gethostbyname(host)
                lines.append(f"A: {ip}  (basic lookup – install dnspython for full records)")
            except Exception as e:
                lines.append(f"[socket error: {e}]")
        return "\n".join(lines) or "[no DNS results]"

    @staticmethod
    def port_scan(host: str, ports: str = "22,80,443,8080,8443") -> str:
        results = []
        port_list = []
        for part in ports.split(","):
            part = part.strip()
            if "-" in part:
                a, b = part.split("-", 1)
                port_list.extend(range(int(a), int(b) + 1))
            else:
                try:
                    port_list.append(int(part))
                except ValueError:
                    pass
        for port in port_list[:100]:
            try:
                with socket.create_connection((host, port), timeout=1):
                    results.append(f"  {port:5d}/tcp  OPEN")
            except Exception:
                results.append(f"  {port:5d}/tcp  closed")
        return "\n".join(results) or "[no results]"

    @staticmethod
    def whois(host: str) -> str:
        try:
            result = subprocess.run(["whois", host],
                                    capture_output=True, text=True, timeout=20)
            return (result.stdout or result.stderr)[:2000]
        except FileNotFoundError:
            return "[whois not installed – pkg install whois]"
        except subprocess.TimeoutExpired:
            return "[whois timed out]"

    @staticmethod
    def http_get(url: str) -> str:
        if not REQUESTS_AVAILABLE:
            return "[requests not installed]"
        try:
            r = requests.get(url, timeout=10,
                             headers={"User-Agent": "termux-llama-ui/1.0"})
            return f"Status : {r.status_code}\nHeaders:\n" + \
                   "\n".join(f"  {k}: {v}" for k, v in r.headers.items()) + \
                   f"\n\nBody (first 1000 chars):\n{r.text[:1000]}"
        except Exception as e:
            return f"[HTTP error: {e}]"

    @staticmethod
    def system_info() -> str:
        lines = []
        lines.append(f"Hostname : {socket.gethostname()}")
        try:
            lines.append(f"Local IP : {socket.gethostbyname(socket.gethostname())}")
        except Exception:
            pass
        if PSUTIL_AVAILABLE:
            lines.append(f"CPU      : {psutil.cpu_percent(interval=0.5):.1f}%  "
                         f"({psutil.cpu_count()} cores)")
            vm = psutil.virtual_memory()
            lines.append(f"RAM      : {vm.used/1024**2:.0f} MB / {vm.total/1024**2:.0f} MB "
                         f"({vm.percent:.1f}%)")
            disk = psutil.disk_usage("/")
            lines.append(f"Disk     : {disk.used/1024**3:.1f} GB / {disk.total/1024**3:.1f} GB")
            net = psutil.net_io_counters()
            lines.append(f"Net TX   : {net.bytes_sent/1024**2:.1f} MB   "
                         f"RX: {net.bytes_recv/1024**2:.1f} MB")
        else:
            lines.append("[psutil not installed – install for system stats]")
        return "\n".join(lines)


# =============================================================================
#  PDF MODULE
# =============================================================================
class PDFModule:
    """Import text from PDFs and export conversations/content as PDF."""

    @staticmethod
    def extract_text(path: str) -> str:
        if not PDFPLUMBER_AVAILABLE:
            return "[pdfplumber not installed – pip install pdfplumber]"
        try:
            with pdfplumber.open(path) as pdf:
                pages = []
                for i, page in enumerate(pdf.pages, 1):
                    text = page.extract_text() or ""
                    pages.append(f"─── Page {i} ───\n{text}")
                return "\n\n".join(pages)
        except Exception as e:
            return f"[PDF read error: {e}]"

    @staticmethod
    def export(content: str, output_path: str = "", title: str = "LlamaUI Export") -> str:
        if not FPDF_AVAILABLE:
            return "[fpdf2 not installed – pip install fpdf2]"
        if not output_path:
            output_path = os.path.join(
                os.path.expanduser("~"),
                f"llama_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
        try:
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            pdf.set_font("Courier", "B", 16)
            pdf.cell(0, 10, title, ln=True, align="C")
            pdf.set_font("Courier", "", 11)
            pdf.ln(5)
            for line in content.splitlines():
                safe_line = line.encode("latin-1", errors="replace").decode("latin-1")
                pdf.multi_cell(0, 6, safe_line)
            pdf.output(output_path)
            return f"PDF saved: {output_path}"
        except Exception as e:
            return f"[PDF export error: {e}]"


# =============================================================================
#  SELF-PROGRAMMING MODULE
# =============================================================================
class SelfProgramModule:
    """Generate, edit, execute, and save Python code via the LLM."""

    def __init__(self):
        self.snippets: List[Dict[str, str]] = []

    def save_snippet(self, code: str, name: str = "") -> str:
        if not name:
            name = f"snippet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
        path = os.path.join(os.path.expanduser("~"), "llama-cpp-termux", "scripts", name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(code)
        self.snippets.append({"name": name, "path": path, "code": code})
        return f"Saved: {path}"

    @staticmethod
    def run_snippet(path: str, timeout: int = 30) -> str:
        try:
            result = subprocess.run(
                [sys.executable, path],
                capture_output=True, text=True, timeout=timeout
            )
            out = result.stdout[-2000:] if result.stdout else ""
            err = result.stderr[-500:]  if result.stderr else ""
            return f"--- STDOUT ---\n{out}\n--- STDERR ---\n{err}"
        except subprocess.TimeoutExpired:
            return "[script timed out]"
        except Exception as e:
            return f"[run error: {e}]"

    @staticmethod
    def extract_code_blocks(text: str) -> List[str]:
        """Extract ```python ... ``` blocks from LLM output."""
        pattern = r"```(?:python)?\s*\n(.*?)```"
        return re.findall(pattern, text, re.DOTALL)


# =============================================================================
#  MINI WEB BROWSER
# =============================================================================
class WebBrowser:
    """
    Terminal web browser shared between the user and the AI.

    • Fetches pages via requests, strips HTML to readable text
    • Numbers all hyperlinks [1]…[N] for keyboard navigation
    • Back / forward history stack
    • Bookmarks persisted to ~/.llama_bookmarks.json
    • inject_context() returns page text suitable for injecting into the LLM
    • find() simple in-page text search
    • save_pdf() exports the current page to PDF via PDFModule
    """

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 12; Termux) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120 Mobile Safari/537.36 termux-llama-ui/1.0"
        ),
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    BOOKMARKS_FILE = os.path.join(
        os.path.expanduser("~"), ".llama_bookmarks.json"
    )
    # HTML tags whose content we keep as-is (roughly block-level)
    BLOCK_TAGS = {"p", "div", "br", "li", "h1", "h2", "h3", "h4",
                  "h5", "h6", "tr", "td", "th", "blockquote", "pre",
                  "article", "section", "header", "footer", "main"}
    # Tags to skip entirely (scripts, styles, nav noise)
    SKIP_TAGS  = {"script", "style", "nav", "noscript", "iframe",
                  "svg", "img", "input", "button", "form", "aside",
                  "meta", "link", "head"}

    def __init__(self):
        self.current_url:  str = ""
        self.current_text: str = ""          # rendered plain-text of current page
        self.current_title: str = ""
        self.current_links: List[Tuple[int, str, str]] = []  # (n, text, href)
        self.history:  List[str] = []        # URL stack for back
        self.forward:  List[str] = []        # URL stack for forward
        self.bookmarks: Dict[str, str] = {}  # url → title
        self._load_bookmarks()

    # ── Public navigation ─────────────────────────────────────────────────────
    def go(self, url: str) -> Tuple[bool, str]:
        """Fetch URL and render. Returns (success, message)."""
        url = self._normalise_url(url)
        if not REQUESTS_AVAILABLE:
            return False, "[requests not installed – pip install requests]"
        try:
            resp = requests.get(url, headers=self.HEADERS,
                                timeout=15, allow_redirects=True)
            final_url = resp.url
            ct = resp.headers.get("Content-Type", "")
            if "text/html" in ct or "text/plain" in ct or not ct:
                if self.current_url:
                    self.history.append(self.current_url)
                    self.forward.clear()
                self.current_url = final_url
                text, title, links = self._render(resp.text, final_url)
                self.current_text  = text
                self.current_title = title
                self.current_links = links
                return True, f"OK  {resp.status_code}  {final_url}"
            else:
                return False, f"[Unsupported content-type: {ct}]"
        except requests.exceptions.SSLError:
            return False, "[SSL error – try http:// instead]"
        except requests.exceptions.ConnectionError as e:
            return False, f"[Connection error: {e}]"
        except Exception as e:
            return False, f"[Fetch error: {e}]"

    def back(self) -> Tuple[bool, str]:
        if not self.history:
            return False, "[No history]"
        self.forward.append(self.current_url)
        prev = self.history.pop()
        ok, msg = self.go(prev)
        if ok:
            self.history = self.history[:-1]   # go() pushed again; undo that
        return ok, msg

    def forward_nav(self) -> Tuple[bool, str]:
        if not self.forward:
            return False, "[Nothing to go forward to]"
        nxt = self.forward.pop()
        return self.go(nxt)

    def follow_link(self, n: int) -> Tuple[bool, str]:
        for idx, text, href in self.current_links:
            if idx == n:
                return self.go(href)
        return False, f"[No link [{n}] on this page]"

    def reload(self) -> Tuple[bool, str]:
        if not self.current_url:
            return False, "[Nothing loaded]"
        url = self.current_url
        self.history.append(url)   # preserve stack; go() will push again, cleaned below
        ok, msg = self.go(url)
        if ok:
            self.history = self.history[:-1]
        return ok, msg

    # ── Search ────────────────────────────────────────────────────────────────
    def find(self, query: str) -> List[Tuple[int, str]]:
        """Return (line_no, line_text) for lines containing query (case-insensitive)."""
        if not self.current_text:
            return []
        results = []
        q = query.lower()
        for i, line in enumerate(self.current_text.splitlines(), 1):
            if q in line.lower():
                results.append((i, line))
        return results[:50]

    # ── Bookmarks ─────────────────────────────────────────────────────────────
    def add_bookmark(self) -> str:
        if not self.current_url:
            return "[No page loaded]"
        self.bookmarks[self.current_url] = self.current_title or self.current_url
        self._save_bookmarks()
        return f"Bookmarked: {self.current_title or self.current_url}"

    def remove_bookmark(self, url: str) -> str:
        url = self._normalise_url(url)
        if url in self.bookmarks:
            del self.bookmarks[url]
            self._save_bookmarks()
            return f"Removed: {url}"
        return "[Bookmark not found]"

    def _load_bookmarks(self):
        try:
            if os.path.exists(self.BOOKMARKS_FILE):
                with open(self.BOOKMARKS_FILE) as f:
                    self.bookmarks = json.load(f)
        except Exception:
            self.bookmarks = {}

    def _save_bookmarks(self):
        try:
            with open(self.BOOKMARKS_FILE, "w") as f:
                json.dump(self.bookmarks, f, indent=2)
        except Exception:
            pass

    # ── AI context injection ──────────────────────────────────────────────────
    def inject_context(self, max_chars: int = 4000) -> str:
        """Return a prompt-friendly summary of the current page for the LLM."""
        if not self.current_url:
            return "[No page loaded in browser]"
        header = (
            f"[Web page fetched by user]\n"
            f"URL   : {self.current_url}\n"
            f"Title : {self.current_title}\n"
            f"─────────────────────────────────\n"
        )
        body = self.current_text[:max_chars]
        if len(self.current_text) > max_chars:
            body += "\n… (truncated)"
        return header + body

    # ── Rendering ─────────────────────────────────────────────────────────────
    def _render(self, html: str, base_url: str
                ) -> Tuple[str, str, List[Tuple[int, str, str]]]:
        """Convert HTML → (plain text, page title, numbered links list)."""
        if BS4_AVAILABLE:
            return self._render_bs4(html, base_url)
        return self._render_regex(html, base_url)

    def _render_bs4(self, html: str, base_url: str
                    ) -> Tuple[str, str, List[Tuple[int, str, str]]]:
        soup  = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title else urlparse(base_url).netloc

        # Remove noise tags
        for tag in soup(list(self.SKIP_TAGS)):
            tag.decompose()

        lines: List[str] = []
        link_counter = [0]
        links: List[Tuple[int, str, str]] = []

        def _visit(el):
            if hasattr(el, "name"):
                name = el.name or ""
                if name in self.SKIP_TAGS:
                    return
                if name == "a":
                    href = el.get("href", "")
                    text = el.get_text(" ", strip=True)
                    if href and text:
                        abs_href = urljoin(base_url, href)
                        link_counter[0] += 1
                        n = link_counter[0]
                        links.append((n, text[:60], abs_href))
                        lines.append(f"[{n}] {text}")
                    else:
                        lines.append(el.get_text(" ", strip=True))
                    return
                if name in ("h1", "h2", "h3"):
                    txt = el.get_text(" ", strip=True)
                    if txt:
                        sep = "═" if name == "h1" else ("─" if name == "h2" else "·")
                        lines.append("")
                        lines.append(sep * min(len(txt), 60))
                        lines.append(txt)
                        lines.append(sep * min(len(txt), 60))
                    return
                if name in ("h4", "h5", "h6"):
                    txt = el.get_text(" ", strip=True)
                    if txt:
                        lines.append(f"\n▸ {txt}")
                    return
                if name == "li":
                    txt = el.get_text(" ", strip=True)
                    if txt:
                        lines.append(f"  • {txt}")
                    return
                if name == "hr":
                    lines.append("─" * 60)
                    return
                if name == "br":
                    lines.append("")
                    return
                for child in el.children:
                    _visit(child)
                if name in self.BLOCK_TAGS:
                    if lines and lines[-1] != "":
                        lines.append("")
            else:
                txt = str(el).strip()
                if txt:
                    lines.append(txt)

        body = soup.body or soup
        _visit(body)

        # Collapse excessive blank lines
        cleaned: List[str] = []
        prev_blank = False
        for ln in lines:
            is_blank = not ln.strip()
            if is_blank and prev_blank:
                continue
            cleaned.append(ln)
            prev_blank = is_blank

        return "\n".join(cleaned), title, links

    def _render_regex(self, html: str, base_url: str
                      ) -> Tuple[str, str, List[Tuple[int, str, str]]]:
        """Fallback plain-regex renderer when bs4 is not available."""
        # Extract title
        title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        title   = re.sub(r"<[^>]+>", "", title_m.group(1)).strip() if title_m else ""

        # Remove script/style blocks
        html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.I | re.S)

        # Collect links
        links: List[Tuple[int, str, str]] = []
        link_n = [0]
        def repl_link(m):
            href = m.group(1) or m.group(2)
            text = re.sub(r"<[^>]+>", "", m.group(3)).strip()
            if href and text:
                abs_href = urljoin(base_url, href)
                link_n[0] += 1
                links.append((link_n[0], text[:60], abs_href))
                return f"[{link_n[0]}] {text}"
            return text
        html = re.sub(
            r'<a[^>]+href=["\']([^"\']*)["\'][^>]*>(.*?)</a>'
            r'|<a[^>]+href=([^ >]+)[^>]*>(.*?)</a>',
            lambda m: repl_link(m), html, flags=re.I | re.S
        )

        # Block tags → newlines
        html = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
        html = re.sub(r"</(p|div|li|h[1-6]|tr|blockquote|article|section)>",
                      "\n", html, flags=re.I)
        html = re.sub(r"<li[^>]*>", "\n  • ", html, flags=re.I)
        html = re.sub(r"<h[1-3][^>]*>", "\n── ", html, flags=re.I)
        html = re.sub(r"<h[4-6][^>]*>", "\n▸ ", html, flags=re.I)

        # Strip all remaining tags
        text = re.sub(r"<[^>]+>", "", html)

        # Decode common HTML entities
        for ent, ch in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                        ("&nbsp;", " "), ("&quot;", '"'), ("&#39;", "'")):
            text = text.replace(ent, ch)

        # Collapse whitespace / blank lines
        lines = [ln.rstrip() for ln in text.splitlines()]
        cleaned: List[str] = []
        prev_blank = False
        for ln in lines:
            is_blank = not ln.strip()
            if is_blank and prev_blank:
                continue
            cleaned.append(ln)
            prev_blank = is_blank

        return "\n".join(cleaned), title, links

    # ── Helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _normalise_url(url: str) -> str:
        url = url.strip()
        if not url:
            return url
        if not re.match(r"^https?://", url, re.I):
            if "/" not in url and "." not in url.split("/")[0]:
                # Treat as a DuckDuckGo search
                from urllib.parse import quote_plus
                return f"https://html.duckduckgo.com/html/?q={quote_plus(url)}"
            url = "https://" + url
        return url

    def get_page_summary(self) -> str:
        """Short one-liner for the status bar."""
        if not self.current_url:
            return "No page loaded"
        title = self.current_title[:30] if self.current_title else "(no title)"
        hist  = len(self.history)
        fwd   = len(self.forward)
        links = len(self.current_links)
        return f"{title}  [{hist}◀ {fwd}▶]  {links} links"


# =============================================================================
#  LLAMA ENGINE
# =============================================================================
class LlamaEngine:
    """Wraps llama-cpp-python for inference."""

    def __init__(self):
        self.model: Optional[Any] = None
        self.model_path: str = ""
        self.model_name: str = ""
        self.ctx_size: int = 4096
        self.n_threads: int = max(1, (os.cpu_count() or 2) - 1)
        self.history: List[Dict[str, str]] = []
        self.system_prompt: str = (
            "You are a helpful, intelligent assistant running on Android via Termux. "
            "Be concise, accurate, and thoughtful."
        )

    def load(self, path: str, on_progress=None) -> str:
        if not LLAMA_AVAILABLE:
            return "ERROR: llama-cpp-python not installed. Run install.sh first."
        try:
            if on_progress:
                on_progress("Initialising model…")
            self.model = Llama(
                model_path=path,
                n_ctx=self.ctx_size,
                n_threads=self.n_threads,
                n_gpu_layers=0,
                verbose=False,
            )
            self.model_path = path
            self.model_name = Path(path).stem
            self.history = []
            return f"Model loaded: {self.model_name}"
        except Exception as e:
            self.model = None
            return f"ERROR loading model: {e}"

    def generate(self, user_msg: str,
                 max_tokens: int = 512,
                 temperature: float = 0.7,
                 on_token=None) -> str:
        if not self.model:
            return "[No model loaded – press L to load a GGUF]"
        self.history.append({"role": "user", "content": user_msg})
        # Build prompt
        prompt = f"[INST] <<SYS>>\n{self.system_prompt}\n<</SYS>>\n\n"
        for msg in self.history[-10:]:
            if msg["role"] == "user":
                prompt += f"{msg['content']} [/INST] "
            else:
                prompt += f"{msg['content']} </s><s>[INST] "

        try:
            output = self.model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=["</s>", "[INST]"],
                stream=on_token is not None,
            )
            if on_token:
                full = ""
                for chunk in output:
                    tok = chunk["choices"][0]["text"]
                    full += tok
                    on_token(tok)
                result = full
            else:
                result = output["choices"][0]["text"]

            self.history.append({"role": "assistant", "content": result})
            return result
        except Exception as e:
            return f"[Generation error: {e}]"

    def get_info(self) -> str:
        if not self.model:
            return "No model loaded"
        try:
            meta = self.model.metadata
            return (
                f"Model   : {self.model_name}\n"
                f"Context : {self.ctx_size} tokens\n"
                f"Threads : {self.n_threads}\n"
                f"Path    : {self.model_path}\n"
                f"Meta    : {json.dumps(meta, indent=2)[:400]}"
            )
        except Exception:
            return f"Model: {self.model_name}\nPath: {self.model_path}"


# =============================================================================
#  SCROLLABLE TEXT PAD
# =============================================================================
class ScrollPad:
    """A scrollable content area within a curses window."""

    def __init__(self, win, start_row: int = 0, start_col: int = 0):
        self.win       = win
        self.lines:    List[Tuple[str, int]] = []  # (text, colour_pair)
        self.offset    = 0
        self.start_row = start_row
        self.start_col = start_col

    def append(self, text: str, pair: int = 1, bold: bool = False):
        attr = CE.pair(pair, bold)
        for line in str(text).splitlines():
            self.lines.append((line, attr))
        self._auto_scroll()

    def _auto_scroll(self):
        h, w = self.win.getmaxyx()
        visible = h - self.start_row - 1
        if len(self.lines) > self.offset + visible:
            self.offset = max(0, len(self.lines) - visible)

    def scroll_up(self, n: int = 3):
        self.offset = max(0, self.offset - n)

    def scroll_down(self, n: int = 3):
        h, _ = self.win.getmaxyx()
        visible = h - self.start_row - 1
        self.offset = min(max(0, len(self.lines) - visible), self.offset + n)

    def render(self):
        h, w = self.win.getmaxyx()
        visible = h - self.start_row - 1
        for i, (line, attr) in enumerate(self.lines[self.offset:self.offset + visible]):
            row = self.start_row + i
            if row >= h - 1:
                break
            try:
                self.win.addstr(row, self.start_col, line[:w - self.start_col - 1], attr)
                self.win.clrtoeol()
            except curses.error:
                pass

    def clear(self):
        self.lines  = []
        self.offset = 0

    def get_text(self) -> str:
        return "\n".join(line for line, _ in self.lines)


# =============================================================================
#  MAIN APPLICATION
# =============================================================================
class LlamaUI:
    MODES = ["CHAT", "WEB", "RSS", "NET", "PDF", "CODE", "INFO"]

    def __init__(self, stdscr, preload_model: str = ""):
        self.stdscr       = stdscr
        self.llama        = LlamaEngine()
        self.mood_engine  = MoodEngine(CE, self._on_mood_change)
        self.rss          = RSSModule()
        self.net          = NetworkTools()
        self.pdf          = PDFModule()
        self.code_mod     = SelfProgramModule()
        self.scroll_pad   = ScrollPad(stdscr, start_row=3)
        self.current_mode = "CHAT"
        self.input_buf    = ""
        self.cursor_pos   = 0
        self.status_msg   = ""
        self.running      = True
        self.token_queue: queue.Queue[str] = queue.Queue()
        self.gen_thread: Optional[threading.Thread] = None
        self.is_generating = False
        self.current_mood  = "neutral"
        self.preload_model = preload_model

        # Sidebar
        self.sidebar_items: List[str] = []
        self.sidebar_sel   = 0
        self.sidebar_offset = 0

        # RSS
        self.rss_feed_sel   = 0
        self.rss_headlines: List[str] = []

        # Code buffer
        self.last_code_blocks: List[str] = []

        # Web browser
        self.browser           = WebBrowser()
        self.browser_find_res: List[Tuple[int, str]] = []  # last find() results

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    def run(self):
        CE.init_pairs()
        curses.curs_set(1)
        self.stdscr.keypad(True)
        self.stdscr.timeout(50)

        # Boot matrix rain
        model_label = Path(self.preload_model).stem if self.preload_model \
                      else "LLAMA.CPP  GGUF  INTERFACE"
        MatrixRain(self.stdscr, duration=3.5, title=model_label).run()

        if self.preload_model:
            self._load_model_bg(self.preload_model)
        else:
            self.scroll_pad.append(
                "Welcome! Press  L  to load a GGUF model.\n"
                "Use  Tab  to switch modules.\n"
                "Press  ?  for help.\n",
                pair=1
            )

        while self.running:
            self._drain_token_queue()
            self._redraw()
            self._handle_key()

    def _on_mood_change(self, new_mood: str):
        self.current_mood = new_mood
        self.status_msg   = f"Mood → {MOODS.get(new_mood, {}).get('label', new_mood)}"

    # ── Model loading ─────────────────────────────────────────────────────────
    def _load_model_bg(self, path: str):
        self.status_msg = f"Loading {Path(path).name}…"
        self.scroll_pad.append(f"\nLoading model: {path}\n", pair=12)

        def _worker():
            msg = self.llama.load(path)
            self.token_queue.put(f"\n{msg}\n")
            self.status_msg = msg

        threading.Thread(target=_worker, daemon=True).start()

    # ── Token streaming ───────────────────────────────────────────────────────
    def _start_generation(self, prompt: str):
        if self.is_generating:
            return
        self.is_generating = True
        self.scroll_pad.append(f"\nYou: {prompt}\n", pair=2, bold=True)
        self.scroll_pad.append("AI : ", pair=1)

        def _worker():
            full_response = []
            def on_token(tok):
                full_response.append(tok)
                self.token_queue.put(tok)
            self.llama.generate(prompt, on_token=on_token)
            joined = "".join(full_response)
            self.mood_engine.update(joined)
            self.last_code_blocks = self.code_mod.extract_code_blocks(joined)
            if self.last_code_blocks:
                self.token_queue.put(
                    f"\n[{len(self.last_code_blocks)} code block(s) detected – "
                    f"switch to CODE mode to manage]\n"
                )
            self.token_queue.put(None)  # sentinel

        self.gen_thread = threading.Thread(target=_worker, daemon=True)
        self.gen_thread.start()

    def _drain_token_queue(self):
        try:
            while True:
                tok = self.token_queue.get_nowait()
                if tok is None:
                    self.is_generating = False
                    self.scroll_pad.append("\n", pair=1)
                else:
                    # Append to last line
                    if self.scroll_pad.lines:
                        last, attr = self.scroll_pad.lines[-1]
                        combined = last + tok
                        # Word-wrap if needed
                        _, w = self.stdscr.getmaxyx()
                        wrap_w = max(20, w - 10)
                        wrapped = textwrap.wrap(combined, wrap_w) or [""]
                        self.scroll_pad.lines[-1] = (wrapped[0], attr)
                        for extra in wrapped[1:]:
                            self.scroll_pad.lines.append((extra, attr))
                    else:
                        self.scroll_pad.append(tok, pair=1)
                    self.scroll_pad._auto_scroll()
        except queue.Empty:
            pass

    # ── Key handling ──────────────────────────────────────────────────────────
    def _handle_key(self):
        key = self.stdscr.getch()
        if key == -1:
            return

        if key == ord('\t'):            # Tab — cycle modes
            idx = self.MODES.index(self.current_mode)
            self.current_mode = self.MODES[(idx + 1) % len(self.MODES)]
            self.status_msg   = f"Mode: {self.current_mode}"
            self._mode_enter()
            return

        if key == curses.KEY_UP:        self.scroll_pad.scroll_up()
        elif key == curses.KEY_DOWN:    self.scroll_pad.scroll_down()
        elif key == curses.KEY_PPAGE:   self.scroll_pad.scroll_up(10)
        elif key == curses.KEY_NPAGE:   self.scroll_pad.scroll_down(10)

        # Mode-specific input
        elif self.current_mode == "CHAT":
            self._handle_chat_key(key)
        elif self.current_mode == "WEB":
            self._handle_web_key(key)
        elif self.current_mode == "RSS":
            self._handle_rss_key(key)
        elif self.current_mode == "NET":
            self._handle_net_key(key)
        elif self.current_mode == "PDF":
            self._handle_pdf_key(key)
        elif self.current_mode == "CODE":
            self._handle_code_key(key)
        elif self.current_mode == "INFO":
            self._handle_info_key(key)

    def _mode_enter(self):
        self.scroll_pad.clear()
        mode = self.current_mode

        if mode == "CHAT":
            self.scroll_pad.append("── CHAT ─────────────────────────────\n", pair=3)
            self.scroll_pad.append("Type a message and press Enter.\n"
                                   "L=Load GGUF  S=System prompt  C=Clear  X=Export PDF\n",
                                   pair=12)
        elif mode == "WEB":
            self.scroll_pad.append("── WEB BROWSER ──────────────────────\n", pair=3)
            if self.browser.current_url:
                self.scroll_pad.append(
                    f"Current : {self.browser.current_url}\n"
                    f"Title   : {self.browser.current_title}\n"
                    f"Links   : {len(self.browser.current_links)}  "
                    f"History: {len(self.browser.history)}\n\n",
                    pair=2
                )
                for line in self.browser.current_text[:3000].splitlines():
                    self.scroll_pad.append(line + "\n", pair=1)
                if len(self.browser.current_text) > 3000:
                    self.scroll_pad.append(
                        f"\n… ({len(self.browser.current_text)-3000} more chars) "
                        "– scroll or use 'find' to search\n",
                        pair=13
                    )
            else:
                self.scroll_pad.append(
                    "No page loaded.\n\n"
                    "Commands:\n"
                    "  <url>          – Navigate (https:// added if missing)\n"
                    "  <search terms> – DuckDuckGo search (no URL needed)\n"
                    "  b              – Back\n"
                    "  f              – Forward\n"
                    "  r              – Reload\n"
                    "  l <n>          – Follow link [n]\n"
                    "  links          – List all links on current page\n"
                    "  find <text>    – Search within page\n"
                    "  bm             – Bookmark current page\n"
                    "  bml            – List bookmarks\n"
                    "  bm del <url>   – Remove bookmark\n"
                    "  ask <question> – Ask AI about current page\n"
                    "  ai             – Inject full page into AI context\n"
                    "  src            – View raw source (first 2000 chars)\n"
                    "  save           – Export page as PDF\n",
                    pair=12
                )
        elif mode == "RSS":
            self.scroll_pad.append("── RSS FEEDS ────────────────────────\n", pair=3)
            self._render_rss_menu()
        elif mode == "NET":
            self.scroll_pad.append("── NETWORK TOOLS ────────────────────\n", pair=3)
            self.scroll_pad.append(
                "Commands:\n"
                "  p <host>        – Ping\n"
                "  t <host>        – Traceroute\n"
                "  d <host>        – DNS lookup\n"
                "  s <host> [ports]– Port scan (e.g.: s example.com 80-443)\n"
                "  w <host>        – Whois\n"
                "  g <url>         – HTTP GET\n"
                "  i               – System info\n",
                pair=12
            )
        elif mode == "PDF":
            self.scroll_pad.append("── PDF MODULE ───────────────────────\n", pair=3)
            self.scroll_pad.append(
                "Commands:\n"
                "  r <path>  – Read / import PDF\n"
                "  e         – Export chat to PDF\n"
                "  ec <text> – Export custom text to PDF\n",
                pair=12
            )
        elif mode == "CODE":
            self.scroll_pad.append("── SELF-PROGRAMMING ─────────────────\n", pair=3)
            if self.last_code_blocks:
                self.scroll_pad.append(
                    f"  {len(self.last_code_blocks)} code block(s) from last AI response.\n",
                    pair=2, bold=True
                )
            self.scroll_pad.append(
                "Commands:\n"
                "  g <description>  – Ask AI to generate code\n"
                "  v [n]            – View block n (default 0)\n"
                "  save [n] [name]  – Save block to file\n"
                "  run [n]          – Run saved block\n"
                "  list             – List saved snippets\n",
                pair=12
            )
        elif mode == "INFO":
            self.scroll_pad.append("── MODEL INFO ───────────────────────\n", pair=3)
            self.scroll_pad.append(self.llama.get_info() + "\n", pair=1)
            self.scroll_pad.append("\nKey bindings:\n"
                                   "  Tab        – Next module\n"
                                   "  ↑↓ PgUp/Dn – Scroll\n"
                                   "  Ctrl+C/Q   – Quit\n"
                                   "  ?          – This screen\n", pair=12)

    # ── CHAT key handler ──────────────────────────────────────────────────────
    def _handle_chat_key(self, key: int):
        if key in (curses.KEY_ENTER, 10, 13):
            if not self.input_buf.strip():
                return
            cmd = self.input_buf.strip()
            self.input_buf  = ""
            self.cursor_pos = 0
            if cmd.startswith("!"):
                self._chat_command(cmd[1:])
            else:
                self._start_generation(cmd)
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            if self.cursor_pos > 0:
                self.input_buf  = self.input_buf[:self.cursor_pos - 1] + \
                                  self.input_buf[self.cursor_pos:]
                self.cursor_pos -= 1
        elif key == curses.KEY_LEFT:
            self.cursor_pos = max(0, self.cursor_pos - 1)
        elif key == curses.KEY_RIGHT:
            self.cursor_pos = min(len(self.input_buf), self.cursor_pos + 1)
        elif key == ord('l') and not self.input_buf:
            self._interactive_load()
        elif key == ord('s') and not self.input_buf:
            self._set_system_prompt()
        elif key == ord('c') and not self.input_buf:
            self.scroll_pad.clear()
            self.llama.history.clear()
            self.scroll_pad.append("(conversation cleared)\n", pair=13)
        elif key == ord('x') and not self.input_buf:
            result = self.pdf.export(
                self.scroll_pad.get_text(),
                title=f"LlamaUI Chat — {self.llama.model_name or 'No model'}"
            )
            self.status_msg = result
        elif key == ord('q') and not self.input_buf:
            self.running = False
        elif key == ord('?') and not self.input_buf:
            self._show_help()
        elif 32 <= key <= 126:
            self.input_buf  = self.input_buf[:self.cursor_pos] + chr(key) + \
                              self.input_buf[self.cursor_pos:]
            self.cursor_pos += 1

    def _chat_command(self, cmd: str):
        if cmd.startswith("temp "):
            try:
                self.llama.temperature = float(cmd.split()[1])
                self.status_msg = f"Temperature: {self.llama.temperature}"
            except ValueError:
                self.status_msg = "Usage: !temp 0.7"
        elif cmd == "clear":
            self.llama.history.clear()
            self.status_msg = "History cleared"
        elif cmd.startswith("browse ") or cmd.startswith("browse\t"):
            # Shared browsing: fetch URL, inject as AI context, ask AI about it
            url = cmd.split(None, 1)[1].strip()
            self.scroll_pad.append(f"\n[Browser] Fetching {url}…\n", pair=13)
            self._redraw()
            ok, msg = self.browser.go(url)
            if ok:
                self.status_msg = f"Browsed: {self.browser.current_title or url}"
                context = self.browser.inject_context(max_chars=3000)
                inject_msg = (
                    f"{context}\n\n"
                    "Please summarise the key points of this page."
                )
                self.scroll_pad.append(
                    f"[Browser] Loaded: {self.browser.current_title}\n"
                    f"[Browser] Injecting into AI context…\n",
                    pair=2
                )
                self._start_generation(inject_msg)
            else:
                self.scroll_pad.append(f"[Browser] {msg}\n", pair=11)
                self.status_msg = msg
        elif cmd.startswith("web "):
            # Jump to WEB module pre-loaded with a URL
            url = cmd.split(None, 1)[1].strip()
            self.current_mode = "WEB"
            self.scroll_pad.clear()
            self.scroll_pad.append(f"Fetching {url}…\n", pair=13)
            self._redraw()
            ok, fetch_msg = self.browser.go(url)
            self.status_msg = fetch_msg
            if ok:
                self._web_render_page()
            else:
                self.scroll_pad.append(fetch_msg + "\n", pair=11)
        else:
            self.status_msg = f"Unknown command: !{cmd}"

    # ── RSS key handler ───────────────────────────────────────────────────────
    def _handle_rss_key(self, key: int):
        if key in (curses.KEY_ENTER, 10, 13):
            if self.input_buf.strip().isdigit():
                idx = int(self.input_buf.strip()) - 1
                self.input_buf  = ""
                self.cursor_pos = 0
                if 0 <= idx < len(self.rss.feeds):
                    name, url = self.rss.feeds[idx]
                    self.scroll_pad.clear()
                    self.scroll_pad.append(f"Fetching {name}…\n", pair=13)
                    self._redraw()
                    headlines = self.rss.fetch(url)
                    self.scroll_pad.clear()
                    self.scroll_pad.append(f"── {name} ──\n\n", pair=2, bold=True)
                    for hl in headlines:
                        self.scroll_pad.append(hl + "\n", pair=1)
            elif self.input_buf.strip().startswith("add "):
                # add FeedName https://...
                parts = self.input_buf.strip().split(" ", 2)
                if len(parts) == 3:
                    self.rss.add_feed(parts[1], parts[2])
                    self.status_msg = f"Feed '{parts[1]}' added"
                    self._render_rss_menu()
                self.input_buf  = ""
                self.cursor_pos = 0
        elif 32 <= key <= 126:
            self.input_buf  = self.input_buf[:self.cursor_pos] + chr(key) + \
                              self.input_buf[self.cursor_pos:]
            self.cursor_pos += 1
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            if self.cursor_pos > 0:
                self.input_buf  = self.input_buf[:self.cursor_pos - 1] + \
                                  self.input_buf[self.cursor_pos:]
                self.cursor_pos -= 1

    def _render_rss_menu(self):
        self.scroll_pad.append("Enter a number to fetch, or 'add Name URL':\n", pair=12)
        for i, (name, url) in enumerate(self.rss.feeds, 1):
            self.scroll_pad.append(f"  [{i:2d}] {name:<20} {url}\n", pair=1)

    # ── Network key handler ───────────────────────────────────────────────────
    def _handle_net_key(self, key: int):
        if key in (curses.KEY_ENTER, 10, 13):
            cmd = self.input_buf.strip()
            self.input_buf  = ""
            self.cursor_pos = 0
            if not cmd:
                return
            self.scroll_pad.clear()
            self.scroll_pad.append(f"$ {cmd}\n", pair=2, bold=True)
            self._redraw()

            parts = cmd.split()
            op    = parts[0].lower() if parts else ""
            host  = parts[1] if len(parts) > 1 else ""

            result = ""
            if   op == "p":  result = self.net.ping(host)
            elif op == "t":  result = self.net.traceroute(host)
            elif op == "d":  result = self.net.dns_lookup(host)
            elif op == "s":
                ports = parts[2] if len(parts) > 2 else "22,80,443,8080,8443"
                result = self.net.port_scan(host, ports)
            elif op == "w":  result = self.net.whois(host)
            elif op == "g":  result = self.net.http_get(host)
            elif op == "i":  result = self.net.system_info()
            else:
                result = f"Unknown command: {op}\nType a command like: p 8.8.8.8"

            for line in result.splitlines():
                self.scroll_pad.append(line + "\n", pair=1)
        elif 32 <= key <= 126:
            self.input_buf  = self.input_buf[:self.cursor_pos] + chr(key) + \
                              self.input_buf[self.cursor_pos:]
            self.cursor_pos += 1
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            if self.cursor_pos > 0:
                self.input_buf  = self.input_buf[:self.cursor_pos - 1] + \
                                  self.input_buf[self.cursor_pos:]
                self.cursor_pos -= 1

    # ── PDF key handler ───────────────────────────────────────────────────────
    def _handle_pdf_key(self, key: int):
        if key in (curses.KEY_ENTER, 10, 13):
            cmd = self.input_buf.strip()
            self.input_buf  = ""
            self.cursor_pos = 0
            if not cmd:
                return
            self.scroll_pad.clear()
            self._redraw()

            if cmd.startswith("r "):
                path = cmd[2:].strip()
                self.scroll_pad.append(f"Reading PDF: {path}\n", pair=13)
                self._redraw()
                text = self.pdf.extract_text(path)
                for line in text.splitlines():
                    self.scroll_pad.append(line + "\n", pair=1)
            elif cmd == "e":
                result = self.pdf.export(
                    self.scroll_pad.get_text(),
                    title="LlamaUI Export"
                )
                self.status_msg = result
            elif cmd.startswith("ec "):
                result = self.pdf.export(cmd[3:], title="LlamaUI Custom Export")
                self.status_msg = result
            else:
                self.scroll_pad.append(f"Unknown command: {cmd}\n", pair=11)
        elif 32 <= key <= 126:
            self.input_buf  = self.input_buf[:self.cursor_pos] + chr(key) + \
                              self.input_buf[self.cursor_pos:]
            self.cursor_pos += 1
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            if self.cursor_pos > 0:
                self.input_buf  = self.input_buf[:self.cursor_pos - 1] + \
                                  self.input_buf[self.cursor_pos:]
                self.cursor_pos -= 1

    # ── Code key handler ──────────────────────────────────────────────────────
    def _handle_code_key(self, key: int):
        if key in (curses.KEY_ENTER, 10, 13):
            cmd = self.input_buf.strip()
            self.input_buf  = ""
            self.cursor_pos = 0
            if not cmd:
                return
            self.scroll_pad.clear()

            parts = cmd.split(None, 2)
            op    = parts[0].lower()

            if op == "g":
                desc = " ".join(parts[1:]) if len(parts) > 1 else "a hello world script"
                prompt = (
                    f"Write complete, runnable Python 3 code for: {desc}\n"
                    "Return ONLY the code inside a ```python ... ``` block."
                )
                self.scroll_pad.append(f"Generating code for: {desc}\n", pair=13)
                self._start_generation(prompt)
                self.current_mode = "CHAT"  # switch back to see output
            elif op == "v":
                n = int(parts[1]) if len(parts) > 1 else 0
                if self.last_code_blocks and n < len(self.last_code_blocks):
                    code = self.last_code_blocks[n]
                    self.scroll_pad.append(
                        f"── Block {n} ──\n{code}\n──────────────\n", pair=14
                    )
                else:
                    self.scroll_pad.append("No code block at that index.\n", pair=11)
            elif op == "save":
                n    = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
                name = parts[2] if len(parts) > 2 else ""
                if self.last_code_blocks and n < len(self.last_code_blocks):
                    result = self.code_mod.save_snippet(self.last_code_blocks[n], name)
                    self.scroll_pad.append(result + "\n", pair=2)
                else:
                    self.scroll_pad.append("No code block at that index.\n", pair=11)
            elif op == "run":
                n = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
                snippets = self.code_mod.snippets
                if snippets and n < len(snippets):
                    path = snippets[n]["path"]
                    self.scroll_pad.append(f"Running {path}…\n", pair=13)
                    self._redraw()
                    out = self.code_mod.run_snippet(path)
                    for line in out.splitlines():
                        self.scroll_pad.append(line + "\n", pair=14)
                else:
                    self.scroll_pad.append("No snippet at that index (use 'list').\n", pair=11)
            elif op == "list":
                if self.code_mod.snippets:
                    for i, s in enumerate(self.code_mod.snippets):
                        self.scroll_pad.append(f"  [{i}] {s['name']}  →  {s['path']}\n", pair=1)
                else:
                    self.scroll_pad.append("No saved snippets yet.\n", pair=13)
            else:
                self.scroll_pad.append(f"Unknown command: {op}\n", pair=11)
        elif 32 <= key <= 126:
            self.input_buf  = self.input_buf[:self.cursor_pos] + chr(key) + \
                              self.input_buf[self.cursor_pos:]
            self.cursor_pos += 1
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            if self.cursor_pos > 0:
                self.input_buf  = self.input_buf[:self.cursor_pos - 1] + \
                                  self.input_buf[self.cursor_pos:]
                self.cursor_pos -= 1

    # ── Info key handler ──────────────────────────────────────────────────────
    def _handle_info_key(self, key: int):
        if key == ord('r'):
            self._mode_enter()

    # ── Web browser key handler ───────────────────────────────────────────────
    def _handle_web_key(self, key: int):
        if key in (curses.KEY_ENTER, 10, 13):
            cmd = self.input_buf.strip()
            self.input_buf  = ""
            self.cursor_pos = 0
            if not cmd:
                return

            self.scroll_pad.clear()
            parts = cmd.split(None, 1)
            op    = parts[0].lower()
            arg   = parts[1].strip() if len(parts) > 1 else ""

            # ── Single-letter navigation ──────────────────────────────────
            if op == "b" and not arg:
                ok, msg = self.browser.back()
                self.status_msg = msg
                if ok:
                    self._web_render_page()
                else:
                    self.scroll_pad.append(msg + "\n", pair=11)

            elif op == "f" and not arg:
                ok, msg = self.browser.forward_nav()
                self.status_msg = msg
                if ok:
                    self._web_render_page()
                else:
                    self.scroll_pad.append(msg + "\n", pair=11)

            elif op == "r" and not arg:
                self.scroll_pad.append("Reloading…\n", pair=13)
                self._redraw()
                ok, msg = self.browser.reload()
                self.status_msg = msg
                if ok:
                    self._web_render_page()
                else:
                    self.scroll_pad.append(msg + "\n", pair=11)

            # ── Follow link ───────────────────────────────────────────────
            elif op == "l" and arg.isdigit():
                n = int(arg)
                self.scroll_pad.append(f"Following link [{n}]…\n", pair=13)
                self._redraw()
                ok, msg = self.browser.follow_link(n)
                self.status_msg = msg
                if ok:
                    self._web_render_page()
                else:
                    self.scroll_pad.append(msg + "\n", pair=11)

            # ── List all links ────────────────────────────────────────────
            elif op == "links":
                if not self.browser.current_links:
                    self.scroll_pad.append("No links on this page.\n", pair=13)
                else:
                    self.scroll_pad.append(
                        f"── {len(self.browser.current_links)} links ──\n\n", pair=2, bold=True
                    )
                    for n, text, href in self.browser.current_links:
                        self.scroll_pad.append(
                            f"  [{n:3d}] {text[:40]:<40}  {href[:60]}\n", pair=1
                        )

            # ── In-page search ────────────────────────────────────────────
            elif op == "find" and arg:
                results = self.browser.find(arg)
                self.browser_find_res = results
                if not results:
                    self.scroll_pad.append(f"Not found: {arg}\n", pair=13)
                else:
                    self.scroll_pad.append(
                        f"── {len(results)} match(es) for '{arg}' ──\n\n",
                        pair=2, bold=True
                    )
                    for lineno, line in results:
                        # Highlight match
                        hi_line = line.replace(
                            arg, f"[{arg}]"   # simple marker; curses attr not in line
                        )
                        self.scroll_pad.append(
                            f"  L{lineno:4d}: {hi_line[:80]}\n", pair=1
                        )

            # ── Bookmarks ─────────────────────────────────────────────────
            elif op == "bm" and not arg:
                msg = self.browser.add_bookmark()
                self.status_msg = msg
                self.scroll_pad.append(msg + "\n", pair=2)

            elif op == "bml":
                if not self.browser.bookmarks:
                    self.scroll_pad.append("No bookmarks yet. Use 'bm' to add one.\n", pair=13)
                else:
                    self.scroll_pad.append(
                        f"── {len(self.browser.bookmarks)} bookmarks ──\n\n",
                        pair=2, bold=True
                    )
                    for i, (url, title) in enumerate(self.browser.bookmarks.items(), 1):
                        self.scroll_pad.append(
                            f"  [{i:2d}] {title[:40]:<42} {url[:60]}\n", pair=1
                        )
                    self.scroll_pad.append(
                        "\nType the URL (or copy-paste) to navigate to a bookmark.\n",
                        pair=12
                    )

            elif op == "bm" and arg.startswith("del "):
                target = arg[4:].strip()
                msg = self.browser.remove_bookmark(target)
                self.status_msg = msg
                self.scroll_pad.append(msg + "\n", pair=13)

            # ── Ask AI about the current page ─────────────────────────────
            elif op in ("ai", "ask"):
                if not self.browser.current_url:
                    self.scroll_pad.append("[No page loaded]\n", pair=11)
                    return
                question = arg if op == "ask" and arg else \
                           "Summarise this web page concisely."
                context  = self.browser.inject_context(max_chars=3000)
                full_prompt = f"{context}\n\nQuestion: {question}"
                self.scroll_pad.append(
                    f"Sending page to AI: {self.browser.current_url}\n", pair=13
                )
                self.current_mode = "CHAT"
                self._start_generation(full_prompt)

            # ── View raw source ───────────────────────────────────────────
            elif op == "src":
                if not REQUESTS_AVAILABLE:
                    self.scroll_pad.append("[requests not installed]\n", pair=11)
                    return
                if not self.browser.current_url:
                    self.scroll_pad.append("[No page loaded]\n", pair=11)
                    return
                try:
                    resp = requests.get(
                        self.browser.current_url,
                        headers=WebBrowser.HEADERS, timeout=15
                    )
                    src = resp.text[:3000]
                    self.scroll_pad.append(
                        f"── Source: {self.browser.current_url} ──\n\n", pair=2
                    )
                    for line in src.splitlines():
                        self.scroll_pad.append(line[:160] + "\n", pair=14)
                    if len(resp.text) > 3000:
                        self.scroll_pad.append(
                            f"\n… ({len(resp.text)-3000} more chars)\n", pair=13
                        )
                except Exception as e:
                    self.scroll_pad.append(f"[Error: {e}]\n", pair=11)

            # ── Export page as PDF ────────────────────────────────────────
            elif op == "save":
                if not self.browser.current_url:
                    self.scroll_pad.append("[No page loaded]\n", pair=11)
                    return
                pm  = PDFModule()
                msg = pm.export(
                    self.browser.current_text,
                    title=self.browser.current_title or self.browser.current_url
                )
                self.status_msg = msg
                self.scroll_pad.append(msg + "\n", pair=2)

            # ── Navigate to URL / DuckDuckGo search ───────────────────────
            else:
                # Anything that doesn't match a command is treated as a URL or search
                nav_target = cmd  # use full original command
                self.scroll_pad.append(f"Fetching: {nav_target}\n", pair=13)
                self._redraw()
                ok, msg = self.browser.go(nav_target)
                self.status_msg = msg
                if ok:
                    self._web_render_page()
                else:
                    self.scroll_pad.append(msg + "\n", pair=11)
                    self.scroll_pad.append(
                        "Tip: type any URL or search terms and press Enter.\n", pair=12
                    )

        elif 32 <= key <= 126:
            self.input_buf  = self.input_buf[:self.cursor_pos] + chr(key) + \
                              self.input_buf[self.cursor_pos:]
            self.cursor_pos += 1
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            if self.cursor_pos > 0:
                self.input_buf  = self.input_buf[:self.cursor_pos - 1] + \
                                  self.input_buf[self.cursor_pos:]
                self.cursor_pos -= 1
        elif key == curses.KEY_LEFT:
            self.cursor_pos = max(0, self.cursor_pos - 1)
        elif key == curses.KEY_RIGHT:
            self.cursor_pos = min(len(self.input_buf), self.cursor_pos + 1)

    def _web_render_page(self):
        """Re-render the browser's current page into the scroll pad."""
        self.scroll_pad.clear()
        b = self.browser
        # URL / title bar
        self.scroll_pad.append(
            f"  URL  : {b.current_url}\n"
            f"  Title: {b.current_title}\n"
            f"  Links: {len(b.current_links)}  │  "
            f"History: {len(b.history)}  │  Forward: {len(b.forward)}\n",
            pair=2, bold=True
        )
        self.scroll_pad.append("─" * 60 + "\n", pair=3)
        # Page body
        for line in b.current_text.splitlines():
            # Colour headings (detected by ═ / ─ lines) differently
            stripped = line.strip()
            if re.match(r"^[═─·]{4,}$", stripped):
                self.scroll_pad.append(line + "\n", pair=3)
            elif stripped.startswith("•"):
                self.scroll_pad.append(line + "\n", pair=1)
            elif re.match(r"^\[\d+\]", stripped):   # numbered link
                self.scroll_pad.append(line + "\n", pair=2)
            else:
                self.scroll_pad.append(line + "\n", pair=14)
        self.scroll_pad.append(
            "\n── Commands: b=back  f=fwd  r=reload  l<n>=link  "
            "find <q>  bm  bml  ask <q>  ai  save ──\n",
            pair=12
        )

    # ── Interactive loaders ───────────────────────────────────────────────────
    def _interactive_load(self):
        browser = GGUFBrowser(self.stdscr)
        path    = browser.browse()
        if path:
            self.scroll_pad.clear()
            CE.init_pairs()
            MatrixRain(self.stdscr, duration=2.5,
                       title=f"Loading {Path(path).stem}").run()
            CE.init_pairs()
            self._load_model_bg(path)

    def _set_system_prompt(self):
        curses.curs_set(1)
        h, w = self.stdscr.getmaxyx()
        dlg_h, dlg_w = 10, min(70, w - 4)
        dy = (h - dlg_h) // 2
        dx = (w - dlg_w) // 2
        dlg = curses.newwin(dlg_h, dlg_w, dy, dx)
        dlg.keypad(True)
        dlg.border()
        dlg.addstr(1, 2, "Set System Prompt (Enter to confirm, ESC to cancel):",
                   CE.pair(2, bold=True))
        dlg.addstr(2, 2, "(current):", CE.pair(12))

        wrapped = textwrap.wrap(self.llama.system_prompt, dlg_w - 4)
        for i, line in enumerate(wrapped[:4]):
            try:
                dlg.addstr(3 + i, 2, line[:dlg_w - 4], CE.pair(14))
            except curses.error:
                pass

        dlg.addstr(7, 2, "> ", CE.pair(1, bold=True))
        dlg.refresh()
        curses.echo()
        try:
            new_prompt = dlg.getstr(7, 4, dlg_w - 6).decode("utf-8", errors="replace")
            if new_prompt.strip():
                self.llama.system_prompt = new_prompt
                self.status_msg = "System prompt updated"
        except Exception:
            pass
        curses.noecho()
        del dlg
        self.stdscr.touchwin()
        self.stdscr.refresh()

    # ── Help overlay ──────────────────────────────────────────────────────────
    def _show_help(self):
        h, w = self.stdscr.getmaxyx()
        dlg_h, dlg_w = min(h - 2, 30), min(w - 2, 60)
        dy = (h - dlg_h) // 2
        dx = (w - dlg_w) // 2
        dlg = curses.newwin(dlg_h, dlg_w, dy, dx)
        dlg.keypad(True)
        dlg.border()
        dlg.addstr(1, 2, f" {APP_NAME} v{APP_VERSION} — Help ",
                   CE.pair(5, bold=True))
        help_text = [
            "",
            "GLOBAL:",
            "  Tab          – Cycle modules",
            "  ↑↓ PgUp/Dn   – Scroll output",
            "  Ctrl-C / Q   – Quit",
            "",
            "CHAT MODULE:",
            "  L              – Open GGUF file browser",
            "  S              – Set system prompt",
            "  C              – Clear conversation",
            "  X              – Export chat to PDF",
            "  !temp 0.8      – Set temperature",
            "  !browse <url>  – Fetch URL → inject to AI",
            "  !web <url>     – Open URL in WEB module",
            "",
            "WEB BROWSER (shared user+AI):",
            "  <url> or terms – Navigate / DuckDuckGo search",
            "  b / f / r      – Back / Forward / Reload",
            "  l <n>          – Follow link [n]",
            "  links          – List all links",
            "  find <text>    – In-page search",
            "  bm / bml       – Bookmark / List bookmarks",
            "  ask <question> – Ask AI about page",
            "  ai             – Inject page into AI context",
            "  save           – Export page to PDF",
            "",
            "RSS MODULE:",
            "  1–N          – Fetch feed N",
            "  add Name URL – Add custom feed",
            "",
            "NETWORK MODULE:",
            "  p/t/d/s/w/g/i  – ping/trace/dns/scan/whois/get/info",
            "",
            "PDF MODULE:",
            "  r <path>   – Import / read PDF",
            "  e          – Export chat to PDF",
            "",
            "CODE MODULE:",
            "  g <desc>   – Generate code with AI",
            "  v/save/run/list",
            "",
            "  Press any key to close…",
        ]
        for i, line in enumerate(help_text):
            row = 2 + i
            if row >= dlg_h - 1:
                break
            try:
                dlg.addstr(row, 2, line[:dlg_w - 4], CE.pair(1))
            except curses.error:
                pass
        dlg.refresh()
        dlg.getch()
        del dlg
        self.stdscr.touchwin()
        self.stdscr.refresh()

    # ── Rendering ─────────────────────────────────────────────────────────────
    def _redraw(self):
        try:
            self._draw()
        except curses.error:
            pass

    def _draw(self):
        h, w = self.stdscr.getmaxyx()
        if h < 10 or w < 30:
            return

        self.stdscr.erase()

        # ── Top header bar ────────────────────────────────────────────────────
        mood_info  = MOODS.get(self.current_mood, MOODS["neutral"])
        model_name = self.llama.model_name or "No model"
        gen_marker = " ◌ GENERATING" if self.is_generating else ""
        if self.current_mode == "WEB" and self.browser.current_url:
            web_info = f"  │  {self.browser.current_url[:40]}"
        else:
            web_info = ""
        header = (
            f" {APP_NAME}  │  [{self.current_mode}]  │  "
            f"Model: {model_name[:20]}  │  "
            f"Mood: {mood_info['label']}{gen_marker}{web_info} "
        )
        try:
            self.stdscr.addstr(0, 0, header[:w].ljust(w), CE.pair(5, bold=True))
        except curses.error:
            pass

        # ── Divider ───────────────────────────────────────────────────────────
        tab_bar = ""
        for m in self.MODES:
            if m == self.current_mode:
                tab_bar += f"[{m}]"
            else:
                tab_bar += f" {m} "
        try:
            self.stdscr.addstr(1, 0, tab_bar[:w].ljust(w), CE.pair(3))
        except curses.error:
            pass

        # ── Content divider ───────────────────────────────────────────────────
        try:
            self.stdscr.addstr(2, 0, "─" * w, CE.pair(3))
        except curses.error:
            pass

        # ── Scroll pad ────────────────────────────────────────────────────────
        self.scroll_pad.win       = self.stdscr
        self.scroll_pad.start_row = 3
        self.scroll_pad.render()

        # ── Input divider ─────────────────────────────────────────────────────
        divider_row = h - 3
        try:
            self.stdscr.addstr(divider_row, 0, "─" * w, CE.pair(3))
        except curses.error:
            pass

        # ── Status bar ────────────────────────────────────────────────────────
        avail = {
            "llama":  LLAMA_AVAILABLE,
            "rss":    FEEDPARSER_AVAILABLE,
            "req":    REQUESTS_AVAILABLE,
            "pdf":    FPDF_AVAILABLE,
            "plumb":  PDFPLUMBER_AVAILABLE,
            "bs4":    BS4_AVAILABLE,
        }
        status_flags = "  ".join(
            f"{k}:{'✓' if v else '✗'}" for k, v in avail.items()
        )
        status_right = f" {status_flags} "
        status_left  = f" {self.status_msg}"
        gap          = max(0, w - len(status_left) - len(status_right))
        status_line  = status_left + " " * gap + status_right
        try:
            self.stdscr.addstr(h - 2, 0, status_line[:w], CE.pair(12))
        except curses.error:
            pass

        # ── Input line ────────────────────────────────────────────────────────
        mode_prompt = {
            "CHAT": "Chat (!browse url / !web url)",
            "WEB":  "Web (url / search / b f r l<n> find ask ai bm bml save)",
            "RSS":  "RSS (1–N / add Name URL)",
            "NET":  "Net (p/t/d/s/g/i host)",
            "PDF":  "PDF (r path / e / ec text)",
            "CODE": "Code (g/v/save/run/list)",
            "INFO": "Info (r=refresh)",
        }.get(self.current_mode, self.current_mode)
        prompt = f" {mode_prompt} ❯ "
        input_display = self.input_buf
        max_input     = w - len(prompt) - 1
        if len(input_display) > max_input:
            input_display = input_display[-(max_input):]
        cursor_in_display = min(self.cursor_pos, len(input_display))
        try:
            self.stdscr.addstr(h - 1, 0, prompt, CE.pair(2, bold=True))
            self.stdscr.addstr(h - 1, len(prompt),
                               input_display[:max_input], CE.pair(4))
        except curses.error:
            pass
        # Position cursor
        try:
            cx = len(prompt) + min(cursor_in_display, max_input)
            self.stdscr.move(h - 1, min(cx, w - 1))
        except curses.error:
            pass

        self.stdscr.refresh()


# =============================================================================
#  ENTRY POINT
# =============================================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Termux llama.cpp Python UI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python llama_ui.py
  python llama_ui.py /path/to/model.gguf
  python llama_ui.py --model ~/models/llama-3.gguf --ctx 8192
        """
    )
    parser.add_argument("model", nargs="?", default="",
                        help="Path to a .gguf model file to preload")
    parser.add_argument("--ctx", type=int, default=4096,
                        help="Context window size (default: 4096)")
    parser.add_argument("--threads", type=int, default=0,
                        help="CPU threads (default: auto)")
    args = parser.parse_args()

    def _run(stdscr):
        app = LlamaUI(stdscr, preload_model=args.model)
        if args.ctx:
            app.llama.ctx_size = args.ctx
        if args.threads:
            app.llama.n_threads = args.threads
        try:
            app.run()
        except KeyboardInterrupt:
            pass

    try:
        curses.wrapper(_run)
    except Exception as e:
        print(f"\n[Fatal error] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
