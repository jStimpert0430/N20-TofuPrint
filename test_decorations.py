# SPDX-License-Identifier: GPL-3.0-or-later WITH LicenseRef-ImGui-Bundle-exception
from dataclasses import asdict
import json
import unittest
from PIL import Image, ImageDraw
from decorations import BORDERS, PATTERNS, pattern_image
from label import Design, render, encode


class Decorations(unittest.TestCase):
    def test_every_border_and_pattern_on_supported_shapes(self):
        for shape,w,h in [('rectangle',40,30),('round',50,50),('rectangle',38,150)]:
            for border in BORDERS:
                with self.subTest(shape=shape,border=border):
                    image,warnings=render(Design(text='',width_mm=w,height_mm=h,shape=shape,
                                                border=True,border_style=border))
                    self.assertFalse(warnings)
                    self.assertGreater(image.histogram()[0],0)
                    self.assertGreater(len(encode(image)),23)
            for pattern in PATTERNS:
                with self.subTest(shape=shape,pattern=pattern):
                    image,warnings=render(Design(width_mm=w,height_mm=h,shape=shape,pattern=pattern))
                    self.assertFalse(warnings)
                    self.assertGreater(image.histogram()[0],0)
                    self.assertEqual(image.getpixel((0,0)),255)

    def test_old_solid_border_output_is_unchanged(self):
        for shape,h in [('rectangle',30),('round',40)]:
            expected=Image.new('1',(320,h*8),1)
            draw=ImageDraw.Draw(expected)
            fn=draw.ellipse if shape=='round' else draw.rectangle
            fn((16,16,303,h*8-17),outline=0,width=2)
            actual,_=render(Design(text='',border=True,shape=shape,height_mm=h))
            self.assertEqual(actual.tobytes(),expected.tobytes())

    def test_patterns_are_deterministic_and_distinct(self):
        results=set()
        for kind in PATTERNS:
            first=pattern_image((120,120),kind).tobytes()
            self.assertEqual(first,pattern_image((120,120),kind).tobytes())
            results.add(first)
        self.assertEqual(len(results),len(PATTERNS))

    def test_pattern_replaces_image_without_loading_it(self):
        image,warnings=render(Design(pattern='hearts',image_path='/missing-file.png'))
        self.assertFalse(warnings)
        self.assertGreater(image.histogram()[0],0)

    def test_round_border_does_not_print_outside_circle(self):
        for border in BORDERS:
            im,_=render(Design(text='',border=True,border_style=border,shape='round',height_mm=40,margin=4))
            for y in range(320):
                for x in range(320):
                    if (x-159.5)**2+(y-159.5)**2>160**2:
                        self.assertEqual(im.getpixel((x,y)),255)

    def test_settings_round_trip_and_old_templates(self):
        design=Design(pattern='stars',border=True,border_style='hearts',border_size=20,pattern_spacing=40)
        self.assertEqual(Design(**json.loads(json.dumps(asdict(design)))),design)
        old=Design(**{'border':True,'text':'Old'})
        self.assertEqual(old.border_style,'solid')
        self.assertEqual(old.pattern,'')

    def test_invalid_decorations_rejected(self):
        for design in [Design(pattern='bad'),Design(border_style='bad'),Design(border_size=100),
                       Design(pattern_spacing=0),Design(pattern_weight=0),
                       Design(height_mm=10,margin=30,border=True,border_style='stars',border_size=24)]:
            with self.assertRaises(ValueError): render(design)


if __name__=='__main__': unittest.main()
