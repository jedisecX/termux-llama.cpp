#!/data/data/com.termux/files/usr/bin/bash
# Auto-installer for llama.cpp in Termux
# Run with: bash install-llama.sh

set -e  # Exit on error

echo "🚀 JediSec Termux llama.cpp Auto-Installer"
echo "Updating Termux packages..."
pkg update -y && pkg upgrade -y

echo "Installing build dependencies..."
pkg install -y git clang cmake ninja python python-pip libandroid-spawn

echo "Creating workspace..."
mkdir -p \~/llama.cpp && cd \~/llama.cpp

if [ -d "llama.cpp" ]; then
  echo "Updating existing llama.cpp repo..."
  cd llama.cpp
  git pull
else
  echo "Cloning llama.cpp..."
  git clone https://github.com/ggerganov/llama.cpp.git
  cd llama.cpp
fi

echo "Building llama.cpp with optimizations for Android/Termux..."
cmake -B build -S . \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLAMA_NATIVE=OFF \
  -DLLAMA_OPENBLAS=ON \
  -DLLAMA_CUBLAS=OFF \
  -DLLAMA_METAL=OFF \
  -DLLAMA_VULKAN=OFF \
  -DGGML_OPENMP=ON

cmake --build build --config Release -j $(nproc) --target llama-server

echo "✅ Build complete! Creating symlinks..."
cp build/bin/llama-server \~/llama-server
chmod +x \~/llama-server

echo "Installing Python bindings (optional but recommended)..."
pip install llama-cpp-python --no-cache-dir --force-reinstall --no-deps

echo "🎉 Installation finished!"
echo "Test it:"
echo "  cd \~/llama.cpp"
echo "  ./build/bin/llama-server -m path/to/your/model.gguf -c 4096 --port 8080"
echo ""
echo "For your repo (termux-llama.cpp), you can now symlink or extend this."
echo "Pro tip: Use tmux or termux-wake-lock for background server."

# Optional: Create a quick start script
cat > \~/start-llama.sh << EOF
#!/bin/bash
cd \~/llama.cpp
./build/bin/llama-server -m \~/models/model.gguf --port 8080 --ctx-size 8192
EOF
chmod +x \~/start-llama.sh

echo "Quick start script created at \~/start-llama.sh"
