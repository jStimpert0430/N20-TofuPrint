# SPDX-License-Identifier: GPL-3.0-or-later WITH LicenseRef-ImGui-Bundle-exception
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from PIL import Image, ImageOps
from label import Design, render


class Brightness(unittest.TestCase):
    def test_default_preserves_previous_render_exactly(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'gradient.png'
            original = Image.linear_gradient('L').resize((90, 60)).convert('RGBA')
            original.putalpha(180)
            original.save(path)
            white = Image.new('RGBA',original.size,'white')
            white.alpha_composite(original)
            fitted = ImageOps.contain(white.convert('L'), (288,208))
            baseline = Image.new('L',(320,240),255)
            baseline.paste(fitted,((320-fitted.width)//2,(240-fitted.height)//2))
            for dither in (True, False):
                expected = baseline.convert('1',dither=Image.Dither.FLOYDSTEINBERG) if dither else baseline.point(lambda v: 255 if v>=128 else 0,mode='1')
                actual,_ = render(Design(image_path=str(path),dither=dither))
                self.assertEqual(actual.tobytes(),expected.tobytes())

    def test_lightening_reduces_printed_black_dots(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'image.png'
            Image.new('L',(100,100),100).save(path)
            for dither in (True, False):
                design = Design(image_path=str(path),dither=dither)
                before,_ = render(design)
                after,_ = render(replace(design,image_brightness=2.0))
                self.assertLess(after.histogram()[0],before.histogram()[0])

    def test_text_is_not_affected(self):
        base = Design(text='Test label',border=True)
        self.assertEqual(render(base)[0].tobytes(),render(replace(base,image_brightness=3.0))[0].tobytes())

    def test_old_templates_default_to_original_brightness(self):
        self.assertEqual(Design(**{'text':'Old template','image_path':''}).image_brightness,1.0)

    def test_invalid_brightness_is_rejected(self):
        for value in (0, 4, float('nan'), float('inf')):
            with self.assertRaises(ValueError): render(Design(image_brightness=value))


if __name__ == '__main__': unittest.main()
