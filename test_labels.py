# SPDX-License-Identifier: GPL-3.0-or-later WITH LicenseRef-ImGui-Bundle-exception
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image
from label import Design, render, encode, decode_status
import printer


class Labels(unittest.TestCase):
    def test_blank_polarity(self):
        data = encode(Image.new('1', (320,240), 1))
        self.assertEqual(data[:10], bytes.fromhex('1f11050a01 1f11050202'))
        self.assertEqual(data[10:19], bytes.fromhex('1f11053500 1d763000'))
        self.assertEqual(data[19:23], struct.pack('<HH', 40, 240))
        self.assertEqual(data[23:], bytes(9600))

    def test_black_bits_are_msb_first_and_rows_top_down(self):
        im = Image.new('1', (320,240), 1)
        im.putpixel((0,0), 0); im.putpixel((7,0), 0); im.putpixel((8,1), 0)
        payload = encode(im)[23:]
        self.assertEqual(payload[0], 0x81)
        self.assertEqual(payload[41], 0x80)
        self.assertEqual(sum(payload), 0x101)

    def test_reject_bad_dimensions_mode_and_darkness(self):
        for im, darkness in [(Image.new('1',(10,10)),2), (Image.new('RGB',(320,240)),2),
                              (Image.new('1',(320,240)),255)]:
            with self.assertRaises(ValueError): encode(im, darkness)

    def test_native_render_and_overflow(self):
        im, warnings = render(Design(text='Björn'))
        self.assertEqual(im.mode, '1'); self.assertEqual(im.size, (320,240))
        self.assertFalse(warnings)
        self.assertTrue(render(Design(text='W'*80))[1])

    def test_transparent_image_renders_white(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'input.png'
            Image.new('RGBA',(12,12),(0,0,0,0)).save(p)
            im, _ = render(Design(image_path=str(p)))
            self.assertEqual(set(im.tobytes()), {255})

    def test_status_fail_closed(self):
        self.assertEqual(decode_status(bytes.fromhex('1c20000d')), 'Ready')
        for data in [b'', bytes.fromhex('1c20010d'), bytes.fromhex('1c20000d00'), b'xxxx']:
            with self.assertRaises(RuntimeError): decode_status(data)

    def test_short_write_is_not_retried(self):
        device = MagicMock(); device.write.return_value = 1
        with self.assertRaises(RuntimeError): printer.write_exact(device,b'123')
        device.write.assert_called_once()

    def test_readiness_tolerates_one_short_timeout_and_split_reply(self):
        device = MagicMock()
        device.write.side_effect = lambda endpoint, data, timeout: len(data)
        device.read.side_effect = [printer.usb.core.USBTimeoutError('timeout'),
                                  bytes.fromhex('1c20'), bytes.fromhex('000d')]
        self.assertEqual(printer.ready(device), 'Ready')
        device.write.assert_called_once()  # Never repeat a print or even the query here.

    def test_readiness_deadline_is_bounded_and_descriptive(self):
        device = MagicMock()
        device.write.side_effect = lambda endpoint, data, timeout: len(data)
        device.read.side_effect = printer.usb.core.USBTimeoutError('timeout')
        with patch.object(printer.time, 'monotonic', side_effect=[0, 0, 0, 6]):
            with self.assertRaisesRegex(RuntimeError, 'no label data was sent'):
                printer.ready(device)
        self.assertEqual(device.read.call_count, 1)

    def test_missing_first_reply_requeries_without_resending_label(self):
        device = MagicMock()
        device.write.side_effect = lambda endpoint, data, timeout: len(data)
        device.read.side_effect = [printer.usb.core.USBTimeoutError('timeout'),
                                  bytes.fromhex('1c20000d')]
        with patch.object(printer.time, 'monotonic', side_effect=[0, 0, 0, .6, .6]):
            self.assertEqual(printer.ready(device), 'Ready')
        self.assertEqual(device.write.call_count, 2)
        for call in device.write.call_args_list:
            self.assertEqual(call.args, (0x02, printer.STATUS_QUERY))

    def test_not_ready_does_not_send_raster(self):
        device = MagicMock()
        device.write.side_effect = lambda endpoint, data, timeout: len(data)
        device.read.return_value = bytes.fromhex('1c20010d')
        from contextlib import contextmanager
        @contextmanager
        def connection(): yield device, 'N20'
        with patch.object(printer, 'connection', connection):
            with self.assertRaises(RuntimeError): printer.print_label(Image.new('1',(320,240),1))
        self.assertEqual(device.write.call_count, 2)  # setup and status only


if __name__ == '__main__':
    unittest.main()
