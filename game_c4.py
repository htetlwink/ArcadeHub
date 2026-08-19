# game_c4.py - Connect 4 Engine & Renderer for WT32-SC01
import random
import time
import gc
from arcade_common import (
    COLOR_DARK_BG, COLOR_HEADER_BG, COLOR_CARD_BG, COLOR_WHITE,
    COLOR_TEXT_MUTED, COLOR_GOOGLE_BLUE, COLOR_GOOGLE_RED,
    COLOR_GOOGLE_YELLOW, COLOR_GOOGLE_GREEN, draw_filled_circle,
    draw_button, draw_header_bar, scoreboard
)

# Pre-computed flattened win lines (r1, c1, r2, c2, r3, c3, r4, c4) for zero-allocation scoring
C4_WIN_INDICES = []
# Horizontal 4-in-a-row (6 * 4 = 24 lines)
for _r in range(6):
    for _c in range(4):
        C4_WIN_INDICES.append((_r, _c, _r, _c+1, _r, _c+2, _r, _c+3))
# Vertical 4-in-a-row (7 * 3 = 21 lines)
for _c in range(7):
    for _r in range(3):
        C4_WIN_INDICES.append((_r, _c, _r+1, _c, _r+2, _c, _r+3, _c))
# Positive Diagonal 4-in-a-row (3 * 4 = 12 lines)
for _r in range(3):
    for _c in range(4):
        C4_WIN_INDICES.append((_r, _c, _r+1, _c+1, _r+2, _c+2, _r+3, _c+3))
# Negative Diagonal 4-in-a-row (3 * 4 = 12 lines)
for _r in range(3):
    for _c in range(4):
        C4_WIN_INDICES.append((_r+3, _c, _r+2, _c+1, _r+1, _c+2, _r, _c+3))

C4_PREFERRED_COLS = (3, 2, 4, 1, 5, 0, 6)

