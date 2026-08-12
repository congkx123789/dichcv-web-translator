#!/bin/bash
# Script khởi chạy Alida TSL C++ GPU REST API Server
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Đảm bảo binary C++ đã được build
if [ ! -f "./tsl_translator" ]; then
    echo "🔨 Building C++ Native Engine binary..."
    ./build.sh
fi

echo "🚀 Launching Alida TSL C++ GPU REST API Server (Port 8000)..."
python3 api_server.py
