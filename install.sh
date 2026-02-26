#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
#  TERMUX LLAMA.CPP INSTALLER
#  Full-featured installer for llama.cpp + Python UI on Termux (Android)
#  Includes: llama.cpp build, Python bindings, transformers check,
#            curses UI deps, PDF, RSS, and network tool dependencies
# =============================================================================

set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m';  GREEN='\033[0;32m';  YELLOW='\033[1;33m'
CYAN='\033[0;36m'; MAGENTA='\033[0;35m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
step()    { echo -e "\n${BOLD}${MAGENTA}▶ $*${RESET}"; }

# ── Banner ────────────────────────────────────────────────────────────────────
banner() {
cat << 'EOF'
  ╔══════════════════════════════════════════════════════════╗
  ║   ██╗     ██╗      █████╗ ███╗   ███╗ █████╗            ║
  ║   ██║     ██║     ██╔══██╗████╗ ████║██╔══██╗           ║
  ║   ██║     ██║     ███████║██╔████╔██║███████║           ║
  ║   ██║     ██║     ██╔══██║██║╚██╔╝██║██╔══██║           ║
  ║   ███████╗███████╗██║  ██║██║ ╚═╝ ██║██║  ██║           ║
  ║   ╚══════╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝           ║
  ║              TERMUX  LLAMA.CPP  INSTALLER                ║
  ║          + Python UI · RSS · PDF · Network Tools         ║
  ╚══════════════════════════════════════════════════════════╝
EOF
}

banner
echo ""
info "Starting installation at $(date)"
echo ""

# ── 1. Environment check ──────────────────────────────────────────────────────
step "1/9  Checking Termux environment"

if [[ -z "${TERMUX_VERSION:-}" && ! -d "/data/data/com.termux" ]]; then
    warn "TERMUX_VERSION not set and /data/data/com.termux not found."
    warn "This script is designed for Termux on Android."
    read -rp "Continue anyway? (y/N) " _ans
    [[ "${_ans,,}" == "y" ]] || { error "Aborting."; exit 1; }
fi

PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"
INSTALL_DIR="${HOME_DIR}/llama-cpp-termux"
VENV_DIR="${INSTALL_DIR}/venv"
LLAMA_DIR="${INSTALL_DIR}/llama.cpp"
MODELS_DIR="${INSTALL_DIR}/models"
SCRIPTS_DIR="${INSTALL_DIR}/scripts"

# Architecture detection
ARCH="$(uname -m)"
info "Architecture: ${ARCH}"
info "Install root : ${INSTALL_DIR}"

mkdir -p "${INSTALL_DIR}" "${MODELS_DIR}" "${SCRIPTS_DIR}"

# ── 2. System packages ────────────────────────────────────────────────────────
step "2/9  Updating Termux package list"
pkg update -y 2>/dev/null || warn "pkg update had warnings (continuing)"

step "3/9  Installing system dependencies"

PKG_LIST=(
    python              # Python 3 interpreter
    python-pip          # pip package manager
    git                 # version control / cloning llama.cpp
    cmake               # build system for llama.cpp
    ninja               # fast build backend
    clang               # C/C++ compiler
    libopenblas         # optimised BLAS for matrix math
    wget                # downloading models
    curl                # HTTP requests
    nmap                # network scanning (network tools module)
    traceroute          # network diagnostic
    dnsutils            # dig/nslookup
    libcurl             # curl dev headers
    zlib                # compression
    openssl             # TLS
    libjpeg-turbo       # image support (for PDF rendering)
    libpng              # PNG support
    freetype            # font rendering (for PDF)
)

for pkg in "${PKG_LIST[@]}"; do
    if ! dpkg -s "$pkg" &>/dev/null 2>&1; then
        info "Installing ${pkg}…"
        pkg install -y "$pkg" 2>/dev/null \
            && success "${pkg} installed" \
            || warn "${pkg} skipped (not found in repo – continuing)"
    else
        success "${pkg} already installed"
    fi
done

# ── 3. Build llama.cpp ────────────────────────────────────────────────────────
step "4/9  Cloning / updating llama.cpp"

if [[ -d "${LLAMA_DIR}/.git" ]]; then
    info "llama.cpp already cloned – pulling latest…"
    git -C "${LLAMA_DIR}" pull origin master 2>/dev/null \
        || git -C "${LLAMA_DIR}" pull origin main 2>/dev/null \
        || warn "git pull failed – using existing checkout"
else
    git clone --depth 1 https://github.com/ggerganov/llama.cpp.git "${LLAMA_DIR}"
fi
success "llama.cpp source ready"

step "5/9  Building llama.cpp (optimised for ${ARCH})"

BUILD_DIR="${LLAMA_DIR}/build"
mkdir -p "${BUILD_DIR}"

# Set BLAS flags
CMAKE_EXTRA=""
if pkg list-installed 2>/dev/null | grep -q "libopenblas"; then
    CMAKE_EXTRA="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS"
    info "OpenBLAS acceleration enabled"
fi

# ARM NEON for most Android devices
if [[ "$ARCH" == aarch64* ]]; then
    CMAKE_EXTRA="${CMAKE_EXTRA} -DLLAMA_NATIVE=ON"
    info "ARM64 native optimisations enabled"
fi

cmake -S "${LLAMA_DIR}" -B "${BUILD_DIR}" \
    -DCMAKE_BUILD_TYPE=Release \
    -DLLAMA_CURL=ON \
    ${CMAKE_EXTRA} 2>&1 | tail -5

cmake --build "${BUILD_DIR}" --config Release -j"$(nproc)" 2>&1 | tail -10

# Copy binaries to scripts dir
for bin in "${BUILD_DIR}/bin/"*; do
    [[ -f "$bin" ]] && cp "$bin" "${SCRIPTS_DIR}/" && chmod +x "${SCRIPTS_DIR}/$(basename "$bin")"
done
success "llama.cpp built successfully"

# Add to PATH in .bashrc / .zshrc
for rc in "${HOME_DIR}/.bashrc" "${HOME_DIR}/.zshrc"; do
    if [[ -f "$rc" ]]; then
        grep -q "llama-cpp-termux/scripts" "$rc" \
            || echo "export PATH=\"${SCRIPTS_DIR}:\$PATH\"" >> "$rc"
    fi
done
export PATH="${SCRIPTS_DIR}:${PATH}"

# ── 4. Python virtual environment ─────────────────────────────────────────────
step "6/9  Creating Python virtual environment"

python -m venv "${VENV_DIR}" 2>/dev/null || python3 -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip setuptools wheel 2>/dev/null | tail -2
success "Virtual environment ready: ${VENV_DIR}"

# ── 5. Core Python packages ───────────────────────────────────────────────────
step "7/9  Installing Python packages"

# llama-cpp-python  ─ build with OpenBLAS if available
info "Building llama-cpp-python (this may take 5–15 min)…"
if pkg list-installed 2>/dev/null | grep -q "libopenblas"; then
    CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS" \
    pip install llama-cpp-python --no-cache-dir 2>&1 | tail -5
else
    pip install llama-cpp-python --no-cache-dir 2>&1 | tail -5
fi
success "llama-cpp-python installed"

# UI, network, PDF, RSS dependencies
PIP_PACKAGES=(
    "requests"            # HTTP / network tools
    "feedparser"          # RSS feed parser
    "fpdf2"               # PDF generation
    "pdfplumber"          # PDF text extraction
    "rich"                # rich terminal formatting (fallback display)
    "prompt_toolkit"      # advanced terminal input
    "pygments"            # syntax highlighting for self-programming module
    "psutil"              # system info (CPU / RAM / network stats)
    "beautifulsoup4"      # HTML parsing for mini web browser (WEB module)
    "lxml"                # fast XML/HTML parser backend for bs4
    "dnspython"           # DNS resolution for network tools
    "scapy"               # packet crafting (network tools, Termux may need root)
    "httpx"               # async HTTP
)

for pkg in "${PIP_PACKAGES[@]}"; do
    info "Installing ${pkg}…"
    pip install "$pkg" --no-cache-dir -q \
        && success "${pkg} OK" \
        || warn "${pkg} failed – continuing (non-critical)"
done

# ── 6. Transformers compatibility check ───────────────────────────────────────
step "8/9  Checking Hugging Face transformers compatibility"

info "Attempting to install transformers (sentencepiece backend – no torch required)…"

TRANSFORMERS_OK=false
TORCH_OK=false
SENTENCE_PIECE_OK=false

pip install sentencepiece tokenizers -q 2>/dev/null \
    && SENTENCE_PIECE_OK=true \
    && success "sentencepiece + tokenizers installed"

pip install transformers -q 2>/dev/null \
    && TRANSFORMERS_OK=true \
    && success "transformers installed (CPU-only mode)"

# PyTorch on ARM64 Termux: check if a wheel is available
info "Attempting PyTorch install (may fail on Android – OK if it does)…"
pip install torch --extra-index-url https://download.pytorch.org/whl/cpu -q 2>/dev/null \
    && TORCH_OK=true \
    && success "PyTorch CPU installed – full transformers pipeline available!" \
    || warn "PyTorch not available for this platform – using llama-cpp-python backend only (recommended)"

echo ""
echo -e "${BOLD}Transformers status:${RESET}"
echo -e "  sentencepiece/tokenizers : $([[ $SENTENCE_PIECE_OK == true ]] && echo "${GREEN}YES${RESET}" || echo "${YELLOW}NO${RESET}")"
echo -e "  transformers library     : $([[ $TRANSFORMERS_OK == true ]] && echo "${GREEN}YES${RESET}" || echo "${YELLOW}NO${RESET}")"
echo -e "  PyTorch backend          : $([[ $TORCH_OK == true ]] && echo "${GREEN}YES${RESET}" || echo "${YELLOW}NO (llama-cpp used instead)${RESET}")"
echo ""

# ── 7. Copy UI script ─────────────────────────────────────────────────────────
step "9/9  Installing Termux llama.cpp Python UI"

SCRIPT_SRC="$(dirname "$(realpath "$0")")/llama_ui.py"

if [[ -f "$SCRIPT_SRC" ]]; then
    cp "$SCRIPT_SRC" "${INSTALL_DIR}/llama_ui.py"
    chmod +x "${INSTALL_DIR}/llama_ui.py"
    success "llama_ui.py installed to ${INSTALL_DIR}"
else
    warn "llama_ui.py not found next to install.sh – skipping copy"
    warn "Place llama_ui.py in ${INSTALL_DIR}/ manually"
fi

# Write a launcher script
cat > "${HOME_DIR}/llamaui" << LAUNCHER
#!/data/data/com.termux/files/usr/bin/bash
source "${VENV_DIR}/bin/activate"
export LLAMA_BIN_DIR="${SCRIPTS_DIR}"
export LLAMA_MODELS_DIR="${MODELS_DIR}"
python "${INSTALL_DIR}/llama_ui.py" "\$@"
LAUNCHER
chmod +x "${HOME_DIR}/llamaui"

grep -q "llamaui" "${HOME_DIR}/.bashrc" 2>/dev/null \
    || echo "export PATH=\"${HOME_DIR}:\$PATH\"" >> "${HOME_DIR}/.bashrc"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${RESET}"
echo -e "${GREEN}║              INSTALLATION COMPLETE!                      ║${RESET}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  Models directory : ${BOLD}${MODELS_DIR}${RESET}"
echo -e "  Launch UI        : ${BOLD}llamaui${RESET}  (or: llamaui /path/to/model.gguf)"
echo -e "  llama-cli path   : ${BOLD}${SCRIPTS_DIR}/llama-cli${RESET}"
echo ""
echo -e "  ${YELLOW}Tip:${RESET} Download a GGUF model with:"
echo -e "  wget -P ${MODELS_DIR} https://huggingface.co/<repo>/<model>.gguf"
echo ""
echo -e "  Restart your Termux session (or run ${BOLD}source ~/.bashrc${RESET}) to refresh PATH."
echo ""
