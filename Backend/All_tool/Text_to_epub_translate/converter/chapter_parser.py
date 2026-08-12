import re
from typing import List, Dict, Any

CHAPTER_REGEX = re.compile(
    r'^\s*(?:'
    r'(?:[【\[\(（]?\s*[0-9０-９]+(?:\.[0-9０-９]+)*\s*[】\]\)）]?[\.．、,，:：\-_—\s]*)?'
    r'(?:第|Chương|Chuong|Tập|Hồi|Quyển|Quyển\s+)[0-9一二三四五六七八九十百千万零两0-9０-９a-zA-Z\s\-]+[章卷回折篇集]?.*'
    r'|'
    r'(?:[【\[\(（]?\s*[0-9０-９]+(?:\.[0-9０-９]+)*\s*[】\]\)）]?[\.．、,，:：\-_—\s]*)?'
    r'(?:序章|前言|楔子|后记|尾声|番外篇?|完本感言|作品相关|设定说明|致读者|写在前面|Mở đầu|Lời nói đầu|Hậu ký|Ngoại truyện).*'
    r'|'
    r'(?:卷|Volume|Book|Part)\s*[0-9一二三四五六七八九十0-9]+\s*.*'
    r'|'
    r'(?:[【\[\(（]?\s*[0-9０-９]+(?:\.[0-9０-９]+)*\s*[】\]\)）]?[\.．、,，:：\-_—\s]*)?'
    r'(?:Chapter|Chap)\s+\d+.*'
    r'|'
    r'^\s*[0-9０-９]{1,4}[\.．、:：\s]+\S+.*'
    r')\s*$',
    re.IGNORECASE
)

class Chapter:
    def __init__(self, title: str, content: List[str], index: int):
        self.title = clean_chapter_title(title)
        self.content = content  # list of strings (paragraphs)
        self.index = index

    @property
    def word_count(self) -> int:
        return sum(len(line) for line in self.content)

def clean_chapter_title(title: str) -> str:
    title = title.strip()
    # Strip leading redundant index numbers before explicit chapter/volume keywords
    # Matches "1.", "12.", "001.", "1.1" etc.
    pattern = (
        r'^\s*(?:[【\[\(（]?\s*[0-9０-９A-Za-z]+(?:\.[0-9０-９A-Za-z]+)*\s*[】\]\)）]?[\.．、,，:：\-_—\s]*)+'
        r'(?=(?:第\s*[0-9一二三四五六七八九十百千万零两0-9０-９a-zA-Z\s\-]+[章卷回折篇集]|'
        r'Chương|Chuong|Tập|Hồi|Quyển|Chapter|Chap|'
        r'序章|前言|楔子|后记|尾声|番外篇?|完本感言|作品相关|设定说明|致读者|写在前面|Mở đầu|Lời nói đầu|Hậu ký|Ngoại truyện|'
        r'卷\s*[0-9一二三四五六七八九十0-9]+))'
    )
    cleaned = re.sub(pattern, '', title, flags=re.IGNORECASE).strip()
    
    # Deduplicate repeated chapter header prefixes (e.g., "第1章 第1章 xxx", "Chương 1 Chương 1 xxx")
    cleaned = re.sub(r'^((?:第[0-9一二三四五六七八九十百千万零两a-zA-Z0-9\s\-]+[章卷回折篇集]|Chương\s+\d+|Chapter\s+\d+))\s+\1', r'\1', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    
    # TRUNCATE excessively long chapter titles
    # Often, text without proper newlines gets lumped into a chapter title.
    # A typical chapter title rarely exceeds 50 characters.
    max_title_length = 50
    if len(cleaned) > max_title_length:
        cleaned = cleaned[:max_title_length] + "..."
        
    return cleaned

def parse_chapters(cleaned_body: str) -> List[Chapter]:
    """
    Parses cleaned body text into a list of Chapter objects.
    """
    lines = cleaned_body.splitlines()
    chapters: List[Chapter] = []
    
    current_title = "Mở đầu / Giới thiệu"
    current_lines: List[str] = []
    chapter_index = 0

    for line in lines:
        stripped = line.strip()
        
        # Check if line is a chapter header
        if CHAPTER_REGEX.match(stripped):
            # Save previous chapter if it has content
            if current_lines:
                # Remove empty trailing lines
                while current_lines and not current_lines[-1].strip():
                    current_lines.pop()
                if current_lines:
                    chapters.append(Chapter(
                        title=current_title,
                        content=current_lines,
                        index=chapter_index
                    ))
                    chapter_index += 1
            
            current_title = stripped
            current_lines = []
        else:
            current_lines.append(line)

    # Append remaining lines
    if current_lines:
        while current_lines and not current_lines[-1].strip():
            current_lines.pop()
        if current_lines:
            chapters.append(Chapter(
                title=current_title,
                content=current_lines,
                index=chapter_index
            ))

    # If no chapters were detected by regex, fall back to fixed line chunks or entire book as single chapter
    if len(chapters) <= 1 and len(lines) > 200:
        # Fallback: attempt looser regex or auto-split by line count if needed
        loose_regex = re.compile(r'^\s*[0-9０-９]+[\.．、,，:：\-_—\s]+.+')
        chapters = []
        current_title = "Chương 1"
        current_lines = []
        chapter_index = 0
        for line in lines:
            stripped = line.strip()
            if loose_regex.match(stripped):
                if current_lines:
                    chapters.append(Chapter(title=current_title, content=current_lines, index=chapter_index))
                    chapter_index += 1
                current_title = stripped
                current_lines = []
            else:
                current_lines.append(line)
        if current_lines:
            chapters.append(Chapter(title=current_title, content=current_lines, index=chapter_index))

    return chapters