class Connect4:
    def __init__(self):
        self.grid = [[None] * 7 for _ in range(6)]
        self.prev_grid = [[None] * 7 for _ in range(6)]
        self.mode = "VS_AI"
        self.difficulty = "MEDIUM" # "EASY", "MEDIUM", "HARD"
        self.turn = 'RED'
        self.winner = None
        self.game_over = False
        self.recorded = False
        self._prev_go = None
        self._prev_winner = None
        self._prev_turn = None
        self._prev_mode = None
        self.reset()

    def reset(self):
        for r in range(6):
            for c in range(7):
                self.grid[r][c] = None
                self.prev_grid[r][c] = None
        self.turn = 'RED'
        self.winner = None
        self.game_over = False
        self.recorded = False
        self._prev_go = None
        self._prev_winner = None
        self._prev_turn = None
        self._prev_mode = None
        gc.collect()

    def to_dict(self):
        return {
            "grid": [row[:] for row in self.grid],
            "mode": self.mode,
            "difficulty": self.difficulty,
            "turn": self.turn,
            "winner": self.winner,
            "game_over": self.game_over,
            "recorded": self.recorded
        }

    def from_dict(self, data):
        if not data:
            return
        grid_data = data.get("grid")
        if grid_data and len(grid_data) == 6:
            self.grid = [list(row) for row in grid_data]
        self.mode = data.get("mode", self.mode)
        self.difficulty = data.get("difficulty", self.difficulty)
        self.turn = data.get("turn", self.turn)
        self.winner = data.get("winner", self.winner)
        self.game_over = data.get("game_over", self.game_over)
        self.recorded = data.get("recorded", self.recorded)
        for r in range(6):
            for c in range(7):
                self.prev_grid[r][c] = None
        self._prev_go = None
        self._prev_winner = None
        self._prev_turn = None
        self._prev_mode = None

    def drop_disc(self, col):
        if self.game_over or col < 0 or col >= 7:
            return False, -1, None
        for r in range(5, -1, -1):
            if self.grid[r][col] is None:
                current_color = self.turn
                self.grid[r][col] = current_color
                self.check_winner()
                if not self.game_over:
                    self.turn = 'YELLOW' if self.turn == 'RED' else 'RED'
                gc.collect()
                return True, r, current_color
        return False, -1, None

    def _sim_drop(self, col, color):
        for r in range(5, -1, -1):
            if self.grid[r][col] is None:
                self.grid[r][col] = color
                return r
        return -1

    def _sim_undo(self, r, col):
        self.grid[r][col] = None

    def _check_win_color(self, c):
        g = self.grid
        for r in range(6):
            for col in range(4):
                if g[r][col] == g[r][col+1] == g[r][col+2] == g[r][col+3] == c: return True
        for r in range(3):
            for col in range(7):
                if g[r][col] == g[r+1][col] == g[r+2][col] == g[r+3][col] == c: return True
        for r in range(3):
            for col in range(4):
                if g[r][col] == g[r+1][col+1] == g[r+2][col+2] == g[r+3][col+3] == c: return True
                if g[r+3][col] == g[r+2][col+1] == g[r+1][col+2] == g[r][col+3] == c: return True
        return False

    def _score_c4_position(self, piece):
        score = 0
        g = self.grid
        opp_piece = "RED" if piece == "YELLOW" else "YELLOW"

        # Center column priority bonus
        for r in range(6):
            if g[r][3] == piece:
                score += 6
            elif g[r][3] == opp_piece:
                score -= 6

        # Zero-allocation line scoring using flattened index tuples
        for r1, c1, r2, c2, r3, c3, r4, c4 in C4_WIN_INDICES:
            p1, p2, p3, p4 = g[r1][c1], g[r2][c2], g[r3][c3], g[r4][c4]
            p_count = (p1 == piece) + (p2 == piece) + (p3 == piece) + (p4 == piece)
            opp_count = (p1 == opp_piece) + (p2 == opp_piece) + (p3 == opp_piece) + (p4 == opp_piece)

            if opp_count == 0:
                if p_count == 4:
                    score += 100000
                elif p_count == 3:
                    score += 100
                elif p_count == 2:
                    score += 10
            elif p_count == 0:
                if opp_count == 3:
                    score -= 140
        return score

    def _c4_minimax(self, depth, alpha, beta, is_max):
        if self._check_win_color("YELLOW"):
            return None, 1000000 + depth
        if self._check_win_color("RED"):
            return None, -1000000 - depth

        has_moves = False
        for c in C4_PREFERRED_COLS:
            if self.grid[0][c] is None:
                has_moves = True
                break

        if not has_moves:
            return None, 0

        if depth == 0:
            return None, self._score_c4_position("YELLOW")

        if is_max:
            value = -1000000000
            best_col = 3
            for col in C4_PREFERRED_COLS:
                if self.grid[0][col] is not None:
                    continue
                r = self._sim_drop(col, "YELLOW")
                _, new_score = self._c4_minimax(depth - 1, alpha, beta, False)
                self._sim_undo(r, col)
                if new_score > value:
                    value = new_score
                    best_col = col
                if value > alpha:
                    alpha = value
                if alpha >= beta:
                    break
            return best_col, value
        else:
            value = 1000000000
            best_col = 3
            for col in C4_PREFERRED_COLS:
                if self.grid[0][col] is not None:
                    continue
                r = self._sim_drop(col, "RED")
                _, new_score = self._c4_minimax(depth - 1, alpha, beta, True)
                self._sim_undo(r, col)
                if new_score < value:
                    value = new_score
                    best_col = col
                if value < beta:
                    beta = value
                if alpha >= beta:
                    break
            return best_col, value

    def ai_move(self):
        if self.game_over or self.turn != 'YELLOW' or self.mode != "VS_AI":
            return -1, False, -1, None

        valid_cols = []
        for c in C4_PREFERRED_COLS:
            if self.grid[0][c] is None:
                valid_cols.append(c)

        if not valid_cols:
            return -1, False, -1, None

        # 1. Immediate Win Check (0 ms) - YELLOW takes win if available
        for c in valid_cols:
            r = self._sim_drop(c, "YELLOW")
            if self._check_win_color("YELLOW"):
                self._sim_undo(r, c)
                success, target_r, disc_col = self.drop_disc(c)
                return c, success, target_r, disc_col
            self._sim_undo(r, c)

        # 2. Immediate Block Check (0 ms) - Block RED's winning move if available
        for c in valid_cols:
            r = self._sim_drop(c, "RED")
            if self._check_win_color("RED"):
                self._sim_undo(r, c)
                success, target_r, disc_col = self.drop_disc(c)
                return c, success, target_r, disc_col
            self._sim_undo(r, c)

        # 3. Minimax / Heuristic Selection based on Difficulty
        if self.difficulty == "EASY":
            if random.random() < 0.3:
                selected_col = valid_cols[0]
            else:
                selected_col = random.choice(valid_cols)

        elif self.difficulty == "MEDIUM":
            col, score = self._c4_minimax(depth=2, alpha=-1000000000, beta=1000000000, is_max=True)
            if col is not None and random.random() < 0.85:
                selected_col = col
            else:
                selected_col = random.choice(valid_cols)

        else: # HARD
            col, score = self._c4_minimax(depth=3, alpha=-1000000000, beta=1000000000, is_max=True)
            selected_col = col if col is not None else valid_cols[0]

        success, target_r, disc_col = self.drop_disc(selected_col)
        return selected_col, success, target_r, disc_col

    def check_winner(self):
        if self._check_win_color('RED'):
            self.winner = 'RED'
            self.game_over = True
            if not self.recorded:
                self.recorded = True
                scoreboard.record_c4('RED')
        elif self._check_win_color('YELLOW'):
            self.winner = 'YELLOW'
            self.game_over = True
            if not self.recorded:
                self.recorded = True
                scoreboard.record_c4('YELLOW')
        elif all(self.grid[0][c] is not None for c in range(7)):
            self.winner = 'DRAW'
            self.game_over = True
            if not self.recorded:
                self.recorded = True
                scoreboard.record_c4('DRAW')

