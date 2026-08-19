# game_checkers.py - Standard 8x8 Checkers / Draughts Engine & GUI (Fast Pure Array AI & Zero-Blink Rendering)
import random
import time
import gc
from arcade_common import (
    COLOR_DARK_BG, COLOR_HEADER_BG, COLOR_CARD_BG, COLOR_WHITE,
    COLOR_TEXT_LIGHT, COLOR_TEXT_MUTED, COLOR_GOOGLE_BLUE, COLOR_GOOGLE_RED,
    COLOR_GOOGLE_YELLOW, COLOR_GOOGLE_GREEN, draw_button, draw_header_bar,
    scoreboard, rgb565
)

# Colors
COLOR_LIGHT_SQ = rgb565(240, 217, 181)
COLOR_DARK_SQ  = rgb565(181, 136, 99)
COLOR_SEL_SQ   = rgb565(255, 235, 59)
COLOR_DOT      = rgb565(76, 175, 80)
COLOR_PIECE_W  = rgb565(245, 245, 245)
COLOR_PIECE_B  = rgb565(40, 40, 40)
COLOR_CROWN    = rgb565(255, 215, 0)

BOARD_Y_OFFSET = 90
TILE_SIZE = 40

# Pre-allocated 40x40 RGB565 tile buffer (3,200 bytes) for zero-blink, single-SPI-write rendering
TILE_BUF = bytearray(40 * 40 * 2)

def fill_tile_buf(color):
    hi = (color >> 8) & 0xFF
    lo = color & 0xFF
    TILE_BUF[0] = hi
    TILE_BUF[1] = lo
    size = 2
    while size < 3200:
        chunk = min(size, 3200 - size)
        TILE_BUF[size : size + chunk] = TILE_BUF[:chunk]
        size += chunk

def draw_buf_rect(x, y, w, h, color):
    x1 = max(0, min(40, x))
    y1 = max(0, min(40, y))
    x2 = max(0, min(40, x + w))
    y2 = max(0, min(40, y + h))
    if x2 <= x1 or y2 <= y1:
        return
    hi = (color >> 8) & 0xFF
    lo = color & 0xFF
    width_bytes = (x2 - x1) * 2
    row0_off = y1 * 80 + x1 * 2
    for px in range(x1, x2):
        idx = y1 * 80 + px * 2
        TILE_BUF[idx] = hi
        TILE_BUF[idx + 1] = lo
    for py in range(y1 + 1, y2):
        row_off = py * 80 + x1 * 2
        TILE_BUF[row_off : row_off + width_bytes] = TILE_BUF[row0_off : row0_off + width_bytes]

def draw_buf_circle(cx, cy, r, color):
    r_sq = r * r
    hi = (color >> 8) & 0xFF
    lo = color & 0xFF
    for dy in range(-r, r + 1):
        py = cy + dy
        if 0 <= py < 40:
            dx = int((r_sq - dy * dy) ** 0.5)
            x1 = max(0, cx - dx)
            x2 = min(40, cx + dx + 1)
            row_off = py * 80
            for px in range(x1, x2):
                idx = row_off + px * 2
                TILE_BUF[idx] = hi
                TILE_BUF[idx + 1] = lo

def draw_buf_crown_glyph(cx, cy, color):
    # 5x8 'K' glyph for King piece
    glyph = b'\x7F\x08\x14\x22\x41'
    hi = (color >> 8) & 0xFF
    lo = color & 0xFF
    start_x = cx - 5
    start_y = cy - 8
    scale = 2
    for col_idx in range(5):
        col_byte = glyph[col_idx]
        for row_idx in range(8):
            if (col_byte >> row_idx) & 0x01:
                px_start = start_x + col_idx * scale
                py_start = start_y + row_idx * scale
                for dy in range(scale):
                    py = py_start + dy
                    if 0 <= py < 40:
                        row_off = py * 80
                        for dx in range(scale):
                            px = px_start + dx
                            if 0 <= px < 40:
                                idx = row_off + px * 2
                                TILE_BUF[idx] = hi
                                TILE_BUF[idx + 1] = lo


