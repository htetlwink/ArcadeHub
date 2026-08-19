# game_alq.py - Alquerque (Orthogonal Variant) Engine & Zero-Blink Renderer
import random
import time
import gc
from arcade_common import (
    COLOR_DARK_BG, COLOR_HEADER_BG, COLOR_CARD_BG, COLOR_WHITE,
    COLOR_TEXT_MUTED, COLOR_GOOGLE_BLUE, COLOR_GOOGLE_RED,
    COLOR_GOOGLE_YELLOW, rgb565, draw_button, draw_header_bar, scoreboard
)

class AlquerqueGame:
    def __init__(self):
        self.grid = [[0] * 5 for _ in range(5)]
        self.prev_grid = [[-1] * 5 for _ in range(5)]
        self.mode = "VS_AI" # "VS_AI", "2P"
        self.difficulty = "MEDIUM" # "EASY", "MEDIUM", "HARD"
        self.turn = 1 # 1: Player 1 (RED), 2: Player 2 (BLUE / AI)
        self.selected = None # (r, c)
        self.prev_selected = (-1, -1)
        self.valid_targets = []
        self.prev_targets = []
        self.must_continue_jump = False
        self.winner = None
        self.game_over = False
        self.recorded = False
        self.status_msg = "RED'S TURN"
        self.prev_status_msg = ""
        self._prev_p1 = -1
        self._prev_p2 = -1
        self.p1_count = 12
        self.p2_count = 12
        self.reset()

    def reset(self):
        # 1 = RED (P1), 2 = BLUE (P2), 0 = EMPTY
        init_layout = [
            (1, 1, 1, 1, 1),
            (1, 1, 1, 1, 1),
            (1, 1, 0, 2, 2),
            (2, 2, 2, 2, 2),
            (2, 2, 2, 2, 2)
        ]
        for r in range(5):
            for c in range(5):
                self.grid[r][c] = init_layout[r][c]
                self.prev_grid[r][c] = -1
        self.turn = 1
        self.selected = None
        self.prev_selected = (-1, -1)
        self.valid_targets = []
        self.prev_targets = []
        self.must_continue_jump = False
        self.winner = None
        self.game_over = False
        self.recorded = False
        self.p1_count = 12
        self.p2_count = 12
        self.status_msg = "RED'S TURN"
        self.prev_status_msg = ""
        self._prev_p1 = -1
        self._prev_p2 = -1
        gc.collect()

    def to_dict(self):
        return {
            "grid": self.grid,
            "mode": self.mode,
            "difficulty": self.difficulty,
            "turn": self.turn,
            "selected": list(self.selected) if self.selected else None,
            "must_continue_jump": self.must_continue_jump,
            "winner": self.winner,
            "game_over": self.game_over,
            "recorded": self.recorded,
            "status_msg": self.status_msg,
            "p1_count": self.p1_count,
            "p2_count": self.p2_count
        }

    def from_dict(self, data):
        if not data: return
        self.grid = data.get("grid", self.grid)
        self.mode = data.get("mode", self.mode)
        self.difficulty = data.get("difficulty", self.difficulty)
        self.turn = data.get("turn", self.turn)
        sel = data.get("selected")
        self.selected = tuple(sel) if sel else None
        self.must_continue_jump = data.get("must_continue_jump", self.must_continue_jump)
        self.winner = data.get("winner", self.winner)
        self.game_over = data.get("game_over", self.game_over)
        self.recorded = data.get("recorded", self.recorded)
        self.status_msg = data.get("status_msg", self.status_msg)
        self.count_pieces()
        if self.selected:
            moves = self.get_legal_moves_for_piece(self.selected[0], self.selected[1])
            self.valid_targets = [m[0] for m in moves]
        else:
            self.valid_targets = []
        self.prev_grid = [[-1] * 5 for _ in range(5)]
        self.prev_selected = (-1, -1)
        self.prev_targets = []
        self.prev_status_msg = ""

    def count_pieces(self):
        p1, p2 = 0, 0
        for r in range(5):
            for c in range(5):
                if self.grid[r][c] == 1: p1 += 1
                elif self.grid[r][c] == 2: p2 += 1
        self.p1_count = p1
        self.p2_count = p2
        return p1, p2

    def get_legal_moves_for_piece(self, r, c):
        moves = []
        player = self.grid[r][c]
        if player == 0:
            return moves
        
        opponent = 3 - player
        dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        jumps = []
        steps = []

        for dr, dc in dirs:
            r_mid, c_mid = r + dr, c + dc
            r_dest, c_dest = r + 2 * dr, c + 2 * dc

            if 0 <= r_dest < 5 and 0 <= c_dest < 5:
                if self.grid[r_mid][c_mid] == opponent and self.grid[r_dest][c_dest] == 0:
                    jumps.append(((r_dest, c_dest), True, (r_mid, c_mid)))

            if not self.must_continue_jump:
                r_step, c_step = r + dr, c + dc
                if 0 <= r_step < 5 and 0 <= c_step < 5:
                    if self.grid[r_step][c_step] == 0:
                        steps.append(((r_step, c_step), False, None))

        if self.must_continue_jump:
            return jumps
        return jumps + steps

    def get_all_legal_moves(self, player):
        all_moves = []
        for r in range(5):
            for c in range(5):
                if self.grid[r][c] == player:
                    p_moves = self.get_legal_moves_for_piece(r, c)
                    for target_pos, is_jump, captured_pos in p_moves:
                        all_moves.append(((r, c), target_pos, is_jump, captured_pos))
        return all_moves

    def select_cell(self, r, c):
        if self.game_over:
            return False

        current_p = self.turn
        if self.selected is not None:
            sr, sc = self.selected
            moves = self.get_legal_moves_for_piece(sr, sc)
            for target_pos, is_jump, captured_pos in moves:
                if target_pos == (r, c):
                    return self.execute_move(self.selected, target_pos, is_jump, captured_pos)

        if self.must_continue_jump:
            return False

        if self.grid[r][c] == current_p:
            self.selected = (r, c)
            moves = self.get_legal_moves_for_piece(r, c)
            self.valid_targets = [m[0] for m in moves]
            return True
        else:
            self.selected = None
            self.valid_targets = []
            return True

    def execute_move(self, from_pos, to_pos, is_jump, captured_pos):
        fr, fc = from_pos
        tr, tc = to_pos
        player = self.grid[fr][fc]
        self.grid[fr][fc] = 0
        self.grid[tr][tc] = player

        if is_jump and captured_pos:
            cr, cc = captured_pos
            self.grid[cr][cc] = 0

        self.count_pieces()

        further_jumps = []
        if is_jump:
            self.must_continue_jump = True
            further_jumps = self.get_legal_moves_for_piece(tr, tc)
            self.must_continue_jump = False

        if is_jump and further_jumps:
            self.selected = (tr, tc)
            self.must_continue_jump = True
            self.valid_targets = [m[0] for m in further_jumps]
            p_name = "RED" if player == 1 else "BLUE"
            self.status_msg = f"{p_name} JUMP AGAIN!"
        else:
            self.selected = None
            self.must_continue_jump = False
            self.valid_targets = []
            self.turn = 3 - player
            p_name = "RED" if self.turn == 1 else "BLUE"
            self.status_msg = f"{p_name}'S TURN"

        self.check_game_over()
        gc.collect()
        return True

    def check_game_over(self):
        p1, p2 = self.count_pieces()
        if p1 == 0:
            self.game_over = True
            self.winner = 2
            self.status_msg = "BLUE WINS!"
        elif p2 == 0:
            self.game_over = True
            self.winner = 1
            self.status_msg = "RED WINS!"
        else:
            current_moves = self.get_all_legal_moves(self.turn)
            if not current_moves:
                self.game_over = True
                self.winner = 3 - self.turn
                w_name = "BLUE" if self.winner == 2 else "RED"
                self.status_msg = f"NO MOVES! {w_name} WINS!"

        if self.game_over and not self.recorded:
            self.recorded = True
            scoreboard.record_alq(self.winner)
        return self.game_over

    def _get_piece_jumps(self, grid, r, c):
        player = grid[r][c]
        if player == 0:
            return []
        opponent = 3 - player
        dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        jumps = []
        for dr, dc in dirs:
            r_mid, c_mid = r + dr, c + dc
            r_dest, c_dest = r + 2 * dr, c + 2 * dc
            if 0 <= r_dest < 5 and 0 <= c_dest < 5:
                if grid[r_mid][c_mid] == opponent and grid[r_dest][c_dest] == 0:
                    jumps.append(((r_dest, c_dest), True, (r_mid, c_mid)))
        return jumps

    def _get_grid_legal_moves(self, grid, player):
        jumps = []
        steps = []
        opponent = 3 - player
        dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]

        for r in range(5):
            for c in range(5):
                if grid[r][c] == player:
                    for dr, dc in dirs:
                        r_mid, c_mid = r + dr, c + dc
                        r_dest, c_dest = r + 2 * dr, c + 2 * dc
                        if 0 <= r_dest < 5 and 0 <= c_dest < 5:
                            if grid[r_mid][c_mid] == opponent and grid[r_dest][c_dest] == 0:
                                jumps.append(((r, c), (r_dest, c_dest), True, (r_mid, c_mid)))

                        r_step, c_step = r + dr, c + dc
                        if 0 <= r_step < 5 and 0 <= c_step < 5:
                            if grid[r_step][c_step] == 0:
                                steps.append(((r, c), (r_step, c_step), False, None))

        return jumps if jumps else steps

    def _apply_move(self, grid, move):
        new_grid = [row[:] for row in grid]
        from_pos, to_pos, is_jump, captured_pos = move
        fr, fc = from_pos
        tr, tc = to_pos
        player = new_grid[fr][fc]
        new_grid[fr][fc] = 0
        new_grid[tr][tc] = player

        if is_jump and captured_pos:
            cr, cc = captured_pos
            new_grid[cr][cc] = 0
            curr_r, curr_c = tr, tc
            while True:
                chain_jumps = self._get_piece_jumps(new_grid, curr_r, curr_c)
                if not chain_jumps:
                    break
                next_to, _, next_cap = chain_jumps[0]
                n_tr, n_tc = next_to
                n_cr, n_cc = next_cap
                new_grid[curr_r][curr_c] = 0
                new_grid[n_cr][n_cc] = 0
                new_grid[n_tr][n_tc] = player
                curr_r, curr_c = n_tr, n_tc

        return new_grid

    def _evaluate_board(self, grid):
        p1_count = sum(row.count(1) for row in grid)
        p2_count = sum(row.count(2) for row in grid)
        score = (p2_count - p1_count) * 100

        for r in range(5):
            for c in range(5):
                piece = grid[r][c]
                if piece == 1:
                    score -= (r * 3 + (2 - abs(2 - c)))
                elif piece == 2:
                    score += ((4 - r) * 3 + (2 - abs(2 - c)))

        p2_moves = self._get_grid_legal_moves(grid, 2)
        p1_moves = self._get_grid_legal_moves(grid, 1)

        p2_jumps = sum(1 for m in p2_moves if m[2])
        p1_jumps = sum(1 for m in p1_moves if m[2])

        score += p2_jumps * 30
        score -= p1_jumps * 35

        return score

    def _minimax(self, grid, depth, alpha, beta, is_maximizing):
        p1_count = sum(row.count(1) for row in grid)
        p2_count = sum(row.count(2) for row in grid)

        if p1_count == 0:
            return 10000 + depth, None
        if p2_count == 0:
            return -10000 - depth, None

        current_player = 2 if is_maximizing else 1
        moves = self._get_grid_legal_moves(grid, current_player)

        if not moves:
            return (10000 + depth if not is_maximizing else -10000 - depth), None

        if depth == 0:
            return self._evaluate_board(grid), None

        best_move = None

        if is_maximizing:
            max_eval = -999999
            for move in moves:
                next_grid = self._apply_move(grid, move)
                eval_val, _ = self._minimax(next_grid, depth - 1, alpha, beta, False)
                if eval_val > max_eval:
                    max_eval = eval_val
                    best_move = move
                alpha = max(alpha, eval_val)
                if beta <= alpha:
                    break
            return max_eval, best_move
        else:
            min_eval = 999999
            for move in moves:
                next_grid = self._apply_move(grid, move)
                eval_val, _ = self._minimax(next_grid, depth - 1, alpha, beta, True)
                if eval_val < min_eval:
                    min_eval = eval_val
                    best_move = move
                beta = min(beta, eval_val)
                if beta <= alpha:
                    break
            return min_eval, best_move

    def ai_move(self):
        if self.game_over or self.turn != 2:
            return False

        all_moves = self.get_all_legal_moves(2)
        if not all_moves:
            self.check_game_over()
            return False

        jumps = [m for m in all_moves if m[2]]
        valid_moves = jumps if jumps else all_moves

        selected_move = None

        if self.difficulty == "EASY":
            if random.random() < 0.5:
                selected_move = random.choice(valid_moves)
            else:
                _, selected_move = self._minimax(self.grid, 1, -999999, 999999, True)
        elif self.difficulty == "MEDIUM":
            _, selected_move = self._minimax(self.grid, 2, -999999, 999999, True)
        else:  # HARD
            _, selected_move = self._minimax(self.grid, 3, -999999, 999999, True)

        if not selected_move or selected_move not in valid_moves:
            selected_move = random.choice(valid_moves)

        if selected_move:
            from_pos, to_pos, is_jump, captured = selected_move
            self.execute_move(from_pos, to_pos, is_jump, captured)
            while self.must_continue_jump and not self.game_over:
                sr, sc = self.selected
                chain_jumps = self.get_legal_moves_for_piece(sr, sc)
                if chain_jumps:
                    best_cj = None
                    best_score = -999999
                    for cj_to, cj_is_jump, cj_cap in chain_jumps:
                        temp_grid = self._apply_move(self.grid, (self.selected, cj_to, cj_is_jump, cj_cap))
                        score = self._evaluate_board(temp_grid)
                        if score > best_score:
                            best_score = score
                            best_cj = (cj_to, cj_is_jump, cj_cap)
                    cj_to, cj_is_jump, cj_cap = best_cj if best_cj else chain_jumps[0]
                    self.execute_move(self.selected, cj_to, cj_is_jump, cj_cap)
                else:
                    break
            import gc
            gc.collect()
            return True
        return False


