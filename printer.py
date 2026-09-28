# SPDX-License-Identifier: GPL-3.0-or-later WITH LicenseRef-ImGui-Bundle-exception
"""USB-only transport. No cloud, shell commands, daemon or vendor dependencies."""
import re
import time
import logging
import sys
import libusb_package
from contextlib import contextmanager
import usb.core
import usb.util
from label import encode, decode_status, STATUS_QUERY

VID, PID = 0x0483, 0x5602
log = logging.getLogger('n20.usb')


@contextmanager
def connection():
    devices = list(usb.core.find(find_all=True, idVendor=VID, idProduct=PID,
                                backend=libusb_package.get_libusb1_backend()))
    if len(devices) != 1:
        raise RuntimeError('Connect exactly one N20 printer by USB and switch it on')
    device = devices[0]
    detached = claimed = False
    try:
        interface = device.get_active_configuration()[(0, 0)]
        if interface.bInterfaceClass != 7:
            raise RuntimeError('Device is not a USB printer')
        if sys.platform != 'win32' and device.is_kernel_driver_active(0):
            device.detach_kernel_driver(0)
            detached = True
        usb.util.claim_interface(device, 0)
        claimed = True
        identity = bytes(device.ctrl_transfer(0xa1, 0, 0, 0, 1024, timeout=2000))[2:]
        if not re.search(rb'(?:^|;)MDL:N20;', identity):
            raise RuntimeError('USB device did not identify itself as model N20')
        endpoints = {e.bEndpointAddress for e in interface}
        if not {0x02, 0x81} <= endpoints:
            raise RuntimeError('Unexpected printer endpoints')
        yield device, identity.rstrip(b'\0').decode('ascii', errors='replace')
    except usb.core.USBError as exc:
        if exc.errno == 13:
            raise RuntimeError('USB permission denied. See README for the device-specific udev rule.') from exc
        raise
    finally:
        try:
            if claimed:
                usb.util.release_interface(device, 0)
        finally:
            try:
                if detached:
                    device.attach_kernel_driver(0)
            finally:
                usb.util.dispose_resources(device)


def identify():
    with connection() as (_, identity):
        return identity


def write_exact(device, data):
    # Do not replay a job on timeout/short write: it could print twice or leave a partial raster.
    log.info('USB OUT: %d bytes', len(data))
    count = device.write(0x02, data, timeout=5000)
    if count != len(data):
        raise RuntimeError(f'Incomplete USB write ({count}/{len(data)} bytes). Power-cycle printer before retrying.')


def ready(device):
    # N20 sometimes ignores the first query, including immediately after power-on.
    # Poll only the status request, never the label raster.
    deadline = time.monotonic() + 5
    next_query = 0
    raw = bytearray()
    while len(raw) < 4 and time.monotonic() < deadline:
        now = time.monotonic()
        if now >= next_query and not raw:
            write_exact(device, STATUS_QUERY)
            next_query = now + .5
        try:
            part = bytes(device.read(0x81, 64, timeout=250))
        except usb.core.USBTimeoutError:
            continue  # A short read timeout is not the overall readiness deadline.
        log.info('USB status IN: %s', part.hex(' '))
        raw.extend(part)
    if len(raw) < 4:
        raise RuntimeError('Printer readiness reply timed out; no label data was sent. '
                           'Switch the printer off and on before retrying.')
    return decode_status(bytes(raw))


def print_label(image, darkness=2, media_type='gap'):
    data = encode(image, darkness, media_type)
    stage = 'opening USB connection'
    raster_started = False
    try:
        with connection() as (device, _):
            stage = 'configuring media and darkness'
            log.info(stage)
            write_exact(device, data[:10])
            stage = 'waiting for printer readiness'
            log.info(stage)
            ready(device)
            stage = 'sending label raster'
            log.info(stage)
            raster_started = True
            write_exact(device, data[10:])
            stage = 'releasing USB connection'
    except Exception as exc:
        log.exception('Print failed while %s; raster_started=%s', stage, raster_started)
        if raster_started:
            raise RuntimeError(f'{stage}: {exc}. The label may have been partially or fully sent; '
                               'check the printer before retrying.') from exc
        raise RuntimeError(f'{stage}: {exc}. No label raster was sent.') from exc
    log.info('Raster transfer completed')
    return 'Label sent over USB. Check the printed result; physical completion is not confirmed.'
