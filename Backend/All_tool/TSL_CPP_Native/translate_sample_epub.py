#!/usr/bin/env python3
"""
Sample 5-Chapter EPUB Translator for instant inspection.
Translates Chapters 1-5 + TOC (toc.ncx) + Metadata (content.opf) in 2 seconds.
"""

import sys
import os
import re
import time
import zipfile
import subprocess
import struct

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

BRACKET_CHARS = ["(", ")", "[", "]", "{", "}", "『", "』", "【", "】", "〔", "〕", "［", "］", "《", "》", "“", "”", "‘", "’", "\"", "`", "‹", "›", "«", "»"]
SYMBOLS_TO_STRIP = ["----", "---", "--", "—", "·", "•", "▪", "▫", "_", "=", "|", "\\", "*", "#", "@", "$", "^", "&"]

CN_PUNCT_MAP = {
    "。": ". ",
    "，": ", ",
    "：": ": ",
    "；": "; ",
    "！": "! ",
    "？": "? ",
    "……": "... ",
    "…": "... ",
}

def clean_vietnamese_text(text):
    for cn, vi in CN_PUNCT_MAP.items():
        text = text.replace(cn, vi)
    for b in BRACKET_CHARS:
        text = text.replace(b, " ")
    for s in SYMBOLS_TO_STRIP:
        text = text.replace(s, " ")
    text = re.sub(r"\s+([\.,!\?:;])", r"\1", text)
    text = re.sub(r"[\.,!\?:;]{2,}", lambda m: m.group(0)[0], text)
    text = re.sub(r" +", " ", text)
    return text.strip()

def ensure_no_chinese(text, hv_map):
    text = clean_vietnamese_text(text)
    if re.search(r'[\u4e00-\u9fff]', text):
        res = []
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                hv = hv_map.get(char, char)
                res.append(hv.split('/')[0] if hv else char)
            else:
                res.append(char)
        return clean_vietnamese_text("".join(res))
    return text

def load_hanviet_map():
    hv_dict = {}
    hv_path = os.path.join(SCRIPT_DIR, "data", "hanviet.bin")
    if os.path.exists(hv_path):
        with open(hv_path, "rb") as f:
            num_entries = struct.unpack("<I", f.read(4))[0]
            for _ in range(num_entries):
                k_len = struct.unpack("<H", f.read(2))[0]
                key = f.read(k_len).decode("utf-8")
                v_len = struct.unpack("<H", f.read(2))[0]
                val = f.read(v_len).decode("utf-8")
                hv_dict[key] = val
    return hv_dict

def translate_sample_epub(input_epub, output_epub, max_chapters=5):
    print("=" * 80)
    print(f"🚀 ALIDA TSL NATIVE C++ GPU SAMPLE TRANSLATOR ({max_chapters} CHAPTER TEST)")
    print("=" * 80)

    t0 = time.time()
    hv_map = load_hanviet_map()

    with zipfile.ZipFile(input_epub, 'r') as z_in:
        all_file_names = z_in.namelist()
        file_contents = {fname: z_in.read(fname) for fname in all_file_names}

    text_exts = ('.xhtml', '.html', '.htm', '.opf', '.ncx', '.xml')
    cjk_pattern = re.compile(r'[\u4e00-\u9fff]')
    tag_pattern = re.compile(r'>([^<>]+)<')

    # Identify exact HTML chapter files 1 to 5
    target_chapters = [f"chap_{i}.xhtml" for i in range(1, max_chapters + 1)]
    test_html_set = set()
    for fname in all_file_names:
        for tch in target_chapters:
            if fname.endswith(tch):
                test_html_set.add(fname)

    # Add TOC and OPF files to target list
    target_files = [f for f in all_file_names if f.endswith(('.opf', '.ncx')) or f in test_html_set]

    all_snippets = []
    snippet_locations = []

    for fname in target_files:
        data = file_contents[fname]
        text_str = data.decode('utf-8', errors='ignore')
        for m in tag_pattern.finditer(text_str):
            inner_text = m.group(1)
            if cjk_pattern.search(inner_text):
                clean_text = inner_text.strip()
                if clean_text:
                    all_snippets.append(clean_text)
                    snippet_locations.append((fname, m.start(1), m.end(1), inner_text))

    print(f"📌 Found {len(all_snippets):,} Chinese text snippets across first {max_chapters} chapters + TOC.")

    if not all_snippets:
        print("⚠️ No snippets found.")
        return

    inp_txt_path = os.path.join(SCRIPT_DIR, "tmp_sample_input.txt")
    out_txt_path = os.path.join(SCRIPT_DIR, "tmp_sample_output.txt")

    with open(inp_txt_path, "w", encoding="utf-8") as f:
        for snip in all_snippets:
            clean_snip = snip.replace("\r", " ").replace("\n", " ")
            f.write(f"{clean_snip}\n")

    cmd = [
        os.path.join(SCRIPT_DIR, "run_tsl.sh"),
        "--file", inp_txt_path,
        "--output", out_txt_path,
        "--gpu"
    ]

    t_cpp_start = time.time()
    res_proc = subprocess.run(cmd, cwd=SCRIPT_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    t_cpp_el = time.time() - t_cpp_start
    print(f"⚡ C++ GPU Engine completed sample batch in {t_cpp_el:.2f}s")

    with open(out_txt_path, "r", encoding="utf-8") as f:
        translated_lines = [line.strip() for line in f]

    file_replacements = {}
    for (fname, start, end, inner_text), raw_trans in zip(snippet_locations, translated_lines):
        clean_trans = ensure_no_chinese(raw_trans, hv_map)
        if fname not in file_replacements:
            file_replacements[fname] = []
        file_replacements[fname].append((start, end, clean_trans))

    output_contents = {}
    for fname, data in file_contents.items():
        if fname in file_replacements:
            text_str = data.decode('utf-8', errors='ignore')
            repls = sorted(file_replacements[fname], key=lambda x: x[0], reverse=True)
            text_list = list(text_str)
            for start, end, vi_trans in repls:
                text_list[start:end] = list(vi_trans)

            modified_text = "".join(text_list)
            modified_text = ensure_no_chinese(modified_text, hv_map)
            output_contents[fname] = modified_text.encode('utf-8')
        else:
            output_contents[fname] = data

    print(f"💾 Repacking test EPUB: {output_epub}...")
    with zipfile.ZipFile(output_epub, 'w', zipfile.ZIP_DEFLATED) as z_out:
        for fname, data in output_contents.items():
            z_out.writestr(fname, data)

    for tmp_f in [inp_txt_path, out_txt_path]:
        if os.path.exists(tmp_f):
            os.remove(tmp_f)

    print("=" * 80)
    print(f"✅ TEST EPUB GENERATED IN {time.time() - t0:.2f} SECONDS!")
    print(f"📦 Test File: {output_epub}")
    print("=" * 80)

if __name__ == '__main__':
    inp = "/home/alida/Documents/My_model_translate/epub/抓住那个魔修.epub"
    out = "/home/alida/Documents/My_model_translate/test_chap1_5.epub"
    translate_sample_epub(inp, out, max_chapters=5)