# Static 48x48 RGB565 node tile buffer (4,608 bytes) for zero-blink rendering
TILE_BUF = bytearray(48 * 48 * 2)

def fill_tile_buf(color):
    hi = (color >> 8) & 0xFF
    lo = color & 0xFF
    TILE_BUF[0] = hi
    TILE_BUF[1] = lo
    size = 2
    while size < 4608:
        chunk = min(size, 4608 - size)
        TILE_BUF[size : size + chunk] = TILE_BUF[:chunk]
        size += chunk

def draw_buf_rect(x, y, w, h, color):
    x1 = max(0, min(48, x))
    y1 = max(0, min(48, y))
    x2 = max(0, min(48, x + w))
    y2 = max(0, min(48, y + h))
    if x2 <= x1 or y2 <= y1:
        return
    hi = (color >> 8) & 0xFF
    lo = color & 0xFF
    width_bytes = (x2 - x1) * 2
    row0_off = y1 * 96 + x1 * 2
    for px in range(x1, x2):
        idx = y1 * 96 + px * 2
        TILE_BUF[idx] = hi
        TILE_BUF[idx + 1] = lo
    for py in range(y1 + 1, y2):
        row_off = py * 96 + x1 * 2
        TILE_BUF[row_off : row_off + width_bytes] = TILE_BUF[row0_off : row0_off + width_bytes]

