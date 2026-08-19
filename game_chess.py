# game_chess.py - Standard 8x8 Chess Engine & GUI (Fast Pure Array AI & Zero-Blink Rendering)
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
COLOR_LIGHT_SQ = rgb565(238, 238, 210) # Cream
COLOR_DARK_SQ  = rgb565(118, 150, 86)  # Chess Green
COLOR_SEL_SQ   = rgb565(255, 235, 59)  # Yellow
COLOR_DOT      = rgb565(76, 175, 80)   # Green Dot
COLOR_W_BADGE  = rgb565(255, 255, 255)
COLOR_B_BADGE  = rgb565(30, 41, 59)
COLOR_W_TEXT   = rgb565(15, 23, 42)
COLOR_B_TEXT   = rgb565(248, 250, 252)

BOARD_Y_OFFSET = 90
TILE_SIZE = 40

# Pre-allocated 40x40 RGB565 tile buffer (3,200 bytes) for zero-blink, single-SPI-write rendering
TILE_BUF = bytearray(40 * 40 * 2)

PIECE_GLYPHS_5X8 = {
    'P': b'\x7F\x09\x09\x09\x06',
    'N': b'\x7F\x04\x08\x10\x7F',
    'B': b'\x7F\x49\x49\x49\x36',
    'R': b'\x7F\x09\x19\x29\x46',
    'Q': b'\x3E\x41\x51\x21\x5E',
    'K': b'\x7F\x08\x14\x22\x41',
}

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

def draw_buf_glyph(cx, cy, char, color):
    glyph = PIECE_GLYPHS_5X8.get(char)
    if not glyph: return
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


PIECE_VALUES = {
    'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 20000
}

PAWN_TABLE = [
    0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0
]

KNIGHT_TABLE = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
]

BISHOP_TABLE = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20
]


