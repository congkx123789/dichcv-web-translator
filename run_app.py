#!/usr/bin/env python3
"""
Launcher script for Alida Web Novel Reader, Converter & Translator Studio.
"""
import os
import sys
import uvicorn

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(SCRIPT_DIR, "Backend")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("=" * 70)
    print("🚀 LAUNCHING ALIDA WEB NOVEL READER & CONVERTER STUDIO")
    print(f"🌐 Access Web Reader app at: http://localhost:{port}")
    print("=" * 70)
    uvicorn.run("Backend.web_server:app", host="0.0.0.0", port=port, reload=False)
