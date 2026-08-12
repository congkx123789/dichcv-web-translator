import os
import zipfile
import uuid
import datetime
import html
from typing import List, Dict, Any
from .chapter_parser import Chapter

CSS_CONTENT = """
@charset "utf-8";
body {
    font-family: "PingFang SC", "Microsoft YaHei", "SimHei", sans-serif;
    line-height: 1.8;
    margin: 0;
    padding: 0;
    text-align: justify;
}
h1, h2, h3 {
    text-align: center;
    font-weight: bold;
    margin-top: 2em;
    margin-bottom: 2em;
}
p {
    text-indent: 2em;
    margin-top: 0.5em;
    margin-bottom: 0.5em;
}
.title-page {
    text-align: center;
    margin-top: 20%;
}
.title-page h1 {
    font-size: 2em;
    margin-bottom: 0.5em;
}
.title-page h2 {
    font-size: 1.2em;
    color: #555;
    font-weight: normal;
}
.description {
    margin-top: 3em;
    text-align: left;
    font-size: 0.9em;
    color: #333;
}
"""

class EpubBuilder:
    def __init__(self, metadata: Dict[str, Any], chapters: List[Chapter], cover_bytes: bytes):
        self.metadata = metadata
        self.chapters = chapters
        self.cover_bytes = cover_bytes
        self.uuid_str = str(uuid.uuid4())
        self.date_str = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    def build(self, output_path: str):
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # mimetype must be first, and must be STORED (not compressed)
            zf.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)

            # META-INF/container.xml
            container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''
            zf.writestr('META-INF/container.xml', container_xml)

            # CSS and Cover image
            zf.writestr('OEBPS/Styles/style.css', CSS_CONTENT)
            if self.cover_bytes:
                zf.writestr('OEBPS/Images/cover.jpg', self.cover_bytes)

            # Title page
            title_html = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-CN">
<head>
    <title>{html.escape(self.metadata.get('title', ''))}</title>
    <link href="../Styles/style.css" rel="stylesheet" type="text/css"/>
</head>
<body>
    <div class="title-page">
        <h1>{html.escape(self.metadata.get('title', ''))}</h1>
        <h2>{html.escape(self.metadata.get('author', ''))}</h2>
        <div class="description">
            <p><strong>简介:</strong></p>
            {"".join(f"<p>{html.escape(p)}</p>" for p in self.metadata.get('description', '').splitlines() if p.strip())}
        </div>
    </div>
</body>
</html>'''
            zf.writestr('OEBPS/Text/titlepage.xhtml', title_html)

            # Cover page
            cover_html = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-CN">
<head>
    <title>Cover</title>
    <style type="text/css">
        body {{ margin: 0; padding: 0; text-align: center; }}
        img {{ max-width: 100%; height: auto; }}
    </style>
</head>
<body>
    <img src="../Images/cover.jpg" alt="Cover" />
</body>
</html>'''
            zf.writestr('OEBPS/Text/cover.xhtml', cover_html)

            # Chapters
            for chap in self.chapters:
                chap_filename = f'chapter_{chap.index:04d}.xhtml'
                chap_html = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-CN">
<head>
    <title>{html.escape(chap.title)}</title>
    <link href="../Styles/style.css" rel="stylesheet" type="text/css"/>
</head>
<body>
    <h1>{html.escape(chap.title)}</h1>
    {"".join(f"<p>{html.escape(line)}</p>" for line in chap.content)}
