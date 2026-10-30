#!/usr/bin/env python3
"""Check recipe photographs: your own, beside their recipe, small, and blank inside.

A photo of a dish is allowed when the household took it, and only in Cooklang's
place for one: `name.jpg` beside `name.cook` is the recipe's photo, and
`name.3.jpg` is the photo for step 3. JPEG and WebP only.

The danger in a photograph is not the dish but what the camera wrote into the
file: GPS coordinates of the kitchen, the phone's make and serial, the time, and
sometimes the owner's name. So a photo with any EXIF, XMP, IPTC or comment
block fails here, rather than being quietly cleaned, and `--strip` is the
deliberate step that removes them. The check reads the file's structure itself:
no image library, for the same reason tools/check_recipes.py has none.

    python3 -m tools.check_images              every photo under recipes/
    python3 -m tools.check_images PATH ...     specific files (how pre-commit calls it)
    python3 -m tools.check_images --strip PATH ...
                                               remove the metadata blocks, in place
"""

from __future__ import annotations

import argparse
import re
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RECIPES_DIR = REPO_ROOT / "recipes"

SUFFIXES = (".jpg", ".webp")
# Matches the large-file hook in .pre-commit-config.yaml.
MAX_BYTES = 256 * 1024
MAX_SIDE = 1600

# `name.jpg` or `name.3.jpg`, where `name.cook` is beside it.
STEP = re.compile(r"^(?P<stem>.+?)(?:\.(?P<step>\d+))?$")

# JPEG segments that carry nothing about who took the photo or where: JFIF
# (APP0), the colour profile (APP2) and Adobe's colour transform (APP14).
JPEG_ALLOWED_APP = {0xE0, 0xE2, 0xEE}
JPEG_NAMES = {0xE1: "EXIF or XMP", 0xED: "IPTC", 0xFE: "a comment"}
# Start-of-frame markers, which carry the size. C4, C8 and CC are not frames.
JPEG_SOF = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}

WEBP_METADATA = {b"EXIF": "EXIF", b"XMP ": "XMP"}


@dataclass
class Problem:
    path: str
    message: str

    def render(self) -> str:
        return f"{self.path}: {self.message}"


@dataclass
class Segment:
    marker: int
    start: int
    end: int


def jpeg_segments(data: bytes) -> tuple[list[Segment], int] | str:
    """The header segments up to the start of scan, and where the scan starts."""
    if data[:2] != b"\xff\xd8":
        return "not a JPEG (no start-of-image marker)"
    segments: list[Segment] = []
    at = 2
    while at + 4 <= len(data):
        if data[at] != 0xFF:
            return f"broken JPEG structure at byte {at}"
        marker = data[at + 1]
        if marker == 0xFF:
            at += 1
            continue
        (length,) = struct.unpack(">H", data[at + 2 : at + 4])
        segments.append(Segment(marker, at, at + 2 + length))
        if marker == 0xDA:
            return segments, at
        at += 2 + length
    return "JPEG ends before its image data"


def check_jpeg(data: bytes, rel: str) -> tuple[list[Problem], tuple[int, int] | None]:
    parsed = jpeg_segments(data)
    if isinstance(parsed, str):
        return [Problem(rel, parsed)], None
    segments, _ = parsed
    problems: list[Problem] = []
    size = None
    for seg in segments:
        if seg.marker in JPEG_SOF:
            height, width = struct.unpack(">HH", data[seg.start + 5 : seg.start + 9])
            size = (width, height)
        elif seg.marker in JPEG_NAMES or (0xE0 <= seg.marker <= 0xEF and seg.marker not in JPEG_ALLOWED_APP):
            name = JPEG_NAMES.get(seg.marker, f"an APP{seg.marker - 0xE0} block")
            problems.append(Problem(rel, f"carries {name}; run `make strip-images`"))
    return problems, size


def strip_jpeg(data: bytes) -> bytes:
    parsed = jpeg_segments(data)
    if isinstance(parsed, str):
        raise ValueError(parsed)
    segments, scan = parsed
    kept = [
        data[s.start : s.end]
        for s in segments[:-1]
        if not (s.marker in JPEG_NAMES or (0xE0 <= s.marker <= 0xEF and s.marker not in JPEG_ALLOWED_APP))
    ]
    return b"\xff\xd8" + b"".join(kept) + data[scan:]


