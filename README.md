# termux-llama.cpp

**Full-featured Termux tools for llama.cpp on Android — with a Python TUI, matrix rain boot screen, mood-driven colour themes, RSS, PDF, network tools, and self-programming.**

---

## Features

| Module | Description |
|--------|-------------|
| **Matrix Rain Boot** | GGUF-themed matrix rain displayed during model load |
| **GGUF File Browser** | Interactive terminal browser to select `.gguf` files |
| **Chat** | Streamed inference via `llama-cpp-python` |
| **Mood Engine** | Detects sentiment in AI responses → changes colour theme in real-time |
| **RSS Feeds** | Reads any RSS/Atom feed; bundled with BBC, HackerNews, Reuters, Wired, ArsTechnica, AI News |
| **Network Tools** | Ping, traceroute, DNS, port scan, whois, HTTP GET, system info |
| **PDF Module** | Import text from PDFs (`pdfplumber`), export conversations/output as PDF (`fpdf2`) |
| **Self-Programming** | Ask the AI to generate Python code, view/save/run code blocks |

---

## Quick Install (Termux)

```bash
# 1. Clone this repo
git clone https://github.com/jedisecX/termux-llama.cpp.git
cd termux-llama.cpp

# 2. Run the installer (builds llama.cpp + installs all Python deps)
bash install.sh

# 3. Download a GGUF model (example — adjust URL to your preferred model)
wget -P ~/llama-cpp-termux/models \
  "https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf"

# 4. Launch the UI
llamaui
# or with a model directly:
llamaui ~/llama-cpp-termux/models/llama-2-7b-chat.Q4_K_M.gguf
```

> The installer detects your CPU architecture (arm64 / x86_64), enables OpenBLAS acceleration, and checks whether `transformers` + PyTorch are installable for your platform. If PyTorch is unavailable (common on Android), the `llama-cpp-python` backend is used exclusively — which is the recommended path anyway.

---

## Key Bindings

### Global
| Key | Action |
|-----|--------|
| `Tab` | Cycle between modules (Chat → RSS → Net → PDF → Code → Info) |
| `↑` / `↓` | Scroll output |
| `PgUp` / `PgDn` | Scroll output fast |
| `Ctrl-C` / `q` | Quit |
| `?` | Help overlay |

### Chat Module
| Key | Action |
|-----|--------|
| `L` | Open GGUF file browser (matrix rain plays on load) |
| `S` | Set/change system prompt |
| `C` | Clear conversation history |
| `X` | Export conversation to PDF |
| `!temp 0.8` | Set inference temperature |

### RSS Module
| Input | Action |
|-------|--------|
| `1` – `N` | Fetch headlines from feed N |
| `add Name https://...` | Add a custom RSS feed |

### Network Module
| Command | Action |
|---------|--------|
| `p <host>` | Ping |
| `t <host>` | Traceroute |
| `d <host>` | DNS lookup (A, AAAA, MX, NS, TXT) |
| `s <host> [ports]` | Port scan (`s 1.1.1.1 80-443`) |
| `w <host>` | WHOIS |
| `g <url>` | HTTP GET + headers |
| `i` | System info (CPU, RAM, disk, network) |

### PDF Module
| Command | Action |
|---------|--------|
| `r <path>` | Read & import text from a PDF |
| `e` | Export current screen content to PDF |
| `ec <text>` | Export arbitrary text to PDF |

### Code / Self-Programming Module
| Command | Action |
|---------|--------|
| `g <description>` | Ask AI to generate Python code |
| `v [n]` | View code block n from last AI response |
| `save [n] [filename]` | Save block n to `~/llama-cpp-termux/scripts/` |
| `run [n]` | Execute saved snippet n |
| `list` | List all saved snippets |

---

## Mood Colour Themes

The AI response is analysed after each generation. The terminal colour scheme updates automatically:

| Mood | Colour | Triggered by |
|------|--------|--------------|
| Neutral | Cyan | (default) |
| Happy | Green | happy, joy, love… |
| Curious | Yellow | wonder, fascinating… |
| Philosophical | Magenta | meaning, consciousness… |
| Technical | White | algorithm, code, system… |
| Creative | Magenta + Yellow | imagine, create, build… |
| Concerned | Red | danger, risk, worry… |
| Excited | Yellow + Green | amazing, incredible… |

---

## Python Dependencies

Installed automatically by `install.sh`:

```
llama-cpp-python   # GGUF inference backend
feedparser         # RSS/Atom parsing
requests           # HTTP networking
fpdf2              # PDF generation / export
pdfplumber         # PDF text extraction
psutil             # System info
dnspython          # Full DNS record lookups
rich               # Terminal formatting
prompt_toolkit     # Advanced input
pygments           # Syntax highlighting
beautifulsoup4     # HTML parsing
httpx              # Async HTTP
```

**Transformers / PyTorch**: `install.sh` attempts to install `transformers` and PyTorch. On most Android (ARM64) devices PyTorch wheels are not available; `transformers` tokenizers still install and the `llama-cpp-python` backend is used for inference.

---

## Directory Layout

```
~/llama-cpp-termux/
├── llama.cpp/          ← cloned & built llama.cpp source
├── models/             ← place your .gguf files here
├── scripts/            ← llama-cli, llama-server binaries + saved code snippets
├── venv/               ← Python virtual environment
└── llama_ui.py         ← the UI script (symlinked via 'llamaui' launcher)
```

---

## License

MIT © 2026 Jedi Security