</body>
</html>'''
                zf.writestr(f'OEBPS/Text/{chap_filename}', chap_html)

            # TOC NCX (EPUB 2 fallback)
            navpoints = []
            navpoints.append(f'''<navPoint id="navPoint-cover" playOrder="1">
                <navLabel><text>Cover</text></navLabel>
                <content src="Text/cover.xhtml"/>
            </navPoint>''')
            navpoints.append(f'''<navPoint id="navPoint-title" playOrder="2">
                <navLabel><text>Title Page</text></navLabel>
                <content src="Text/titlepage.xhtml"/>
            </navPoint>''')
            
            for idx, chap in enumerate(self.chapters, start=3):
                chap_filename = f'chapter_{chap.index:04d}.xhtml'
                navpoints.append(f'''<navPoint id="navPoint-{idx}" playOrder="{idx}">
                <navLabel><text>{html.escape(chap.title)}</text></navLabel>
                <content src="Text/{chap_filename}"/>
            </navPoint>''')

            ncx = f'''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="urn:uuid:{self.uuid_str}"/>
        <meta name="dtb:depth" content="1"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
    </head>
    <docTitle><text>{html.escape(self.metadata.get('title', ''))}</text></docTitle>
    <docAuthor><text>{html.escape(self.metadata.get('author', ''))}</text></docAuthor>
    <navMap>
        {"".join(navpoints)}
    </navMap>
</ncx>'''
            zf.writestr('OEBPS/toc.ncx', ncx)

            # EPUB 3 NAV document (toc.xhtml)
            nav_li = []
            nav_li.append('<li><a href="Text/cover.xhtml">封面</a></li>')
            nav_li.append('<li><a href="Text/titlepage.xhtml">信息</a></li>')
            for chap in self.chapters:
                chap_filename = f'chapter_{chap.index:04d}.xhtml'
                nav_li.append(f'<li><a href="Text/{chap_filename}">{html.escape(chap.title)}</a></li>')

            toc_xhtml = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-CN">
<head>
    <title>目录</title>
</head>
<body>
    <nav epub:type="toc" id="toc">
        <h1>目录</h1>
        <ol>
            {"".join(nav_li)}
        </ol>
    </nav>
</body>
</html>'''
            zf.writestr('OEBPS/toc.xhtml', toc_xhtml)

            # content.opf
            manifest_items = []
            spine_refs = []

            manifest_items.append('<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')
            manifest_items.append('<item id="nav" href="toc.xhtml" media-type="application/xhtml+xml" properties="nav"/>')
            manifest_items.append('<item id="css" href="Styles/style.css" media-type="text/css"/>')
            
            if self.cover_bytes:
                manifest_items.append('<item id="cover-image" href="Images/cover.jpg" media-type="image/jpeg" properties="cover-image"/>')
                manifest_items.append('<item id="cover" href="Text/cover.xhtml" media-type="application/xhtml+xml"/>')
                spine_refs.append('<itemref idref="cover" linear="yes"/>')

            manifest_items.append('<item id="titlepage" href="Text/titlepage.xhtml" media-type="application/xhtml+xml"/>')
            spine_refs.append('<itemref idref="titlepage" linear="yes"/>')

            for chap in self.chapters:
                chap_id = f'chapter_{chap.index:04d}'
                chap_filename = f'{chap_id}.xhtml'
                manifest_items.append(f'<item id="{chap_id}" href="Text/{chap_filename}" media-type="application/xhtml+xml"/>')
                spine_refs.append(f'<itemref idref="{chap_id}" linear="yes"/>')

            content_opf = f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="3.0">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:identifier id="BookId">urn:uuid:{self.uuid_str}</dc:identifier>
        <dc:title>{html.escape(self.metadata.get('title', ''))}</dc:title>
        <dc:creator>{html.escape(self.metadata.get('author', ''))}</dc:creator>
        <dc:language>{html.escape(self.metadata.get('language', 'zh-CN'))}</dc:language>
        <meta property="dcterms:modified">{self.date_str}</meta>
        {"<meta name='cover' content='cover-image'/>" if self.cover_bytes else ""}
    </metadata>
    <manifest>
        {"".join(manifest_items)}
    </manifest>
    <spine toc="ncx">
        {"".join(spine_refs)}
    </spine>
    <guide>
        <reference type="cover" title="Cover" href="Text/cover.xhtml"/>
        <reference type="toc" title="Table of Contents" href="Text/titlepage.xhtml"/>
    </guide>
</package>'''
            zf.writestr('OEBPS/content.opf', content_opf)
