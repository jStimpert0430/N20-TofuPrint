# SPDX-License-Identifier: GPL-3.0-or-later WITH LicenseRef-ImGui-Bundle-exception
"""Presentation for the label editor; print and render logic remain in their modules."""
from pathlib import Path
from functools import lru_cache
from imgui_bundle import imgui, portable_file_dialogs as dialogs
from label import PRESETS, dimensions
from decorations import BORDERS, PATTERNS, pattern_image
from imports import import_link
import printer

BG = (0.055, 0.071, 0.090, 1)
PANEL = (0.085, 0.106, 0.129, 1)
FIELD = (0.12, 0.145, 0.17, 1)
TEXT = (0.89, 0.92, 0.94, 1)
MUTED = (0.52, 0.60, 0.65, 1)
ACCENT = (0.73, 0.65, 0.94, 1)


def color(value):
    return imgui.get_color_u32(value)


def theme():
    style = imgui.get_style()
    style.font_scale_main = 1.15
    style.window_padding = (22, 18)
    style.frame_padding = (11, 7)
    style.item_spacing = (10, 8)
    style.item_inner_spacing = (8, 6)
    style.window_rounding = 10
    style.child_rounding = 12
    style.frame_rounding = 6
    style.popup_rounding = 8
    style.grab_rounding = 6
    style.scrollbar_rounding = 8
    style.scrollbar_size = 10
    style.child_border_size = 1
    colors = {
        'text': TEXT, 'text_disabled': MUTED, 'window_bg': BG, 'child_bg': PANEL,
        'popup_bg': PANEL, 'border': (0.19, 0.24, 0.28, .65),
        'frame_bg': FIELD, 'frame_bg_hovered': (0.17, 0.22, 0.25, 1),
        'frame_bg_active': (0.24, 0.22, 0.32, 1),
        'button': (0.16, 0.21, 0.24, 1), 'button_hovered': (0.28, 0.25, 0.37, 1),
        'button_active': (0.35, 0.29, 0.47, 1), 'check_mark': ACCENT,
        'slider_grab': ACCENT, 'slider_grab_active': (0.84, 0.76, 1.0, 1),
        'header': FIELD, 'header_hovered': (0.24, 0.22, 0.32, 1),
        'header_active': (0.30, 0.25, 0.41, 1),
        'tab': FIELD, 'tab_hovered': (0.30, 0.25, 0.41, 1),
        'tab_selected': (0.25, 0.22, 0.35, 1), 'tab_selected_overline': ACCENT,
        'separator': (0.20, 0.25, 0.29, 1), 'resize_grip': (0.73, 0.65, 0.94, .2),
        'scrollbar_bg': (0, 0, 0, 0), 'scrollbar_grab': (0.23, 0.30, 0.34, 1),
    }
    for name, value in colors.items():
        style.set_color_(getattr(imgui.Col_, name), value)


def heading(text):
    imgui.text_colored(ACCENT, text)


def full_width():
    imgui.set_next_item_width(-1)


def primary(label, size=(0, 0)):
    imgui.push_style_color(imgui.Col_.button, ACCENT)
    imgui.push_style_color(imgui.Col_.button_hovered, (0.82, 0.75, 1.0, 1))
    imgui.push_style_color(imgui.Col_.button_active, (0.62, 0.53, 0.83, 1))
    imgui.push_style_color(imgui.Col_.text, (0.10, 0.07, 0.16, 1))
    pressed = imgui.button(label, size)
    imgui.pop_style_color(4)
    return pressed


@lru_cache(maxsize=16)
def pattern_thumbnail(kind):
    image = pattern_image((100,40),kind,20,1)
    pixels=image.load()
    spans=[]
    for y in range(40):
        start=None
        for x in range(101):
            black=x<100 and pixels[x,y]<128
            if black and start is None: start=x
            if not black and start is not None:
                spans.append((start,y,x))
                start=None
    return spans


