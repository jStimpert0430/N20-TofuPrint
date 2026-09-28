# SPDX-License-Identifier: GPL-3.0-or-later WITH LicenseRef-ImGui-Bundle-exception
from concurrent.futures import Future
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import imports


def png():
    output = BytesIO()
    Image.new('RGBA', (60, 40), (255, 0, 0, 128)).save(output, 'PNG')
    return output.getvalue()


class Imports(unittest.TestCase):
    def test_local_file_is_copied_and_normalized(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root)/'source.png'
            source.write_bytes(png())
            result = imports.import_file(source, Path(root)/'cache')
            source.unlink()
            with Image.open(result.path) as im:
                self.assertEqual(im.size, (60, 40))
                self.assertEqual(im.getpixel((0,0)), (255,0,0,128))

    def test_direct_url_does_not_require_file_extension(self):
        with tempfile.TemporaryDirectory() as root, patch.object(imports, 'fetch',
                return_value=(png(), 'application/octet-stream', 'https://example.org/image?id=2')):
            result = imports.import_link('https://example.org/image?id=2', root)
            self.assertTrue(Path(result.path).is_file())

    def test_page_prefers_featured_image_and_resolves_relative_redirected_base(self):
        page = b'<img src="/logo.png"><meta property="og:image" content="../photo.png">'
        with tempfile.TemporaryDirectory() as root, patch.object(imports, 'fetch', side_effect=[
                (page, 'text/html', 'https://example.org/posts/1'),
                (png(), 'image/png', 'https://example.org/photo.png')]) as fetch:
            result = imports.import_link('https://example.org/short', root)
            self.assertEqual(fetch.call_args_list[1].args[0], 'https://example.org/photo.png')
            self.assertTrue(Path(result.path).is_file())

    def test_page_skips_broken_candidate(self):
        page = b'<img src="/bad"><img src="/good">'
        with tempfile.TemporaryDirectory() as root, patch.object(imports, 'fetch', side_effect=[
                (page, 'text/html', 'https://example.org'), OSError('404'),
                (png(), 'image/png', 'https://example.org/good')]):
            self.assertTrue(Path(imports.import_link('https://example.org',root).path).is_file())

    def test_reject_non_web_urls_and_credentials(self):
        for url in ['file:///etc/passwd', 'ftp://example.org/a', 'javascript:alert(1)',
                    'https://user:password@example.org/a', 'not a url']:
            with self.assertRaises(ValueError): imports.validate_url(url)

    def test_invalid_image_and_size_limits(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(OSError): imports.cache_image(b'not image',root,'test')
            with patch.object(imports,'MAX_BYTES',4):
                with self.assertRaises(ValueError): imports.cache_image(png(),root,'test')
            with patch.object(imports,'MAX_PIXELS',4):
                with self.assertRaises(ValueError): imports.cache_image(png(),root,'test')

    def test_failed_import_preserves_current_label(self):
        from app import Editor
        editor = Editor(smoke=True)
        try:
            editor.design.image_path = 'old-image.png'
            editor.job_kind = 'Web image import'
            editor.job = Future()
            editor.job.set_exception(ValueError('No image found'))
            editor.finish_job()
            self.assertEqual(editor.design.image_path, 'old-image.png')
            self.assertIn('Web image import failed',editor.status)
            self.assertIsNone(editor.job)
        finally: editor.pool.shutdown()

    def test_successful_import_updates_canvas_on_main_thread(self):
        from app import Editor
        editor = Editor(smoke=True)
        try:
            editor.job = Future()
            editor.job.set_result(imports.ImportedImage('cached.png','test image'))
            editor.finish_job()
            self.assertEqual(editor.design.image_path,'cached.png')
            self.assertEqual(editor.image_description,'test image')
        finally: editor.pool.shutdown()


if __name__ == '__main__': unittest.main()
