# arcade_common.py - Shared design system, colors, drawing helpers, and scoreboard
import time
import gc

def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

COLOR_DARK_BG       = rgb565(15, 23, 42)    # Slate 900
COLOR_HEADER_BG     = rgb565(30, 41, 59)    # Slate 800
COLOR_CARD_BG       = rgb565(51, 65, 85)    # Slate 700
COLOR_WHITE         = rgb565(255, 255, 255)
COLOR_TEXT_LIGHT    = rgb565(241, 245, 249) # Slate 100
COLOR_TEXT_MUTED    = rgb565(148, 163, 184) # Slate 400

# Google Brand Colors
COLOR_GOOGLE_BLUE   = rgb565(26, 115, 232)  # #1A73E8
COLOR_GOOGLE_RED    = rgb565(234, 67, 53)   # #EA4335
COLOR_GOOGLE_YELLOW = rgb565(251, 188, 4)   # #FBBC04
COLOR_GOOGLE_GREEN  = rgb565(52, 168, 83)   # #34A853

# 2048 Tile Colors
COLOR_2048_BOARD    = rgb565(187, 173, 160)
COLOR_TEXT_DARK     = rgb565(119, 110, 101)

TILE_COLORS = {
    0:    rgb565(205, 193, 180),
    2:    rgb565(238, 228, 218),
    4:    rgb565(237, 224, 200),
    8:    rgb565(242, 177, 121),
    16:   rgb565(245, 149, 99),
    32:   rgb565(246, 124, 95),
    64:   rgb565(246, 94, 59),
    128:  rgb565(237, 207, 114),
    256:  rgb565(237, 204, 97),
    512:  rgb565(237, 200, 80),
    1024: rgb565(237, 197, 63),
    2048: rgb565(237, 194, 46),
}


def draw_filled_circle(tft, cx, cy, r, color):
    """Draws a filled circle efficiently using scanlines."""
    r_sq = r * r
    for dy in range(-r, r + 1):
        dx = int((r_sq - dy * dy) ** 0.5)
        tft.fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, color)

def draw_circle_ring(tft, cx, cy, outer_r, inner_r, color, bg_color):
    """Draws a ring (annulus) for O marks or buttons."""
    draw_filled_circle(tft, cx, cy, outer_r, color)
    draw_filled_circle(tft, cx, cy, inner_r, bg_color)

def draw_thick_line_diag(tft, x1, y1, x2, y2, thickness, color):
    """Draws a bold diagonal line for X marks using integer arithmetic."""
    dx = x2 - x1
    dy = y2 - y1
    steps = abs(dx) if abs(dx) > abs(dy) else abs(dy)
    if steps == 0:
        return
    half_t = thickness // 2
    for i in range(steps + 1):
        cx = x1 + (i * dx) // steps
        cy = y1 + (i * dy) // steps
        tft.fill_rect(cx - half_t, cy - half_t, thickness, thickness, color)

def draw_button(tft, x, y, w, h, text, bg_color, text_color=COLOR_TEXT_LIGHT, scale=2):
    """Draws a crisp button with border and centered text."""
    tft.fill_rect(x, y, w, h, bg_color)
    tft.fill_rect(x, y, w, 1, COLOR_WHITE)
    tft.fill_rect(x, y, 1, h, COLOR_WHITE)
    tft.fill_rect(x + w - 1, y, 1, h, rgb565(100, 116, 139))
    tft.fill_rect(x, y + h - 1, w, 1, rgb565(100, 116, 139))
    
    # Auto-adjust scale if text width exceeds button inner area
    if scale > 1 and len(text) * 6 * scale > w - 6:
        scale = 1

    char_w = 6 * scale
    char_h = 8 * scale
    tx = x + (w - len(text) * char_w) // 2
    ty = y + (h - char_h) // 2
    tft.draw_text(text, max(x + 2, tx), max(y + 2, ty), text_color, bg=bg_color, scale=scale)