def draw_buf_circle(cx, cy, r, color):
    r_sq = r * r
    hi = (color >> 8) & 0xFF
    lo = color & 0xFF
    for dy in range(-r, r + 1):
        py = cy + dy
        if 0 <= py < 48:
            dx = int((r_sq - dy * dy) ** 0.5)
            x1 = max(0, cx - dx)
            x2 = min(48, cx + dx + 1)
            row_off = py * 96
            for px in range(x1, x2):
                idx = row_off + px * 2
                TILE_BUF[idx] = hi
                TILE_BUF[idx + 1] = lo

def render_node_tile(tft, r, c, val, is_sel, is_target):
    cx = 30 + c * 65
    cy = 110 + r * 68

    fill_tile_buf(COLOR_CARD_BG)

    if c > 0: draw_buf_rect(0, 23, 24, 3, COLOR_TEXT_MUTED)
    if c < 4: draw_buf_rect(24, 23, 24, 3, COLOR_TEXT_MUTED)
    if r > 0: draw_buf_rect(23, 0, 3, 24, COLOR_TEXT_MUTED)
    if r < 4: draw_buf_rect(23, 24, 3, 24, COLOR_TEXT_MUTED)

    if val == 0:
        if is_target:
            draw_buf_circle(24, 24, 10, COLOR_GOOGLE_YELLOW)
            draw_buf_circle(24, 24, 6, COLOR_CARD_BG)
        else:
            draw_buf_circle(24, 24, 4, COLOR_TEXT_MUTED)
    elif val == 1: # RED P1
        border_c = COLOR_WHITE if is_sel else rgb565(180, 40, 30)
        draw_buf_circle(24, 24, 20, border_c)
        draw_buf_circle(24, 24, 16, COLOR_GOOGLE_RED)
        draw_buf_circle(20, 20, 5, rgb565(255, 140, 130))
    elif val == 2: # BLUE P2
        border_c = COLOR_WHITE if is_sel else rgb565(20, 80, 180)
        draw_buf_circle(24, 24, 20, border_c)
        draw_buf_circle(24, 24, 16, COLOR_GOOGLE_BLUE)
        draw_buf_circle(20, 20, 5, rgb565(120, 190, 255))

    if hasattr(tft, 'blit_buffer'):
        tft.blit_buffer(cx - 24, cy - 24, 48, 48, TILE_BUF)
    else:
        tft.set_window(cx - 24, cy - 24, cx + 23, cy + 23)
        tft.dc.value(1)
        tft.cs.value(0)
        tft.spi.write(TILE_BUF)
        tft.cs.value(1)


