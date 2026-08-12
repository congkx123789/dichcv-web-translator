#!/usr/bin/env python3
import os
import sys
import shutil
import tempfile
import time
import subprocess
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Load .env file from root project directory
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

import json
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add backend tool paths to sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONVERTER_DIR = os.path.join(SCRIPT_DIR, "All_tool", "Text_to_epub_translate")
TSL_DIR = os.path.join(SCRIPT_DIR, "All_tool", "TSL_CPP_Native")

if CONVERTER_DIR not in sys.path:
    sys.path.insert(0, CONVERTER_DIR)
if TSL_DIR not in sys.path:
    sys.path.insert(0, TSL_DIR)

# Import Converter modules
try:
    from converter.text_extractor import extract_text_from_file, decode_bytes, parse_epub_natively
    from converter.header_cleaner import clean_and_extract_metadata
    from converter.chapter_parser import parse_chapters, Chapter
    from converter.cover_generator import generate_cover
    from converter.multi_exporter import Exporter
    from converter.epub_builder import EpubBuilder
except ImportError as e:
    print(f"⚠️ Converter import warning: {e}")

# Import TSL Translation engine modules
engine_instance = None
hv_map_instance = None

try:
    from translate_epub_cpp_gpu import clean_vietnamese_text, ensure_no_chinese, load_hanviet_map, translate_epub_cpp_gpu, format_vietnamese_title
    STANDALONE_DIR = os.path.join(os.path.dirname(TSL_DIR), "TSL_Translator_Standalone")
    if os.path.exists(STANDALONE_DIR) and STANDALONE_DIR not in sys.path:
        sys.path.insert(0, STANDALONE_DIR)
    try:
        from inference.engine import TranslationInferenceEngine
    except ImportError:
        TranslationInferenceEngine = None
