import time
try:
    import ustruct
except ImportError:
    import struct as ustruct
import gc
from machine import Pin, SPI

# Full 5x8 ASCII Bitmap Font (ASCII 32 to 126: all symbols, punctuation, digits, uppercase, lowercase)
FONT_5X8_DATA = (
    b'\x00\x00\x00\x00\x00'  # 32 space
    b'\x00\x00\x5F\x00\x00'  # 33 !
    b'\x00\x07\x00\x07\x00'  # 34 "
    b'\x14\x7F\x14\x7F\x14'  # 35 #
    b'\x24\x2A\x7F\x2A\x12'  # 36 $
    b'\x23\x13\x08\x64\x62'  # 37 %
    b'\x36\x49\x55\x22\x50'  # 38 &
    b'\x00\x05\x03\x00\x00'  # 39 '
    b'\x00\x1C\x22\x41\x00'  # 40 (
    b'\x00\x41\x22\x1C\x00'  # 41 )
    b'\x14\x08\x3E\x08\x14'  # 42 *
    b'\x08\x08\x3E\x08\x08'  # 43 +
    b'\x00\x50\x30\x00\x00'  # 44 ,
    b'\x08\x08\x08\x08\x08'  # 45 -
    b'\x00\x60\x60\x00\x00'  # 46 .
    b'\x20\x10\x08\x04\x02'  # 47 /
    b'\x3E\x51\x49\x45\x3E'  # 48 0
    b'\x00\x42\x7F\x40\x00'  # 49 1
    b'\x42\x61\x51\x49\x46'  # 50 2
    b'\x21\x41\x45\x4B\x31'  # 51 3
    b'\x18\x14\x12\x7F\x10'  # 52 4
    b'\x27\x45\x45\x45\x39'  # 53 5
    b'\x3C\x4A\x49\x49\x30'  # 54 6
    b'\x01\x71\x09\x05\x03'  # 55 7
    b'\x36\x49\x49\x49\x36'  # 56 8
    b'\x06\x49\x49\x29\x1E'  # 57 9
    b'\x00\x36\x36\x00\x00'  # 58 :
    b'\x00\x56\x36\x00\x00'  # 59 ;
    b'\x08\x14\x22\x41\x00'  # 60 <
    b'\x14\x14\x14\x14\x14'  # 61 =
    b'\x00\x41\x22\x14\x08'  # 62 >
    b'\x02\x01\x51\x09\x06'  # 63 ?
    b'\x32\x49\x79\x41\x3E'  # 64 @
    b'\x7E\x11\x11\x11\x7E'  # 65 A
    b'\x7F\x49\x49\x49\x36'  # 66 B
    b'\x3E\x41\x41\x41\x22'  # 67 C
    b'\x7F\x41\x41\x22\x1C'  # 68 D
    b'\x7F\x49\x49\x49\x41'  # 69 E
    b'\x7F\x09\x09\x09\x01'  # 70 F
    b'\x3E\x41\x49\x49\x7A'  # 71 G
    b'\x7F\x08\x08\x08\x7F'  # 72 H
    b'\x00\x41\x7F\x41\x00'  # 73 I
    b'\x20\x40\x41\x3F\x01'  # 74 J
    b'\x7F\x08\x14\x22\x41'  # 75 K
    b'\x7F\x40\x40\x40\x40'  # 76 L
    b'\x7F\x02\x0C\x02\x7F'  # 77 M
    b'\x7F\x04\x08\x10\x7F'  # 78 N
    b'\x3E\x41\x41\x41\x3E'  # 79 O
    b'\x7F\x09\x09\x09\x06'  # 80 P
    b'\x3E\x41\x51\x21\x5E'  # 81 Q
    b'\x7F\x09\x19\x29\x46'  # 82 R
    b'\x46\x49\x49\x49\x31'  # 83 S
    b'\x01\x01\x7F\x01\x01'  # 84 T
    b'\x3F\x40\x40\x40\x3F'  # 85 U
    b'\x1F\x20\x40\x20\x1F'  # 86 V
    b'\x3F\x40\x38\x40\x3F'  # 87 W
    b'\x63\x14\x08\x14\x63'  # 88 X
    b'\x07\x08\x70\x08\x07'  # 89 Y
    b'\x61\x51\x49\x45\x43'  # 90 Z
    b'\x00\x7F\x41\x41\x00'  # 91 [
    b'\x02\x04\x08\x10\x20'  # 92 \
    b'\x00\x41\x41\x7F\x00'  # 93 ]
    b'\x04\x02\x01\x02\x04'  # 94 ^
    b'\x40\x40\x40\x40\x40'  # 95 _
    b'\x00\x01\x02\x04\x00'  # 96 `
    b'\x20\x54\x54\x54\x78'  # 97 a
    b'\x7F\x48\x44\x44\x38'  # 98 b
    b'\x38\x44\x44\x44\x20'  # 99 c
    b'\x38\x44\x44\x48\x7F'  # 100 d
    b'\x38\x54\x54\x54\x18'  # 101 e
    b'\x08\x7E\x09\x01\x02'  # 102 f
    b'\x0C\x52\x52\x52\x3E'  # 103 g
    b'\x7F\x08\x04\x04\x78'  # 104 h
    b'\x00\x44\x7D\x40\x00'  # 105 i
    b'\x20\x40\x44\x3D\x00'  # 106 j
    b'\x7F\x10\x28\x44\x00'  # 107 k
    b'\x00\x41\x7F\x40\x00'  # 108 l
    b'\x7C\x04\x18\x04\x78'  # 109 m
    b'\x7C\x08\x04\x04\x78'  # 110 n
    b'\x38\x44\x44\x44\x38'  # 111 o
    b'\x7C\x14\x14\x14\x08'  # 112 p
    b'\x08\x14\x14\x18\x7C'  # 113 q
    b'\x7C\x08\x04\x04\x08'  # 114 r
    b'\x48\x54\x54\x54\x20'  # 115 s
    b'\x04\x3F\x44\x40\x20'  # 116 t
    b'\x3C\x40\x40\x20\x7C'  # 117 u
    b'\x1C\x20\x40\x20\x1C'  # 118 v
    b'\x3C\x40\x30\x40\x3C'  # 119 w
    b'\x44\x28\x10\x28\x44'  # 120 x
    b'\x0C\x50\x50\x50\x3C'  # 121 y
    b'\x44\x64\x54\x4C\x44'  # 122 z
    b'\x00\x08\x36\x41\x00'  # 123 {
    b'\x00\x00\x7F\x00\x00'  # 124 |
    b'\x00\x41\x36\x08\x00'  # 125 }
    b'\x08\x04\x08\x10\x08'  # 126 ~
)



