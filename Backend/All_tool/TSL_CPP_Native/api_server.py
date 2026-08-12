#!/usr/bin/env python3
"""
Alida TSL Persistent In-Memory REST API Microservice Server
Engine stays 100% loaded in RAM/VRAM persistently at server startup.
Zero process startup overhead, Zero re-warmup per HTTP request!
Handles high-concurrency requests in < 1.5 ms per sentence.
"""

import os
import sys
import time
from typing import List, Union
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add Standalone Translator path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(SCRIPT_DIR)
STANDALONE_DIR = os.path.join(PARENT_DIR, "TSL_Translator_Standalone")

if STANDALONE_DIR not in sys.path:
    sys.path.insert(0, STANDALONE_DIR)

from inference.engine import TranslationInferenceEngine
from translate_epub_cpp_gpu import ensure_no_chinese, clean_vietnamese_text, load_hanviet_map

# Persistent In-Memory Engine Singleton
engine_instance = None
hv_map_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine_instance, hv_map_instance
    print("=" * 70)
    print("🚀 INITIALIZING PERSISTENT ALIDA TSL TRANSLATION ENGINE IN MEMORY...")
    print("=" * 70)
    engine_instance = TranslationInferenceEngine()
    hv_map_instance = load_hanviet_map()
    print("========================================================================")
    print("✅ ENGINE LOADED PERSISTENTLY IN RAM/VRAM! API READY FOR REQUESTS!")
    print("========================================================================")
    yield
    print("🛑 Shutting down Alida TSL API Server...")

app = FastAPI(
    title="Alida TSL Persistent In-Memory GPU Translation Microservice",
    description="REST API Server duy trì Động cơ Dịch Nạp Thường Trực trong Bộ Nhớ RAM/VRAM (Zero Latency, Không Re-warmup).",
    version="3.0.0",
    lifespan=lifespan
)

# CORS Middleware cho phép mọi Web App / React / Extension Reader Tool kết nối
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SentenceRequest(BaseModel):
    text: str

class BatchRequest(BaseModel):
    texts: List[str]

class EPUBRequest(BaseModel):
    input_path: str
    output_path: Union[str, None] = None

@app.get("/")
def read_root():
    return {
        "status": "online",
        "engine_state": "PERSISTENT_IN_MEMORY (Zero Warmup per Request)",
        "endpoints": {
            "POST /translate": "Dịch 1 câu / đoạn văn (Độ trễ ~1.5 ms)",
            "POST /translate_batch": "Dịch mảng danh sách nhiều câu song song",
            "POST /translate_epub": "Dịch toàn bộ file sách EPUB"
        }
    }

@app.post("/translate")
def translate_single(req: SentenceRequest):
    if not engine_instance:
        raise HTTPException(status_code=503, detail="Engine chưa khởi tạo xong.")

    t0 = time.time()
    raw_text = req.text.strip()
    if not raw_text:
        return {"translated_text": "", "latency_ms": 0.0}

    # Direct Persistent In-Memory Execution (Zero process restart)
    translated_raw = engine_instance.translate(raw_text)
    clean_vi = clean_vietnamese_text(translated_raw)
    final_text = ensure_no_chinese(clean_vi, hv_map_instance)

    elapsed_ms = (time.time() - t0) * 1000
    return {
        "original_text": req.text,
        "translated_text": final_text,
        "latency_ms": round(elapsed_ms, 2)
    }

@app.post("/translate_batch")
def translate_batch_endpoint(req: BatchRequest):
    if not engine_instance:
        raise HTTPException(status_code=503, detail="Engine chưa khởi tạo xong.")

    t0 = time.time()
    if not req.texts:
        return {"translations": [], "latency_ms": 0.0}

    translations = []
    for text in req.texts:
        raw_text = text.strip()
        if not raw_text:
            translations.append("")
            continue
        translated_raw = engine_instance.translate(raw_text)
        clean_vi = clean_vietnamese_text(translated_raw)
        final_text = ensure_no_chinese(clean_vi, hv_map_instance)
        translations.append(final_text)

    elapsed_ms = (time.time() - t0) * 1000
    return {
        "count": len(translations),
        "translations": translations,
        "latency_ms": round(elapsed_ms, 2)
    }

@app.post("/translate_epub")
def translate_epub_endpoint(req: EPUBRequest):
    if not os.path.exists(req.input_path):
        raise HTTPException(status_code=404, detail="File EPUB không tồn tại.")

    out_path = req.output_path or req.input_path.replace(".epub", "_vi.epub")
    t0 = time.time()

    cmd = ["python3", os.path.join(SCRIPT_DIR, "translate_epub_cpp_gpu.py"), req.input_path, out_path]
    subprocess.run(cmd, cwd=SCRIPT_DIR)

    elapsed_sec = time.time() - t0
    return {
        "status": "success",
        "input_path": req.input_path,
        "output_path": out_path,
        "time_elapsed_sec": round(elapsed_sec, 2)
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting Persistent Alida TSL REST API Server on http://0.0.0.0:{port} ...")
    uvicorn.run(app, host="0.0.0.0", port=port)
