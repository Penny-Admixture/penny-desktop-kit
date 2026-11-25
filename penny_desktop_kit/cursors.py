"""Windows .cur cursor files: build them from Pillow images, parse them back.

A .cur file is the ICO container with type 2 instead of 1, and the two
bytes that hold colour planes in an .ico hold the hotspot (x, y) in a
.cur. The image data here is a 32bpp BGRA DIB plus a 1bpp AND mask,
bottom-up, exactly like classic Windows cursor files. PNG-compressed
cursors exist, but the DIB form works on every Windows version, so
Build 1 uses DIB only.

build_cur(image, hotspot, path)  -- image is a square RGBA Pillow image
parse_cur(path)                  -- returns header info, raises ValueError
                                  on anything malformed
"""

import struct

CUR_TYPE = 2


def build_cur(image, hotspot, path):
    """Write a 32x32 .cur file from a square RGBA Pillow image.

    hotspot is (x, y) in pixels from the top-left. The image is resized
    to 32x32 if it is not already.
    """
    im = image.convert("RGBA").resize((32, 32))
    hx, hy = hotspot
    if not (0 <= hx < 32 and 0 <= hy < 32):
        raise ValueError("hotspot %r outside 32x32 cursor" % (hotspot,))
    px = im.load()
    xor = bytearray()
    and_mask = bytearray()
    # DIB rows are bottom-up.
    for y in range(31, -1, -1):
        for x in range(32):
            r, g, b, a = px[x, y]
            xor += bytes((b, g, r, a))
    # AND mask: 1 bit per pixel, 1 = transparent (alpha 0), bottom-up,
    # rows padded to a 32-bit boundary (32 px wide is already aligned).
    for y in range(31, -1, -1):
        row = 0
        for x in range(32):
            _r, _g, _b, a = px[x, y]
            if a == 0:
                row |= 1 << (31 - x)
        and_mask += struct.pack(">I", row)
    dib = struct.pack("<IiiHHIIIIII", 40, 32, 64, 1, 32, 0,
                      len(xor) + len(and_mask), 0, 0, 0, 0)
    dib += bytes(xor) + bytes(and_mask)
    header = struct.pack("<HHH", 0, CUR_TYPE, 1)
    entry = struct.pack("<BBBBHHII", 32, 32, 0, 0, hx, hy,
                        len(dib), 6 + 16)
    with open(path, "wb") as f:
        f.write(header + entry + dib)
    return path


def parse_cur(path):
    """Parse a .cur file and return its header info.

    Returns {"type": 2, "count": n, "entries": [{"width":, "height":,
    "hotspot": (x, y), "bytes":, "offset":}, ...]}. Raises ValueError
    on a bad magic, wrong type, truncated file, or an entry whose
    image data runs past the end of the file.
    """
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 6:
        raise ValueError("%s: too short for a cursor header" % path)
    _reserved, typ, count = struct.unpack_from("<HHH", data, 0)
    if typ != CUR_TYPE:
        raise ValueError("%s: not a cursor file (type %d, want 2)" % (path, typ))
    if count < 1:
        raise ValueError("%s: cursor with zero images" % path)
    if len(data) < 6 + 16 * count:
        raise ValueError("%s: truncated cursor directory" % path)
    entries = []
    for i in range(count):
        off = 6 + 16 * i
        w, h, _cc, _res, hx, hy, size, img_off = struct.unpack_from(
            "<BBBBHHII", data, off)
        width = 256 if w == 0 else w
        height = 256 if h == 0 else h
        if img_off + size > len(data):
            raise ValueError("%s: image %d runs past end of file" % (path, i))
        if not (0 <= hx < width and 0 <= hy < height):
            raise ValueError("%s: hotspot (%d, %d) outside %dx%d image"
                             % (path, hx, hy, width, height))
        entries.append({"width": width, "height": height,
                        "hotspot": (hx, hy), "bytes": size, "offset": img_off})
    return {"type": typ, "count": count, "entries": entries}
