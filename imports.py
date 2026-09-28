# SPDX-License-Identifier: GPL-3.0-or-later WITH LicenseRef-ImGui-Bundle-exception
"""Bounded image imports. Web pages are parsed as text, never executed."""
from dataclasses import dataclass
from hashlib import sha256
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
import time
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener
import warnings
import ssl
import certifi
from urllib.request import HTTPSHandler

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 16 * 1024 * 1024
MAX_PIXELS = 16_000_000


@dataclass(frozen=True)
class ImportedImage:
    path: str
    description: str


def validate_url(url):
    url = url.strip()
    parts = urlsplit(url)
    if parts.scheme.lower() not in ('http', 'https') or not parts.hostname:
        raise ValueError('Enter an http:// or https:// image or web-page link.')
    if parts.username is not None or parts.password is not None:
        raise ValueError('Links containing login credentials are not supported.')
    return url


class WebRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, deadline):
    url = validate_url(url)
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('Image import timed out.')
    request = Request(url, headers={'User-Agent': 'N20Labels/0.1',
                                   'Accept': 'image/*,text/html;q=0.8',
                                   'Accept-Encoding': 'identity'})
    with build_opener(WebRedirects(), HTTPSHandler(context=ssl.create_default_context(cafile=certifi.where()))).open(request, timeout=min(8, remaining)) as response:
        if int(response.headers.get('Content-Length', '0')) > MAX_BYTES:
            raise ValueError('Image or page exceeds the 16 MB download limit.')
        chunks, size = [], 0
        while True:
            if time.monotonic() >= deadline:
                raise TimeoutError('Image import timed out.')
            chunk = response.read(65536)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_BYTES:
                raise ValueError('Image or page exceeds the 16 MB download limit.')
            chunks.append(chunk)
        return b''.join(chunks), response.headers.get_content_type(), response.geturl()


class PageImages(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.featured, self.images = [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta' and (attrs.get('property') or attrs.get('name') or '').lower() in (
                'og:image', 'og:image:url', 'og:image:secure_url', 'twitter:image', 'twitter:image:src'):
            if attrs.get('content') and len(self.featured) < 20:
                self.featured.append(attrs['content'])
        if tag == 'img' and len(self.images) < 40:
            source = attrs.get('src') or attrs.get('data-src')
            if source:
                self.images.append(source)

    def candidates(self, base):
        result = []
        for link in self.featured + self.images:
            try:
                url = validate_url(urljoin(base, link))
            except ValueError:
                continue
            if url not in result:
                result.append(url)
        return result[:6]


def cache_image(data, cache, description):
    if len(data) > MAX_BYTES:
        raise ValueError('Image exceeds the 16 MB import limit.')
    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        with Image.open(BytesIO(data)) as source:
            if source.width * source.height > MAX_PIXELS:
                raise ValueError('Image exceeds the 16 megapixel limit.')
            source.seek(0)  # Animated images use their first frame.
            image = ImageOps.exif_transpose(source).convert('RGBA')
            image.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
    output = BytesIO()
    image.save(output, format='PNG')
    normalized = output.getvalue()
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / (sha256(normalized).hexdigest() + '.png')
    path.write_bytes(normalized)
    return ImportedImage(str(path.resolve()), description)


def import_file(path, cache):
    path = Path(path).expanduser()
    with path.open('rb') as stream:
        data = stream.read(MAX_BYTES+1)
    return cache_image(data, cache, path.name)


def import_link(url, cache):
    deadline = time.monotonic() + 30
    data, content_type, final_url = fetch(url, deadline)
    try:
        return cache_image(data, cache, f'Image from {urlsplit(final_url).hostname}')
    except UnidentifiedImageError:
        if content_type not in ('text/html', 'application/xhtml+xml'):
            raise ValueError('That link did not return a supported image or web page.') from None
    page = PageImages()
    page.feed(data.decode('utf-8', errors='replace'))
    for candidate in page.candidates(final_url):
        try:
            image, _, resolved = fetch(candidate, deadline)
            return cache_image(image, cache, f'Image found on {urlsplit(final_url).hostname}')
        except (OSError, ValueError):
            continue
    raise ValueError('No downloadable image found. Try a direct image link; login-only or JavaScript pages are not supported.')
