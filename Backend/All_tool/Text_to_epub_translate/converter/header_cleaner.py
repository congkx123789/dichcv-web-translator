import re
from typing import Dict, Any, Tuple

AD_PATTERNS = [
    r'爱下电子书.*',
    r'https?://[^\s]+',
    r'E-mail:[^\s]+',
    r'------章节内容开始-------',
    r'------章节内容结束-------',
    r'更多电子书请访问.*',
    r'TXT版阅读,下载和分享.*',
    r'本书由[^\s]+整理.*',
    r'\[\s*全本精校\s*\]',
]

def clean_and_extract_metadata(raw_text: str, default_title: str = "Untitled Novel") -> Tuple[Dict[str, Any], str]:
    """
    Parses novel metadata (Title, Author, Description, Status) from header lines,
    strips ads/promotional lines, and returns (metadata_dict, cleaned_body_text).
    """
    metadata = {
        "title": default_title.replace(".txt", "").strip(),
        "author": "Unknown",
        "status": "",
        "description": "",
        "language": "zh-CN",
    }

    lines = raw_text.splitlines()
    header_end_idx = 0
    in_desc = False
    desc_lines = []

    for i, line in enumerate(lines[:150]):  # Inspect first 150 lines for metadata
        stripped = line.strip()

        # Match header format 『书名/作者:xxx』 or 『书名』
        match_header = re.search(r'『([^/』]+)(?:/作者:([^』]+))?』', stripped)
        if match_header and not stripped.startswith('『状态:'):
            if metadata["title"] == default_title.replace(".txt", "").strip() or match_header.group(2):
                metadata["title"] = match_header.group(1).strip()
            if match_header.group(2):
                metadata["author"] = match_header.group(2).strip()
            header_end_idx = max(header_end_idx, i + 1)
            continue

        # Match status 『状态:xxx』
        match_status = re.search(r'『状态:([^』]+)』', stripped)
        if match_status:
            metadata["status"] = match_status.group(1).strip()
            header_end_idx = max(header_end_idx, i + 1)
            continue

        # Match author standalone: 作者：xxx or 作者: xxx
        match_author = re.search(r'^(?:作者|作\s*者)[：:]\s*(.+)', stripped)
        if match_author and metadata["author"] == "Unknown":
            metadata["author"] = match_author.group(1).strip()
            header_end_idx = max(header_end_idx, i + 1)
            continue

        # Match description start: 『内容简介: or 内容简介：
        if re.search(r'(?:『内容简介|内容简介|简介)[：:]', stripped):
            in_desc = True
            desc_start = stripped.partition('：')[-1] or stripped.partition(':')[-1]
            desc_start = desc_start.lstrip('『').strip()
            if desc_start:
                desc_lines.append(desc_start)
            header_end_idx = max(header_end_idx, i + 1)
            continue

        if in_desc:
            if stripped.endswith('』'):
                desc_lines.append(stripped[:-1].strip())
                in_desc = False
            elif stripped.startswith('------') or stripped.startswith('爱下'):
                in_desc = False
            else:
                desc_lines.append(stripped)
            header_end_idx = max(header_end_idx, i + 1)
            continue

        if '------章节内容开始-------' in stripped:
            header_end_idx = i + 1
            break

    if desc_lines:
        metadata["description"] = "\n".join(d for d in desc_lines if d.strip())

    # Process remaining text starting from after header
    body_lines = lines[header_end_idx:] if header_end_idx > 0 else lines

    # Clean ad patterns from lines
    cleaned_lines = []
    ad_regex = re.compile('|'.join(f'(?:{p})' for p in AD_PATTERNS), re.IGNORECASE)

    for line in body_lines:
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append("")
            continue
        
        # Check if line matches ad regex
        if ad_regex.search(stripped):
            continue

        cleaned_lines.append(line)

    cleaned_body = "\n".join(cleaned_lines)

    return metadata, cleaned_body
