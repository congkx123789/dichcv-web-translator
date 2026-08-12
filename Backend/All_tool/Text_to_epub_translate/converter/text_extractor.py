import os
import zipfile
from typing import Tuple

ENCODING_CANDIDATES = [
    'gb18030',
    'gbk',
    'utf-8-sig',
    'utf-8',
    'big5',
    'utf-16-le',
    'utf-16-be',
    'utf-16',
]

def decode_bytes(raw_bytes: bytes) -> Tuple[str, str]:
    """
    Attempts to decode raw bytes using candidate Chinese and Unicode encodings.
    Returns (decoded_text, encoding_used).
    """
    for enc in ENCODING_CANDIDATES:
        try:
            text = raw_bytes.decode(enc)
            # Basic sanity check: check if null characters are excessive
            if text.count('\x00') < len(text) * 0.01:
                return text, enc
        except (UnicodeDecodeError, ValueError):
            continue
            
    # Fallback with error replacement
    return raw_bytes.decode('gb18030', errors='replace'), 'gb18030 (fallback)'

def clean_html_text(raw_html: str) -> str:
    """
    Cleans raw HTML/XHTML code from EPUB/ZIP files, removing scripts, styles,
    xml declarations, and converting HTML block tags into clean linebreaks.
    """
    import re
    import html
    # 1. Remove script, style, head, and xml/doctype tags completely
    text = re.sub(r'<(?:script|style|head|xml)[^>]*>.*?</(?:script|style|head|xml)>', '', raw_html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<\?xml.*?\?>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<!DOCTYPE.*?>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)

    # 2. Replace paragraph, heading, list, break tags with newlines
    text = re.sub(r'</?(?:p|div|h[1-6]|br|li|blockquote|tr|section|article)[^>]*>', '\n', text, flags=re.IGNORECASE)

    # 3. Strip all remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # 4. Unescape HTML entities (&nbsp;, &gt;, &lt;, &#...;)
    text = html.unescape(text)

    # 5. Clean full-width Chinese spaces, non-breaking spaces, zero-width spaces
    text = text.replace('\u3000', ' ').replace('\xa0', ' ').replace('\u200b', '')

    # 6. Normalize lines
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def get_epub_spine_files(zf: zipfile.ZipFile) -> list:
    """
    Parses container.xml and content.opf to return text files in spine reading order.
    """
    try:
        import xml.etree.ElementTree as ET
        if 'META-INF/container.xml' in zf.namelist():
            container_bytes = zf.read('META-INF/container.xml')
            container_root = ET.fromstring(container_bytes)
            opf_path = None
            for rootfile in container_root.findall('.//{*}rootfile'):
                opf_path = rootfile.attrib.get('full-path')
                if opf_path:
                    break
            
            if opf_path and opf_path in zf.namelist():
                opf_bytes = zf.read(opf_path)
                opf_root = ET.fromstring(opf_bytes)
                opf_dir = os.path.dirname(opf_path)
                
                manifest = {}
                for item in opf_root.findall('.//{*}manifest/{*}item'):
                    item_id = item.attrib.get('id')
                    href = item.attrib.get('href')
                    if item_id and href:
                        full_href = os.path.normpath(os.path.join(opf_dir, href)).replace('\\', '/')
                        manifest[item_id] = full_href
                
                spine_files = []
                for itemref in opf_root.findall('.//{*}spine/{*}itemref'):
                    idref = itemref.attrib.get('idref')
                    if idref in manifest:
                        target_file = manifest[idref]
                        if target_file in zf.namelist() and target_file.lower().endswith(('.xhtml', '.html', '.htm', '.txt')):
                            spine_files.append(target_file)
                
                if spine_files:
                    return spine_files
    except Exception as e:
        print(f"⚠️ EPUB spine parsing warning: {e}")
    
    files = [f for f in zf.namelist() if f.lower().endswith(('.xhtml', '.html', '.htm', '.txt')) and not f.startswith('__MACOSX/')]
    files.sort()
    return files


