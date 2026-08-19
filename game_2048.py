# game_2048.py - 2048 Puzzle Game Module for WT32-SC01
import random
import gc
from arcade_common import (
    COLOR_DARK_BG, COLOR_HEADER_BG, COLOR_CARD_BG, COLOR_WHITE,
    COLOR_TEXT_MUTED, COLOR_GOOGLE_RED, COLOR_GOOGLE_GREEN,
    COLOR_2048_BOARD, COLOR_TEXT_DARK, TILE_COLORS, draw_header_bar, scoreboard
)

class Game2048:
    def __init__(self):
        self.grid = [[0] * 4 for _ in range(4)]
        self.prev_grid = [[-1] * 4 for _ in range(4)]
        self.score = 0
        self.prev_score = -1
        self.game_over = False
        self.won = False
        self.prev_banner = ""
        self.reset()

    def reset(self):
        for r in range(4):
            for c in range(4):
                self.grid[r][c] = 0
                self.prev_grid[r][c] = -1
        self.score = 0
        self.prev_score = -1
        self.game_over = False
        self.won = False
        self.prev_banner = ""
        self.spawn_tile()
        self.spawn_tile()
        gc.collect()

    def to_dict(self):
        return {
            "grid": [row[:] for row in self.grid],
            "score": self.score,
            "game_over": self.game_over,
            "won": self.won
        }

    def from_dict(self, data):
        if not data:
            return
        grid_data = data.get("grid")
        if grid_data and len(grid_data) == 4:
            self.grid = [list(row) for row in grid_data]
        self.score = data.get("score", self.score)
        self.game_over = data.get("game_over", self.game_over)
        self.won = data.get("won", self.won)
        for r in range(4):
            for c in range(4):
                self.prev_grid[r][c] = -1
        self.prev_score = -1
        self.prev_banner = ""

    def get_empty_cells(self):
        empty = []
        for r in range(4):
            for c in range(4):
                if self.grid[r][c] == 0:
                    empty.append((r, c))
        return empty

    def spawn_tile(self):
        """Zero-allocation random empty cell tile spawner."""
        count = 0
        for r in range(4):
            for c in range(4):
                if self.grid[r][c] == 0:
                    count += 1
        if count == 0:
            return
        target_idx = random.randint(0, count - 1)
        curr = 0
        val = 4 if random.random() < 0.1 else 2
        for r in range(4):
            for c in range(4):
                if self.grid[r][c] == 0:
                    if curr == target_idx:
                        self.grid[r][c] = val
                        return
                    curr += 1

    def _merge_line(self, a, b, c, d):
        """Merges 4 integers and returns (r0, r1, r2, r3, gained) without list allocations."""
        v0, v1, v2, v3 = 0, 0, 0, 0
        n = 0
        if a != 0: v0 = a; n = 1
        if b != 0:
            if n == 0: v0 = b; n = 1
            else: v1 = b; n = 2
        if c != 0:
            if n == 0: v0 = c; n = 1
            elif n == 1: v1 = c; n = 2
            else: v2 = c; n = 3
        if d != 0:
            if n == 0: v0 = d; n = 1
            elif n == 1: v1 = d; n = 2
            elif n == 2: v2 = d; n = 3
            else: v3 = d; n = 4

        gained = 0
        out0, out1, out2, out3 = 0, 0, 0, 0
        out_idx = 0
        i = 0
        vals = (v0, v1, v2, v3)
        while i < n:
            if i + 1 < n and vals[i] == vals[i + 1]:
                m_val = vals[i] * 2
                gained += m_val
                if out_idx == 0: out0 = m_val
                elif out_idx == 1: out1 = m_val
                elif out_idx == 2: out2 = m_val
                elif out_idx == 3: out3 = m_val
                out_idx += 1
                i += 2
            else:
                v = vals[i]
                if out_idx == 0: out0 = v
                elif out_idx == 1: out1 = v
                elif out_idx == 2: out2 = v
                elif out_idx == 3: out3 = v
                out_idx += 1
                i += 1

        return out0, out1, out2, out3, gained

    def move(self, direction):
        if self.game_over:
            return False

        changed = False
        total_gained = 0

        if direction == "LEFT":
            for r in range(4):
                g = self.grid[r]
                o0, o1, o2, o3, gained = self._merge_line(g[0], g[1], g[2], g[3])
                if g[0] != o0 or g[1] != o1 or g[2] != o2 or g[3] != o3:
                    changed = True
                    g[0], g[1], g[2], g[3] = o0, o1, o2, o3
                total_gained += gained

        elif direction == "RIGHT":
            for r in range(4):
                g = self.grid[r]
                o0, o1, o2, o3, gained = self._merge_line(g[3], g[2], g[1], g[0])
                if g[3] != o0 or g[2] != o1 or g[1] != o2 or g[0] != o3:
                    changed = True
                    g[3], g[2], g[1], g[0] = o0, o1, o2, o3
                total_gained += gained

        elif direction == "UP":
            for c in range(4):
                o0, o1, o2, o3, gained = self._merge_line(self.grid[0][c], self.grid[1][c], self.grid[2][c], self.grid[3][c])
                if self.grid[0][c] != o0 or self.grid[1][c] != o1 or self.grid[2][c] != o2 or self.grid[3][c] != o3:
                    changed = True
                    self.grid[0][c] = o0
                    self.grid[1][c] = o1
                    self.grid[2][c] = o2
                    self.grid[3][c] = o3
                total_gained += gained

        elif direction == "DOWN":
            for c in range(4):
                o0, o1, o2, o3, gained = self._merge_line(self.grid[3][c], self.grid[2][c], self.grid[1][c], self.grid[0][c])
                if self.grid[3][c] != o0 or self.grid[2][c] != o1 or self.grid[1][c] != o2 or self.grid[0][c] != o3:
                    changed = True
                    self.grid[3][c] = o0
                    self.grid[2][c] = o1
                    self.grid[1][c] = o2
                    self.grid[0][c] = o3
                total_gained += gained

        if changed:
            self.score += total_gained
            scoreboard.update_2048(self.score)
            self.spawn_tile()
            self.check_game_over()
            gc.collect()
        return changed

    def check_game_over(self):
        has_empty = False
        has_merge = False
        for r in range(4):
            for c in range(4):
                v = self.grid[r][c]
                if v == 0:
                    has_empty = True
                elif v >= 2048 and not self.won:
                    self.won = True
                if c < 3 and v == self.grid[r][c + 1]:
                    has_merge = True
                if r < 3 and v == self.grid[r + 1][c]:
                    has_merge = True

        if not has_empty and not has_merge:
            self.game_over = True
            return True
        return False