def webp_chunks(data: bytes) -> list[tuple[bytes, int, int]] | str:
    """(fourcc, start of payload, payload length) for each chunk."""
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return "not a WebP (no RIFF/WEBP header)"
    chunks = []
    at = 12
    while at + 8 <= len(data):
        fourcc = data[at : at + 4]
        (length,) = struct.unpack("<I", data[at + 4 : at + 8])
        chunks.append((fourcc, at + 8, length))
        at += 8 + length + (length & 1)
    return chunks


def webp_size(data: bytes, chunks: list[tuple[bytes, int, int]]) -> tuple[int, int] | None:
    for fourcc, start, _ in chunks:
        if fourcc == b"VP8X":
            w = int.from_bytes(data[start + 4 : start + 7], "little") + 1
            h = int.from_bytes(data[start + 7 : start + 10], "little") + 1
            return w, h
        if fourcc == b"VP8 ":
            w, h = struct.unpack("<HH", data[start + 6 : start + 10])
            return w & 0x3FFF, h & 0x3FFF
        if fourcc == b"VP8L":
            (bits,) = struct.unpack("<I", data[start + 1 : start + 5])
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return None


def check_webp(data: bytes, rel: str) -> tuple[list[Problem], tuple[int, int] | None]:
    chunks = webp_chunks(data)
    if isinstance(chunks, str):
        return [Problem(rel, chunks)], None
    problems = [
        Problem(rel, f"carries {WEBP_METADATA[fourcc]}; run `make strip-images`")
        for fourcc, _, _ in chunks
        if fourcc in WEBP_METADATA
    ]
    return problems, webp_size(data, chunks)


def strip_webp(data: bytes) -> bytes:
    chunks = webp_chunks(data)
    if isinstance(chunks, str):
        raise ValueError(chunks)
    out = bytearray()
    for fourcc, start, length in chunks:
        if fourcc in WEBP_METADATA:
            continue
        payload = bytearray(data[start : start + length])
        if fourcc == b"VP8X":
            payload[0] &= ~(0x08 | 0x04) & 0xFF  # the EXIF and XMP flags
        out += fourcc + struct.pack("<I", length) + payload + (b"\x00" if length & 1 else b"")
    return b"RIFF" + struct.pack("<I", 4 + len(out)) + b"WEBP" + bytes(out)


def check_file(path: Path) -> list[Problem]:
    rel = str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path)
    problems: list[Problem] = []
    suffix = path.suffix.lower()
    if suffix not in SUFFIXES or path.suffix != suffix:
        return [Problem(rel, "photos are .jpg or .webp, in lowercase")]
    if not path.is_relative_to(RECIPES_DIR):
        problems.append(Problem(rel, "photos live beside their recipe under recipes/"))
    stem = STEP.match(path.stem)
    recipe = path.with_name(f"{stem.group('stem')}.cook") if stem else None
    if recipe is None or not recipe.exists():
        problems.append(
            Problem(rel, "no recipe beside it: name it after the recipe, NAME.jpg or NAME.3.jpg for step 3")
        )

    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        problems.append(Problem(rel, f"{len(data) // 1024} KB is over {MAX_BYTES // 1024} KB; export it smaller"))
    found, size = (check_jpeg if suffix == ".jpg" else check_webp)(data, rel)
    problems += found
    if size and max(size) > MAX_SIDE:
        problems.append(Problem(rel, f"{size[0]}x{size[1]} is over {MAX_SIDE} px on its long side"))
    return problems


def image_paths(argv: list[str]) -> list[Path]:
    if argv:
        return [Path(p).resolve() for p in argv]
    return sorted(p for p in RECIPES_DIR.rglob("*") if p.suffix.lower() in SUFFIXES)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--strip", action="store_true", help="remove metadata blocks in place")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(argv)

    paths = image_paths(args.paths)
    if args.strip:
        for path in paths:
            data = path.read_bytes()
            path.write_bytes(strip_jpeg(data) if path.suffix.lower() == ".jpg" else strip_webp(data))
            print(f"stripped {path.name}")
        return 0

    problems = [p for path in paths for p in check_file(path)]
    if not problems:
        print(f"check_images: {len(paths)} photo(s) OK")
        return 0
    print(f"check_images: {len(problems)} problem(s)\n", file=sys.stderr)
    for p in problems:
        print(p.render(), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