def extract_text_from_file(file_path: str) -> Tuple[str, str, str]:
    """
    Extracts text from a given file path (.zip, .epub, or .txt).
    Returns (extracted_text, filename_or_entry_name, encoding_used).
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.epub':
        with zipfile.ZipFile(file_path, 'r') as zf:
            text_files = get_epub_spine_files(zf)
            extracted_chunks = []
            for tf in text_files:
                raw = zf.read(tf)
                raw_txt, _ = decode_bytes(raw)
                clean_txt = clean_html_text(raw_txt)
                if clean_txt:
                    extracted_chunks.append(clean_txt)
            combined_text = "\n\n".join(extracted_chunks)
            return combined_text, os.path.basename(file_path), 'utf-8 (EPUB)'

    elif ext == '.zip':
        with zipfile.ZipFile(file_path, 'r') as zf:
            namelist = zf.namelist()
            txt_files = [f for f in namelist if f.lower().endswith(('.txt', '.xhtml', '.html', '.htm', '.md')) and not f.startswith('__MACOSX/')]
            if not txt_files:
                txt_files = [f for f in namelist if not zf.getinfo(f).is_dir() and not f.startswith('__MACOSX/')]
            
            if not txt_files:
                raise ValueError("No readable text files found in ZIP archive.")

            txt_files.sort()

            combined_chunks = []
            encodings_used = set()
            for tf in txt_files:
                raw_bytes = zf.read(tf)
                decoded_text, enc = decode_bytes(raw_bytes)
                encodings_used.add(enc)
                if tf.lower().endswith(('.xhtml', '.html', '.htm')):
                    clean_txt = clean_html_text(decoded_text)
                else:
                    clean_txt = decoded_text.replace('\u3000', ' ').replace('\xa0', ' ').strip()
                
                if clean_txt:
                    combined_chunks.append(clean_txt)
            
            combined_text = "\n\n".join(combined_chunks)
            return combined_text, os.path.basename(file_path), ", ".join(encodings_used)

    # Fallback for direct text files (.txt, .raw, etc.)
    with open(file_path, 'rb') as f:
        raw_bytes = f.read()
    decoded_text, enc = decode_bytes(raw_bytes)
    return decoded_text, os.path.basename(file_path), enc


def parse_epub_natively(file_path: str) -> dict:
    """
    Parses an EPUB file directly using OPF metadata and spine/TOC structure.
    Returns structured dict with metadata, total_chapters, total_words, and chapters array.
    """
    import xml.etree.ElementTree as ET
    import re
    import html

    with zipfile.ZipFile(file_path, 'r') as zf:
        if 'META-INF/container.xml' not in zf.namelist():
            raise ValueError("File EPUB không đúng cấu trúc (thiếu META-INF/container.xml)")

        container_bytes = zf.read('META-INF/container.xml')
        container_root = ET.fromstring(container_bytes)
        opf_path = None
        for rootfile in container_root.findall('.//{*}rootfile'):
            opf_path = rootfile.attrib.get('full-path')
            if opf_path:
                break

        if not opf_path or opf_path not in zf.namelist():
            raise ValueError("File EPUB không đúng cấu trúc (thiếu file content.opf)")

        opf_bytes = zf.read(opf_path)
        opf_root = ET.fromstring(opf_bytes)
        opf_dir = os.path.dirname(opf_path)

        # 1. Extract Metadata from OPF (Dublin Core)
        title = None
        author = None
        description = None

        for dc_title in opf_root.findall('.//{*}title'):
            if dc_title.text and dc_title.text.strip():
                title = dc_title.text.strip()
                break

        for dc_creator in opf_root.findall('.//{*}creator'):
            if dc_creator.text and dc_creator.text.strip():
                author = dc_creator.text.strip()
                break

        for dc_desc in opf_root.findall('.//{*}description'):
            if dc_desc.text and dc_desc.text.strip():
                description = dc_desc.text.strip()
                break

        filename = os.path.basename(file_path)
        title = title or os.path.splitext(filename)[0]
        author = author or "Vô Danh"
        description = description or ""

        # 2. Build Manifest & Spine Map
        manifest = {}
        ncx_path = None
        for item in opf_root.findall('.//{*}manifest/{*}item'):
            item_id = item.attrib.get('id')
            href = item.attrib.get('href')
            media_type = item.attrib.get('media-type', '')
            if item_id and href:
                full_href = os.path.normpath(os.path.join(opf_dir, href)).replace('\\', '/')
                manifest[item_id] = full_href
                if 'ncx' in media_type or href.lower().endswith('.ncx'):
                    ncx_path = full_href

        spine_files = []
        for itemref in opf_root.findall('.//{*}spine/{*}itemref'):
            idref = itemref.attrib.get('idref')
            if idref in manifest:
                target_file = manifest[idref]
                if target_file in zf.namelist() and target_file.lower().endswith(('.xhtml', '.html', '.htm', '.txt')):
                    spine_files.append(target_file)

        if not spine_files:
            spine_files = [f for f in zf.namelist() if f.lower().endswith(('.xhtml', '.html', '.htm', '.txt')) and not f.startswith('__MACOSX/')]
            spine_files.sort()

        # 3. Read toc.ncx for Chapter Titles if available
        toc_titles = {}
        if ncx_path and ncx_path in zf.namelist():
            try:
                ncx_bytes = zf.read(ncx_path)
                ncx_root = ET.fromstring(ncx_bytes)
                ncx_dir = os.path.dirname(ncx_path)
                for navpoint in ncx_root.findall('.//{*}navPoint'):
                    text_node = navpoint.find('.//{*}text')
                    content_node = navpoint.find('.//{*}content')
                    if text_node is not None and content_node is not None:
                        t_text = text_node.text.strip() if text_node.text else ""
                        c_src = content_node.attrib.get('src', '')
                        if c_src:
                            clean_src = c_src.split('#')[0]
                            full_src = os.path.normpath(os.path.join(ncx_dir, clean_src)).replace('\\', '/')
                            if full_src and t_text:
                                toc_titles[full_src] = t_text
            except Exception as e:
                print(f"⚠️ Warning reading toc.ncx: {e}")

        # 4. Extract Chapters
        chapters = []
        total_words = 0

        for sf in spine_files:
            raw_bytes = zf.read(sf)
            raw_txt, _ = decode_bytes(raw_bytes)
            
            extracted_title = None
            if sf in toc_titles:
                extracted_title = toc_titles[sf]
            else:
                h_match = re.search(r'<h[1-3][^>]*>(.*?)</h[1-3]>', raw_txt, re.IGNORECASE | re.DOTALL)
                if h_match:
                    extracted_title = re.sub(r'<[^>]+>', '', h_match.group(1)).strip()
                else:
                    t_match = re.search(r'<title[^>]*>(.*?)</title>', raw_txt, re.IGNORECASE | re.DOTALL)
                    if t_match:
                        extracted_title = re.sub(r'<[^>]+>', '', t_match.group(1)).strip()

            clean_body = clean_html_text(raw_txt)
            lines = [l.strip() for l in clean_body.splitlines() if l.strip()]

            if not lines:
                continue

            if not extracted_title or len(extracted_title) > 60 or extracted_title.lower() in ('untitled', 'chapter', 'document', 'index'):
                extracted_title = lines[0] if lines else f"Chương {len(chapters) + 1}"

            extracted_title = html.unescape(extracted_title).strip()
            word_count = sum(len(line) for line in lines)
            total_words += word_count

            chapters.append({
                "index": len(chapters),
                "title": extracted_title,
                "word_count": word_count,
                "content": lines
            })

        return {
            "status": "success",
            "filename": filename,
            "encoding": "utf-8 (EPUB Native)",
            "metadata": {
                "title": title,
                "author": author,
                "description": description,
                "status": ""
            },
            "total_chapters": len(chapters),
            "total_words": total_words,
            "chapters": chapters
        }


