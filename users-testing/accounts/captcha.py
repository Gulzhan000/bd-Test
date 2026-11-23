import secrets
import struct
import zlib
from datetime import timedelta
from hmac import compare_digest

from django.utils import timezone

from .models import LoginChallenge

GLYPHS = {
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
}


def new_challenge(request):
    if request.session.session_key is None:
        request.session.create()
    now = timezone.now()
    LoginChallenge.objects.filter(expires_at__lte=now).delete()
    return LoginChallenge.objects.create(
        session_key=request.session.session_key,
        code="".join(secrets.choice(tuple(GLYPHS)) for _ in range(5)),
        expires_at=now + timedelta(minutes=5),
    )


def check_challenge(request, challenge_id, answer):
    candidates = LoginChallenge.objects.filter(
        pk=challenge_id,
        session_key=request.session.session_key,
        expires_at__gt=timezone.now(),
    )
    code = candidates.values_list("code", flat=True).first()
    if code is None:
        return False
    # A concurrent submission can read the code, but only one can delete it.
    deleted, _ = candidates.delete()
    return bool(deleted) and compare_digest(code.encode(), answer.encode())


def png_chunk(kind, data):
    payload = kind + data
    return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload))


def draw_challenge(code):
    width, height = 220, 65
    palette = bytes.fromhex("e0f2fe 7aa4bc 15354b")
    rows = [bytearray(width) for _ in range(height)]
    for _ in range(300):
        x, y = secrets.randbelow(width), secrets.randbelow(height)
        rows[y][x] = 1
    for index, character in enumerate(code):
        left = 13 + index * 42
        top = 12 + secrets.randbelow(12)
        slant = secrets.choice((-1, 0, 1))
        for row, pixels in enumerate(GLYPHS[character]):
            for column, pixel in enumerate(pixels):
                if pixel == "1":
                    for offset in range(7):
                        y = top + row * 7 + offset
                        x = left + column * 7 + slant * (row - 2)
                        rows[y][x:x + 7] = b"\x02" * 7
    data = b"".join(b"\x00" + row for row in rows)
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 3, 0, 0, 0))
        + png_chunk(b"PLTE", palette)
        + png_chunk(b"IDAT", zlib.compress(data))
        + png_chunk(b"IEND", b"")
    )
