# SPDX-License-Identifier: GPL-3.0-or-later WITH LicenseRef-ImGui-Bundle-exception
"""Local label rendering and independently implemented N20 raster framing."""
from dataclasses import dataclass
from pathlib import Path
import struct
import math
from decorations import BORDERS, PATTERNS, border_padding, draw_border, pattern_image

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

WIDTH, HEIGHT = 320, 240  # 40 x 30 mm, nominal 8 dots/mm
STATUS_QUERY = bytes.fromhex('1f110501')
MEDIA_TYPES = {'continuous': 0, 'gap': 1, 'black_mark': 2}
PRESETS = [
    ('Included stickers / 40 x 30 mm', 40, 30, 'rectangle', 'gap'),
    ('Rectangle / 40 x 60 mm', 40, 60, 'rectangle', 'gap'),
    ('Rectangle / 50 x 30 mm', 50, 30, 'rectangle', 'gap'),
    ('Rectangle / 50 x 80 mm', 50, 80, 'rectangle', 'gap'),
    ('Round stickers / 30 mm', 30, 30, 'round', 'gap'),
    ('Round stickers / 40 mm', 40, 40, 'round', 'gap'),
    ('Round stickers / 50 mm', 50, 50, 'round', 'gap'),
    ('Receipt paper / 38 mm wide', 38, 80, 'rectangle', 'continuous'),
    ('Continuous paper / 48 mm wide', 48, 80, 'rectangle', 'continuous'),
]


@dataclass
class Design:
    text: str = 'Hello, labels!\n40 x 30 mm'
    font_size: int = 30
    margin: int = 16
    border: bool = False
    align: str = 'center'
    image_path: str = ''
    dither: bool = True
    image_brightness: float = 1.0
    width_mm: int = 40
    height_mm: int = 30
    shape: str = 'rectangle'
    media_type: str = 'gap'
    border_style: str = 'solid'
    border_size: int = 12
    pattern: str = ''
    pattern_spacing: int = 28
    pattern_weight: int = 2


def dimensions(design):
    if not isinstance(design.width_mm, int) or not 20 <= design.width_mm <= 50:
        raise ValueError('Roll width must be 20-50 mm')
    if not isinstance(design.height_mm, int) or not 10 <= design.height_mm <= 300:
        raise ValueError('Print length must be 10-300 mm')
    if design.media_type not in MEDIA_TYPES or design.shape not in ('rectangle', 'round'):
        raise ValueError('Unsupported paper mode or shape')
    if design.shape == 'round' and design.width_mm != design.height_mm:
        raise ValueError('Round labels must have equal width and height')
    return design.width_mm*8, design.height_mm*8