class CheckersGame:
    def __init__(self):
        self.mode = "VS_AI"
        self.difficulty = "MEDIUM" # EASY, MEDIUM, HARD
        self.reset()

    def reset(self):
        self.grid = [[None] * 8 for _ in range(8)]
        # Setup starting pieces on dark squares ((r+c)%2 == 1)
        for r in range(3):
            for c in range(8):
                if (r + c) % 2 == 1:
                    self.grid[r][c] = 'B'
        for r in range(5, 8):
            for c in range(8):
                if (r + c) % 2 == 1:
                    self.grid[r][c] = 'W'

        self.turn = 'W' # 'W' or 'B'
        self.selected_pos = None
        self.valid_moves = [] # list of (to_r, to_c, captured_r, captured_c)
        self.must_jump_pos = None # Enforces multi-jump for piece at (r, c)
        self.game_over = False
        self.winner = None
        self.recorded = False

        self.prev_grid = [[None] * 8 for _ in range(8)]
        self.prev_selected_pos = None
        self._prev_valid = [(0, 0)] * 64
        self._prev_valid_count = 0
        self._dirty = bytearray(64)
        self._prev_go = None
        self._prev_winner = None
        self._prev_turn = None
        self._prev_w_cnt = -1
        self._prev_b_cnt = -1
        self._prev_must_jump = None
        self._prev_is_jump = None
        gc.collect()

    def to_dict(self):
        return {
            "grid": self.grid,
            "mode": self.mode,
            "difficulty": self.difficulty,
            "turn": self.turn,
            "selected_pos": list(self.selected_pos) if self.selected_pos else None,
            "must_jump_pos": list(self.must_jump_pos) if self.must_jump_pos else None,
            "game_over": self.game_over,
            "winner": self.winner,
            "recorded": self.recorded
        }

    def from_dict(self, data):
        if not data: return
        self.grid = data.get("grid", self.grid)
        self.mode = data.get("mode", self.mode)
        self.difficulty = data.get("difficulty", self.difficulty)
        self.turn = data.get("turn", self.turn)
        sel = data.get("selected_pos")
        self.selected_pos = tuple(sel) if sel else None
        mjp = data.get("must_jump_pos")
        self.must_jump_pos = tuple(mjp) if mjp else None
        self.game_over = data.get("game_over", self.game_over)
        self.winner = data.get("winner", self.winner)
        self.recorded = data.get("recorded", self.recorded)

        if self.must_jump_pos:
            jumps, _ = self._get_piece_moves_grid(self.grid, self.must_jump_pos[0], self.must_jump_pos[1])
            self.selected_pos = self.must_jump_pos
            self.valid_moves = jumps
        elif self.selected_pos:
            moves_dict, _ = self.get_all_valid_moves(self.turn)
            self.valid_moves = moves_dict.get(self.selected_pos, [])
        else:
            self.valid_moves = []

        self.prev_grid = [[None] * 8 for _ in range(8)]
        self.prev_selected_pos = None
        self._prev_valid = [(0, 0)] * 64
        self._prev_valid_count = 0
        self._dirty = bytearray(64)
        self._prev_go = None
        self._prev_winner = None
        self._prev_turn = None
        self._prev_w_cnt = -1
        self._prev_b_cnt = -1
        self._prev_must_jump = None
        self._prev_is_jump = None

    def has_any_jump(self, player):
        for r in range(8):
            row = self.grid[r]
            for c in range(8):
                p = row[c]
                if p and self.get_piece_color(p) == player:
                    jumps, _ = self._get_piece_moves_grid(self.grid, r, c)
                    if jumps:
                        return True
        return False

    def get_piece_color(self, p):
        if p in ('W', 'WK'): return 'W'
        if p in ('B', 'BK'): return 'B'
        return None

    def is_king(self, p):
        return p in ('WK', 'BK')

    def get_all_valid_moves(self, player):
        return self._get_grid_moves(self.grid, player)

    def _get_grid_moves(self, grid, player):
        all_jumps = {}
        all_steps = {}

        for r in range(8):
            for c in range(8):
                p = grid[r][c]
                if p and self.get_piece_color(p) == player:
                    jumps, steps = self._get_piece_moves_grid(grid, r, c)
                    if jumps:
                        all_jumps[(r, c)] = jumps
                    if steps:
                        all_steps[(r, c)] = steps

        if all_jumps:
            return all_jumps, True
        return all_steps, False

    def _get_piece_moves_grid(self, grid, r, c):
        p = grid[r][c]
        if not p: return [], []

        color = self.get_piece_color(p)
        king = self.is_king(p)
        opp_color = 'B' if color == 'W' else 'W'

        if king:
            dirs = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        elif color == 'W':
            dirs = [(-1, -1), (-1, 1)]
        else:
            dirs = [(1, -1), (1, 1)]

        jumps = []
        steps = []

        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < 8 and 0 <= nc < 8:
                target = grid[nr][nc]
                if target is None:
                    steps.append((nr, nc, None, None))
                elif self.get_piece_color(target) == opp_color:
                    j_r, j_c = nr + dr, nc + dc
                    if 0 <= j_r < 8 and 0 <= j_c < 8 and grid[j_r][j_c] is None:
                        jumps.append((j_r, j_c, nr, nc))

        return jumps, steps

    def select_cell(self, r, c):
        if self.game_over: return False
        if not (0 <= r < 8 and 0 <= c < 8): return False

        # Forced multi-jump state
        if self.must_jump_pos:
            if (r, c) == self.must_jump_pos:
                self.selected_pos = (r, c)
                jumps, _ = self._get_piece_moves_grid(self.grid, r, c)
                self.valid_moves = jumps
                return True
            elif self.selected_pos and any(m[0] == r and m[1] == c for m in self.valid_moves):
                return self.execute_move(self.selected_pos, (r, c))
            else:
                # Re-select the mandatory jumping piece if user taps elsewhere
                self.selected_pos = self.must_jump_pos
                jumps, _ = self._get_piece_moves_grid(self.grid, self.must_jump_pos[0], self.must_jump_pos[1])
                self.valid_moves = jumps
                return True

        p = self.grid[r][c]
        if p and self.get_piece_color(p) == self.turn:
            moves_dict, is_jump = self.get_all_valid_moves(self.turn)
            if (r, c) in moves_dict:
                self.selected_pos = (r, c)
                self.valid_moves = moves_dict[(r, c)]
                return True
            else:
                # Piece has no valid moves (e.g., blocked or another piece has forced jump)
                self.selected_pos = (r, c)
                self.valid_moves = []
                return True

        if self.selected_pos and any(m[0] == r and m[1] == c for m in self.valid_moves):
            return self.execute_move(self.selected_pos, (r, c))

        self.selected_pos = None
        self.valid_moves = []
        return True

    select_square = select_cell

    def execute_move(self, from_pos, to_pos):
        fr, fc = from_pos
        tr, tc = to_pos
        move_info = None

        for m in self.valid_moves:
            if m[0] == tr and m[1] == tc:
                move_info = m
                break

        if not move_info: return False

        p = self.grid[fr][fc]
        self.grid[fr][fc] = None
        cap_r, cap_c = move_info[2], move_info[3]

        if cap_r is not None:
            self.grid[cap_r][cap_c] = None

        promoted = False
        if p == 'W' and tr == 0:
            p = 'WK'
            promoted = True
        elif p == 'B' and tr == 7:
            p = 'BK'
            promoted = True

        self.grid[tr][tc] = p

        # Check for multi-jump (crowned pieces end turn upon reaching king row)
        if cap_r is not None and not promoted:
            jumps, _ = self._get_piece_moves_grid(self.grid, tr, tc)
            if jumps:
                self.must_jump_pos = (tr, tc)
                self.selected_pos = (tr, tc)
                self.valid_moves = jumps
                gc.collect()
                return True

        self.must_jump_pos = None
        self.selected_pos = None
        self.valid_moves = []
        self.switch_turn()
        gc.collect()
        return True

    def switch_turn(self):
        self.turn = 'B' if self.turn == 'W' else 'W'
        self.check_game_over()

    def check_game_over(self):
        moves_dict, _ = self.get_all_valid_moves(self.turn)
        if not moves_dict:
            self.game_over = True
            self.winner = 'B' if self.turn == 'W' else 'W'
            if not self.recorded:
                scoreboard.record_checkers(self.winner)
                self.recorded = True

    def count_pieces(self):
        w_cnt, b_cnt = 0, 0
        for r in range(8):
            for c in range(8):
                p = self.grid[r][c]
                if p in ('W', 'WK'): w_cnt += 1
                elif p in ('B', 'BK'): b_cnt += 1
        return w_cnt, b_cnt

    # --- Fast Pure Array Minimax AI ---
    def _eval_grid_checkers(self, grid):
        score = 0
        for r in range(8):
            for c in range(8):
                p = grid[r][c]
                if p == 'W':
                    score += (10 + (7 - r))
                elif p == 'WK':
                    score += 20
                elif p == 'B':
                    score -= (10 + r)
                elif p == 'BK':
                    score -= 20
        return score

    def _apply_move_to_grid(self, grid, fr, fc, tr, tc, cap_r, cap_c):
        new_grid = [row[:] for row in grid]
        p = new_grid[fr][fc]
        new_grid[fr][fc] = None
        if cap_r is not None:
            new_grid[cap_r][cap_c] = None

        promoted = False
        if p == 'W' and tr == 0:
            p = 'WK'
            promoted = True
        elif p == 'B' and tr == 7:
            p = 'BK'
            promoted = True

        new_grid[tr][tc] = p

        # Auto-apply chain jumps in simulation
        if cap_r is not None and not promoted:
            curr_r, curr_c = tr, tc
            while True:
                jumps, _ = self._get_piece_moves_grid(new_grid, curr_r, curr_c)
                if not jumps:
                    break
                next_jr, next_jc, next_cr, next_cc = jumps[0]
                new_grid[curr_r][curr_c] = None
                new_grid[next_cr][next_cc] = None
                if p == 'W' and next_jr == 0:
                    p = 'WK'
                    new_grid[next_jr][next_jc] = p
                    break
                elif p == 'B' and next_jr == 7:
                    p = 'BK'
                    new_grid[next_jr][next_jc] = p
                    break
                new_grid[next_jr][next_jc] = p
                curr_r, curr_c = next_jr, next_jc

        return new_grid

    def _minimax_fast(self, grid, depth, alpha, beta, is_max):
        if depth == 0:
            return self._eval_grid_checkers(grid), None

        current_player = 'W' if is_max else 'B'
        moves_dict, _ = self._get_grid_moves(grid, current_player)

        if not moves_dict:
            return (10000 + depth if not is_max else -10000 - depth), None

        all_flat_moves = []
        for fr_pos, m_list in moves_dict.items():
            for m in m_list:
                to_pos = (m[0], m[1])
                cap_r, cap_c = m[2], m[3]
                all_flat_moves.append((fr_pos, to_pos, cap_r, cap_c))

        best_move = all_flat_moves[0]

        if is_max:
            max_eval = -999999
            for fr_pos, to_pos, cap_r, cap_c in all_flat_moves:
                next_grid = self._apply_move_to_grid(grid, fr_pos[0], fr_pos[1], to_pos[0], to_pos[1], cap_r, cap_c)
                eval_val, _ = self._minimax_fast(next_grid, depth - 1, alpha, beta, False)
                if eval_val > max_eval:
                    max_eval = eval_val
                    best_move = (fr_pos, to_pos, cap_r, cap_c)
                alpha = max(alpha, eval_val)
                if beta <= alpha:
                    break
            return max_eval, best_move
        else:
            min_eval = 999999
            for fr_pos, to_pos, cap_r, cap_c in all_flat_moves:
                next_grid = self._apply_move_to_grid(grid, fr_pos[0], fr_pos[1], to_pos[0], to_pos[1], cap_r, cap_c)
                eval_val, _ = self._minimax_fast(next_grid, depth - 1, alpha, beta, True)
                if eval_val < min_eval:
                    min_eval = eval_val
                    best_move = (fr_pos, to_pos, cap_r, cap_c)
                beta = min(beta, eval_val)
                if beta <= alpha:
                    break
            return min_eval, best_move

    def ai_move(self):
        if self.game_over or self.turn != 'B' or self.mode != "VS_AI":
            return

        # Complete entire AI turn including any chain jumps
        while self.turn == 'B' and not self.game_over:
            if self.must_jump_pos:
                jumps, _ = self._get_piece_moves_grid(self.grid, self.must_jump_pos[0], self.must_jump_pos[1])
                if not jumps:
                    self.must_jump_pos = None
                    self.switch_turn()
                    break

                if self.difficulty == "EASY":
                    chosen_m = random.choice(jumps)
                else:
                    best_m = jumps[0]
                    best_score = 999999
                    for jm in jumps:
                        sim_g = self._apply_move_to_grid(self.grid, self.must_jump_pos[0], self.must_jump_pos[1], jm[0], jm[1], jm[2], jm[3])
                        val, _ = self._minimax_fast(sim_g, 1, -999999, 999999, True)
                        if val < best_score:
                            best_score = val
                            best_m = jm
                    chosen_m = best_m

                self.selected_pos = self.must_jump_pos
                self.valid_moves = jumps
                self.execute_move(self.must_jump_pos, (chosen_m[0], chosen_m[1]))
            else:
                moves_dict, _ = self.get_all_valid_moves('B')
                if not moves_dict:
                    self.check_game_over()
                    break

                all_flat_moves = []
                for pos, m_list in moves_dict.items():
                    for m in m_list:
                        all_flat_moves.append((pos, (m[0], m[1])))

                if not all_flat_moves:
                    break

                if self.difficulty == "EASY":
                    chosen_from, chosen_to = random.choice(all_flat_moves)
                else:
                    depth = 3 if self.difficulty == "HARD" else 2
                    _, best_full_move = self._minimax_fast(self.grid, depth, -999999, 999999, False)
                    if best_full_move:
                        chosen_from, chosen_to = best_full_move[0], best_full_move[1]
                    else:
                        chosen_from, chosen_to = random.choice(all_flat_moves)

                self.select_cell(chosen_from[0], chosen_from[1])
                self.select_cell(chosen_to[0], chosen_to[1])

        gc.collect()


