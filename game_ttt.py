# game_ttt.py - Tic-Tac-Toe Game Engine & Renderer for WT32-SC01
import random
import gc
from arcade_common import (
    COLOR_DARK_BG, COLOR_HEADER_BG, COLOR_CARD_BG, COLOR_WHITE,
    COLOR_TEXT_MUTED, COLOR_GOOGLE_BLUE, COLOR_GOOGLE_RED,
    COLOR_GOOGLE_YELLOW, COLOR_GOOGLE_GREEN, draw_thick_line_diag,
    draw_circle_ring, draw_button, draw_header_bar, scoreboard
)

TTT_WIN_LINES = (
    (0, 0, 0, 1, 0, 2),
    (1, 0, 1, 1, 1, 2),
    (2, 0, 2, 1, 2, 2),
    (0, 0, 1, 0, 2, 0),
    (0, 1, 1, 1, 2, 1),
    (0, 2, 1, 2, 2, 2),
    (0, 0, 1, 1, 2, 2),
    (0, 2, 1, 1, 2, 0)
)

class TicTacToe:
    def __init__(self):
        self.grid = [[None] * 3 for _ in range(3)]
        self.prev_grid = [[None] * 3 for _ in range(3)]
        self.mode = "VS_AI"
        self.difficulty = "MEDIUM" # "EASY", "MEDIUM", "HARD"
        self.turn = 'X'
        self.winner = None
        self.game_over = False
        self.recorded = False
        self._prev_go = None
        self._prev_winner = None
        self._prev_turn = None
        self._prev_mode = None
        self.reset()

    def reset(self):
        for r in range(3):
            for c in range(3):
                self.grid[r][c] = None
                self.prev_grid[r][c] = None
        self.turn = 'X'
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
        if grid_data and len(grid_data) == 3:
            self.grid = [list(row) for row in grid_data]
        self.mode = data.get("mode", self.mode)
        self.difficulty = data.get("difficulty", self.difficulty)
        self.turn = data.get("turn", self.turn)
        self.winner = data.get("winner", self.winner)
        self.game_over = data.get("game_over", self.game_over)
        self.recorded = data.get("recorded", self.recorded)
        for r in range(3):
            for c in range(3):
                self.prev_grid[r][c] = None
        self._prev_go = None
        self._prev_winner = None
        self._prev_turn = None
        self._prev_mode = None

    def play_move(self, r, c):
        if self.game_over or self.grid[r][c] is not None:
            return False
        self.grid[r][c] = self.turn
        self.check_winner()
        if not self.game_over:
            self.turn = 'O' if self.turn == 'X' else 'X'
        gc.collect()
        return True

    def _eval_grid(self, g):
        for r1, c1, r2, c2, r3, c3 in TTT_WIN_LINES:
            p1 = g[r1][c1]
            if p1 is not None and p1 == g[r2][c2] == g[r3][c3]:
                return 10 if p1 == 'O' else -10
        return 0

    def _minimax_ab(self, g, depth, alpha, beta, is_max):
        score = self._eval_grid(g)
        if score == 10: return score - depth
        if score == -10: return score + depth

        has_empty = False
        if is_max:
            best = -1000
            for r in range(3):
                for c in range(3):
                    if g[r][c] is None:
                        has_empty = True
                        g[r][c] = 'O'
                        val = self._minimax_ab(g, depth + 1, alpha, beta, False)
                        g[r][c] = None
                        if val > best:
                            best = val
                        if best > alpha:
                            alpha = best
                        if beta <= alpha:
                            return best
            return best if has_empty else 0
        else:
            best = 1000
            for r in range(3):
                for c in range(3):
                    if g[r][c] is None:
                        has_empty = True
                        g[r][c] = 'X'
                        val = self._minimax_ab(g, depth + 1, alpha, beta, True)
                        g[r][c] = None
                        if val < best:
                            best = val
                        if best < beta:
                            beta = best
                        if beta <= alpha:
                            return best
            return best if has_empty else 0

    def ai_move(self):
        if self.game_over or self.turn != 'O' or self.mode != "VS_AI":
            return

        open_cells = []
        for r in range(3):
            for c in range(3):
                if self.grid[r][c] is None:
                    open_cells.append((r, c))

        if not open_cells:
            return

        # Fast opening moves
        if len(open_cells) == 9:
            r, c = random.choice([(1,1), (0,0), (0,2), (2,0), (2,2)])
            self.play_move(r, c)
            return

        if len(open_cells) == 8:
            if self.grid[1][1] is None:
                r, c = 1, 1
            else:
                r, c = random.choice([(0,0), (0,2), (2,0), (2,2)])
            self.play_move(r, c)
            return

        if self.difficulty == "EASY":
            # 1. Immediate Win
            for r, c in open_cells:
                self.grid[r][c] = 'O'
                if self._eval_grid(self.grid) == 10:
                    self.grid[r][c] = None
                    self.play_move(r, c)
                    return
                self.grid[r][c] = None
            # 2. Immediate Block
            for r, c in open_cells:
                self.grid[r][c] = 'X'
                if self._eval_grid(self.grid) == -10:
                    self.grid[r][c] = None
                    self.play_move(r, c)
                    return
                self.grid[r][c] = None
            # 3. Random move
            r, c = random.choice(open_cells)
            self.play_move(r, c)
            return

        # Score open cells with Minimax
        best_score = -2000
        best_r, best_c = open_cells[0]
        best_moves = []
        for r, c in open_cells:
            self.grid[r][c] = 'O'
            score = self._minimax_ab(self.grid, 0, -1000, 1000, False)
            self.grid[r][c] = None
            if score > best_score:
                best_score = score
                best_moves = [(r, c)]
            elif score == best_score:
                best_moves.append((r, c))

        if self.difficulty == "HARD":
            r, c = random.choice(best_moves)
        elif self.difficulty == "MEDIUM":
            if random.random() < 0.8:
                r, c = random.choice(best_moves)
            else:
                r, c = random.choice(open_cells)

        self.play_move(r, c)

    def check_winner(self):
        g = self.grid
        for r1, c1, r2, c2, r3, c3 in TTT_WIN_LINES:
            p1 = g[r1][c1]
            if p1 is not None and p1 == g[r2][c2] == g[r3][c3]:
                self.winner = p1
                self.game_over = True
                if not self.recorded:
                    self.recorded = True
                    scoreboard.record_ttt(self.winner)
                return

        for r in range(3):
            for c in range(3):
                if g[r][c] is None:
                    return

        self.winner = 'DRAW'
        self.game_over = True
        if not self.recorded:
            self.recorded = True
            scoreboard.record_ttt('DRAW')