def init_alq_ui(tft, game):
    tft.fill_rect(0, 0, 320, 480, COLOR_DARK_BG)
    draw_header_bar(tft, "ALQUERQUE")

    draw_button(tft, 8, 56, 145, 32, "VS AI" if game.mode == "VS_AI" else "2P MODE", COLOR_CARD_BG, COLOR_WHITE, scale=1)
    draw_button(tft, 167, 56, 145, 32, "DIFF: " + game.difficulty, COLOR_CARD_BG, COLOR_WHITE, scale=1)

    tft.fill_rect(14, 94, 292, 292, COLOR_CARD_BG)
    tft.fill_rect(14, 94, 292, 2, COLOR_WHITE)
    tft.fill_rect(14, 94, 2, 292, COLOR_WHITE)
    tft.fill_rect(304, 94, 2, 292, rgb565(100, 116, 139))
    tft.fill_rect(14, 384, 292, 2, rgb565(100, 116, 139))

    for r in range(5):
        cy = 110 + r * 68
        tft.fill_rect(30, cy - 1, 260, 3, COLOR_TEXT_MUTED)

    for c in range(5):
        cx = 30 + c * 65
        tft.fill_rect(cx - 1, 110, 3, 272, COLOR_TEXT_MUTED)

    tft.fill_rect(10, 396, 300, 75, COLOR_CARD_BG)
    
    for r in range(5):
        for c in range(5):
            game.prev_grid[r][c] = -1
    game.prev_selected = (-1, -1)
    game.prev_targets = []
    game.prev_status_msg = ""
    game._prev_p1 = -1
    game._prev_p2 = -1
    update_alq_ui(tft, game)