# --- Zero-Blink GUI Renderer ---
def render_checkers_tile(tft, game_obj, r, c):
    x = c * TILE_SIZE
    y = BOARD_Y_OFFSET + r * TILE_SIZE
    is_dark = (r + c) % 2 == 1
    bg_col = COLOR_DARK_SQ if is_dark else COLOR_LIGHT_SQ

    if game_obj.selected_pos is not None and game_obj.selected_pos[0] == r and game_obj.selected_pos[1] == c:
        bg_col = COLOR_SEL_SQ

    fill_tile_buf(bg_col)

    # Grid border lines (1px top and left)
    draw_buf_rect(0, 0, 40, 1, COLOR_DARK_BG)
    draw_buf_rect(0, 0, 1, 40, COLOR_DARK_BG)

    is_valid_target = False
    for m in game_obj.valid_moves:
        if m[0] == r and m[1] == c:
            is_valid_target = True
            break

    if is_valid_target:
        draw_buf_circle(20, 20, 6, COLOR_DOT)
    else:
        p = game_obj.grid[r][c]
        if p:
            is_w = (p == 'W' or p == 'WK')
            is_k = (p == 'WK' or p == 'BK')
            p_col = COLOR_PIECE_W if is_w else COLOR_PIECE_B
            border_col = COLOR_CARD_BG if is_w else COLOR_WHITE

            if game_obj.must_jump_pos is not None and game_obj.must_jump_pos[0] == r and game_obj.must_jump_pos[1] == c:
                draw_buf_circle(20, 20, 19, COLOR_GOOGLE_YELLOW)

            draw_buf_circle(20, 20, 16, border_col)
            draw_buf_circle(20, 20, 14, p_col)
            draw_buf_circle(20, 20, 11, border_col)
            draw_buf_circle(20, 20, 10, p_col)

            if is_k:
                draw_buf_rect(14, 11, 12, 18, COLOR_CROWN)
                draw_buf_crown_glyph(20, 20, COLOR_DARK_BG)

    if hasattr(tft, 'blit_buffer'):
        tft.blit_buffer(x, y, TILE_SIZE, TILE_SIZE, TILE_BUF)
    else:
        tft.set_window(x, y, x + TILE_SIZE - 1, y + TILE_SIZE - 1)
        tft.dc.value(1)
        tft.cs.value(0)
        tft.spi.write(TILE_BUF)
        tft.cs.value(1)