class ST7796S:
    def __init__(self, spi, width=320, height=480, reset=22, dc=21, cs=15, backlight=23):
        self.spi = spi
        self.width = width
        self.height = height

        self.rst = Pin(reset, Pin.OUT) if isinstance(reset, int) else reset
        self.dc = Pin(dc, Pin.OUT) if isinstance(dc, int) else dc
        self.cs = Pin(cs, Pin.OUT) if isinstance(cs, int) else cs

        if backlight is not None:
            self.bl = Pin(backlight, Pin.OUT) if isinstance(backlight, int) else backlight
            self.bl.value(1)
        else:
            self.bl = None

        self.cs.value(1)
        self.dc.value(0)

        # Static reusable buffers to eliminate RAM allocation/fragmentation during drawing
        self._cmd_buf = bytearray(1)
        self._data_buf = bytearray(1)
        self._win_buf = bytearray(4)
        self._fill_chunk = bytearray(512)
        self._fill_chunk_mv = memoryview(self._fill_chunk)
        self._char_buf = bytearray(12 * 16 * 2)
        self._char_buf_mv = memoryview(self._char_buf)
        self._last_fill_color = -1

        self.init()
        gc.collect()

    def write_cmd(self, cmd):
        self.dc.value(0)
        self.cs.value(0)
        self._cmd_buf[0] = cmd
        self.spi.write(self._cmd_buf)
        self.cs.value(1)

    def write_data(self, data):
        self.dc.value(1)
        self.cs.value(0)
        if isinstance(data, int):
            self._data_buf[0] = data
            self.spi.write(self._data_buf)
        else:
            self.spi.write(data)
        self.cs.value(1)

    def reset_display(self):
        self.rst.value(0)
        time.sleep_ms(50)
        self.rst.value(1)
        time.sleep_ms(120)

    def init(self):
        self.reset_display()

        self.write_cmd(0x01)  # Software Reset
        time.sleep_ms(120)

        self.write_cmd(0x11)  # Sleep Out
        time.sleep_ms(120)

        self.write_cmd(0xF0)  # Command Set Control
        self.write_data(0xC3)

        self.write_cmd(0xF0)
        self.write_data(0x96)

        self.write_cmd(0x36)  # MADCTL: Portrait mode BGR
        self.write_data(0x48)

        self.write_cmd(0x3A)  # COLMOD: 16-bit RGB565
        self.write_data(0x55)

        self.write_cmd(0xB4)  # Display Inversion Control
        self.write_data(0x01)

        self.write_cmd(0x29)  # Display ON
        time.sleep_ms(50)

    def set_window(self, x0, y0, x1, y1):
        self.write_cmd(0x2A)  # CASET
        self._win_buf[0] = x0 >> 8
        self._win_buf[1] = x0 & 0xFF
        self._win_buf[2] = x1 >> 8
        self._win_buf[3] = x1 & 0xFF
        self.write_data(self._win_buf)

        self.write_cmd(0x2B)  # RASET
        self._win_buf[0] = y0 >> 8
        self._win_buf[1] = y0 & 0xFF
        self._win_buf[2] = y1 >> 8
        self._win_buf[3] = y1 & 0xFF
        self.write_data(self._win_buf)

        self.write_cmd(0x2C)  # RAMWR

    def blit_buffer(self, x, y, w, h, buf):
        """Push a raw RGB565 bytearray buffer directly to the display window with 0 heap allocation."""
        if x >= self.width or y >= self.height:
            return
        x2 = min(x + w - 1, self.width - 1)
        y2 = min(y + h - 1, self.height - 1)
        if x2 < x or y2 < y:
            return
        self.set_window(x, y, x2, y2)
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(buf)
        self.cs.value(1)

    def fill_rect(self, x, y, w, h, color):
        """Draw filled rectangle with RGB565 color integer using pre-allocated zero-alloc buffer."""
        if x >= self.width or y >= self.height:
            return
        x2 = min(x + w - 1, self.width - 1)
        y2 = min(y + h - 1, self.height - 1)
        if x2 < x or y2 < y:
            return

        self.set_window(x, y, x2, y2)

        pixels = (x2 - x + 1) * (y2 - y + 1)
        hi = (color >> 8) & 0xFF
        lo = color & 0xFF

        if self._last_fill_color != color:
            self._fill_chunk[0] = hi
            self._fill_chunk[1] = lo
            size = 2
            while size < 512:
                chunk = min(size, 512 - size)
                self._fill_chunk[size : size + chunk] = self._fill_chunk[:chunk]
                size += chunk
            self._last_fill_color = color

        self.dc.value(1)
        self.cs.value(0)
        chunk_pixels = 256
        remaining = pixels

        while remaining >= chunk_pixels:
            self.spi.write(self._fill_chunk)
            remaining -= chunk_pixels

        if remaining > 0:
            self.spi.write(self._fill_chunk_mv[:remaining * 2])

        self.cs.value(1)

    def fill(self, color):
        self.fill_rect(0, 0, self.width, self.height, color)

    def draw_char(self, char, x, y, color, bg=None, scale=2):
        """Draw a single ASCII character (full range 32 to 126 supported)"""
        code = ord(char[0]) if isinstance(char, str) and len(char) > 0 else (char if isinstance(char, int) else 32)
        if 32 <= code <= 126:
            offset = (code - 32) * 5
        else:
            offset = (63 - 32) * 5  # '?' fallback

        if bg is not None and scale in (1, 2):
            hi_fg = (color >> 8) & 0xFF
            lo_fg = color & 0xFF
            hi_bg = (bg >> 8) & 0xFF
            lo_bg = bg & 0xFF

            if scale == 1:
                cw, ch = 6, 8
                total_bytes = 6 * 8 * 2
                self._char_buf[0] = hi_bg
                self._char_buf[1] = lo_bg
                cur = 2
                while cur < total_bytes:
                    ck = min(cur, total_bytes - cur)
                    self._char_buf[cur : cur + ck] = self._char_buf[:ck]
                    cur += ck

                for col_idx in range(5):
                    col_byte = FONT_5X8_DATA[offset + col_idx]
                    for row_idx in range(8):
                        if (col_byte >> row_idx) & 0x01:
                            idx = (row_idx * 6 + col_idx) * 2
                            self._char_buf[idx] = hi_fg
                            self._char_buf[idx + 1] = lo_fg

                self.blit_buffer(x, y, 6, 8, self._char_buf_mv[:total_bytes])
                return

            elif scale == 2:
                cw, ch = 12, 16
                total_bytes = 12 * 16 * 2
                self._char_buf[0] = hi_bg
                self._char_buf[1] = lo_bg
                cur = 2
                while cur < total_bytes:
                    ck = min(cur, total_bytes - cur)
                    self._char_buf[cur : cur + ck] = self._char_buf[:ck]
                    cur += ck

                for col_idx in range(5):
                    col_byte = FONT_5X8_DATA[offset + col_idx]
                    for row_idx in range(8):
                        if (col_byte >> row_idx) & 0x01:
                            px = col_idx * 2
                            py = row_idx * 2
                            idx1 = (py * 12 + px) * 2
                            idx2 = (py * 12 + px + 1) * 2
                            idx3 = ((py + 1) * 12 + px) * 2
                            idx4 = ((py + 1) * 12 + px + 1) * 2
                            self._char_buf[idx1] = hi_fg; self._char_buf[idx1 + 1] = lo_fg
                            self._char_buf[idx2] = hi_fg; self._char_buf[idx2 + 1] = lo_fg
                            self._char_buf[idx3] = hi_fg; self._char_buf[idx3 + 1] = lo_fg
                            self._char_buf[idx4] = hi_fg; self._char_buf[idx4 + 1] = lo_fg

                self.blit_buffer(x, y, 12, 16, self._char_buf_mv[:total_bytes])
                return

        # Fallback for transparent background or other scales
        for col_idx in range(5):
            col_byte = FONT_5X8_DATA[offset + col_idx]
            for row_idx in range(8):
                if (col_byte >> row_idx) & 0x01:
                    self.fill_rect(x + col_idx * scale, y + row_idx * scale, scale, scale, color)
                elif bg is not None:
                    self.fill_rect(x + col_idx * scale, y + row_idx * scale, scale, scale, bg)

    def draw_text(self, text, x, y, color, bg=None, scale=2):
        """Draw a text string with zero extra allocation if string"""
        cursor_x = x
        text_str = text if isinstance(text, str) else str(text)
        for char in text_str:
            self.draw_char(char, cursor_x, y, color, bg, scale)
            cursor_x += (5 + 1) * scale

