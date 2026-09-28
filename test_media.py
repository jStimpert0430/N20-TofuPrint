# SPDX-License-Identifier: GPL-3.0-or-later WITH LicenseRef-ImGui-Bundle-exception
from dataclasses import replace, asdict
import json
from pathlib import Path
import struct
import tempfile
import unittest
from PIL import Image
from label import Design, PRESETS, render, encode


class Media(unittest.TestCase):
    def test_all_presets_have_matching_raster_dimensions(self):
        for name,w,h,shape,mode in PRESETS:
            with self.subTest(name=name):
                image,_=render(Design(text='Test',width_mm=w,height_mm=h,shape=shape,media_type=mode))
                self.assertEqual(image.size,(w*8,h*8))
                data=encode(image,media_type=mode)
                row_bytes,rows=struct.unpack('<HH',data[19:23])
                self.assertEqual((row_bytes,rows),(min(w,48),h*8))
                self.assertEqual(len(data)-23,row_bytes*rows)

    def test_media_mode_changes_only_mode_byte(self):
        image=Image.new('1',(320,240),1)
        original=encode(image)
        for mode,value in [('gap',1),('continuous',0),('black_mark',2)]:
            result=encode(image,media_type=mode)
            self.assertEqual(result[4],value)
            self.assertEqual(result[:4]+result[5:],original[:4]+original[5:])

    def test_50mm_uses_center_48mm_and_white_preview_edges(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'black.png'
            Image.new('L',(500,500),0).save(path)
            image,_=render(Design(image_path=str(path),width_mm=50,height_mm=50,margin=4))
            self.assertEqual(set(image.crop((0,0,8,400)).tobytes()),{255})
            self.assertEqual(set(image.crop((392,0,400,400)).tobytes()),{255})
            data=encode(image)
            self.assertEqual(data[23:],bytes(v^255 for v in image.crop((8,0,392,400)).tobytes()))

    def test_round_image_fits_inside_circle_and_border_is_round(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'black.png'
            Image.new('L',(320,320),0).save(path)
            image,warnings=render(Design(image_path=str(path),shape='round',height_mm=40,border=True))
            self.assertFalse(warnings)
            self.assertEqual(image.getpixel((16,16)),255)
            self.assertEqual(image.getpixel((160,16)),0)
            for y in range(320):
                for x in range(320):
                    if (x-159.5)**2+(y-159.5)**2>160**2:
                        self.assertEqual(image.getpixel((x,y)),255)

    def test_old_templates_keep_original_roll(self):
        d=Design(**{'text':'Old'})
        self.assertEqual((d.width_mm,d.height_mm,d.shape,d.media_type),(40,30,'rectangle','gap'))

    def test_new_roll_settings_roundtrip(self):
        d=Design(width_mm=38,height_mm=120,media_type='continuous')
        self.assertEqual(Design(**json.loads(json.dumps(asdict(d)))),d)

    def test_invalid_media_does_not_render_or_encode(self):
        for d in [Design(width_mm=58),Design(height_mm=1000),Design(shape='round'),
                  Design(media_type='unknown'),Design(height_mm=10,margin=48)]:
            with self.assertRaises(ValueError): render(d)
        with self.assertRaises(ValueError): encode(Image.new('1',(320,240)),media_type='unknown')


if __name__=='__main__': unittest.main()