def init_checkers_ui(tft, game_obj):
    tft.fill_rect(0, 0, 320, 480, COLOR_DARK_BG)
    draw_header_bar(tft, "CHECKERS")

    mode_str = "VS AI" if game_obj.mode == "VS_AI" else "2 PLAYER"
    draw_button(tft, 8, 56, 145, 30, mode_str, COLOR_CARD_BG, COLOR_WHITE, scale=1)
    
    diff_str = "DIFF: " + game_obj.difficulty
    draw_button(tft, 167, 56, 145, 30, diff_str, COLOR_CARD_BG, COLOR_GOOGLE_YELLOW, scale=1)

    for r in range(8):
        for c in range(8):
            render_checkers_tile(tft, game_obj, r, c)
            game_obj.prev_grid[r][c] = game_obj.grid[r][c]

    game_obj.prev_selected_pos = game_obj.selected_pos
    n_valid = len(game_obj.valid_moves)
    game_obj._prev_valid_count = n_valid
    for i in range(n_valid):
        m = game_obj.valid_moves[i]
        game_obj._prev_valid[i] = (m[0], m[1])

    game_obj._prev_go = None
    game_obj._prev_winner = None
    game_obj._prev_turn = None
    game_obj._prev_w_cnt = -1
    game_obj._prev_b_cnt = -1
    game_obj._prev_must_jump = None
    game_obj._prev_is_jump = None

    update_checkers_status(tft, game_obj)


