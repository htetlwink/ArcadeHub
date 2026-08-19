# game_dots.py - Dots and Boxes Game Engine & Renderer for WT32-SC01 (Zero-Flicker Edition)
import random
import time
import gc
from arcade_common import (
    COLOR_DARK_BG, COLOR_HEADER_BG, COLOR_CARD_BG, COLOR_WHITE,
    COLOR_TEXT_LIGHT, COLOR_TEXT_MUTED, COLOR_GOOGLE_BLUE, COLOR_GOOGLE_RED,
    COLOR_GOOGLE_YELLOW, COLOR_GOOGLE_GREEN, rgb565, draw_filled_circle,
    draw_button, draw_header_bar, scoreboard
)

# Player Colors and Labels
PLAYER_COLORS = [
    COLOR_GOOGLE_BLUE,    # P1 - Blue
    COLOR_GOOGLE_RED,     # P2 - Red / AI
    COLOR_GOOGLE_YELLOW,  # P3 - Yellow
    COLOR_GOOGLE_GREEN,   # P4 - Green
]

PLAYER_BOX_BG = [
    rgb565(18, 48, 88),   # P1 Dark Blue Tint
    rgb565(88, 22, 22),   # P2 Dark Red Tint
    rgb565(88, 70, 12),   # P3 Dark Yellow Tint
    rgb565(18, 70, 32),   # P4 Dark Green Tint
]

PLAYER_NAMES = ["P1", "P2", "P3", "P4"]

COLOR_DOT_DEFAULT = rgb565(226, 232, 240)  # Slate 200
COLOR_LINE_EMPTY   = rgb565(30, 41, 59)    # Subtle guide line
COLOR_BOARD_BG     = rgb565(15, 23, 42)    # Slate 900
COLOR_BOARD_PLATE  = rgb565(24, 32, 47)    # Sleek dark plate