def draw_header_bar(tft, title, show_back=True, show_restart=True):
    """Draws the top navigation header bar."""
    tft.fill_rect(0, 0, 320, 50, COLOR_HEADER_BG)
    tft.fill_rect(0, 49, 320, 1, COLOR_GOOGLE_BLUE)
    
    if show_back:
        draw_button(tft, 8, 8, 70, 34, "< MENU", COLOR_CARD_BG, COLOR_WHITE, scale=1)
    
    # Title centered
    tft.draw_text(title, 90, 16, COLOR_WHITE, scale=2)
    
    if show_restart:
        draw_button(tft, 240, 8, 72, 34, "RESET", COLOR_CARD_BG, COLOR_WHITE, scale=1)


import json

def save_json_file(filename, data):
    try:
        with open(filename, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print("Save file error:", e)

def load_json_file(filename, default=None):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except Exception as e:
        return default

def save_game_state(mode, game_obj):
    if mode == "MENU" or game_obj is None:
        data = {"current_mode": "MENU", "game_data": None}
    else:
        game_data = game_obj.to_dict() if hasattr(game_obj, "to_dict") else None
        data = {"current_mode": mode, "game_data": game_data}
    save_json_file("game_state.json", data)

def load_game_state():
    return load_json_file("game_state.json", default={"current_mode": "MENU", "game_data": None})


class ScoreboardManager:
    def __init__(self):
        self.stats = {
            "2048_best": 0,
            "ttt_wins": 0,
            "ttt_ai_wins": 0,
            "ttt_draws": 0,
            "c4_wins": 0,
            "c4_ai_wins": 0,
            "c4_draws": 0,
            "uno_wins": 0,
            "uno_ai_wins": 0,
            "alq_wins": 0,
            "alq_ai_wins": 0,
            "alq_draws": 0,
            "checkers_wins": 0,
            "checkers_ai_wins": 0,
            "checkers_draws": 0,
            "chess_wins": 0,
            "chess_ai_wins": 0,
            "chess_draws": 0,
            "city_max_pop": 0,
            "dots_wins": 0,
            "dots_ai_wins": 0,
            "dots_draws": 0,
            "tridots_wins": 0,
            "tridots_ai_wins": 0,
            "tridots_draws": 0,
        }
        self.load_stats()

    def load_stats(self):
        loaded = load_json_file("stats.json")
        if isinstance(loaded, dict):
            for k, v in loaded.items():
                if k in self.stats:
                    self.stats[k] = v

    def save_stats(self):
        save_json_file("stats.json", self.stats)

    def update_2048(self, score):
        if score > self.stats["2048_best"]:
            self.stats["2048_best"] = score
            self.save_stats()

    def record_ttt(self, winner):
        if winner == 'X': self.stats["ttt_wins"] += 1
        elif winner == 'O': self.stats["ttt_ai_wins"] += 1
        elif winner == 'DRAW': self.stats["ttt_draws"] += 1
        self.save_stats()

    def record_c4(self, winner):
        if winner == 'RED': self.stats["c4_wins"] += 1
        elif winner == 'YELLOW': self.stats["c4_ai_wins"] += 1
        elif winner == 'DRAW': self.stats["c4_draws"] += 1
        self.save_stats()

    def record_uno(self, winner):
        if winner == "PLAYER": self.stats["uno_wins"] += 1
        else: self.stats["uno_ai_wins"] += 1
        self.save_stats()

    def record_alq(self, winner):
        if winner == 1: self.stats["alq_wins"] += 1
        elif winner == 2: self.stats["alq_ai_wins"] += 1
        elif winner == 'DRAW': self.stats["alq_draws"] += 1
        self.save_stats()

    def record_checkers(self, winner):
        if winner == 'W': self.stats["checkers_wins"] += 1
        elif winner == 'B': self.stats["checkers_ai_wins"] += 1
        elif winner == 'DRAW': self.stats["checkers_draws"] += 1
        self.save_stats()

    def record_chess(self, winner):
        if winner == 'W': self.stats["chess_wins"] += 1
        elif winner == 'B': self.stats["chess_ai_wins"] += 1
        elif winner == 'DRAW': self.stats["chess_draws"] += 1
        self.save_stats()

    def record_dots(self, winner):
        if winner == 0: self.stats["dots_wins"] += 1
        elif winner == 'DRAW': self.stats["dots_draws"] += 1
        else: self.stats["dots_ai_wins"] += 1
        self.save_stats()

    def record_tridots(self, winner):
        if winner == 0: self.stats["tridots_wins"] += 1
        elif winner == 'DRAW': self.stats["tridots_draws"] += 1
        else: self.stats["tridots_ai_wins"] += 1
        self.save_stats()

    def reset_stats(self):
        for k in self.stats:
            self.stats[k] = 0
        self.save_stats()

scoreboard = ScoreboardManager()


def _ticks_ms():
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.time() * 1000)

