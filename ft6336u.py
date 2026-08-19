# ft6336u.py - MicroPython FT6336U Capacitive Touch Controller Driver for WT32-SC01
from machine import I2C, Pin

class FT6336U:
    def __init__(self, i2c, addr=0x38):
        self.i2c = i2c
        self.addr = addr
        self._buf = bytearray(5)

    def read_touch(self):
        """Returns (touch_count, x, y) or (0, 0, 0) with zero heap allocation."""
        try:
            if hasattr(self.i2c, "readfrom_mem_into"):
                self.i2c.readfrom_mem_into(self.addr, 0x02, self._buf)
                data = self._buf
            else:
                data = self.i2c.readfrom_mem(self.addr, 0x02, 5)
            touches = data[0] & 0x0F
            if touches > 0:
                x = ((data[1] & 0x0F) << 8) | data[2]
                y = ((data[3] & 0x0F) << 8) | data[4]
                # Clamp coordinates to physical display bounds (0..319, 0..479)
                x = max(0, min(319, x))
                y = max(0, min(479, y))
                return touches, x, y
        except Exception:
            pass
        return 0, 0, 0