class ChessGame:
    def __init__(self):
        self.mode = "VS_AI"
        self.difficulty = "MEDIUM" # EASY, MEDIUM, HARD
        self.reset()

    def reset(self):
        self.grid = [[None] * 8 for _ in range(8)]
        back_row = ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
        for c in range(8):
            self.grid[0][c] = 'B_' + back_row[c]
            self.grid[1][c] = 'B_P'
            self.grid[6][c] = 'W_P'
            self.grid[7][c] = 'W_' + back_row[c]

        self.turn = 'W' # 'W' or 'B'
        self.selected_pos = None
        self.valid_moves = [] # list of (to_r, to_c)
        self.en_passant_target = None # (r, c) or None
        self.castling_rights = {
            'W_K': True, 'W_Q': True,
            'B_K': True, 'B_Q': True
        }
        self.game_over = False
        self.in_check = False
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
        self._prev_in_check = None
        gc.collect()

    def to_dict(self):
        return {
            "grid": [row[:] for row in self.grid],
            "mode": self.mode,
            "difficulty": self.difficulty,
            "turn": self.turn,
            "selected_pos": list(self.selected_pos) if self.selected_pos else None,
            "en_passant_target": list(self.en_passant_target) if self.en_passant_target else None,
            "castling_rights": dict(self.castling_rights),
            "game_over": self.game_over,
            "in_check": self.in_check,
            "winner": self.winner,
            "recorded": self.recorded
        }

    def from_dict(self, data):
        if not data: return
        self.grid = [row[:] for row in data.get("grid", self.grid)]
        self.mode = data.get("mode", self.mode)
        self.difficulty = data.get("difficulty", self.difficulty)
        self.turn = data.get("turn", self.turn)
        sel = data.get("selected_pos")
        self.selected_pos = tuple(sel) if sel else None
        ep = data.get("en_passant_target")
        self.en_passant_target = tuple(ep) if ep else None
        cr = data.get("castling_rights", self.castling_rights)
        self.castling_rights = dict(cr) if isinstance(cr, dict) else self.castling_rights
        self.game_over = data.get("game_over", self.game_over)
        self.in_check = data.get("in_check", self.in_check)
        self.winner = data.get("winner", self.winner)
        self.recorded = data.get("recorded", self.recorded)

        if self.selected_pos:
            self.valid_moves = self.get_legal_moves(self.selected_pos[0], self.selected_pos[1])
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
        self._prev_in_check = None

    def get_color(self, piece):
        if not piece: return None
        return piece[0]

    def get_type(self, piece):
        if not piece: return None
        return piece[2]

    def find_king(self, grid, color):
        target = color + '_K'
        for r in range(8):
            for c in range(8):
                if grid[r][c] == target:
                    return r, c
        return None

    def is_square_attacked(self, grid, r, c, by_color):
        """
        Reverse raycasting and attack check:
        Determines whether square (r, c) is attacked by any piece of `by_color`.
        """
        # 1. Knight checks
        knight_offsets = [(-2,-1), (-2,1), (-1,-2), (-1,2), (1,-2), (1,2), (2,-1), (2,1)]
        for dr, dc in knight_offsets:
            nr, nc = r + dr, c + dc
            if 0 <= nr < 8 and 0 <= nc < 8:
                p = grid[nr][nc]
                if p == by_color + '_N':
                    return True

        # 2. Pawn checks
        # White pawns move UP (-1), so a White pawn attacking (r, c) is located at (r + 1, c ± 1)
        # Black pawns move DOWN (+1), so a Black pawn attacking (r, c) is located at (r - 1, c ± 1)
        pr = r + 1 if by_color == 'W' else r - 1
        if 0 <= pr < 8:
            for pc in (c - 1, c + 1):
                if 0 <= pc < 8 and grid[pr][pc] == by_color + '_P':
                    return True

        # 3. Orthogonal rays (Rook / Queen)
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            while 0 <= nr < 8 and 0 <= nc < 8:
                p = grid[nr][nc]
                if p:
                    if p in (by_color + '_R', by_color + '_Q'):
                        return True
                    break
                nr += dr
                nc += dc

        # 4. Diagonal rays (Bishop / Queen)
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            nr, nc = r + dr, c + dc
            while 0 <= nr < 8 and 0 <= nc < 8:
                p = grid[nr][nc]
                if p:
                    if p in (by_color + '_B', by_color + '_Q'):
                        return True
                    break
                nr += dr
                nc += dc

        # 5. Adjacent King
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr != 0 or dc != 0:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < 8 and 0 <= nc < 8 and grid[nr][nc] == by_color + '_K':
                        return True

        return False

    def is_king_in_check(self, grid, color):
        kpos = self.find_king(grid, color)
        if not kpos: return False
        opp_color = 'B' if color == 'W' else 'W'
        return self.is_square_attacked(grid, kpos[0], kpos[1], opp_color)

    def _get_raw_pseudo_moves_grid(self, grid, r, c, check_castling=True, ep_target=None):
        p = grid[r][c]
        if not p: return []
        color = self.get_color(p)
        ptype = self.get_type(p)
        opp_color = 'B' if color == 'W' else 'W'
        moves = []
        if ep_target is None:
            ep_target = self.en_passant_target

        if ptype == 'P':
            dir_r = -1 if color == 'W' else 1
            start_row = 6 if color == 'W' else 1

            # Single push
            nr = r + dir_r
            if 0 <= nr < 8 and grid[nr][c] is None:
                moves.append((nr, c))
                # Double push
                nnr = r + 2 * dir_r
                if r == start_row and grid[nnr][c] is None:
                    moves.append((nnr, c))

            # Diagonal captures
            for dc in (-1, 1):
                nc = c + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    target = grid[nr][nc]
                    if target and self.get_color(target) == opp_color:
                        moves.append((nr, nc))
                    elif ep_target and (nr, nc) == ep_target:
                        # En Passant capture
                        moves.append((nr, nc))

        elif ptype == 'N':
            offsets = [(-2,-1), (-2,1), (-1,-2), (-1,2), (1,-2), (1,2), (2,-1), (2,1)]
            for dr, dc in offsets:
                nr, nc = r + dr, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    target = grid[nr][nc]
                    if target is None or self.get_color(target) == opp_color:
                        moves.append((nr, nc))

        elif ptype in ('B', 'R', 'Q'):
            dirs = []
            if ptype in ('B', 'Q'):
                dirs.extend([(-1,-1), (-1,1), (1,-1), (1,1)])
            if ptype in ('R', 'Q'):
                dirs.extend([(-1,0), (1,0), (0,-1), (0,1)])

            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                while 0 <= nr < 8 and 0 <= nc < 8:
                    target = grid[nr][nc]
                    if target is None:
                        moves.append((nr, nc))
                    elif self.get_color(target) == opp_color:
                        moves.append((nr, nc))
                        break
                    else:
                        break
                    nr += dr
                    nc += dc

        elif ptype == 'K':
            offsets = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]
            for dr, dc in offsets:
                nr, nc = r + dr, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    target = grid[nr][nc]
                    if target is None or self.get_color(target) == opp_color:
                        moves.append((nr, nc))

            # Castling moves (only allowed if king not currently in check and squares clear/safe)
            if check_castling and not self.is_king_in_check(grid, color):
                if color == 'W' and r == 7 and c == 4:
                    # Kingside Castling
                    if self.castling_rights.get('W_K') and grid[7][5] is None and grid[7][6] is None and grid[7][7] == 'W_R':
                        if not self.is_square_attacked(grid, 7, 5, 'B') and not self.is_square_attacked(grid, 7, 6, 'B'):
                            moves.append((7, 6))
                    # Queenside Castling
                    if self.castling_rights.get('W_Q') and grid[7][3] is None and grid[7][2] is None and grid[7][1] is None and grid[7][0] == 'W_R':
                        if not self.is_square_attacked(grid, 7, 3, 'B') and not self.is_square_attacked(grid, 7, 2, 'B'):
                            moves.append((7, 2))
                elif color == 'B' and r == 0 and c == 4:
                    # Kingside Castling
                    if self.castling_rights.get('B_K') and grid[0][5] is None and grid[0][6] is None and grid[0][7] == 'B_R':
                        if not self.is_square_attacked(grid, 0, 5, 'W') and not self.is_square_attacked(grid, 0, 6, 'W'):
                            moves.append((0, 6))
                    # Queenside Castling
                    if self.castling_rights.get('B_Q') and grid[0][3] is None and grid[0][2] is None and grid[0][1] is None and grid[0][0] == 'B_R':
                        if not self.is_square_attacked(grid, 0, 3, 'W') and not self.is_square_attacked(grid, 0, 2, 'W'):
                            moves.append((0, 2))

        return moves

    def get_legal_moves(self, r, c):
        p = self.grid[r][c]
        if not p or self.get_color(p) != self.turn:
            return []

        pseudo_moves = self._get_raw_pseudo_moves_grid(self.grid, r, c, check_castling=True, ep_target=self.en_passant_target)
        legal = []

        for tr, tc in pseudo_moves:
            saved_tr = self.grid[tr][tc]
            self.grid[tr][tc] = p
            self.grid[r][c] = None

            # Handle en-passant captured pawn simulation
            ep_captured = None
            if self.get_type(p) == 'P' and self.en_passant_target and (tr, tc) == self.en_passant_target:
                ep_captured = self.grid[r][tc]
                self.grid[r][tc] = None

            if not self.is_king_in_check(self.grid, self.turn):
                legal.append((tr, tc))

            self.grid[r][c] = p
            self.grid[tr][tc] = saved_tr
            if ep_captured is not None:
                self.grid[r][tc] = ep_captured

        return legal

    def get_all_legal_moves(self, color):
        return self._get_grid_legal_moves(self.grid, color, self.en_passant_target)

    def _get_grid_legal_moves(self, grid, color, ep_target=None):
        all_moves = {}
        for r in range(8):
            for c in range(8):
                p = grid[r][c]
                if p and self.get_color(p) == color:
                    pseudo = self._get_raw_pseudo_moves_grid(grid, r, c, check_castling=True, ep_target=ep_target)
                    legal = []
                    for tr, tc in pseudo:
                        saved_target = grid[tr][tc]
                        grid[tr][tc] = p
                        grid[r][c] = None

                        ep_captured = None
                        if self.get_type(p) == 'P' and ep_target and (tr, tc) == ep_target:
                            ep_captured = grid[r][tc]
                            grid[r][tc] = None

                        if not self.is_king_in_check(grid, color):
                            legal.append((tr, tc))

                        grid[r][c] = p
                        grid[tr][tc] = saved_target
                        if ep_captured is not None:
                            grid[r][tc] = ep_captured

                    if legal:
                        all_moves[(r, c)] = legal
        return all_moves

    def select_cell(self, r, c):
        if self.game_over: return False
        if not (0 <= r < 8 and 0 <= c < 8): return False

        p = self.grid[r][c]
        if p and self.get_color(p) == self.turn:
            self.selected_pos = (r, c)
            self.valid_moves = self.get_legal_moves(r, c)
            return True

        if self.selected_pos and (r, c) in self.valid_moves:
            return self.execute_move(self.selected_pos, (r, c))

        self.selected_pos = None
        self.valid_moves = []
        return True

    select_square = select_cell

    def execute_move(self, fr_pos, to_pos):
        fr, fc = fr_pos
        tr, tc = to_pos
        p = self.grid[fr][fc]
        if not p: return False
        color = self.get_color(p)
        ptype = self.get_type(p)

        self.grid[fr][fc] = None

        # En Passant capture: cleanly wipe opponent pawn
        if ptype == 'P' and self.en_passant_target and (tr, tc) == self.en_passant_target:
            self.grid[fr][tc] = None

        # Castling move execution (move King and corresponding Rook, clear origins)
        if ptype == 'K':
            if color == 'W':
                self.castling_rights['W_K'] = False
                self.castling_rights['W_Q'] = False
                if fr == 7 and fc == 4:
                    if tr == 7 and tc == 6: # Kingside
                        self.grid[7][7] = None
                        self.grid[7][5] = 'W_R'
                    elif tr == 7 and tc == 2: # Queenside
                        self.grid[7][0] = None
                        self.grid[7][3] = 'W_R'
            elif color == 'B':
                self.castling_rights['B_K'] = False
                self.castling_rights['B_Q'] = False
                if fr == 0 and fc == 4:
                    if tr == 0 and tc == 6: # Kingside
                        self.grid[0][7] = None
                        self.grid[0][5] = 'B_R'
                    elif tr == 0 and tc == 2: # Queenside
                        self.grid[0][0] = None
                        self.grid[0][3] = 'B_R'

        # Revoke castling rights if Rook moves or is captured on initial square
        if fr == 7 and fc == 7: self.castling_rights['W_K'] = False
        elif fr == 7 and fc == 0: self.castling_rights['W_Q'] = False
        elif fr == 0 and fc == 7: self.castling_rights['B_K'] = False
        elif fr == 0 and fc == 0: self.castling_rights['B_Q'] = False

        if tr == 7 and tc == 7: self.castling_rights['W_K'] = False
        elif tr == 7 and tc == 0: self.castling_rights['W_Q'] = False
        elif tr == 0 and tc == 7: self.castling_rights['B_K'] = False
        elif tr == 0 and tc == 0: self.castling_rights['B_Q'] = False

        # Set or reset En Passant target
        if ptype == 'P' and abs(tr - fr) == 2:
            self.en_passant_target = ((fr + tr) // 2, fc)
        else:
            self.en_passant_target = None

        # Pawn Promotion (Default to Queen)
        if p == 'W_P' and tr == 0:
            p = 'W_Q'
        elif p == 'B_P' and tr == 7:
            p = 'B_Q'

        self.grid[tr][tc] = p
        self.selected_pos = None
        self.valid_moves = []

        self.switch_turn()
        gc.collect()
        return True

    def switch_turn(self):
        self.turn = 'B' if self.turn == 'W' else 'W'
        self.in_check = self.is_king_in_check(self.grid, self.turn)
        self.check_game_over()

    def check_game_over(self):
        moves_dict = self.get_all_legal_moves(self.turn)
        if not moves_dict:
            self.game_over = True
            if self.in_check:
                self.winner = 'B' if self.turn == 'W' else 'W'
            else:
                self.winner = 'DRAW'

            if not self.recorded:
                scoreboard.record_chess(self.winner)
                self.recorded = True

    # --- Fast Pure Array Minimax AI ---
    def _eval_grid_chess(self, grid):
        score = 0
        for r in range(8):
            for c in range(8):
                p = grid[r][c]
                if p:
                    color = self.get_color(p)
                    ptype = self.get_type(p)
                    val = PIECE_VALUES[ptype]

                    pos_idx = r * 8 + c
                    if ptype == 'P':
                        pos_bonus = PAWN_TABLE[pos_idx] if color == 'W' else PAWN_TABLE[63 - pos_idx]
                    elif ptype == 'N':
                        pos_bonus = KNIGHT_TABLE[pos_idx] if color == 'W' else KNIGHT_TABLE[63 - pos_idx]
                    elif ptype == 'B':
                        pos_bonus = BISHOP_TABLE[pos_idx] if color == 'W' else BISHOP_TABLE[63 - pos_idx]
                    else:
                        pos_bonus = 0

                    if color == 'W':
                        score += (val + pos_bonus)
                    else:
                        score -= (val + pos_bonus)
        return score

    def _apply_move_to_grid(self, grid, fr, fc, tr, tc):
        new_grid = [row[:] for row in grid]
        p = new_grid[fr][fc]
        if not p: return new_grid
        new_grid[fr][fc] = None

        ptype = self.get_type(p)

        # En Passant capture simulation
        if ptype == 'P' and fc != tc and grid[tr][tc] is None:
            new_grid[fr][tc] = None

        # Castling simulation (move rook)
        if ptype == 'K':
            if p == 'W_K' and fr == 7 and fc == 4:
                if tr == 7 and tc == 6:
                    new_grid[7][7] = None
                    new_grid[7][5] = 'W_R'
                elif tr == 7 and tc == 2:
                    new_grid[7][0] = None
                    new_grid[7][3] = 'W_R'
            elif p == 'B_K' and fr == 0 and fc == 4:
                if tr == 0 and tc == 6:
                    new_grid[0][7] = None
                    new_grid[0][5] = 'B_R'
                elif tr == 0 and tc == 2:
                    new_grid[0][0] = None
                    new_grid[0][3] = 'B_R'

        # Promotion
        if p == 'W_P' and tr == 0: p = 'W_Q'
        elif p == 'B_P' and tr == 7: p = 'B_Q'

        new_grid[tr][tc] = p
        return new_grid

    def _minimax_fast(self, grid, depth, alpha, beta, is_max):
        if depth == 0:
            return self._eval_grid_chess(grid), None

        current_player = 'W' if is_max else 'B'
        moves_dict = self._get_grid_legal_moves(grid, current_player, self.en_passant_target)

        if not moves_dict:
            if self.is_king_in_check(grid, current_player):
                return (100000 + depth if not is_max else -100000 - depth), None
            return 0, None

        all_flat_moves = []
        for fr_pos, m_list in moves_dict.items():
            for to_pos in m_list:
                # Capture move prioritization for faster alpha-beta cutoffs
                target = grid[to_pos[0]][to_pos[1]]
                priority = PIECE_VALUES.get(self.get_type(target), 0) if target else 0
                all_flat_moves.append(((fr_pos, to_pos), priority))

        all_flat_moves.sort(key=lambda item: item[1], reverse=True)
        best_move = all_flat_moves[0][0]

        if is_max:
            max_eval = -999999
            for (fr_pos, to_pos), _ in all_flat_moves:
                next_grid = self._apply_move_to_grid(grid, fr_pos[0], fr_pos[1], to_pos[0], to_pos[1])
                eval_val, _ = self._minimax_fast(next_grid, depth - 1, alpha, beta, False)
                if eval_val > max_eval:
                    max_eval = eval_val
                    best_move = (fr_pos, to_pos)
                alpha = max(alpha, eval_val)
                if beta <= alpha:
                    break
            return max_eval, best_move
        else:
            min_eval = 999999
            for (fr_pos, to_pos), _ in all_flat_moves:
                next_grid = self._apply_move_to_grid(grid, fr_pos[0], fr_pos[1], to_pos[0], to_pos[1])
                eval_val, _ = self._minimax_fast(next_grid, depth - 1, alpha, beta, True)
                if eval_val < min_eval:
                    min_eval = eval_val
                    best_move = (fr_pos, to_pos)
                beta = min(beta, eval_val)
                if beta <= alpha:
                    break
            return min_eval, best_move

    def ai_move(self):
        if self.game_over or self.turn != 'B' or self.mode != "VS_AI":
            return

        moves_dict = self.get_all_legal_moves('B')
        if not moves_dict:
            self.check_game_over()
            return

        all_flat_moves = []
        for pos, m_list in moves_dict.items():
            for m in m_list:
                all_flat_moves.append((pos, m))

        if not all_flat_moves: return

        if self.difficulty == "EASY":
            chosen_from, chosen_to = random.choice(all_flat_moves)
        else:
            depth = 2 if self.difficulty == "MEDIUM" else 3
            _, best_move = self._minimax_fast(self.grid, depth, -999999, 999999, False)
            if best_move:
                chosen_from, chosen_to = best_move[0], best_move[1]
            else:
                chosen_from, chosen_to = random.choice(all_flat_moves)

        self.execute_move(chosen_from, chosen_to)
        gc.collect()


# --- Zero-Blink GUI Renderer ---
def render_chess_tile(tft, game_obj, r, c):
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
            color = p[0] # 'W' or 'B'
            ptype = p[2] # 'P', 'N', 'B', 'R', 'Q', 'K'
            badge_col = COLOR_W_BADGE if color == 'W' else COLOR_B_BADGE
            text_col  = COLOR_W_TEXT if color == 'W' else COLOR_B_TEXT

            draw_buf_circle(20, 20, 16, COLOR_DARK_BG)
            draw_buf_circle(20, 20, 14, badge_col)
            draw_buf_glyph(20, 20, ptype, text_col)

    if hasattr(tft, 'blit_buffer'):
        tft.blit_buffer(x, y, TILE_SIZE, TILE_SIZE, TILE_BUF)
    else:
        tft.set_window(x, y, x + TILE_SIZE - 1, y + TILE_SIZE - 1)
        tft.dc.value(1)
        tft.cs.value(0)
        tft.spi.write(TILE_BUF)
        tft.cs.value(1)


def init_chess_ui(tft, game_obj):
    tft.fill_rect(0, 0, 320, 480, COLOR_DARK_BG)
    draw_header_bar(tft, "STANDARD CHESS")

    mode_str = "VS AI" if game_obj.mode == "VS_AI" else "2 PLAYER"
    draw_button(tft, 8, 56, 145, 30, mode_str, COLOR_CARD_BG, COLOR_WHITE, scale=1)
    
    diff_str = "DIFF: " + game_obj.difficulty
    draw_button(tft, 167, 56, 145, 30, diff_str, COLOR_CARD_BG, COLOR_GOOGLE_YELLOW, scale=1)

    for r in range(8):
        for c in range(8):
            render_chess_tile(tft, game_obj, r, c)
            game_obj.prev_grid[r][c] = game_obj.grid[r][c]

    game_obj.prev_selected_pos = game_obj.selected_pos
    n_valid = len(game_obj.valid_moves)
    game_obj._prev_valid_count = n_valid
    for i in range(n_valid):
        game_obj._prev_valid[i] = game_obj.valid_moves[i]

    game_obj._prev_go = None
    game_obj._prev_winner = None
    game_obj._prev_turn = None
    game_obj._prev_in_check = None

    update_chess_status(tft, game_obj)


def update_chess_status(tft, game_obj):
    if (game_obj.game_over == game_obj._prev_go and 
        game_obj.winner == game_obj._prev_winner and 
        game_obj.turn == game_obj._prev_turn and 
        game_obj.in_check == game_obj._prev_in_check):
        return

    game_obj._prev_go = game_obj.game_over
    game_obj._prev_winner = game_obj.winner
    game_obj._prev_turn = game_obj.turn
    game_obj._prev_in_check = game_obj.in_check

    tft.fill_rect(0, 415, 320, 65, COLOR_HEADER_BG)

    if game_obj.game_over:
        if game_obj.winner == 'W':
            msg, col = "CHECKMATE! YOU WIN!", COLOR_GOOGLE_GREEN
        elif game_obj.winner == 'B':
            msg = "CHECKMATE! AI WINS!" if game_obj.mode == "VS_AI" else "CHECKMATE! BLACK WINS!"
            col = COLOR_GOOGLE_RED
        else:
            msg, col = "STALEMATE! DRAW!", COLOR_GOOGLE_YELLOW
    else:
        check_str = " (CHECK!)" if game_obj.in_check else ""
        if game_obj.turn == 'W':
            msg = "WHITE'S TURN" + check_str
            col = COLOR_GOOGLE_RED if game_obj.in_check else COLOR_WHITE
        else:
            msg = ("AI THINKING..." if game_obj.mode == "VS_AI" else "BLACK'S TURN") + check_str
            col = COLOR_GOOGLE_YELLOW

    tft.draw_text(msg, 15, 428, col, bg=COLOR_HEADER_BG, scale=2)
    tft.draw_text("TAP PIECE TO MOVE", 15, 453, COLOR_TEXT_MUTED, bg=COLOR_HEADER_BG, scale=1)


def update_chess_ui(tft, game_obj):
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
                render_chess_tile(tft, game_obj, r, c)
                game_obj.prev_grid[r][c] = game_obj.grid[r][c]

    game_obj.prev_selected_pos = game_obj.selected_pos

    n_valid = len(game_obj.valid_moves)
    game_obj._prev_valid_count = n_valid
    for i in range(n_valid):
        game_obj._prev_valid[i] = game_obj.valid_moves[i]

    update_chess_status(tft, game_obj)