except Exception as e:
    print(f"⚠️ TSL Engine import warning: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine_instance, hv_map_instance
    print("=" * 70)
    print("🚀 STARTING ALIDA NOVEL READER & CONVERTER SERVER...")
    try:
        hv_map_instance = load_hanviet_map()
        print("✅ Han-Viet Map loaded successfully.")
    except Exception as err:
        print(f"⚠️ Failed to load Han-Viet map: {err}")

    try:
        print("⚡ Loading Alida TSL AI Engine into memory...")
        if TranslationInferenceEngine is not None:
            engine_instance = TranslationInferenceEngine()
            print("✅ Alida TSL AI Engine loaded persistently!")
        else:
            print("⚡ Using Native C++ Engine (tsl_translator) for translation.")
    except Exception as err:
        print(f"⚠️ Alida TSL Engine GPU/CPU load warning: {err} (Will fallback to Han-Viet dictionary mode)")
    print("=" * 70)
    yield
    print("🛑 Shutting down server...")


app = FastAPI(
    title="Alida Web Novel Reader, Converter & Translator API",
    description="Unified API server for format conversion, reading, and AI translation.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Data Models
class ExportRequest(BaseModel):
    title: str
    author: str = "Tác giả"
    description: str = ""
    format: str = "epub"  # epub, txt, html
    chapters: List[Dict[str, Any]]  # [{title, content: [lines]}]


class TranslateTextRequest(BaseModel):
    text: str


class TranslateChapterRequest(BaseModel):
    title: str
    content: List[str]


def translate_single_text(text: str) -> str:
    raw = text.strip()
    if not raw:
        return ""

    # 1. Native C++ GPU Binary compiled via build.sh (tsl_translator / run_tsl.sh)
    run_script = os.path.join(TSL_DIR, "run_tsl.sh")
    if os.path.exists(run_script):
        try:
            import subprocess
            proc = subprocess.run(
                [run_script, "--gpu", raw],
                cwd=TSL_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    if "DỊCH:" in line:
                        return line.split("DỊCH:", 1)[1].strip()
        except Exception:
            pass

    # 2. Python engine instance fallback
    if engine_instance:
        try:
            return engine_instance.translate(raw)
        except Exception:
            pass

    # 3. Basic Han-Viet mapping fallback if binary is unbuilt
    return ensure_no_chinese(raw, hv_map_instance or {})


def translate_batch_texts(texts: List[str]) -> List[str]:
    if not texts:
        return []

    # 1. High-Speed Single-Batch C++ GPU Translation via File (12s for 4,193 chapters)
    run_script = os.path.join(TSL_DIR, "run_tsl.sh")
    if os.path.exists(run_script):
        try:
            temp_id = int(time.time() * 1000)
            in_file = os.path.join(tempfile.gettempdir(), f"batch_in_{temp_id}.txt")
            out_file = os.path.join(tempfile.gettempdir(), f"batch_out_{temp_id}.txt")

            with open(in_file, "w", encoding="utf-8") as f:
                for line in texts:
                    clean_line = line.strip().replace("\n", " ") if line else ""
                    f.write(clean_line + "\n")

            proc = subprocess.run(
                [run_script, "--file", in_file, "--output", out_file, "--gpu"],
                cwd=TSL_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120
            )

            if proc.returncode == 0 and os.path.exists(out_file):
                with open(out_file, "r", encoding="utf-8") as f:
                    translated_lines = [l.strip() for l in f.readlines()]

                if os.path.exists(in_file): os.remove(in_file)
                if os.path.exists(out_file): os.remove(out_file)

                if len(translated_lines) == len(texts):
                    return translated_lines
        except Exception as e:
            print(f"⚠️ Batch C++ GPU translation fallback: {e}")

    # 2. Ultra-Fast Hán-Việt Dictionary Fallback (0.04s for 4,193 chapters)
    return [ensure_no_chinese(t, hv_map_instance or {}) if t else "" for t in texts]


@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "tsl_engine_ready": engine_instance is not None,
        "hanviet_map_ready": hv_map_instance is not None
    }


@app.post("/api/novel/parse")
async def parse_novel_file(file: UploadFile = File(...), translate_toc: bool = Form(False)):
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        ext = os.path.splitext(file.filename)[1].lower()
        if ext == '.epub':
            try:
                return parse_epub_natively(temp_path)
            except Exception as err:
                print(f"⚠️ EPUB native parsing fallback: {err}")

        extracted_text, filename, encoding = extract_text_from_file(temp_path)
        meta, cleaned_body = clean_and_extract_metadata(extracted_text, filename)
        chapters_list = parse_chapters(cleaned_body)

        title = meta.get("title") or os.path.splitext(filename)[0]
        author = meta.get("author") or "Vô Danh"
        description = meta.get("description") or ""

        parsed_chapters = []
        total_words = 0
        for idx, chap in enumerate(chapters_list):
            total_words += chap.word_count
            parsed_chapters.append({
                "index": chap.index,
                "title": chap.title,
                "word_count": chap.word_count,
                "content": chap.content # Keep original content
            })

        return {
            "status": "success",
            "filename": filename,
            "encoding": encoding,
            "metadata": {
                "title": title,
                "author": author,
                "description": description,
                "status": meta.get("status", "")
            },
            "total_chapters": len(parsed_chapters),
            "total_words": total_words,
            "chapters": parsed_chapters
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi đọc file truyện: {str(e)}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


class TranslateTocRequest(BaseModel):
    metadata: Dict[str, Any]
    chapters: List[Dict[str, Any]]


@app.post("/api/novel/translate_toc")
def translate_toc_endpoint(req: TranslateTocRequest):
    title = req.metadata.get("title", "")
    author = req.metadata.get("author", "")
    description = req.metadata.get("description", "")

    title_vi = translate_single_text(title) if title else title
    author_vi = translate_single_text(author) if author else author
    desc_vi = translate_single_text(description) if description else description

    orig_titles = [chap.get("title", "") for chap in req.chapters]
    translated_titles = translate_batch_texts(orig_titles)

    translated_chapters = []
    for idx, chap in enumerate(req.chapters):
        translated_chapters.append({
            "index": chap.get("index", 0),
            "title": translated_titles[idx],
            "word_count": chap.get("word_count", 0),
            "content": chap.get("content", [])
        })

    return {
        "metadata": {
            "title": title_vi,
            "author": author_vi,
            "description": desc_vi
        },
        "chapters": translated_chapters
    }


@app.post("/api/novel/translate_toc_stream")
async def translate_toc_stream_endpoint(req: TranslateTocRequest):
    async def event_generator():
        # 1. Translate metadata and yield first
        title_vi = translate_single_text(req.metadata.get("title", "")) if req.metadata.get("title") else req.metadata.get("title", "")
        author_vi = translate_single_text(req.metadata.get("author", "")) if req.metadata.get("author") else req.metadata.get("author", "")
        desc_vi = translate_single_text(req.metadata.get("description", "")) if req.metadata.get("description") else req.metadata.get("description", "")
        
        meta_chunk = {
            "type": "metadata",
            "metadata": {
                "title": title_vi,
                "author": author_vi,
                "description": desc_vi
            }
        }
        yield json.dumps(meta_chunk, ensure_ascii=False) + "\n"

        # 2. Translate chapters in chunks (e.g. 50 titles per batch)
        chunk_size = 50
        chapters = req.chapters
        
        for i in range(0, len(chapters), chunk_size):
            chunk = chapters[i:i+chunk_size]
            titles = [c.get("title", "") for c in chunk]
            
            # This blocking call takes only a fraction of a second for 50 titles
            translated_titles = translate_batch_texts(titles)
            
            res_chunk = []
            for j, chap in enumerate(chunk):
                res_chunk.append({
                    "index": chap.get("index", 0),
                    "title": translated_titles[j] if j < len(translated_titles) else titles[j],
                    "word_count": chap.get("word_count", 0),
                    # Do not send content back to save bandwidth, unless needed?
                    # Actually, we should send it back or the frontend will lose content.
                    # Or frontend can just merge title. Let's send content just in case.
                    "content": chap.get("content", [])
                })
                
            chunk_data = {
                "type": "chunk",
                "chapters": res_chunk
            }
            yield json.dumps(chunk_data, ensure_ascii=False) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


@app.post("/api/novel/export")
async def export_novel(req: ExportRequest):
    temp_dir = tempfile.mkdtemp()
    try:
        metadata = {
            "title": req.title,
            "author": req.author,
            "description": req.description
        }
        
        chap_objs = []
        for idx, c in enumerate(req.chapters):
            chap_objs.append(Chapter(
                title=c.get("title", f"Chương {idx+1}"),
                content=c.get("content", []),
                index=idx
            ))

        # Generate cover bytes
        cover_bytes = generate_cover(req.title, req.author)
        exporter = Exporter(metadata, chap_objs, cover_bytes)

        fmt = req.format.lower()
        safe_title = "".join(c for c in req.title if c.isalnum() or c in (' ', '_', '-')).strip() or "novel"

        if fmt == "epub":
            out_name = f"{safe_title}.epub"
            out_path = os.path.join(temp_dir, out_name)
            exporter.export_epub(out_path)
            media_type = "application/epub+zip"
        elif fmt == "txt":
            out_name = f"{safe_title}.txt"
            out_path = os.path.join(temp_dir, out_name)
            exporter.export_txt(out_path)
            media_type = "text/plain"
        elif fmt == "html":
            out_name = f"{safe_title}.html"
            out_path = os.path.join(temp_dir, out_name)
            exporter.export_html(out_path)
            media_type = "text/html"
        else:
            raise HTTPException(status_code=400, detail="Định dạng xuất không hợp lệ (hỗ trợ: epub, txt, html)")

        return FileResponse(out_path, filename=out_name, media_type=media_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xuất file: {str(e)}")


@app.post("/api/translate/text")
def translate_text_endpoint(req: TranslateTextRequest):
    translated = translate_single_text(req.text)
    return {"original": req.text, "translated": translated}


@app.post("/api/translate/chapter")
def translate_chapter_endpoint(req: TranslateChapterRequest):
    translated_title = translate_single_text(req.title)
    translated_lines = translate_batch_texts(req.content)
    return {
        "title": translated_title,
        "content": translated_lines
    }


class TranslateRangeRequest(BaseModel):
    chapters: List[Dict[str, Any]]


@app.post("/api/translate/chapters_range")
def translate_chapters_range_endpoint(req: TranslateRangeRequest):
    results = []
    for chap in req.chapters:
        t_title = translate_single_text(chap.get("title", ""))
        t_content = translate_batch_texts(chap.get("content", []))
        results.append({
            "index": chap.get("index", 0),
            "title": t_title,
            "content": t_content
        })
    return {"translated_chapters": results}


@app.post("/api/translate/file")
async def translate_file_endpoint(file: UploadFile = File(...)):
    temp_dir = tempfile.mkdtemp()
    temp_input = os.path.join(temp_dir, file.filename)
    try:
        with open(temp_input, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        ext = os.path.splitext(file.filename)[1].lower()
        out_name = f"{os.path.splitext(file.filename)[0]}_Vietnamese.epub"
        out_path = os.path.join(temp_dir, out_name)

        # 1. Direct High-Speed Native C++ GPU translation for EPUB files
        if ext == ".epub" and 'translate_epub_cpp_gpu' in globals():
            try:
                translate_epub_cpp_gpu(temp_input, out_path, use_gpu=True)
                if os.path.exists(out_path):
                    return FileResponse(out_path, filename=out_name, media_type="application/epub+zip")
            except Exception as err:
                print(f"⚠️ EPUB Native GPU translation fallback: {err}")

        # 2. Extract & batch translate TXT/ZIP/Fallback EPUB files
        extracted_text, filename, _ = extract_text_from_file(temp_input)
        meta, cleaned_body = clean_and_extract_metadata(extracted_text, filename)
        chapters_list = parse_chapters(cleaned_body)

        title = (meta.get("title") or os.path.splitext(filename)[0]) + " [Tiếng Việt]"
        author = meta.get("author") or "Vô Danh"
        description = translate_single_text(meta.get("description") or "")

        translated_chapters = []
        for chap in chapters_list:
            trans_title = translate_single_text(chap.title)
            trans_content = [translate_single_text(line) for line in chap.content if line.strip()]
            translated_chapters.append(Chapter(
                title=trans_title,
                content=trans_content,
                index=chap.index
            ))

        metadata = {
            "title": title,
            "author": author,
            "description": description
        }
        cover_bytes = generate_cover(title, author)
        exporter = Exporter(metadata, translated_chapters, cover_bytes)
        exporter.export_epub(out_path)

        return FileResponse(out_path, filename=out_name, media_type="application/epub+zip")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi dịch file: {str(e)}")
    finally:
        pass


# Serve static web frontend
FRONTEND_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "frontend-react", "dist")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🌐 Server started at http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