class DotsAndBoxes:
    def __init__(self, grid_size=4, game_type="PVP", player_count=2, difficulty="MEDIUM"):
        self.grid_size = grid_size        # Number of dots per side (3, 4, 5, 6)
        self.game_type = game_type        # "PVP" or "VS_AI"
        self.player_count = player_count  # 2, 3, 4 (if PVP)
        self.difficulty = difficulty      # "EASY", "MEDIUM", "HARD" (if VS_AI)

        self.num_players = player_count if game_type == "PVP" else 2
        self.current_player = 0           # 0..num_players-1
        self.scores = [0, 0, 0, 0]
        self.selected_dot = None          # (r, c) or None
        self.game_over = False
        self.winner = None
        self.recorded = False
        self.status_msg = "P1: TAP A DOT TO START"
        self.last_edge = None             # ("H", r, c) or ("V", r, c)
        self.last_completed = []          # list of (r, c)
        self.prev_selected = None

        # State tracking for zero-flicker differential HUD rendering
        self.prev_hud_player = -1
        self.prev_hud_scores = [-1, -1, -1, -1]
        self.prev_status_msg = ""

        self._init_board()

    def _init_board(self):
        N = self.grid_size
        self.h_edges = [[None] * (N - 1) for _ in range(N)]
        self.v_edges = [[None] * N for _ in range(N - 1)]
        self.boxes = [[None] * (N - 1) for _ in range(N - 1)]

    def reset(self):
        self.num_players = self.player_count if self.game_type == "PVP" else 2
        self.current_player = 0
        self.scores = [0, 0, 0, 0]
        self.selected_dot = None
        self.prev_selected = None
        self.game_over = False
        self.winner = None
        self.recorded = False
        self.last_edge = None
        self.last_completed = []
        p_name = "P1"
        self.status_msg = p_name + ": TAP A DOT TO START"
        self.prev_hud_player = -1
        self.prev_hud_scores = [-1, -1, -1, -1]
        self.prev_status_msg = ""
        self._init_board()
        gc.collect()

    def to_dict(self):
        return {
            "grid_size": self.grid_size,
            "game_type": self.game_type,
            "player_count": self.player_count,
            "difficulty": self.difficulty,
            "current_player": self.current_player,
            "scores": list(self.scores),
            "h_edges": [row[:] for row in self.h_edges],
            "v_edges": [row[:] for row in self.v_edges],
            "boxes": [row[:] for row in self.boxes],
            "game_over": self.game_over,
            "winner": self.winner,
            "recorded": self.recorded,
            "status_msg": self.status_msg
        }

    def from_dict(self, data):
        if not data:
            return
        self.grid_size = data.get("grid_size", self.grid_size)
        self.game_type = data.get("game_type", data.get("mode", "PVP"))
        if self.game_type == "2P":
            self.game_type = "PVP"
            self.player_count = 2
        elif self.game_type == "3P":
            self.game_type = "PVP"
            self.player_count = 3
        elif self.game_type == "4P":
            self.game_type = "PVP"
            self.player_count = 4
        elif self.game_type == "VS_AI":
            self.player_count = 2

        self.player_count = data.get("player_count", self.player_count)
        self.difficulty = data.get("difficulty", self.difficulty)
        self.num_players = self.player_count if self.game_type == "PVP" else 2

        self.current_player = data.get("current_player", self.current_player)
        saved_scores = data.get("scores")
        if saved_scores and isinstance(saved_scores, list):
            self.scores = list(saved_scores)
            while len(self.scores) < 4:
                self.scores.append(0)

        saved_h = data.get("h_edges")
        if saved_h and isinstance(saved_h, list):
            self.h_edges = [list(row) for row in saved_h]

        saved_v = data.get("v_edges")
        if saved_v and isinstance(saved_v, list):
            self.v_edges = [list(row) for row in saved_v]

        saved_boxes = data.get("boxes")
        if saved_boxes and isinstance(saved_boxes, list):
            self.boxes = [list(row) for row in saved_boxes]

        self.game_over = data.get("game_over", self.game_over)
        self.winner = data.get("winner", self.winner)
        self.recorded = data.get("recorded", self.recorded)
        self.status_msg = data.get("status_msg", self.status_msg)
        self.selected_dot = None
        self.prev_selected = None
        self.prev_hud_player = -1
        self.prev_hud_scores = [-1, -1, -1, -1]
        self.prev_status_msg = ""

    def get_layout(self):
        N = self.grid_size
        cell_size = 240 // (N - 1)
        if N == 6:
            cell_size = 48
        board_w = (N - 1) * cell_size
        board_h = (N - 1) * cell_size
        origin_x = (320 - board_w) // 2
        origin_y = 138 + (292 - board_h) // 2
        dot_r = 7 if N <= 4 else (6 if N == 5 else 5)
        line_t = 4 if N <= 5 else 3
        return origin_x, origin_y, cell_size, dot_r, line_t

    def get_dot_pos(self, r, c):
        ox, oy, cell_size, _, _ = self.get_layout()
        return ox + c * cell_size, oy + r * cell_size

    def find_closest_dot(self, tx, ty):
        """O(1) exact nearest dot hit test."""
        N = self.grid_size
        ox, oy, cell_size, _, _ = self.get_layout()
        touch_radius = cell_size // 2
        c = (tx - ox + cell_size // 2) // cell_size
        r = (ty - oy + cell_size // 2) // cell_size
        if 0 <= r < N and 0 <= c < N:
            dx = tx - (ox + c * cell_size)
            dy = ty - (oy + r * cell_size)
            if dx * dx + dy * dy <= touch_radius * touch_radius:
                return (r, c)
        return None

    def _check_completed_boxes(self, player_idx):
        N = self.grid_size
        completed = []
        for r in range(N - 1):
            for c in range(N - 1):
                if self.boxes[r][c] is None:
                    if (self.h_edges[r][c] is not None and
                        self.h_edges[r + 1][c] is not None and
                        self.v_edges[r][c] is not None and
                        self.v_edges[r][c + 1] is not None):
                        self.boxes[r][c] = player_idx
                        self.scores[player_idx] += 1
                        completed.append((r, c))
        return completed

    def _is_board_full(self):
        N = self.grid_size
        for r in range(N - 1):
            for c in range(N - 1):
                if self.boxes[r][c] is None:
                    return False
        return True

    def _finalize_game(self):
        self.game_over = True
        max_score = max(self.scores[:self.num_players])
        winners = [i for i in range(self.num_players) if self.scores[i] == max_score]
        
        if len(winners) == 1:
            self.winner = winners[0]
            w_name = "AI" if (self.game_type == "VS_AI" and self.winner == 1) else PLAYER_NAMES[self.winner]
            self.status_msg = "WINNER: " + w_name + "! (" + str(max_score) + " BOXES)"
            if not self.recorded:
                scoreboard.record_dots(self.winner)
                self.recorded = True
        else:
            self.winner = "DRAW"
            self.status_msg = "DRAW GAME! (" + str(max_score) + " BOXES EACH)"
            if not self.recorded:
                scoreboard.record_dots("DRAW")
                self.recorded = True

    def place_edge(self, edge_type, r, c):
        if self.game_over:
            return False, []

        player = self.current_player
        if edge_type == "H":
            if self.h_edges[r][c] is not None:
                return False, []
            self.h_edges[r][c] = player
            self.last_edge = ("H", r, c)
        elif edge_type == "V":
            if self.v_edges[r][c] is not None:
                return False, []
            self.v_edges[r][c] = player
            self.last_edge = ("V", r, c)
        else:
            return False, []

        completed = self._check_completed_boxes(player)
        self.last_completed = completed

        if self._is_board_full():
            self._finalize_game()
            return True, completed

        if len(completed) > 0:
            p_name = "AI" if (self.game_type == "VS_AI" and player == 1) else PLAYER_NAMES[player]
            self.status_msg = p_name + " SCORED +" + str(len(completed)) + "! BONUS TURN!"
        else:
            self.current_player = (self.current_player + 1) % self.num_players
            p_name = "AI" if (self.game_type == "VS_AI" and self.current_player == 1) else PLAYER_NAMES[self.current_player]
            self.status_msg = p_name + "'S TURN - SELECT A DOT"

        gc.collect()
        return True, completed

    def handle_dot_tap(self, r, c):
        if self.game_over:
            return "GAME_OVER"

        if self.selected_dot is None:
            self.selected_dot = (r, c)
            self.prev_selected = None
            p_name = "AI" if (self.game_type == "VS_AI" and self.current_player == 1) else PLAYER_NAMES[self.current_player]
            self.status_msg = p_name + ": TAP AN ADJACENT DOT"
            return "SELECT"

        r0, c0 = self.selected_dot

        if (r, c) == (r0, c0):
            self.prev_selected = self.selected_dot
            self.selected_dot = None
            p_name = "AI" if (self.game_type == "VS_AI" and self.current_player == 1) else PLAYER_NAMES[self.current_player]
            self.status_msg = p_name + ": SELECT A DOT"
            return "DESELECT"

        dr = abs(r - r0)
        dc = abs(c - c0)

        if dr + dc == 1:
            if r == r0:
                min_c = min(c0, c)
                success, completed = self.place_edge("H", r, min_c)
            else:
                min_r = min(r0, r)
                success, completed = self.place_edge("V", min_r, c)

            if success:
                self.prev_selected = (r0, c0)
                self.selected_dot = None
                return "DRAW"
            else:
                self.prev_selected = (r0, c0)
                self.selected_dot = (r, c)
                return "SWITCH"
        else:
            self.prev_selected = (r0, c0)
            self.selected_dot = (r, c)
            return "SWITCH"

    def _get_box_edge_count(self, br, bc):
        count = 0
        if self.h_edges[br][bc] is not None: count += 1
        if self.h_edges[br + 1][bc] is not None: count += 1
        if self.v_edges[br][bc] is not None: count += 1
        if self.v_edges[br][bc + 1] is not None: count += 1
        return count

    def ai_move(self):
        """Intelligent AI move engine respecting EASY, MEDIUM, HARD difficulty."""
        if self.game_over or self.game_type != "VS_AI" or self.current_player != 1:
            return None

        N = self.grid_size
        open_h = []
        for r in range(N):
            for c in range(N - 1):
                if self.h_edges[r][c] is None:
                    open_h.append((r, c))

        open_v = []
        for r in range(N - 1):
            for c in range(N):
                if self.v_edges[r][c] is None:
                    open_v.append((r, c))

        if not open_h and not open_v:
            return None

        # -------------------------------------------------------------
        # EASY DIFFICULTY: 40% random, 60% standard basic capture
        # -------------------------------------------------------------
        if self.difficulty == "EASY":
            if random.random() < 0.40:
                all_remaining = [("H", r, c) for r, c in open_h] + [("V", r, c) for r, c in open_v]
                chosen = random.choice(all_remaining)
                self.place_edge(chosen[0], chosen[1], chosen[2])
                return chosen

            for r, c in open_h:
                if (r > 0 and self._get_box_edge_count(r - 1, c) == 3) or (r < N - 1 and self._get_box_edge_count(r, c) == 3):
                    self.place_edge("H", r, c)
                    return ("H", r, c)
            for r, c in open_v:
                if (c > 0 and self._get_box_edge_count(r, c - 1) == 3) or (c < N - 1 and self._get_box_edge_count(r, c) == 3):
                    self.place_edge("V", r, c)
                    return ("V", r, c)

            all_remaining = [("H", r, c) for r, c in open_h] + [("V", r, c) for r, c in open_v]
            chosen = random.choice(all_remaining)
            self.place_edge(chosen[0], chosen[1], chosen[2])
            return chosen

        # -------------------------------------------------------------
        # MEDIUM & HARD DIFFICULTY: Always take immediate captures
        # -------------------------------------------------------------
        for r, c in open_h:
            if (r > 0 and self._get_box_edge_count(r - 1, c) == 3) or (r < N - 1 and self._get_box_edge_count(r, c) == 3):
                self.place_edge("H", r, c)
                return ("H", r, c)

        for r, c in open_v:
            if (c > 0 and self._get_box_edge_count(r, c - 1) == 3) or (c < N - 1 and self._get_box_edge_count(r, c) == 3):
                self.place_edge("V", r, c)
                return ("V", r, c)

        safe_moves = []
        for r, c in open_h:
            is_safe = True
            if r > 0 and self._get_box_edge_count(r - 1, c) == 2: is_safe = False
            if r < N - 1 and self._get_box_edge_count(r, c) == 2: is_safe = False
            if is_safe:
                safe_moves.append(("H", r, c))

        for r, c in open_v:
            is_safe = True
            if c > 0 and self._get_box_edge_count(r, c - 1) == 2: is_safe = False
            if c < N - 1 and self._get_box_edge_count(r, c) == 2: is_safe = False
            if is_safe:
                safe_moves.append(("V", r, c))

        if safe_moves:
            chosen = random.choice(safe_moves)
            self.place_edge(chosen[0], chosen[1], chosen[2])
            return chosen

        all_remaining = [("H", r, c) for r, c in open_h] + [("V", r, c) for r, c in open_v]
        if self.difficulty == "HARD":
            best_move = None
            min_damage = 999

            for m in all_remaining:
                t, r, c = m
                damage = 0
                if t == "H":
                    if r > 0 and self._get_box_edge_count(r - 1, c) == 2: damage += 1
                    if r < N - 1 and self._get_box_edge_count(r, c) == 2: damage += 1
                else:
                    if c > 0 and self._get_box_edge_count(r, c - 1) == 2: damage += 1
                    if c < N - 1 and self._get_box_edge_count(r, c) == 2: damage += 1

                if damage < min_damage:
                    min_damage = damage
                    best_move = m

            if best_move:
                self.place_edge(best_move[0], best_move[1], best_move[2])
                return best_move

        chosen = random.choice(all_remaining)
        self.place_edge(chosen[0], chosen[1], chosen[2])
        return chosen


# ==============================================================================
# UI RENDERING FUNCTIONS (ZERO-FLICKER DIFFERENTIAL UPDATES)
# ==============================================================================

def draw_player_hud(tft, game, force=False):
    """Renders the player score cards with zero-flicker differential updates."""
    num_p = game.num_players
    
    # Check if HUD actually changed
    scores_changed = False
    for i in range(num_p):
        if game.scores[i] != game.prev_hud_scores[i]:
            scores_changed = True
            break

    if not force and game.current_player == game.prev_hud_player and not scores_changed:
        return

    spacing = 6
    total_w = 320 - (num_p + 1) * spacing
    card_w = total_w // num_p

    for i in range(num_p):
        cx = spacing + i * (card_w + spacing)
        cy = 90
        ch = 42

        is_active = (i == game.current_player and not game.game_over)
        bg_col = COLOR_CARD_BG if not is_active else rgb565(38, 52, 78)
        border_col = PLAYER_COLORS[i] if is_active else rgb565(71, 85, 105)

        # Draw card container directly without clearing whole bar
        tft.fill_rect(cx, cy, card_w, ch, bg_col)
        tft.fill_rect(cx, cy, card_w, 2, border_col)
        tft.fill_rect(cx, cy + ch - 2, card_w, 2, border_col)
        tft.fill_rect(cx, cy, 2, ch, border_col)
        tft.fill_rect(cx + card_w - 2, cy, 2, ch, border_col)

        label = "AI" if (game.game_type == "VS_AI" and i == 1) else PLAYER_NAMES[i]
        tft.draw_text(label, cx + 6, cy + 6, PLAYER_COLORS[i], bg=bg_col, scale=1)

        score_str = str(game.scores[i])
        tft.draw_text(score_str, cx + card_w - len(score_str) * 12 - 6, cy + 12, COLOR_WHITE, bg=bg_col, scale=2)

        if is_active:
            tft.fill_rect(cx + 6, cy + 32, card_w - 12, 3, PLAYER_COLORS[i])

    game.prev_hud_player = game.current_player
    for i in range(4):
        game.prev_hud_scores[i] = game.scores[i]


def draw_dots_board_background(tft, game):
    ox, oy, cell_size, dot_r, line_t = game.get_layout()
    N = game.grid_size
    board_w = (N - 1) * cell_size
    board_h = (N - 1) * cell_size

    tft.fill_rect(ox - 16, oy - 16, board_w + 32, board_h + 32, COLOR_BOARD_PLATE)
    tft.fill_rect(ox - 14, oy - 14, board_w + 28, board_h + 28, COLOR_BOARD_BG)

    for r in range(N):
        for c in range(N - 1):
            x1, y1 = game.get_dot_pos(r, c)
            tft.fill_rect(x1 + dot_r, y1 - 1, cell_size - 2 * dot_r, 2, COLOR_LINE_EMPTY)

    for r in range(N - 1):
        for c in range(N):
            x1, y1 = game.get_dot_pos(r, c)
            tft.fill_rect(x1 - 1, y1 + dot_r, 2, cell_size - 2 * dot_r, COLOR_LINE_EMPTY)


def draw_single_box(tft, game, r, c):
    owner = game.boxes[r][c]
    if owner is None:
        return

    ox, oy, cell_size, dot_r, _ = game.get_layout()
    x1, y1 = game.get_dot_pos(r, c)
    box_x = x1 + dot_r + 2
    box_y = y1 + dot_r + 2
    box_w = cell_size - 2 * dot_r - 4
    box_h = cell_size - 2 * dot_r - 4

    box_bg = PLAYER_BOX_BG[owner]
    tft.fill_rect(box_x, box_y, box_w, box_h, box_bg)
    tft.fill_rect(box_x, box_y, box_w, 1, PLAYER_COLORS[owner])
    tft.fill_rect(box_x, box_y + box_h - 1, box_w, 1, PLAYER_COLORS[owner])
    tft.fill_rect(box_x, box_y, 1, box_h, PLAYER_COLORS[owner])
    tft.fill_rect(box_x + box_w - 1, box_y, 1, box_h, PLAYER_COLORS[owner])

    label = "AI" if (game.game_type == "VS_AI" and owner == 1) else PLAYER_NAMES[owner]
    scale = 2 if game.grid_size <= 4 else 1
    char_w = 6 * scale
    char_h = 8 * scale
    tx = box_x + (box_w - len(label) * char_w) // 2
    ty = box_y + (box_h - char_h) // 2
    tft.draw_text(label, tx, ty, COLOR_WHITE, bg=box_bg, scale=scale)


def draw_single_edge(tft, game, edge_type, r, c):
    ox, oy, cell_size, dot_r, line_t = game.get_layout()
    
    if edge_type == "H":
        owner = game.h_edges[r][c]
        if owner is None:
            return
        x1, y1 = game.get_dot_pos(r, c)
        col = PLAYER_COLORS[owner]
        half_t = line_t // 2
        tft.fill_rect(x1 + dot_r - 1, y1 - half_t, cell_size - 2 * dot_r + 2, line_t, col)
    elif edge_type == "V":
        owner = game.v_edges[r][c]
        if owner is None:
            return
        x1, y1 = game.get_dot_pos(r, c)
        col = PLAYER_COLORS[owner]
        half_t = line_t // 2
        tft.fill_rect(x1 - half_t, y1 + dot_r - 1, line_t, cell_size - 2 * dot_r + 2, col)


def draw_single_dot(tft, game, r, c):
    ox, oy, cell_size, dot_r, _ = game.get_layout()
    x, y = game.get_dot_pos(r, c)
    is_selected = (game.selected_dot == (r, c))

    if is_selected:
        p_col = PLAYER_COLORS[game.current_player]
        draw_filled_circle(tft, x, y, dot_r + 4, p_col)
        draw_filled_circle(tft, x, y, dot_r + 2, COLOR_DARK_BG)
        draw_filled_circle(tft, x, y, dot_r, COLOR_WHITE)
    else:
        tft.fill_rect(x - dot_r - 5, y - dot_r - 5, (dot_r + 5) * 2 + 1, (dot_r + 5) * 2 + 1, COLOR_BOARD_BG)
        N = game.grid_size
        if c > 0:
            if game.h_edges[r][c - 1] is not None:
                draw_single_edge(tft, game, "H", r, c - 1)
            else:
                tft.fill_rect(x - dot_r - 5, y - 1, 5, 2, COLOR_LINE_EMPTY)

        if c < N - 1:
            if game.h_edges[r][c] is not None:
                draw_single_edge(tft, game, "H", r, c)
            else:
                tft.fill_rect(x + dot_r + 1, y - 1, 5, 2, COLOR_LINE_EMPTY)

        if r > 0:
            if game.v_edges[r - 1][c] is not None:
                draw_single_edge(tft, game, "V", r - 1, c)
            else:
                tft.fill_rect(x - 1, y - dot_r - 5, 2, 5, COLOR_LINE_EMPTY)

        if r < N - 1:
            if game.v_edges[r][c] is not None:
                draw_single_edge(tft, game, "V", r, c)
            else:
                tft.fill_rect(x - 1, y + dot_r + 1, 2, 5, COLOR_LINE_EMPTY)
        
        draw_filled_circle(tft, x, y, dot_r, COLOR_DOT_DEFAULT)


def draw_status_bar(tft, game, force=False):
    """Draws the bottom status banner only if the status text changed."""
    if not force and game.status_msg == game.prev_status_msg:
        return

    tft.fill_rect(0, 442, 320, 38, COLOR_HEADER_BG)
    tft.fill_rect(0, 442, 320, 1, rgb565(71, 85, 105))

    msg = game.status_msg
    color = COLOR_WHITE
    if game.game_over:
        color = COLOR_GOOGLE_YELLOW if game.winner != "DRAW" else COLOR_TEXT_LIGHT
    elif "EXTRA TURN" in msg or "SCORED" in msg:
        color = COLOR_GOOGLE_GREEN

    scale = 1
    char_w = 6 * scale
    tx = (320 - len(msg) * char_w) // 2
    tft.draw_text(msg, max(8, tx), 454, color, bg=COLOR_HEADER_BG, scale=scale)

    game.prev_status_msg = msg


def init_dots_ui(tft, game):
    """Full initialization and redraw of the Dots and Boxes UI with 3 subheader controls."""
    tft.fill_rect(0, 0, 320, 480, COLOR_DARK_BG)
    draw_header_bar(tft, "DOTS & BOXES")

    # Subheader Control 1: Game Type (PVP vs AI)
    mode_txt = "MODE: PVP" if game.game_type == "PVP" else "MODE: AI"
    mode_col = COLOR_GOOGLE_BLUE if game.game_type == "PVP" else COLOR_GOOGLE_RED
    draw_button(tft, 6, 52, 98, 30, mode_txt, COLOR_CARD_BG, mode_col, scale=1)

    # Subheader Control 2: Conditional Sub-Option (Player Count if PVP, Difficulty if AI)
    if game.game_type == "PVP":
        sub_txt = str(game.player_count) + " PLAYERS"
        sub_col = COLOR_GOOGLE_GREEN
    else:
        sub_txt = "DIF:" + game.difficulty[:4]
        sub_col = COLOR_GOOGLE_YELLOW if game.difficulty == "MEDIUM" else (COLOR_GOOGLE_GREEN if game.difficulty == "EASY" else COLOR_GOOGLE_RED)
    draw_button(tft, 110, 52, 100, 30, sub_txt, COLOR_CARD_BG, sub_col, scale=1)

    # Subheader Control 3: Grid Size
    grid_label = "GRID:" + str(game.grid_size) + "x" + str(game.grid_size)
    draw_button(tft, 216, 52, 98, 30, grid_label, COLOR_CARD_BG, COLOR_WHITE, scale=1)

    # Player Score HUD (force=True on initial draw)
    draw_player_hud(tft, game, force=True)

    # Board background & plate
    draw_dots_board_background(tft, game)

    # Draw all existing lines
    N = game.grid_size
    for r in range(N):
        for c in range(N - 1):
            if game.h_edges[r][c] is not None:
                draw_single_edge(tft, game, "H", r, c)

    for r in range(N - 1):
        for c in range(N):
            if game.v_edges[r][c] is not None:
                draw_single_edge(tft, game, "V", r, c)

    # Draw all completed boxes
    for r in range(N - 1):
        for c in range(N - 1):
            if game.boxes[r][c] is not None:
                draw_single_box(tft, game, r, c)

    # Draw all dots
    for r in range(N):
        for c in range(N):
            draw_single_dot(tft, game, r, c)

    # Bottom status bar (force=True on initial draw)
    draw_status_bar(tft, game, force=True)


def update_dots_ui(tft, game):
    """Incremental update for high-speed, 100% flicker-free UI refreshes."""
    # Only redraws HUD if turn or score changed!
    draw_player_hud(tft, game, force=False)

    if game.last_edge:
        edge_t, r, c = game.last_edge
        draw_single_edge(tft, game, edge_t, r, c)
        game.last_edge = None

    if game.last_completed:
        for r, c in game.last_completed:
            draw_single_box(tft, game, r, c)
        game.last_completed = []

    if game.prev_selected:
        pr, pc = game.prev_selected
        draw_single_dot(tft, game, pr, pc)
        game.prev_selected = None

    if game.selected_dot:
        sr, sc = game.selected_dot
        draw_single_dot(tft, game, sr, sc)

    # Only redraws status bar if text changed!
    draw_status_bar(tft, game, force=False)
