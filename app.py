#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH LicenseRef-ImGui-Bundle-exception
"""N20 Labels: a small, offline Dear ImGui label editor."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import json
import logging
import os
import sys
from pathlib import Path

from imgui_bundle import hello_imgui, imgui, portable_file_dialogs as dialogs
from label import Design, render, WIDTH, HEIGHT
import printer
from imports import ImportedImage, import_file, import_link

if getattr(sys, 'frozen', False):
    data_home = Path(os.environ.get('LOCALAPPDATA', str(Path.home()/'AppData'/'Local'))) if sys.platform=='win32' else Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local'/'share')))
    ROOT = data_home/'N20TofuPrint'
else:
    ROOT = Path(__file__).resolve().parent


class Editor:
    def __init__(self, smoke=False):
        self.design = Design()
        self.darkness = 2
        self.image = None
        self.spans = []
        self.warnings = []
        self.error = ''
        self.signature = None
        self.status = 'Connect your N20 over USB. Nothing prints until you click Print.'
        self.export_path = str(ROOT / 'output' / 'label.png')
        self.template_path = str(ROOT / 'output' / 'label.json')
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.job = None
        self.job_kind = ''
        self.file_dialog = None
        self.web_link = ''
        self.image_description = ''
        self.smoke = smoke
        self.frames = 0

    def start(self, fn, *args, kind='USB operation'):
        if self.job is None:
            self.job_kind = kind
            self.status = f'{kind} in progress...'
            self.job = self.pool.submit(fn, *args)

    def finish_job(self):
        if self.job is None or not self.job.done():
            return
        try:
            result = self.job.result()
            if isinstance(result, ImportedImage):
                self.design.image_path = result.path
                self.design.pattern = ''
                self.image_description = result.description
                self.signature = None
                self.status = f'Imported {result.description}'
            else:
                self.status = result
        except Exception as exc:
            self.status = f'{self.job_kind} failed: {exc}'
        self.job = None

    def refresh(self):
        signature = tuple(asdict(self.design).values())
        if signature == self.signature:
            return
        self.signature = signature
        self.image, self.spans, self.warnings, self.error = None, [], [], ''
        try:
            self.image, self.warnings = render(self.design)
            pixels = self.image.load()
            width, height = self.image.size
            for y in range(height):
                start = None
                for x in range(width+1):
                    black = x < width and pixels[x, y] == 0
                    if black and start is None:
                        start = x
                    elif not black and start is not None:
                        self.spans.append((start, y, x))
                        start = None
        except Exception as exc:
            self.error = str(exc)

    def save(self, template=False):
        try:
            path = Path(self.template_path if template else self.export_path).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            if template:
                path.write_text(json.dumps(asdict(self.design), ensure_ascii=False, indent=2))
            else:
                self.image.save(path, format='PNG', dpi=(203.2, 203.2))
            self.status = f'Saved {path}'
        except Exception as exc:
            self.status = str(exc)

    def load(self):
        try:
            data = json.loads(Path(self.template_path).expanduser().read_text())
            design = Design(**data)
            render(design)  # Validate before replacing the current design.
            self.design = design
            self.signature = None
            self.status = 'Template loaded'
        except Exception as exc:
            self.status = str(exc)

    def draw(self):
        self.finish_job()
        if self.file_dialog is not None and self.file_dialog.ready(0):
            paths = self.file_dialog.result()
            self.file_dialog = None
            if paths:
                self.start(import_file, paths[0], ROOT/'output'/'imports', kind='Image import')
            else:
                self.status = 'Image import cancelled.'

        from ui import draw
        draw(self, ROOT)
        self.frames += 1
        if self.smoke and self.frames >= 8:
            hello_imgui.get_runner_params().app_shall_exit = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke-test', action='store_true', help='Render eight frames and exit; never accesses USB')
    parser.add_argument('--identify', action='store_true', help='Read the USB model ID without printing')
    args = parser.parse_args()
    (ROOT / 'output').mkdir(parents=True, exist_ok=True)
    from logging.handlers import RotatingFileHandler
    handler = RotatingFileHandler(ROOT / 'output' / 'usb.log', maxBytes=262144, backupCount=2)
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    printer.log.addHandler(handler)
    printer.log.setLevel(logging.INFO)
    if args.identify:
        print(printer.identify())
        return
    editor = Editor(args.smoke_test)
    try:
        params = hello_imgui.RunnerParams()
        params.app_window_params.window_title = 'N20 TofuPrint'
        params.app_window_params.window_geometry.size = (1120,850)
        params.callbacks.show_gui = editor.draw
        params.fps_idling.fps_idle = 8
        params.ini_filename_use_app_window_title = False
        params.ini_filename = str(ROOT/'output'/'window.ini')
        hello_imgui.run(params)
    finally:
        if editor.file_dialog is not None:
            editor.file_dialog.kill()
        editor.pool.shutdown(wait=True)


if __name__ == '__main__':
    main()