def pattern_gallery(editor):
    design=editor.design
    imgui.spacing()
    imgui.text_wrapped('Choose a pattern to place on the label.')
    busy=editor.job is not None or editor.file_dialog is not None
    imgui.begin_disabled(busy)
    imgui.begin_child('pattern_gallery',(0,230))
    card_width=(imgui.get_content_region_avail().x-10)/2
    for i,kind in enumerate(PATTERNS):
        if i%2: imgui.same_line()
        origin=imgui.get_cursor_screen_pos()
        selected=design.pattern==kind
        if selected: imgui.push_style_color(imgui.Col_.button,(.32,.27,.43,1))
        clicked=imgui.button('##pattern_'+kind,(card_width,76))
        if selected: imgui.pop_style_color()
        if clicked: design.pattern=kind
        draw=imgui.get_window_draw_list()
        scale=min(1,(card_width-16)/100)
        x,y=origin.x+(card_width-100*scale)/2,origin.y+7
        draw.add_rect_filled((x,y),(x+100*scale,y+40),0xffffffff,3)
        for start,row,end in pattern_thumbnail(kind):
            draw.add_rect_filled((x+start*scale,y+row),(x+end*scale,y+row+1),0xff202020)
        label=kind.title()
        width=imgui.calc_text_size(label).x
        draw.add_text((origin.x+(card_width-width)/2,origin.y+52),color(ACCENT if selected else TEXT),label)
    imgui.end_child()
    imgui.end_disabled()
    full_width()
    _,design.pattern_spacing=imgui.slider_int('##pattern_spacing',design.pattern_spacing,12,64,'Spacing: %d dots')
    full_width()
    _,design.pattern_weight=imgui.slider_int('##pattern_weight',design.pattern_weight,1,5,'Line weight: %d')
    if imgui.is_item_hovered():
        imgui.set_tooltip('Applies to line patterns and confetti. Filled shapes use spacing for size.')


