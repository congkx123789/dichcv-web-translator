import os
import html
from typing import List, Dict, Any
from .chapter_parser import Chapter
from .epub_builder import EpubBuilder

class Exporter:
    def __init__(self, metadata: Dict[str, Any], chapters: List[Chapter], cover_bytes: bytes = None):
        self.metadata = metadata
        self.chapters = chapters
        self.cover_bytes = cover_bytes

    def export_epub(self, output_path: str):
        builder = EpubBuilder(self.metadata, self.chapters, self.cover_bytes)
        builder.build(output_path)

    def export_txt(self, output_path: str):
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"『{self.metadata.get('title', '')} / 作者:{self.metadata.get('author', '')}』\n")
            if self.metadata.get('status'):
                f.write(f"『状态:{self.metadata.get('status')}』\n")
            if self.metadata.get('description'):
                f.write("『内容简介:\n")
                f.write(self.metadata.get('description') + "\n")
                f.write("』\n")
            f.write("------章节内容开始-------\n\n")
            
            for chap in self.chapters:
                f.write(f"{chap.title}\n\n")
                for line in chap.content:
                    f.write(f"{line}\n")
                f.write("\n\n")

    def export_html(self, output_path: str):
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(self.metadata.get('title', ''))}</title>
    <style>
        :root {{ --bg: #ffffff; --text: #333333; --link: #0366d6; --sidebar-bg: #f9f9f9; --border: #eeeeee; }}
        [data-theme="dark"] {{ --bg: #121212; --text: #e0e0e0; --link: #66b3ff; --sidebar-bg: #1e1e1e; --border: #333333; }}
        body {{ margin: 0; padding: 0; font-family: "PingFang SC", "Microsoft YaHei", sans-serif; line-height: 1.8; color: var(--text); background: var(--bg); transition: background 0.3s, color 0.3s; display: flex; height: 100vh; overflow: hidden; }}
        #sidebar {{ width: 300px; background: var(--sidebar-bg); border-right: 1px solid var(--border); display: flex; flex-direction: column; transition: transform 0.3s; }}
        #sidebar.hidden {{ transform: translateX(-100%); position: absolute; height: 100%; z-index: 10; }}
        #sidebar-header {{ padding: 20px; border-bottom: 1px solid var(--border); }}
        #sidebar-header h2 {{ margin: 0; font-size: 1.2em; }}
        #toc-list {{ flex: 1; overflow-y: auto; padding: 10px; margin: 0; list-style: none; }}
        #toc-list li {{ margin-bottom: 5px; }}
        #toc-list a {{ text-decoration: none; color: var(--text); display: block; padding: 5px 10px; border-radius: 4px; }}
        #toc-list a:hover, #toc-list a.active {{ background: rgba(128,128,128,0.2); color: var(--link); }}
        #content-wrapper {{ flex: 1; display: flex; flex-direction: column; height: 100vh; overflow: hidden; position: relative; }}
        #navbar {{ padding: 10px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: var(--bg); }}
        .btn {{ background: transparent; border: 1px solid var(--border); color: var(--text); padding: 5px 15px; cursor: pointer; border-radius: 4px; }}
        .btn:hover {{ background: rgba(128,128,128,0.1); }}
        #main-content {{ flex: 1; overflow-y: auto; padding: 20px 40px; scroll-behavior: smooth; }}
        .chapter, #home-page {{ display: none; max-width: 800px; margin: 0 auto; }}
        .chapter.active, #home-page.active {{ display: block; }}
        h1 {{ text-align: center; margin-bottom: 30px; font-size: 2em; }}
        p {{ text-indent: 2em; text-align: justify; margin: 0.8em 0; font-size: 1.1em; }}
        .nav-buttons {{ display: flex; justify-content: space-between; margin-top: 50px; padding-top: 20px; border-top: 1px solid var(--border); }}
        @media (max-width: 768px) {{ #sidebar {{ position: absolute; height: 100%; z-index: 10; transform: translateX(-100%); }} #sidebar.show {{ transform: translateX(0); }} #main-content {{ padding: 20px; }} }}
    </style>
</head>
<body>
    <div id="sidebar" class="hidden">
        <div id="sidebar-header">
            <h2>目录 (TOC)</h2>
        </div>
        <ul id="toc-list">
            <li><a href="#" onclick="showChapter('home'); return false;">首页 (Home)</a></li>
''')
            for chap in self.chapters:
                f.write(f'            <li><a href="#" id="link-{chap.index}" onclick="showChapter({chap.index}); return false;">{html.escape(chap.title)}</a></li>\n')
            
            f.write(f'''        </ul>
    </div>
    
    <div id="content-wrapper">
        <div id="navbar">
            <button class="btn" onclick="toggleSidebar()">☰ 目录</button>
            <span id="nav-title" style="font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 50%;">{html.escape(self.metadata.get('title', ''))}</span>
            <button class="btn" onclick="toggleTheme()">🌗 主题</button>
        </div>
        
        <div id="main-content">
            <div id="home-page" class="active">
                <h1>{html.escape(self.metadata.get('title', ''))}</h1>
                <h3 style="text-align: center; color: gray;">作者: {html.escape(self.metadata.get('author', ''))}</h3>
                <div style="margin-top: 40px; padding: 20px; background: rgba(128,128,128,0.1); border-radius: 8px;">
                    <strong>内容简介:</strong>
                    {"".join(f"<p>{html.escape(p)}</p>" for p in self.metadata.get('description', '').splitlines() if p.strip())}
                </div>
                <div style="text-align: center; margin-top: 40px;">
                    <button class="btn" style="font-size: 1.2em; padding: 10px 30px;" onclick="showChapter(0)">开始阅读</button>
                </div>
            </div>
''')

            for chap in self.chapters:
                f.write(f'            <div class="chapter" id="chapter-{chap.index}">\n')
                f.write(f'                <h1>{html.escape(chap.title)}</h1>\n')
                for line in chap.content:
                    f.write(f'                <p>{html.escape(line)}</p>\n')
                
                f.write('                <div class="nav-buttons">\n')
                prev_action = f"showChapter({chap.index - 1})" if chap.index > 0 else "showChapter('home')"
                next_action = f"showChapter({chap.index + 1})" if chap.index < len(self.chapters) - 1 else "alert('已经是最后一章了')"
                f.write(f'                    <button class="btn" onclick="{prev_action}">上一章</button>\n')
                f.write(f'                    <button class="btn" onclick="{next_action}">下一章</button>\n')
                f.write('                </div>\n')
                f.write('            </div>\n')

            f.write('''        </div>
    </div>

    <script>
        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            if (window.innerWidth <= 768) {
                sidebar.classList.toggle('show');
            } else {
                sidebar.classList.toggle('hidden');
            }
        }
        
        function toggleTheme() {
            const body = document.documentElement;
            if (body.getAttribute('data-theme') === 'dark') {
                body.removeAttribute('data-theme');
            } else {
                body.setAttribute('data-theme', 'dark');
            }
        }

        function showChapter(index) {
            // Hide all
            document.getElementById('home-page').classList.remove('active');
            document.querySelectorAll('.chapter').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('#toc-list a').forEach(el => el.classList.remove('active'));
            
            let target;
            if (index === 'home') {
                target = document.getElementById('home-page');
                document.getElementById('nav-title').innerText = document.title;
            } else {
                target = document.getElementById('chapter-' + index);
                const link = document.getElementById('link-' + index);
                if (link) {
                    link.classList.add('active');
                    link.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    document.getElementById('nav-title').innerText = link.innerText;
                }
            }
            
            if (target) {
                target.classList.add('active');
                document.getElementById('main-content').scrollTop = 0;
            }
            
            // Auto-hide sidebar on mobile after click
            if (window.innerWidth <= 768) {
                document.getElementById('sidebar').classList.remove('show');
            }
        }
        
        // Hide sidebar initially on desktop for cleaner look
        if (window.innerWidth > 768) {
            document.getElementById('sidebar').classList.remove('hidden');
        }
    </script>
</body>
</html>
''')