def update_checkers_status(tft, game_obj):
    w_cnt, b_cnt = game_obj.count_pieces()
    is_jump = (game_obj.must_jump_pos is not None) or game_obj.has_any_jump(game_obj.turn)

    if (game_obj.game_over == game_obj._prev_go and
        game_obj.winner == game_obj._prev_winner and
        game_obj.turn == game_obj._prev_turn and
        w_cnt == game_obj._prev_w_cnt and
        b_cnt == game_obj._prev_b_cnt and
        is_jump == game_obj._prev_is_jump and
        game_obj.must_jump_pos == game_obj._prev_must_jump):
        return

    game_obj._prev_go = game_obj.game_over
    game_obj._prev_winner = game_obj.winner
    game_obj._prev_turn = game_obj.turn
    game_obj._prev_w_cnt = w_cnt
    game_obj._prev_b_cnt = b_cnt
    game_obj._prev_is_jump = is_jump
    game_obj._prev_must_jump = game_obj.must_jump_pos

    tft.fill_rect(0, 415, 320, 65, COLOR_HEADER_BG)

    if game_obj.game_over:
        if game_obj.winner == 'W':
            msg, col = "YOU WIN! (WHITE)", COLOR_GOOGLE_GREEN
        elif game_obj.winner == 'B':
            msg = "AI WINS! (BLACK)" if game_obj.mode == "VS_AI" else "BLACK WINS!"
            col = COLOR_GOOGLE_RED
        else:
            msg, col = "GAME DRAW!", COLOR_GOOGLE_YELLOW
    else:
        turn_name = "WHITE" if game_obj.turn == 'W' else ("AI" if game_obj.mode == "VS_AI" else "BLACK")
        col = COLOR_WHITE if game_obj.turn == 'W' else COLOR_GOOGLE_YELLOW

        if game_obj.must_jump_pos:
            msg = turn_name + ": MULTI-JUMP!"
            col = COLOR_GOOGLE_GREEN
        elif is_jump:
            msg = turn_name + ": MUST JUMP!"
            col = COLOR_GOOGLE_YELLOW
        else:
            msg = turn_name + "'S TURN"

    tft.draw_text(msg, 20, 425, col, bg=COLOR_HEADER_BG, scale=2)
    stats_str = "WHITE: " + str(w_cnt) + "   BLACK: " + str(b_cnt)
    tft.draw_text(stats_str, 20, 452, COLOR_TEXT_MUTED, bg=COLOR_HEADER_BG, scale=1)