def update_alq_ui(tft, game):
    sel = game.selected if game.selected else (-1, -1)
    prev_sel = game.prev_selected if game.prev_selected else (-1, -1)

    for r in range(5):
        for c in range(5):
            val = game.grid[r][c]
            prev_val = game.prev_grid[r][c]
            pos = (r, c)

            is_sel = (pos == sel)
            was_sel = (pos == prev_sel)
            is_target = (pos in game.valid_targets)
            was_target = (pos in game.prev_targets)

            if val != prev_val or is_sel != was_sel or is_target != was_target:
                render_node_tile(tft, r, c, val, is_sel, is_target)

    for r in range(5):
        for c in range(5):
            game.prev_grid[r][c] = game.grid[r][c]
    game.prev_selected = sel
    game.prev_targets = list(game.valid_targets)

    if (game.status_msg != game.prev_status_msg or
        game.p1_count != game._prev_p1 or
        game.p2_count != game._prev_p2):

        game.prev_status_msg = game.status_msg
        game._prev_p1 = game.p1_count
        game._prev_p2 = game.p2_count
        tft.fill_rect(15, 402, 290, 63, COLOR_CARD_BG)
        
        p1, p2 = game.p1_count, game.p2_count
        tft.draw_text("RED P1: " + str(p1), 20, 408, COLOR_GOOGLE_RED, bg=COLOR_CARD_BG, scale=1)
        tft.draw_text("BLUE P2: " + str(p2), 180, 408, COLOR_GOOGLE_BLUE, bg=COLOR_CARD_BG, scale=1)
        
        scale = 2 if len(game.status_msg) <= 12 else 1
        tft.draw_text(game.status_msg, 20, 432, COLOR_GOOGLE_YELLOW, bg=COLOR_CARD_BG, scale=scale)
