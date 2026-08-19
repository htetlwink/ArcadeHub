# game_tri_dots.py - Dots & Triangles Game Engine & Renderer for WT32-SC01 (Non-Crossing Diagonals)
import random
import time
import gc
from arcade_common import (
    COLOR_DARK_BG, COLOR_HEADER_BG, COLOR_CARD_BG, COLOR_WHITE,
    COLOR_TEXT_LIGHT, COLOR_TEXT_MUTED, COLOR_GOOGLE_BLUE, COLOR_GOOGLE_RED,
    COLOR_GOOGLE_YELLOW, COLOR_GOOGLE_GREEN, rgb565, draw_filled_circle,
    draw_thick_line_diag, draw_button, draw_header_bar, scoreboard
)

# Player Colors and Tint Backgrounds
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
COLOR_BOARD_PLATE  = rgb565(24, 32, 47)    # Dark plate


class DotsAndTriangles:
    def __init__(self, grid_size=4, game_type="PVP", player_count=2, difficulty="MEDIUM"):
        self.grid_size = grid_size        # 3 (8 Triangles), 4 (18 Triangles), 5 (32 Triangles)
        self.game_type = game_type        # "PVP" or "VS_AI"
        self.player_count = player_count  # 2, 3, 4 (if PVP)
        self.difficulty = difficulty      # "EASY", "MEDIUM", "HARD" (if VS_AI)

        self.num_players = player_count if game_type == "PVP" else 2
        self.current_player = 0
        self.scores = [0, 0, 0, 0]
        self.selected_dot = None          # (r, c) or None
        self.game_over = False
        self.winner = None
        self.recorded = False
        self.status_msg = "P1: TAP A DOT TO START"
        self.last_edge = None             # ("H"/"V"/"SLASH"/"BSLASH", r, c)
        self.last_triangles = []          # list of ("TL"/"BR"/"TR"/"BL", r, c)
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

        # Diagonals (Non-crossing: exactly 1 diagonal per cell allowed)
        self.d_slash = [[None] * (N - 1) for _ in range(N - 1)]
        self.d_bslash = [[None] * (N - 1) for _ in range(N - 1)]

        # 2 Triangles per cell
        self.tri_TL = [[None] * (N - 1) for _ in range(N - 1)]
        self.tri_BR = [[None] * (N - 1) for _ in range(N - 1)]
        self.tri_TR = [[None] * (N - 1) for _ in range(N - 1)]
        self.tri_BL = [[None] * (N - 1) for _ in range(N - 1)]

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
        self.last_triangles = []
        self.status_msg = "P1: TAP A DOT TO START"
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
            "d_slash": [row[:] for row in self.d_slash],
            "d_bslash": [row[:] for row in self.d_bslash],
            "tri_TL": [row[:] for row in self.tri_TL],
            "tri_BR": [row[:] for row in self.tri_BR],
            "tri_TR": [row[:] for row in self.tri_TR],
            "tri_BL": [row[:] for row in self.tri_BL],
            "game_over": self.game_over,
            "winner": self.winner,
            "recorded": self.recorded,
            "status_msg": self.status_msg
        }

    def from_dict(self, data):
        if not data:
            return
        self.grid_size = data.get("grid_size", self.grid_size)
        self.game_type = data.get("game_type", "PVP")
        self.player_count = data.get("player_count", self.player_count)
        self.difficulty = data.get("difficulty", self.difficulty)
        self.num_players = self.player_count if self.game_type == "PVP" else 2
        self.current_player = data.get("current_player", 0)

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

        saved_s = data.get("d_slash")
        if saved_s and isinstance(saved_s, list):
            self.d_slash = [list(row) for row in saved_s]

        saved_bs = data.get("d_bslash")
        if saved_bs and isinstance(saved_bs, list):
            self.d_bslash = [list(row) for row in saved_bs]

        saved_tl = data.get("tri_TL")
        if saved_tl and isinstance(saved_tl, list):
            self.tri_TL = [list(row) for row in saved_tl]

        saved_br = data.get("tri_BR")
        if saved_br and isinstance(saved_br, list):
            self.tri_BR = [list(row) for row in saved_br]

        saved_tr = data.get("tri_TR")
        if saved_tr and isinstance(saved_tr, list):
            self.tri_TR = [list(row) for row in saved_tr]

        saved_bl = data.get("tri_BL")
        if saved_bl and isinstance(saved_bl, list):
            self.tri_BL = [list(row) for row in saved_bl]

        self.game_over = data.get("game_over", False)
        self.winner = data.get("winner", None)
        self.recorded = data.get("recorded", False)
        self.status_msg = data.get("status_msg", "RESUMED MATCH")
        self.selected_dot = None
        self.prev_selected = None
        self.prev_hud_player = -1
        self.prev_hud_scores = [-1, -1, -1, -1]
        self.prev_status_msg = ""

    # ==========================================================================
    # LAYOUT & TOUCH LOGIC (TFT 320x480)
    # ==========================================================================
    def get_layout(self):
        N = self.grid_size
        if N == 3:
            cell_size = 90
            ox = 70
            oy = 170
            dot_r = 7
            line_t = 4
        elif N == 5:
            cell_size = 56
            ox = 48
            oy = 152
            dot_r = 5
            line_t = 3
        else:  # N == 4
            cell_size = 72
            ox = 52
            oy = 158
            dot_r = 6
            line_t = 4

        return ox, oy, cell_size, dot_r, line_t

    def get_dot_pos(self, r, c):
        ox, oy, cell_size, _, _ = self.get_layout()
        return ox + c * cell_size, oy + r * cell_size

    def find_closest_dot(self, tx, ty):
        """O(1) exact nearest dot hit test."""
        ox, oy, cell_size, _, _ = self.get_layout()
        N = self.grid_size
        touch_r = cell_size // 2
        c = (tx - ox + cell_size // 2) // cell_size
        r = (ty - oy + cell_size // 2) // cell_size
        if 0 <= r < N and 0 <= c < N:
            dx = tx - (ox + c * cell_size)
            dy = ty - (oy + r * cell_size)
            if dx * dx + dy * dy <= touch_r * touch_r:
                return (r, c)
        return None

    def handle_dot_tap(self, r, c):
        if self.game_over:
            return False

        if self.selected_dot is None:
            self.selected_dot = (r, c)
            self.prev_selected = None
            p_name = "AI" if (self.game_type == "VS_AI" and self.current_player == 1) else PLAYER_NAMES[self.current_player]
            self.status_msg = p_name + ": TAP ADJACENT DOT"
            return True

        r0, c0 = self.selected_dot
        if (r, c) == (r0, c0):
            self.prev_selected = self.selected_dot
            self.selected_dot = None
            p_name = "AI" if (self.game_type == "VS_AI" and self.current_player == 1) else PLAYER_NAMES[self.current_player]
            self.status_msg = p_name + ": SELECTION CANCELED"
            return True

        dr = abs(r - r0)
        dc = abs(c - c0)

        if dr <= 1 and dc <= 1 and (dr + dc > 0):
            edge_type = None
            er, ec = 0, 0

            if dr == 0 and dc == 1:
                edge_type = "H"
                er = r0
                ec = min(c0, c)
            elif dr == 1 and dc == 0:
                edge_type = "V"
                er = min(r0, r)
                ec = c0
            elif dr == 1 and dc == 1:
                if (r - r0) == (c - c0):
                    edge_type = "BSLASH"
                    er = min(r0, r)
                    ec = min(c0, c)
                else:
                    edge_type = "SLASH"
                    er = min(r0, r)
                    ec = min(c0, c)

            success, captured, reason = self.place_edge(edge_type, er, ec)
            if success:
                self.prev_selected = self.selected_dot
                self.selected_dot = None
                return True
            else:
                if reason == "CROSSING_BLOCKED":
                    self.status_msg = "CANNOT CROSS DIAGONALS!"
                else:
                    self.status_msg = "LINE ALREADY DRAWN"
                self.prev_selected = self.selected_dot
                self.selected_dot = (r, c)
                return True
        else:
            self.prev_selected = self.selected_dot
            self.selected_dot = (r, c)
            p_name = "AI" if (self.game_type == "VS_AI" and self.current_player == 1) else PLAYER_NAMES[self.current_player]
            self.status_msg = p_name + ": TAP ADJACENT DOT"
            return True

    # ==========================================================================
    # CORE ENGINE & TRIANGLE DETECTION (NON-CROSSING DIAGONALS)
    # ==========================================================================
    def place_edge(self, edge_type, r, c):
        if edge_type == "H":
            if self.h_edges[r][c] is not None:
                return False, 0, "ALREADY_DRAWN"
        elif edge_type == "V":
            if self.v_edges[r][c] is not None:
                return False, 0, "ALREADY_DRAWN"
        elif edge_type == "SLASH":
            if self.d_slash[r][c] is not None:
                return False, 0, "ALREADY_DRAWN"
            if self.d_bslash[r][c] is not None:
                return False, 0, "CROSSING_BLOCKED"
        elif edge_type == "BSLASH":
            if self.d_bslash[r][c] is not None:
                return False, 0, "ALREADY_DRAWN"
            if self.d_slash[r][c] is not None:
                return False, 0, "CROSSING_BLOCKED"

        p = self.current_player
        if edge_type == "H": self.h_edges[r][c] = p
        elif edge_type == "V": self.v_edges[r][c] = p
        elif edge_type == "SLASH": self.d_slash[r][c] = p
        elif edge_type == "BSLASH": self.d_bslash[r][c] = p

        self.last_edge = (edge_type, r, c)
        self.last_triangles = []

        captured = self._check_completed_triangles(p)

        if captured > 0:
            self.scores[p] += captured
            p_name = "AI" if (self.game_type == "VS_AI" and p == 1) else PLAYER_NAMES[p]
            if captured >= 2:
                self.status_msg = p_name + " DUAL CAPTURE! +" + str(captured) + " EXTRA TURN"
            else:
                self.status_msg = p_name + " SCORED! EXTRA TURN"
        else:
            self.current_player = (self.current_player + 1) % self.num_players
            next_p = "AI" if (self.game_type == "VS_AI" and self.current_player == 1) else PLAYER_NAMES[self.current_player]
            self.status_msg = next_p + "'S TURN"

        self._check_endgame()
        gc.collect()
        return True, captured, "SUCCESS"

    def _check_completed_triangles(self, player_idx):
        N = self.grid_size
        completed_count = 0

        for r in range(N - 1):
            for c in range(N - 1):
                if self.d_slash[r][c] is not None:
                    # TL Triangle
                    if self.tri_TL[r][c] is None and self.h_edges[r][c] is not None and self.v_edges[r][c] is not None:
                        self.tri_TL[r][c] = player_idx
                        self.last_triangles.append(("TL", r, c))
                        completed_count += 1
                    # BR Triangle
                    if self.tri_BR[r][c] is None and self.v_edges[r][c + 1] is not None and self.h_edges[r + 1][c] is not None:
                        self.tri_BR[r][c] = player_idx
                        self.last_triangles.append(("BR", r, c))
                        completed_count += 1
                elif self.d_bslash[r][c] is not None:
                    # TR Triangle
                    if self.tri_TR[r][c] is None and self.h_edges[r][c] is not None and self.v_edges[r][c + 1] is not None:
                        self.tri_TR[r][c] = player_idx
                        self.last_triangles.append(("TR", r, c))
                        completed_count += 1
                    # BL Triangle
                    if self.tri_BL[r][c] is None and self.v_edges[r][c] is not None and self.h_edges[r + 1][c] is not None:
                        self.tri_BL[r][c] = player_idx
                        self.last_triangles.append(("BL", r, c))
                        completed_count += 1

        return completed_count

    def _get_all_unplaced_edges(self):
        N = self.grid_size
        edges = []
        for r in range(N):
            for c in range(N - 1):
                if self.h_edges[r][c] is None: edges.append(("H", r, c))
        for r in range(N - 1):
            for c in range(N):
                if self.v_edges[r][c] is None: edges.append(("V", r, c))
        for r in range(N - 1):
            for c in range(N - 1):
                if self.d_slash[r][c] is None and self.d_bslash[r][c] is None:
                    edges.append(("SLASH", r, c))
                    edges.append(("BSLASH", r, c))
        return edges

    def _check_endgame(self):
        N = self.grid_size
        total_triangles = 2 * (N - 1) * (N - 1)
        claimed = sum(self.scores[:self.num_players])

        if not self._get_all_unplaced_edges() or claimed == total_triangles:
            self.game_over = True
            max_score = max(self.scores[:self.num_players])
            winners = [i for i in range(self.num_players) if self.scores[i] == max_score]

            if len(winners) == 1:
                w = winners[0]
                self.winner = w
                w_name = "YOU" if (self.game_type == "VS_AI" and w == 0) else ("AI" if (self.game_type == "VS_AI" and w == 1) else PLAYER_NAMES[w])
                self.status_msg = "GAME OVER: " + w_name + " WINS (" + str(self.scores[w]) + " PTS)!"
            else:
                self.winner = "DRAW"
                self.status_msg = "GAME OVER: TIED AT " + str(max_score) + " PTS!"

            if not self.recorded:
                scoreboard.record_tridots(self.winner)
                self.recorded = True

    # ==========================================================================
    # AI OPPONENT ENGINE (ZERO ALLOCATION IN-PLACE SIMULATION)
    # ==========================================================================
    def ai_move(self):
        if self.game_over or self.current_player != 1:
            return None

        edges = self._get_all_unplaced_edges()
        if not edges:
            return None

        # 1. Immediate Captures
        completing = []
        for e in edges:
            c = self._count_simulated_captures(e)
            if c > 0:
                completing.append((c, e))

        if completing:
            completing.sort(key=lambda x: x[0], reverse=True)
            chosen = completing[0][1]
            self.place_edge(chosen[0], chosen[1], chosen[2])
            return chosen

        if self.difficulty == "EASY":
            chosen = random.choice(edges)
            self.place_edge(chosen[0], chosen[1], chosen[2])
            return chosen

        # 2. Safe moves (does not leave 2 edges in any triangle)
        safe_moves = []
        dangerous_moves = []

        for e in edges:
            if self._is_move_dangerous(e):
                dangerous_moves.append(e)
            else:
                safe_moves.append(e)

        if safe_moves:
            chosen = random.choice(safe_moves)
            self.place_edge(chosen[0], chosen[1], chosen[2])
            return chosen

        # 3. Hard / Medium fallback
        chosen = random.choice(dangerous_moves if dangerous_moves else edges)
        self.place_edge(chosen[0], chosen[1], chosen[2])
        return chosen

    def _count_simulated_captures(self, edge):
        etype, er, ec = edge
        N = self.grid_size
        captures = 0

        # Temporarily apply edge
        if etype == "H": self.h_edges[er][ec] = 99
        elif etype == "V": self.v_edges[er][ec] = 99
        elif etype == "SLASH": self.d_slash[er][ec] = 99
        elif etype == "BSLASH": self.d_bslash[er][ec] = 99

        for r in range(N - 1):
            for c in range(N - 1):
                if self.d_slash[r][c] is not None:
                    if self.tri_TL[r][c] is None and self.h_edges[r][c] is not None and self.v_edges[r][c] is not None:
                        captures += 1
                    if self.tri_BR[r][c] is None and self.v_edges[r][c + 1] is not None and self.h_edges[r + 1][c] is not None:
                        captures += 1
                elif self.d_bslash[r][c] is not None:
                    if self.tri_TR[r][c] is None and self.h_edges[r][c] is not None and self.v_edges[r][c + 1] is not None:
                        captures += 1
                    if self.tri_BL[r][c] is None and self.v_edges[r][c] is not None and self.h_edges[r + 1][c] is not None:
                        captures += 1

        # Undo edge
        if etype == "H": self.h_edges[er][ec] = None
        elif etype == "V": self.v_edges[er][ec] = None
        elif etype == "SLASH": self.d_slash[er][ec] = None
        elif etype == "BSLASH": self.d_bslash[er][ec] = None

        return captures

    def _is_move_dangerous(self, edge):
        etype, er, ec = edge
        N = self.grid_size
        is_dangerous = False

        # Temporarily apply edge
        if etype == "H": self.h_edges[er][ec] = 99
        elif etype == "V": self.v_edges[er][ec] = 99
        elif etype == "SLASH": self.d_slash[er][ec] = 99
        elif etype == "BSLASH": self.d_bslash[er][ec] = 99

        for r in range(N - 1):
            for c in range(N - 1):
                if self.d_slash[r][c] is not None:
                    if self.tri_TL[r][c] is None:
                        drawn = (self.h_edges[r][c] is not None) + (self.v_edges[r][c] is not None) + (self.d_slash[r][c] is not None)
                        if drawn == 2:
                            is_dangerous = True
                            break
                    if self.tri_BR[r][c] is None:
                        drawn = (self.v_edges[r][c + 1] is not None) + (self.h_edges[r + 1][c] is not None) + (self.d_slash[r][c] is not None)
                        if drawn == 2:
                            is_dangerous = True
                            break
                elif self.d_bslash[r][c] is not None:
                    if self.tri_TR[r][c] is None:
                        drawn = (self.h_edges[r][c] is not None) + (self.v_edges[r][c + 1] is not None) + (self.d_bslash[r][c] is not None)
                        if drawn == 2:
                            is_dangerous = True
                            break
                    if self.tri_BL[r][c] is None:
                        drawn = (self.v_edges[r][c] is not None) + (self.h_edges[r + 1][c] is not None) + (self.d_bslash[r][c] is not None)
                        if drawn == 2:
                            is_dangerous = True
                            break
            if is_dangerous:
                break

        # Undo edge
        if etype == "H": self.h_edges[er][ec] = None
        elif etype == "V": self.v_edges[er][ec] = None
        elif etype == "SLASH": self.d_slash[er][ec] = None
        elif etype == "BSLASH": self.d_bslash[er][ec] = None

        return is_dangerous


# ==============================================================================
# UI RENDERING FUNCTIONS (ZERO-FLICKER SCANLINE DIFFERENTIAL UPDATES)
# ==============================================================================

def draw_player_hud(tft, game, force=False):
    num_p = game.num_players
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


def draw_tridots_board_background(tft, game):
    ox, oy, cell_size, dot_r, line_t = game.get_layout()
    N = game.grid_size
    board_w = (N - 1) * cell_size
    board_h = (N - 1) * cell_size

    tft.fill_rect(ox - 16, oy - 16, board_w + 32, board_h + 32, COLOR_BOARD_PLATE)
    tft.fill_rect(ox - 14, oy - 14, board_w + 28, board_h + 28, COLOR_BOARD_BG)

    # Empty guide lines (H and V)
    for r in range(N):
        for c in range(N - 1):
            x1, y1 = game.get_dot_pos(r, c)
            tft.fill_rect(x1 + dot_r, y1 - 1, cell_size - 2 * dot_r, 2, COLOR_LINE_EMPTY)

    for r in range(N - 1):
        for c in range(N):
            x1, y1 = game.get_dot_pos(r, c)
            tft.fill_rect(x1 - 1, y1 + dot_r, 2, cell_size - 2 * dot_r, COLOR_LINE_EMPTY)


def draw_single_triangle(tft, game, tri_type, r, c):
    """Draws a filled right-angled triangle using fast integer scanline rasterization."""
    ox, oy, cell_size, dot_r, _ = game.get_layout()
    x0, y0 = game.get_dot_pos(r, c)
    x1, y1 = game.get_dot_pos(r + 1, c + 1)

    owner = None
    if tri_type == "TL": owner = game.tri_TL[r][c]
    elif tri_type == "BR": owner = game.tri_BR[r][c]
    elif tri_type == "TR": owner = game.tri_TR[r][c]
    elif tri_type == "BL": owner = game.tri_BL[r][c]

    if owner is None:
        return

    col = PLAYER_BOX_BG[owner]

    # Insets to preserve outer lines
    ix0 = x0 + dot_r + 1
    ix1 = x1 - dot_r - 1
    iy0 = y0 + dot_r + 1
    iy1 = y1 - dot_r - 1
    W = ix1 - ix0
    H = iy1 - iy0

    if W <= 0 or H <= 0:
        return

    # Fast integer scanline fills
    if tri_type == "TL":
        # Top-left half above slash
        for dy in range(H):
            curr_y = iy0 + dy
            curr_w = (W * (H - dy)) // H
            if curr_w > 0:
                tft.fill_rect(ix0, curr_y, curr_w, 1, col)
        badge = "AI" if (game.game_type == "VS_AI" and owner == 1) else PLAYER_NAMES[owner]
        tft.draw_text(badge, x0 + cell_size // 4 - 4, y0 + cell_size // 4 - 4, COLOR_WHITE, bg=col, scale=1)

    elif tri_type == "BR":
        # Bottom-right half below slash
        for dy in range(H):
            curr_y = iy0 + dy
            curr_start_x = ix0 + (W * (H - dy)) // H
            curr_w = ix1 - curr_start_x
            if curr_w > 0:
                tft.fill_rect(curr_start_x, curr_y, curr_w, 1, col)
        badge = "AI" if (game.game_type == "VS_AI" and owner == 1) else PLAYER_NAMES[owner]
        tft.draw_text(badge, x0 + (cell_size * 3) // 4 - 6, y0 + (cell_size * 3) // 4 - 4, COLOR_WHITE, bg=col, scale=1)

    elif tri_type == "TR":
        # Top-right half above backslash
        for dy in range(H):
            curr_y = iy0 + dy
            curr_start_x = ix0 + (W * dy) // H
            curr_w = ix1 - curr_start_x
            if curr_w > 0:
                tft.fill_rect(curr_start_x, curr_y, curr_w, 1, col)
        badge = "AI" if (game.game_type == "VS_AI" and owner == 1) else PLAYER_NAMES[owner]
        tft.draw_text(badge, x0 + (cell_size * 3) // 4 - 6, y0 + cell_size // 4 - 4, COLOR_WHITE, bg=col, scale=1)

    elif tri_type == "BL":
        # Bottom-left half below backslash
        for dy in range(H):
            curr_y = iy0 + dy
            curr_w = (W * dy) // H
            if curr_w > 0:
                tft.fill_rect(ix0, curr_y, curr_w, 1, col)
        badge = "AI" if (game.game_type == "VS_AI" and owner == 1) else PLAYER_NAMES[owner]
        tft.draw_text(badge, x0 + cell_size // 4 - 4, y0 + (cell_size * 3) // 4 - 4, COLOR_WHITE, bg=col, scale=1)


def draw_single_edge(tft, game, edge_type, r, c):
    ox, oy, cell_size, dot_r, line_t = game.get_layout()
    half_t = line_t // 2

    if edge_type == "H":
        owner = game.h_edges[r][c]
        if owner is None: return
        x1, y1 = game.get_dot_pos(r, c)
        col = PLAYER_COLORS[owner]
        tft.fill_rect(x1 + dot_r - 1, y1 - half_t, cell_size - 2 * dot_r + 2, line_t, col)

    elif edge_type == "V":
        owner = game.v_edges[r][c]
        if owner is None: return
        x1, y1 = game.get_dot_pos(r, c)
        col = PLAYER_COLORS[owner]
        tft.fill_rect(x1 - half_t, y1 + dot_r - 1, line_t, cell_size - 2 * dot_r + 2, col)

    elif edge_type == "SLASH":
        owner = game.d_slash[r][c]
        if owner is None: return
        x_tr, y_tr = game.get_dot_pos(r, c + 1)
        x_bl, y_bl = game.get_dot_pos(r + 1, c)
        col = PLAYER_COLORS[owner]
        draw_thick_line_diag(tft, x_tr - dot_r, y_tr + dot_r, x_bl + dot_r, y_bl - dot_r, line_t, col)

    elif edge_type == "BSLASH":
        owner = game.d_bslash[r][c]
        if owner is None: return
        x_tl, y_tl = game.get_dot_pos(r, c)
        x_br, y_br = game.get_dot_pos(r + 1, c + 1)
        col = PLAYER_COLORS[owner]
        draw_thick_line_diag(tft, x_tl + dot_r, y_tl + dot_r, x_br - dot_r, y_br - dot_r, line_t, col)


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

        # Redraw adjacent triangles first
        if r > 0 and c > 0:
            if game.tri_BR[r - 1][c - 1] is not None: draw_single_triangle(tft, game, "BR", r - 1, c - 1)
            if game.tri_BL[r - 1][c - 1] is not None: draw_single_triangle(tft, game, "BL", r - 1, c - 1)
            if game.tri_TR[r - 1][c - 1] is not None: draw_single_triangle(tft, game, "TR", r - 1, c - 1)
        if r > 0 and c < N - 1:
            if game.tri_BL[r - 1][c] is not None: draw_single_triangle(tft, game, "BL", r - 1, c)
            if game.tri_BR[r - 1][c] is not None: draw_single_triangle(tft, game, "BR", r - 1, c)
            if game.tri_TL[r - 1][c] is not None: draw_single_triangle(tft, game, "TL", r - 1, c)
        if r < N - 1 and c > 0:
            if game.tri_TR[r][c - 1] is not None: draw_single_triangle(tft, game, "TR", r, c - 1)
            if game.tri_TL[r][c - 1] is not None: draw_single_triangle(tft, game, "TL", r, c - 1)
            if game.tri_BR[r][c - 1] is not None: draw_single_triangle(tft, game, "BR", r, c - 1)
        if r < N - 1 and c < N - 1:
            if game.tri_TL[r][c] is not None: draw_single_triangle(tft, game, "TL", r, c)
            if game.tri_TR[r][c] is not None: draw_single_triangle(tft, game, "TR", r, c)
            if game.tri_BL[r][c] is not None: draw_single_triangle(tft, game, "BL", r, c)

        # Redraw connected H-edges and guide lines
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

        # Redraw connected V-edges and guide lines
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

        # Redraw connected diagonals
        if r > 0 and c > 0 and game.d_bslash[r - 1][c - 1] is not None:
            draw_single_edge(tft, game, "BSLASH", r - 1, c - 1)
        if r > 0 and c < N - 1 and game.d_slash[r - 1][c] is not None:
            draw_single_edge(tft, game, "SLASH", r - 1, c)
        if r < N - 1 and c > 0 and game.d_slash[r][c - 1] is not None:
            draw_single_edge(tft, game, "SLASH", r, c - 1)
        if r < N - 1 and c < N - 1 and game.d_bslash[r][c] is not None:
            draw_single_edge(tft, game, "BSLASH", r, c)

        draw_filled_circle(tft, x, y, dot_r, COLOR_DOT_DEFAULT)


def draw_status_bar(tft, game, force=False):
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
    elif "CANNOT CROSS" in msg:
        color = COLOR_GOOGLE_RED

    scale = 1
    char_w = 6 * scale
    tx = (320 - len(msg) * char_w) // 2
    tft.draw_text(msg, max(8, tx), 454, color, bg=COLOR_HEADER_BG, scale=scale)

    game.prev_status_msg = msg


def init_tridots_ui(tft, game):
    """Full initialization and render of the Dots & Triangles UI."""
    tft.fill_rect(0, 0, 320, 480, COLOR_DARK_BG)
    draw_header_bar(tft, "DOTS & TRIANGLES")

    # Subheader Control 1: Mode
    mode_txt = "MODE: PVP" if game.game_type == "PVP" else "MODE: AI"
    mode_col = COLOR_GOOGLE_BLUE if game.game_type == "PVP" else COLOR_GOOGLE_RED
    draw_button(tft, 6, 52, 98, 30, mode_txt, COLOR_CARD_BG, mode_col, scale=1)

    # Subheader Control 2: Sub-Option
    if game.game_type == "PVP":
        sub_txt = str(game.player_count) + " PLAYERS"
        sub_col = COLOR_GOOGLE_GREEN
    else:
        sub_txt = "DIF:" + game.difficulty[:4]
        sub_col = COLOR_GOOGLE_YELLOW if game.difficulty == "MEDIUM" else (COLOR_GOOGLE_GREEN if game.difficulty == "EASY" else COLOR_GOOGLE_RED)
    draw_button(tft, 110, 52, 100, 30, sub_txt, COLOR_CARD_BG, sub_col, scale=1)

    # Subheader Control 3: Grid Size
    total_tri = 2 * (game.grid_size - 1) * (game.grid_size - 1)
    grid_label = str(game.grid_size) + "x" + str(game.grid_size) + " (" + str(total_tri) + "T)"
    draw_button(tft, 216, 52, 98, 30, grid_label, COLOR_CARD_BG, COLOR_WHITE, scale=1)

    # Player Score HUD
    draw_player_hud(tft, game, force=True)

    # Board plate & background
    draw_tridots_board_background(tft, game)

    # Draw all completed triangles
    N = game.grid_size
    for r in range(N - 1):
        for c in range(N - 1):
            if game.tri_TL[r][c] is not None: draw_single_triangle(tft, game, "TL", r, c)
            if game.tri_BR[r][c] is not None: draw_single_triangle(tft, game, "BR", r, c)
            if game.tri_TR[r][c] is not None: draw_single_triangle(tft, game, "TR", r, c)
            if game.tri_BL[r][c] is not None: draw_single_triangle(tft, game, "BL", r, c)

    # Draw all lines
    for r in range(N):
        for c in range(N - 1):
            if game.h_edges[r][c] is not None: draw_single_edge(tft, game, "H", r, c)

    for r in range(N - 1):
        for c in range(N):
            if game.v_edges[r][c] is not None: draw_single_edge(tft, game, "V", r, c)

    for r in range(N - 1):
        for c in range(N - 1):
            if game.d_slash[r][c] is not None: draw_single_edge(tft, game, "SLASH", r, c)
            if game.d_bslash[r][c] is not None: draw_single_edge(tft, game, "BSLASH", r, c)

    # Draw all dots
    for r in range(N):
        for c in range(N):
            draw_single_dot(tft, game, r, c)

    # Bottom status bar
    draw_status_bar(tft, game, force=True)


def update_tridots_ui(tft, game):
    """Incremental fast zero-flicker UI updates."""
    draw_player_hud(tft, game, force=False)

    # Draw completed triangles first (so lines render cleanly on top)
    if game.last_triangles:
        for tri_type, r, c in game.last_triangles:
            draw_single_triangle(tft, game, tri_type, r, c)
        game.last_triangles = []

    # Draw last edge
    if game.last_edge:
        edge_t, r, c = game.last_edge
        draw_single_edge(tft, game, edge_t, r, c)
        game.last_edge = None

    # Redraw dots if selection changed
    if game.prev_selected:
        pr, pc = game.prev_selected
        draw_single_dot(tft, game, pr, pc)
        game.prev_selected = None

    if game.selected_dot:
        sr, sc = game.selected_dot
        draw_single_dot(tft, game, sr, sc)

    draw_status_bar(tft, game, force=False)