def update_checkers_ui(tft, game_obj):
    dirty = game_obj._dirty
    for i in range(64):
        dirty[i] = 0

    for r in range(8):
        prev_row = game_obj.prev_grid[r]
        curr_row = game_obj.grid[r]
        row_off = r * 8
        for c in range(8):
            if curr_row[c] != prev_row[c]:
                dirty[row_off + c] = 1

    if game_obj.prev_selected_pos is not None:
        dirty[game_obj.prev_selected_pos[0] * 8 + game_obj.prev_selected_pos[1]] = 1
    for i in range(game_obj._prev_valid_count):
        m = game_obj._prev_valid[i]
        dirty[m[0] * 8 + m[1]] = 1

    if game_obj.selected_pos is not None:
        dirty[game_obj.selected_pos[0] * 8 + game_obj.selected_pos[1]] = 1
    for m in game_obj.valid_moves:
        dirty[m[0] * 8 + m[1]] = 1

    for r in range(8):
        row_off = r * 8
        for c in range(8):
            if dirty[row_off + c]:
                render_checkers_tile(tft, game_obj, r, c)
                game_obj.prev_grid[r][c] = game_obj.grid[r][c]

    game_obj.prev_selected_pos = game_obj.selected_pos

    n_valid = len(game_obj.valid_moves)
    game_obj._prev_valid_count = n_valid
    for i in range(n_valid):
        m = game_obj.valid_moves[i]
        game_obj._prev_valid[i] = (m[0], m[1])

    update_checkers_status(tft, game_obj)