def font(size):
    for path in (Path(__file__).resolve().parent/'assets'/'DejaVuSans.ttf',
                 '/usr/share/fonts/TTF/DejaVuSans.ttf',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def render(design: Design):
    width, height = dimensions(design)
    if not 8 <= design.font_size <= 96 or not 4 <= design.margin <= 48:
        raise ValueError('Font or margin outside supported range')
    if design.align not in ('left', 'center', 'right'):
        raise ValueError('Unsupported alignment')
    if not .25 <= design.image_brightness <= 3.0:
        raise ValueError('Image brightness must be between 0.25 and 3.0')
    if design.border_style not in BORDERS or not 8 <= design.border_size <= 24:
        raise ValueError('Invalid border style or ornament size')
    if design.pattern not in ['']+PATTERNS or not 12 <= design.pattern_spacing <= 64 or not 1 <= design.pattern_weight <= 5:
        raise ValueError('Invalid pattern settings')
    canvas = Image.new('L', (width, height), 255)
    draw = ImageDraw.Draw(canvas)
    margin = design.margin
    content_margin = margin+(border_padding(design.border_style,design.border_size) if design.border else 0)
    available = (min(width,384) - 2 * content_margin, height - 2 * content_margin)
    if design.shape == 'round':
        side = int((width-2*content_margin)/math.sqrt(2))
        available = (min(side,available[0]), side)
    if min(available) <= 0:
        raise ValueError('Margins leave no printable area; reduce the margin or increase the paper size')
    warnings = []
    if design.pattern:
        # Fill the inner shape; the margin and border remain clear.
        pattern = pattern_image(canvas.size,design.pattern,design.pattern_spacing,design.pattern_weight)
        mask = Image.new('L',canvas.size,0)
        mask_draw = ImageDraw.Draw(mask)
        left=max(0,(width-384)//2)+content_margin
        if design.shape=='round':
            mask_draw.ellipse((content_margin,content_margin,width-content_margin-1,height-content_margin-1),fill=255)
        else:
            mask_draw.rectangle((left,content_margin,width-left-1,height-content_margin-1),fill=255)
        canvas.paste(pattern,(0,0),mask)
    elif design.image_path:
        with Image.open(Path(design.image_path).expanduser()) as source:
            source = ImageOps.exif_transpose(source).convert('RGBA')
            white = Image.new('RGBA', source.size, 'white')
            white.alpha_composite(source)
            fitted = ImageOps.contain(white.convert('L'), available)
            if design.image_brightness != 1.0:
                fitted = ImageEnhance.Brightness(fitted).enhance(design.image_brightness)
        canvas.paste(fitted, ((width-fitted.width)//2, (height-fitted.height)//2))
    else:
        f = font(design.font_size)
        box = draw.multiline_textbbox((0, 0), design.text, font=f, spacing=5, align=design.align)
        w, h = box[2]-box[0], box[3]-box[1]
        if w > available[0] or h > available[1]:
            warnings.append('Text exceeds the label margins. Reduce the font size or add line breaks.')
        left = (width-available[0])//2
        x = {'left': left, 'center': (width-w)//2, 'right': left+available[0]-w}[design.align]
        draw.multiline_text((x-box[0], (height-h)//2-box[1]), design.text,
                            font=f, fill=0, spacing=5, align=design.align)
    if design.border:
        draw_border(canvas,design.shape,margin,design.border_style,design.border_size)
    if design.shape == 'round':
        mask = Image.new('L',(width,height),0)
        ImageDraw.Draw(mask).ellipse((0,0,width-1,height-1),fill=255)
        canvas = Image.composite(canvas,Image.new('L',canvas.size,255),mask)
    if width > 384:
        edge = (width-384)//2
        edge_draw = ImageDraw.Draw(canvas)
        edge_draw.rectangle((0,0,edge-1,height-1),fill=255)
        edge_draw.rectangle((width-edge,0,width-1,height-1),fill=255)
    if design.dither:
        mono = canvas.convert('1', dither=Image.Dither.FLOYDSTEINBERG)
    else:
        mono = canvas.point(lambda v: 255 if v >= 128 else 0, mode='1')
    return mono, warnings


def encode(image, darkness=2, media_type='gap'):
    """One label; black=1, MSB first. No vendor code is loaded or invoked."""
    width, height = image.size
    if image.mode != '1' or not 160 <= width <= 400 or width%8 or not 80 <= height <= 2400:
        raise ValueError('Expected a monochrome label 20-50 mm wide and 10-300 mm long')
    if darkness not in (1, 2, 3):
        raise ValueError('Darkness must be 1, 2 or 3')
    if media_type not in MEDIA_TYPES:
        raise ValueError('Unsupported paper mode')
    if width > 384:
        left = (width-384)//2
        image = image.crop((left,0,left+384,height))
        width = 384
    setup = bytes.fromhex('1f11050a') + bytes([MEDIA_TYPES[media_type]]) + bytes.fromhex('1f110502') + bytes([darkness])
    raster = bytes.fromhex('1f11053500 1d763000') + struct.pack('<HH', width//8, height)
    return setup + raster + bytes(value ^ 255 for value in image.tobytes())


def decode_status(raw):
    if len(raw) != 4 or raw[0] not in (0x1a, 0x1c) or raw[1] != 0x20 or raw[3] != 0x0d:
        raise RuntimeError(f'Unrecognized printer status: {raw.hex(" ")}')
    if raw[2]:
        raise RuntimeError(f'Printer not ready (status 0x{raw[2]:02x}); check lid, paper and battery')
    return 'Ready'