def init_2048_ui(tft, game):
    tft.fill_rect(0, 0, 320, 480, COLOR_DARK_BG)
    draw_header_bar(tft, "2048 GAME")

    # Board container
    tft.fill_rect(10, 115, 300, 300, COLOR_2048_BOARD)

    # Header scores background
    tft.fill_rect(10, 60, 140, 45, COLOR_CARD_BG)
    tft.draw_text("SCORE", 20, 65, COLOR_TEXT_MUTED, scale=1)

    tft.fill_rect(170, 60, 140, 45, COLOR_CARD_BG)
    tft.draw_text("BEST", 180, 65, COLOR_TEXT_MUTED, scale=1)

    for r in range(4):
        for c in range(4):
            game.prev_grid[r][c] = -1
    game.prev_score = -1
    game.prev_banner = ""
    update_2048_ui(tft, game)


def update_2048_ui(tft, game):
    if game.score != game.prev_score:
        game.prev_score = game.score
        tft.fill_rect(20, 78, 120, 22, COLOR_CARD_BG)
        tft.draw_text(str(game.score), 20, 78, COLOR_WHITE, bg=COLOR_CARD_BG, scale=2)

        tft.fill_rect(180, 78, 120, 22, COLOR_CARD_BG)
        tft.draw_text(str(scoreboard.stats["2048_best"]), 180, 78, COLOR_WHITE, bg=COLOR_CARD_BG, scale=2)

    for r in range(4):
        for c in range(4):
            val = game.grid[r][c]
            if val != game.prev_grid[r][c]:
                game.prev_grid[r][c] = val
                x = 19 + c * 73
                y = 124 + r * 73
                bg_color = TILE_COLORS.get(val, TILE_COLORS[2048])
                tft.fill_rect(x, y, 64, 64, bg_color)

                if val > 0:
                    txt = str(val)
                    txt_len = len(txt)
                    txt_color = COLOR_TEXT_DARK if val in (2, 4) else COLOR_WHITE
                    scale = 3 if txt_len <= 2 else (2 if txt_len <= 4 else 1)
                    char_w = 6 * scale
                    tx = x + (64 - (txt_len * char_w)) // 2
                    ty = y + (64 - (8 * scale)) // 2
                    tft.draw_text(txt, tx, ty, txt_color, bg=(bg_color if scale in (1, 2) else None), scale=scale)

    banner = ""
    banner_color = COLOR_WHITE
    if game.game_over:
        banner = "GAME OVER!"
        banner_color = COLOR_GOOGLE_RED
    elif game.won:
        banner = "2048 REACHED!"
        banner_color = COLOR_GOOGLE_GREEN

    if banner != game.prev_banner:
        game.prev_banner = banner
        tft.fill_rect(0, 430, 320, 45, COLOR_DARK_BG)
        if banner:
            tx = (320 - len(banner) * 12) // 2
            tft.draw_text(banner, max(10, tx), 440, banner_color, bg=COLOR_DARK_BG, scale=2)
