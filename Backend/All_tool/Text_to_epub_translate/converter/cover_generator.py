from PIL import Image, ImageDraw, ImageFont
import os
import random
import io
import math

def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Attempts to load a Chinese-supporting font."""
    # Prioritize high quality Noto fonts for beautiful CJK rendering
    font_paths = [
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "msyhbd.ttc" if bold else "msyh.ttc",
        "simhei.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
    ]
    
    for font_path in font_paths:
        try:
            return ImageFont.truetype(font_path, size)
        except IOError:
            continue
            
    return ImageFont.load_default()

def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Wraps text to fit within a given width perfectly."""
    if not hasattr(font, 'getlength'):
        chars_per_line = max(1, max_width // 40)
        return [text[i:i+chars_per_line] for i in range(0, len(text), chars_per_line)]

    if font.getlength(text) <= max_width:
        return [text]

    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        if font.getlength(test_line) <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = char
    if current_line:
        lines.append(current_line)
    return lines

def draw_abstract_shapes(draw: ImageDraw.ImageDraw, width: int, height: int, fg_color: tuple):
    """Draw random elegant abstract shapes on the background."""
    for _ in range(random.randint(2, 5)):
        radius = random.randint(100, 400)
        x = random.randint(-radius, width)
        y = random.randint(-radius, height)
        
        # Transparent white/gold overlay circles
        alpha = random.randint(10, 30)
        color = (fg_color[0], fg_color[1], fg_color[2], alpha)
        
        # We need a separate RGBA image for transparent shapes to composite
        shape_img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
        shape_draw = ImageDraw.Draw(shape_img)
        shape_draw.ellipse([x, y, x + radius*2, y + radius*2], fill=color)
        draw._image.paste(shape_img, (0, 0), shape_img)

def generate_cover(title: str, author: str, width: int = 800, height: int = 1200) -> bytes:
    """
    Generates a highly aesthetic cover image using PIL.
    """
    # 1. Background Palettes (Premium Dark/Elegant Colors)
    palettes = [
        # Navy to Deep Purple
        ((15, 23, 42), (49, 46, 129), (216, 180, 254)), 
        # Obsidian to Crimson
        ((39, 39, 42), (153, 27, 27), (254, 202, 202)),
        # Emerald Dark
        ((2, 44, 34), (4, 120, 87), (167, 243, 208)),
        # Midnight Blue
        ((23, 37, 84), (30, 64, 175), (191, 219, 254)),
        # Royal Gold/Black
        ((20, 20, 20), (80, 60, 20), (253, 224, 71)),
        # Minimalist Slate
        ((15, 23, 42), (51, 65, 85), (248, 250, 252))
    ]
    bg_start, bg_end, accent = random.choice(palettes)

    # Base Image (RGBA to allow transparent shapes)
    img = Image.new('RGBA', (width, height))
    draw = ImageDraw.Draw(img)

    # Smooth Gradient Background
    for y in range(height):
        r = int(bg_start[0] + (bg_end[0] - bg_start[0]) * y / height)
        g = int(bg_start[1] + (bg_end[1] - bg_start[1]) * y / height)
        b = int(bg_start[2] + (bg_end[2] - bg_start[2]) * y / height)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # Add abstract artistic shapes
    draw_abstract_shapes(draw, width, height, accent)

    # Elegant Border
    margin = 50
    draw.rectangle(
        [margin, margin, width - margin, height - margin],
        outline=(accent[0], accent[1], accent[2], 180),
        width=4
    )
    
    # Inner thin border
    draw.rectangle(
        [margin + 15, margin + 15, width - margin - 15, height - margin - 15],
        outline=(accent[0], accent[1], accent[2], 80),
        width=1
    )

    # Convert back to RGB
    img = img.convert('RGB')
    draw = ImageDraw.Draw(img)

    # 2. Typography
    title_font = get_font(90, bold=True)
    author_font = get_font(40, bold=False)

    max_text_width = width - (margin * 4)
    title_lines = wrap_text(title, title_font, max_text_width)
    
    line_height = 110
    total_title_height = len(title_lines) * line_height
    
    # Vertically center title in the upper half
    start_y = (height * 0.45) - (total_title_height / 2)
    
    # Draw Title
    for i, line in enumerate(title_lines):
        line_w = title_font.getlength(line) if hasattr(title_font, 'getlength') else len(line)*90
        x = (width - line_w) / 2
        y = start_y + i * line_height
        
        # Soft drop shadow
        draw.text((x + 4, y + 4), line, font=title_font, fill=(0, 0, 0, 150))
        # Crisp text
        draw.text((x, y), line, font=title_font, fill=(255, 255, 255))

    # Decorative separator line below title
    sep_y = start_y + total_title_height + 40
    sep_w = 150
    draw.line([(width/2 - sep_w/2, sep_y), (width/2 + sep_w/2, sep_y)], fill=accent, width=4)

    # Draw Author
    author = f"作者 : {author}" if not author.startswith("作") else author
    author_w = author_font.getlength(author) if hasattr(author_font, 'getlength') else len(author)*40
    author_x = (width - author_w) / 2
    author_y = sep_y + 50
    
    draw.text((author_x + 2, author_y + 2), author, font=author_font, fill=(0, 0, 0, 100))
    draw.text((author_x, author_y), author, font=author_font, fill=accent)

    # Publisher / Studio Label at bottom
    label = "ALIDA WEB NOVEL STUDIO"
    label_font = get_font(22, bold=True)
    label_w = label_font.getlength(label) if hasattr(label_font, 'getlength') else len(label)*15
    label_y = height - margin - 60
    
    # Letter spacing simulation for label
    draw.text(((width - label_w) / 2, label_y), label, font=label_font, fill=(255, 255, 255, 120))

    # Save
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG', quality=95, optimize=True)
    return img_byte_arr.getvalue()