def content(editor, root):
    design = editor.design
    busy = editor.job is not None or editor.file_dialog is not None
    heading('PAPER ROLL')
    current = (design.width_mm,design.height_mm,design.shape,design.media_type)
    selected = next((i for i,p in enumerate(PRESETS) if tuple(p[1:]) == current),len(PRESETS))
    full_width()
    changed, selected = imgui.combo('##roll_preset',selected,[p[0] for p in PRESETS]+['Custom roll'])
    if changed and selected < len(PRESETS):
        _,design.width_mm,design.height_mm,design.shape,design.media_type = PRESETS[selected]
    if changed and selected == len(PRESETS):
        imgui.set_next_item_open(True)
    if imgui.collapsing_header('Paper size & feed'):
        full_width()
        _,design.width_mm = imgui.slider_int('##paper_width',design.width_mm,20,50,'Width: %d mm')
        shapes = ['rectangle','round']
        full_width()
        _,shape = imgui.combo('##shape',shapes.index(design.shape),['Rectangle / receipt','Round sticker'])
        design.shape = shapes[shape]
        if design.shape == 'round':
            design.height_mm = design.width_mm
        else:
            full_width()
            _,design.height_mm = imgui.slider_int('##paper_height',design.height_mm,10,300,'Print length: %d mm')
        modes = ['gap','continuous','black_mark']
        full_width()
        _,mode = imgui.combo('##paper_mode',modes.index(design.media_type),
                            ['Labels with gaps','Continuous / receipt paper','Labels with black marks'])
        design.media_type = modes[mode]
        imgui.text_wrapped('Match the feed mode to the loaded roll. Widths over 48 mm have unprinted side edges.')
    if design.media_type == 'continuous':
        imgui.text_disabled(f'Continuous paper / {design.height_mm} mm per print')
    imgui.spacing()
    imgui.separator()
    imgui.spacing()
    heading('01  /  CONTENT')
    if imgui.begin_tab_bar('content_tabs'):
        if imgui.begin_tab_item('Text')[0]:
            imgui.spacing()
            _, design.text = imgui.input_text_multiline('##text', design.text, (-1, 110))
            full_width()
            _, design.font_size = imgui.slider_int('##font', design.font_size, 8, 96, 'Font size: %d')
            full_width()
            values = ['left', 'center', 'right']
            _, alignment = imgui.combo('##alignment', values.index(design.align),
                                       ['Align left', 'Align center', 'Align right'])
            design.align = values[alignment]
            if design.image_path or design.pattern:
                imgui.text_disabled('Another design is currently on the label.')
                imgui.begin_disabled(busy)
                if imgui.button('Use this text', (-1, 0)):
                    design.image_path = ''
                    design.pattern = ''
                    editor.image_description = ''
                imgui.end_disabled()
            imgui.end_tab_item()
        initial_image = imgui.TabItemFlags_.set_selected if editor.frames == 0 and design.image_path and not design.pattern else 0
        if imgui.begin_tab_item('Image', flags=initial_image)[0]:
            imgui.spacing()
            imgui.begin_disabled(busy)
            if primary('Import image...', (-1, 36)):
                try:
                    editor.file_dialog = dialogs.open_file('Import label image', str(Path.home()),
                        ['Images', '*.png *.jpg *.jpeg *.webp *.gif *.bmp *.tif *.tiff', 'All files', '*'])
                except Exception as exc:
                    editor.status = f'Could not open file picker: {exc}'
            imgui.text_disabled('Or import from the web')
            full_width()
            _, editor.web_link = imgui.input_text_with_hint('##web_image', 'https://image-or-page-link', editor.web_link)
            imgui.begin_disabled(not editor.web_link.strip())
            if imgui.button('Import link', (-1, 0)):
                editor.start(import_link, editor.web_link, root/'output'/'imports', kind='Web image import')
            imgui.end_disabled()
            imgui.end_disabled()
            if design.image_path:
                imgui.text_wrapped(editor.image_description or 'Imported image')
                if imgui.is_item_hovered():
                    imgui.set_tooltip(design.image_path)
                if design.pattern:
                    imgui.begin_disabled(busy)
                    if imgui.button('Use this image',(-1,0)):
                        design.pattern=''
                    imgui.end_disabled()
            imgui.begin_disabled(not design.image_path)
            full_width()
            _, design.image_brightness = imgui.slider_float('##brightness', design.image_brightness,
                                                          .25, 3, 'Brightness: %.2fx')
            if imgui.small_button('Reset to 1.00x'):
                design.image_brightness = 1.0
            imgui.same_line()
            imgui.text_disabled('Higher = lighter')
            imgui.end_disabled()
            imgui.end_tab_item()
        initial_pattern = imgui.TabItemFlags_.set_selected if editor.frames == 0 and design.pattern else 0
        if imgui.begin_tab_item('Patterns',flags=initial_pattern)[0]:
            pattern_gallery(editor)
            imgui.end_tab_item()
        imgui.end_tab_bar()
    imgui.spacing()
    imgui.separator()
    imgui.spacing()
    heading('02  /  FINISH')
    full_width()
    _, design.margin = imgui.slider_int('##margin', design.margin, 4, 48, 'Margin: %d dots')
    border_names=['No border']+[s.title() for s in BORDERS]
    border_selected=BORDERS.index(design.border_style)+1 if design.border else 0
    full_width()
    changed,border_selected=imgui.combo('##border_style',border_selected,border_names)
    if changed:
        design.border=border_selected!=0
        if design.border: design.border_style=BORDERS[border_selected-1]
    if design.border and design.border_style in ('stars','hearts','streamers'):
        full_width()
        _,design.border_size=imgui.slider_int('##border_size',design.border_size,8,24,'Ornament size: %d')
    _, design.dither = imgui.checkbox('Dither grayscale', design.dither)
    if imgui.is_item_hovered():
        imgui.set_tooltip('Use a pattern of black dots to represent gray tones.')
    imgui.spacing()
    imgui.separator()
    imgui.spacing()
    if imgui.collapsing_header('Saved templates'):
        imgui.text_disabled('Template file')
        full_width()
        _, editor.template_path = imgui.input_text('##template', editor.template_path)
        width = (imgui.get_content_region_avail().x-10)/2
        if imgui.button('Save template', (width, 0)):
            editor.save(template=True)
        imgui.same_line()
        imgui.begin_disabled(busy)
        if imgui.button('Load template', (width, 0)):
            editor.load()
            editor.image_description = ''
        imgui.end_disabled()