def animate_c4_drop(tft, col, target_row, disc_color):
    """Animates a Connect 4 disc dropping down from top to target row."""
    cx = 6 + col * 44 + 22
    color = COLOR_GOOGLE_RED if disc_color == 'RED' else COLOR_GOOGLE_YELLOW
    for r in range(target_row + 1):
        if r > 0:
            prev_cy = 90 + (r - 1) * 44 + 22
            draw_filled_circle(tft, cx, prev_cy, 17, COLOR_DARK_BG)
        cy = 90 + r * 44 + 22
        draw_filled_circle(tft, cx, cy, 17, color)
        time.sleep_ms(30)

def init_c4_ui(tft, game):
    tft.fill_rect(0, 0, 320, 480, COLOR_DARK_BG)
    draw_header_bar(tft, "CONNECT 4")

    mode_text = "MODE: VS AI" if game.mode == "VS_AI" else "MODE: 2 PLAYERS"
    draw_button(tft, 8, 54, 145, 30, mode_text, COLOR_CARD_BG, COLOR_GOOGLE_YELLOW, scale=1)

    diff_text = "DIFF: " + game.difficulty
    diff_color = COLOR_GOOGLE_GREEN if game.difficulty == "EASY" else (COLOR_GOOGLE_YELLOW if game.difficulty == "MEDIUM" else COLOR_GOOGLE_RED)
    draw_button(tft, 167, 54, 145, 30, diff_text, COLOR_CARD_BG, diff_color, scale=1)

    tft.fill_rect(6, 90, 308, 270, COLOR_GOOGLE_BLUE)
    for r in range(6):
        for c in range(7):
            cx = 6 + c * 44 + 22
            cy = 90 + r * 44 + 22
            draw_filled_circle(tft, cx, cy, 17, COLOR_DARK_BG)

    for r in range(6):
        for c in range(7):
            game.prev_grid[r][c] = None
    game._prev_go = None
    game._prev_winner = None
    game._prev_turn = None
    game._prev_mode = None
    update_c4_ui(tft, game)

def update_c4_ui(tft, game):
    for r in range(6):
        for c in range(7):
            disc = game.grid[r][c]
            if disc != game.prev_grid[r][c]:
                game.prev_grid[r][c] = disc
                cx = 6 + c * 44 + 22
                cy = 90 + r * 44 + 22
                color = COLOR_GOOGLE_RED if disc == 'RED' else COLOR_GOOGLE_YELLOW
                draw_filled_circle(tft, cx, cy, 17, color)

    # Differential status banner update
    if (game.game_over != game._prev_go or
        game.winner != game._prev_winner or
        game.turn != game._prev_turn or
        game.mode != game._prev_mode):

        game._prev_go = game.game_over
        game._prev_winner = game.winner
        game._prev_turn = game.turn
        game._prev_mode = game.mode

        tft.fill_rect(0, 385, 320, 85, COLOR_DARK_BG)
        if game.game_over:
            if game.winner == 'RED':
                msg = "P1 WINS! (RED)" if game.mode == "2P" else "YOU WIN! (RED)"
                tft.draw_text(msg, 65, 410, COLOR_GOOGLE_RED, bg=COLOR_DARK_BG, scale=2)
            elif game.winner == 'YELLOW':
                msg = "P2 WINS! (YELLOW)" if game.mode == "2P" else "AI WINS! (YELLOW)"
                tft.draw_text(msg, 50, 410, COLOR_GOOGLE_YELLOW, bg=COLOR_DARK_BG, scale=2)
            else:
                tft.draw_text("IT'S A DRAW!", 95, 410, COLOR_WHITE, bg=COLOR_DARK_BG, scale=2)
        else:
            if game.mode == "2P":
                msg = "P1 TURN (RED)" if game.turn == 'RED' else "P2 TURN (YELLOW)"
                color = COLOR_GOOGLE_RED if game.turn == 'RED' else COLOR_GOOGLE_YELLOW
            else:
                msg = "YOUR TURN (RED)" if game.turn == 'RED' else "AI THINKING..."
                color = COLOR_GOOGLE_RED if game.turn == 'RED' else COLOR_GOOGLE_YELLOW
            tft.draw_text(msg, 60, 410, color, bg=COLOR_DARK_BG, scale=2)