def _ticks_diff(t1, t0):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(t1, t0)
    return t1 - t0


class SwipeDetector:
    """
    Capacitive Touch Debouncer & Gesture Detector for WT32-SC01.
    - Single-frame ghost tap filter (requires min_touch_ms duration or min_frames).
    - Release bounce suppression and refractory cooldown (~140ms).
    - Touch coordinate stabilization to eliminate release drift.
    - Clean swipe gesture discrimination with boundary clamping.
    """
    def __init__(self, min_dist=28, min_touch_ms=35, min_frames=2, refractory_ms=140):
        self.min_dist = min_dist
        self.min_touch_ms = min_touch_ms
        self.min_frames = min_frames
        self.refractory_ms = refractory_ms

        self.start_x = 0
        self.start_y = 0
        self.stable_x = 0
        self.stable_y = 0
        self.last_x = 0
        self.last_y = 0
        self.max_disp = 0

        self.touch_frames = 0
        self.touch_start_time = 0
        self.last_event_time = 0
        self.touching = False

    def reset(self):
        self.touching = False
        self.touch_frames = 0
        self.start_x = 0
        self.start_y = 0
        self.stable_x = 0
        self.stable_y = 0
        self.last_x = 0
        self.last_y = 0
        self.max_disp = 0

    def update(self, touches, x, y):
        now = _ticks_ms()

        if touches > 0:
            # Clamp coordinates to physical display bounds
            x = max(0, min(319, x))
            y = max(0, min(479, y))

            if not self.touching:
                # If within refractory cooldown from previous event, suppress new touch contact
                if _ticks_diff(now, self.last_event_time) < self.refractory_ms:
                    return None

                self.touching = True
                self.touch_frames = 1
                self.touch_start_time = now
                self.start_x = x
                self.start_y = y
                self.stable_x = x
                self.stable_y = y
                self.last_x = x
                self.last_y = y
                self.max_disp = 0
            else:
                self.touch_frames += 1
                self.last_x = x
                self.last_y = y
                # Exponential smoothing of touch centroid during contact hold
                self.stable_x = (self.stable_x * 3 + x) // 4
                self.stable_y = (self.stable_y * 3 + y) // 4
                disp = max(abs(x - self.start_x), abs(y - self.start_y))
                if disp > self.max_disp:
                    self.max_disp = disp

            return None
        else:
            if self.touching:
                duration = _ticks_diff(now, self.touch_start_time)
                frames = self.touch_frames
                self.touching = False
                self.touch_frames = 0

                # 1. Ghost-Tap Filter: reject single-frame spurious contact noise
                if duration < self.min_touch_ms and frames < self.min_frames:
                    return None

                # 2. Refractory check
                if _ticks_diff(now, self.last_event_time) < self.refractory_ms:
                    return None

                dx = self.last_x - self.start_x
                dy = self.last_y - self.start_y
                total_disp = max(abs(dx), abs(dy), self.max_disp)

                # 3. Deliberate Stationary Tap vs Swipe Gesture
                if total_disp < self.min_dist:
                    # Stabilized tap coordinate: avoid release glitch
                    tap_x = self.start_x if abs(self.last_x - self.start_x) < 8 else self.stable_x
                    tap_y = self.start_y if abs(self.last_y - self.start_y) < 8 else self.stable_y
                    tap_x = max(0, min(319, tap_x))
                    tap_y = max(0, min(479, tap_y))

                    self.last_event_time = now
                    return ("TAP", tap_x, tap_y)
                else:
                    self.last_event_time = now
                    if abs(dx) > abs(dy):
                        return "RIGHT" if dx > 0 else "LEFT"
                    else:
                        return "DOWN" if dy > 0 else "UP"

        return None