def init_ttt_ui(tft, game):
    tft.fill_rect(0, 0, 320, 480, COLOR_DARK_BG)
    draw_header_bar(tft, "TIC-TAC-TOE")

    mode_text = "MODE: VS AI" if game.mode == "VS_AI" else "MODE: 2 PLAYERS"
    draw_button(tft, 8, 56, 145, 32, mode_text, COLOR_CARD_BG, COLOR_GOOGLE_YELLOW, scale=1)

    diff_text = "DIFF: " + game.difficulty
    diff_color = COLOR_GOOGLE_GREEN if game.difficulty == "EASY" else (COLOR_GOOGLE_YELLOW if game.difficulty == "MEDIUM" else COLOR_GOOGLE_RED)
    draw_button(tft, 167, 56, 145, 32, diff_text, COLOR_CARD_BG, diff_color, scale=1)

    tft.fill_rect(25, 95, 270, 270, COLOR_CARD_BG)
    tft.fill_rect(113, 95, 4, 270, COLOR_DARK_BG)
    tft.fill_rect(203, 95, 4, 270, COLOR_DARK_BG)
    tft.fill_rect(25, 183, 270, 4, COLOR_DARK_BG)
    tft.fill_rect(25, 273, 270, 4, COLOR_DARK_BG)

    for r in range(3):
        for c in range(3):
            game.prev_grid[r][c] = None
    game._prev_go = None
    game._prev_winner = None
    game._prev_turn = None
    game._prev_mode = None
    update_ttt_ui(tft, game)

def update_ttt_ui(tft, game):
    for r in range(3):
        for c in range(3):
            mark = game.grid[r][c]
            if mark != game.prev_grid[r][c]:
                game.prev_grid[r][c] = mark
                cx = 25 + c * 90 + 45
                cy = 95 + r * 90 + 45
                if mark == 'X':
                    draw_thick_line_diag(tft, cx - 28, cy - 28, cx + 28, cy + 28, 6, COLOR_GOOGLE_RED)
                    draw_thick_line_diag(tft, cx + 28, cy - 28, cx - 28, cy + 28, 6, COLOR_GOOGLE_RED)
                elif mark == 'O':
                    draw_circle_ring(tft, cx, cy, 32, 24, COLOR_GOOGLE_BLUE, COLOR_CARD_BG)

    # Differential status banner update
    if (game.game_over != game._prev_go or
        game.winner != game._prev_winner or
        game.turn != game._prev_turn or
        game.mode != game._prev_mode):

        game._prev_go = game.game_over
        game._prev_winner = game.winner
        game._prev_turn = game.turn
        game._prev_mode = game.mode

        tft.fill_rect(0, 395, 320, 75, COLOR_DARK_BG)
        if game.game_over:
            if game.winner == 'X':
                msg = "PLAYER 1 WINS! (X)" if game.mode == "2P" else "YOU WIN! (X)"
                tft.draw_text(msg, 50, 415, COLOR_GOOGLE_GREEN, bg=COLOR_DARK_BG, scale=2)
            elif game.winner == 'O':
                msg = "PLAYER 2 WINS! (O)" if game.mode == "2P" else "AI WINS! (O)"
                tft.draw_text(msg, 50, 415, COLOR_GOOGLE_RED, bg=COLOR_DARK_BG, scale=2)
            else:
                tft.draw_text("IT'S A DRAW!", 95, 415, COLOR_GOOGLE_YELLOW, bg=COLOR_DARK_BG, scale=2)
        else:
            if game.mode == "2P":
                status = "P1 TURN (X)" if game.turn == 'X' else "P2 TURN (O)"
                color = COLOR_GOOGLE_RED if game.turn == 'X' else COLOR_GOOGLE_BLUE
            else:
                status = "YOUR TURN (X)" if game.turn == 'X' else "AI THINKING..."
                color = COLOR_GOOGLE_RED if game.turn == 'X' else COLOR_GOOGLE_YELLOW
            tft.draw_text(status, 80, 415, color, bg=COLOR_DARK_BG, scale=2)