def canvas(editor, height):
    try:
        pixel_width, pixel_height = dimensions(editor.design)
    except ValueError:
        imgui.text_wrapped(editor.error)
        return
    heading('LABEL PREVIEW')
    imgui.same_line()
    imgui.text_disabled(f' /  {editor.design.width_mm} x {editor.design.height_mm} mm')
    imgui.text_disabled('The dots you see are the dots we print.')
    imgui.spacing()
    origin = imgui.get_cursor_screen_pos()
    width = imgui.get_content_region_avail().x
    height = max(130, height)
    draw = imgui.get_window_draw_list()
    draw.add_rect_filled(origin, (origin.x+width, origin.y+height), color(BG), 10)
    # A quiet drafting surface, kept entirely outside the printed raster.
    for x in range(18, int(width)-8, 22):
        for y in range(18, int(height)-8, 22):
            draw.add_circle_filled((origin.x+x, origin.y+y), .8, color((.21,.27,.30,.7)))
    scale = max(.01, min(2, (width-80)/pixel_width, (height-72)/pixel_height))
    w, h = pixel_width*scale, pixel_height*scale
    x, y = origin.x+(width-w)/2, origin.y+(height-h)/2
    if editor.design.shape == 'round':
        draw.add_circle_filled((x+w/2+5,y+h/2+8),w/2,color((0,0,0,.30)),96)
        draw.add_circle_filled((x+w/2,y+h/2),w/2,0xffffffff,96)
    else:
        draw.add_rect_filled((x+5,y+8),(x+w+5,y+h+8),color((0,0,0,.30)),8)
        draw.add_rect_filled((x,y),(x+w,y+h),0xffffffff,6)
    draw.push_clip_rect((x,y),(x+w,y+h),True)
    for start, row, end in editor.spans:
        draw.add_rect_filled((x+start*scale,y+row*scale),
                             (x+end*scale,y+(row+1)*scale),0xff101010)
    draw.pop_clip_rect()
    ink = color(MUTED)
    draw.add_line((x,y-16),(x+w,y-16),ink)
    for end in (x,x+w):
        draw.add_line((end,y-20),(end,y-12),ink)
    label = f'{editor.design.width_mm} mm'
    size = imgui.calc_text_size(label)
    draw.add_rect_filled((x+w/2-size.x/2-6,y-26),(x+w/2+size.x/2+6,y-7),color(BG))
    draw.add_text((x+w/2-size.x/2,y-25),ink,label)
    imgui.dummy((width,height))


def preview(editor, body_height):
    editor.refresh()
    canvas(editor, body_height-270)
    if editor.error or editor.warnings:
        imgui.text_colored((1,.68,.40,1),'Check your label')
        imgui.text_wrapped(editor.error or editor.warnings[0])
    else:
        w,h = editor.image.size
        imgui.text_disabled(f'{min(w,384)} x {h} print dots / Monochrome / Centered')
        if w>384:
            imgui.text_disabled(f'48 mm printable width; {(w-384)/16:g} mm blank on each side.')
    imgui.spacing()
    imgui.text_disabled('Export location')
    full_width()
    _, editor.export_path = imgui.input_text('##export',editor.export_path)
    imgui.begin_disabled(editor.image is None)
    if imgui.button('Export PNG'):
        editor.save()
    imgui.end_disabled()


def draw(editor, root):
    if not getattr(editor, '_themed', False):
        theme()
        editor._themed = True
    imgui.push_font(None, 26)
    imgui.text('N20')
    imgui.same_line()
    imgui.text_colored(ACCENT, 'TofuPrint')
    imgui.pop_font()
    imgui.spacing()
    available = imgui.get_content_region_avail()
    body_height = max(280, available.y-164)
    left = min(350, available.x*.38)
    flags = imgui.ChildFlags_.borders | imgui.ChildFlags_.always_use_window_padding
    imgui.begin_child('design_card', (left,body_height),flags)
    content(editor,root)
    imgui.end_child()
    imgui.same_line()
    imgui.begin_child('preview_card',(0,body_height),flags)
    preview(editor,body_height)
    imgui.end_child()
    imgui.spacing()
    imgui.begin_child('print_card',(0,0),flags)
    busy = editor.job is not None or editor.file_dialog is not None
    imgui.begin_disabled(busy)
    if imgui.button('Check printer',(136,38)):
        editor.start(printer.identify)
    imgui.same_line()
    imgui.set_next_item_width(180)
    _, darkness = imgui.combo('##darkness',editor.darkness-1,['Light ink','Normal ink','Dark ink'])
    editor.darkness=darkness+1
    if imgui.is_item_hovered():
        imgui.set_tooltip('Printer heat setting. Image brightness is adjusted in the Image tab.')
    imgui.same_line()
    remaining = imgui.get_content_region_avail().x
    if remaining > 185:
        imgui.set_cursor_pos_x(imgui.get_cursor_pos_x()+remaining-185)
    imgui.begin_disabled(editor.image is None or bool(editor.warnings))
    caption = 'Print receipt' if editor.design.media_type == 'continuous' else 'Print one label'
    if primary(caption,(185,38)):
        editor.start(printer.print_label,editor.image.copy(),editor.darkness,editor.design.media_type)
    imgui.end_disabled()
    imgui.end_disabled()
    imgui.text_colored(ACCENT if busy else MUTED,'WORKING' if busy else 'STATUS')
    imgui.same_line()
    imgui.text_wrapped(editor.status)
    imgui.end_child()
