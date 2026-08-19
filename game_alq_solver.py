# game_alq_solver.py - Alquerque Tactical Solver & Assistant for MicroPython WT32 Arcade
import gc
from arcade_common import (
    COLOR_DARK_BG, COLOR_HEADER_BG, COLOR_CARD_BG, COLOR_WHITE,
    COLOR_TEXT_LIGHT, COLOR_TEXT_MUTED, COLOR_GOOGLE_BLUE, COLOR_GOOGLE_RED,
    COLOR_GOOGLE_YELLOW, COLOR_GOOGLE_GREEN, rgb565, draw_button,
    draw_header_bar, draw_thick_line_diag
)

COLOR_BEST_GREEN = rgb565(34, 197, 94)   # Emerald Green
COLOR_ALT_YELLOW = rgb565(251, 188, 4)   # Gold / Yellow

# ============================================================================
# PRECOMPUTED MOVEMENT & JUMP TABLES (0..24 Flat Node Indexing)
# ============================================================================
# Board Layout:
#  0  1  2  3  4
#  5  6  7  8  9
# 10 11 12 13 14
# 15 16 17 18 19
# 20 21 22 23 24

_ORTHO_STEPS = []
_ORTHO_JUMPS = []
_FULL_STEPS = []
_FULL_JUMPS = []

for _idx in range(25):
    _r, _c = _idx // 5, _idx % 5

    # Orthogonal movement
    _o_steps = []
    _o_jumps = []
    if _r > 0: _o_steps.append(_idx - 5)
    if _r < 4: _o_steps.append(_idx + 5)
    if _c > 0: _o_steps.append(_idx - 1)
    if _c < 4: _o_steps.append(_idx + 1)

    if _r >= 2: _o_jumps.append((_idx - 10, _idx - 5))
    if _r <= 2: _o_jumps.append((_idx + 10, _idx + 5))
    if _c >= 2: _o_jumps.append((_idx - 2, _idx - 1))
    if _c <= 2: _o_jumps.append((_idx + 2, _idx + 1))

    _ORTHO_STEPS.append(tuple(_o_steps))
    _ORTHO_JUMPS.append(tuple(_o_jumps))

    # Full variant (Orthogonal + Diagonals for even parity nodes: (r+c)%2 == 0)
    _f_steps = list(_o_steps)
    _f_jumps = list(_o_jumps)
    if (_r + _c) % 2 == 0:
        if _r > 0 and _c > 0: _f_steps.append(_idx - 6)
        if _r > 0 and _c < 4: _f_steps.append(_idx - 4)
        if _r < 4 and _c > 0: _f_steps.append(_idx + 4)
        if _r < 4 and _c < 4: _f_steps.append(_idx + 6)

        if _r >= 2 and _c >= 2: _f_jumps.append((_idx - 12, _idx - 6))
        if _r >= 2 and _c <= 2: _f_jumps.append((_idx - 8, _idx - 4))
        if _r <= 2 and _c >= 2: _f_jumps.append((_idx + 8, _idx + 4))
        if _r <= 2 and _c <= 2: _f_jumps.append((_idx + 12, _idx + 6))

    _FULL_STEPS.append(tuple(_f_steps))
    _FULL_JUMPS.append(tuple(_f_jumps))

ORTHO_STEPS = tuple(_ORTHO_STEPS)
ORTHO_JUMPS = tuple(_ORTHO_JUMPS)
FULL_STEPS = tuple(_FULL_STEPS)
FULL_JUMPS = tuple(_FULL_JUMPS)


# ============================================================================
# ZERO-ALLOCATION IN-PLACE ENGINE CORE
# ============================================================================

def _find_chains_inplace(board, idx, opp, jumps_table, path_captured, all_chains):
    """Recursively finds all multi-jump capture paths for piece at idx in-place."""
    has_subjump = False
    player = 3 - opp
    for dest, mid in jumps_table[idx]:
        if board[mid] == opp and board[dest] == 0:
            # Make jump hop in-place
            board[idx] = 0
            board[mid] = 0
            board[dest] = player

            new_captured = path_captured + (mid,)
            sub_found = _find_chains_inplace(board, dest, opp, jumps_table, new_captured, all_chains)
            if not sub_found:
                all_chains.append((dest, new_captured))
            has_subjump = True

            # Undo jump hop in-place
            board[dest] = 0
            board[mid] = opp
            board[idx] = player

    return has_subjump


def get_flat_moves(board, p, is_full):
    """Generates all legal moves for player p using precomputed move tables."""
    jumps_table = FULL_JUMPS if is_full else ORTHO_JUMPS
    steps_table = FULL_STEPS if is_full else ORTHO_STEPS
    opp = 3 - p

    jumps = []
    # 1. Collect jump moves and multi-jump chains
    for idx in range(25):
        if board[idx] == p:
            chains = []
            _find_chains_inplace(board, idx, opp, jumps_table, (), chains)
            for final_dest, captured in chains:
                jumps.append((idx, final_dest, True, captured))

    # In FULL variant, jump captures are mandatory if any exist
    if is_full and jumps:
        return jumps

    # 2. Collect regular step moves
    steps = []
    for idx in range(25):
        if board[idx] == p:
            for dest in steps_table[idx]:
                if board[dest] == 0:
                    steps.append((idx, dest, False, ()))

    if is_full:
        return steps
    else:
        # In ORTHO variant, jumps + steps are both legal
        return jumps + steps


def make_move_inplace(board, move, player):
    """Applies a move in-place on the flat board."""
    fr, to, is_jump, captured = move
    board[fr] = 0
    if is_jump:
        for mid in captured:
            board[mid] = 0
    board[to] = player


def unmake_move_inplace(board, move, player):
    """Reverts a move in-place on the flat board."""
    fr, to, is_jump, captured = move
    board[to] = 0
    board[fr] = player
    if is_jump:
        opp = 3 - player
        for mid in captured:
            board[mid] = opp


def evaluate_flat_board(board, player_view, is_full):
    """Static evaluation heuristic with piece count, advancement, center control & mobility."""
    p1_count = 0
    p2_count = 0
    p1_pos = 0
    p2_pos = 0

    for idx in range(25):
        piece = board[idx]
        if piece == 1:
            p1_count += 1
            r = idx // 5
            c = idx % 5
            # Advancement + center column bonus
            p1_pos += r * 8 + (2 - abs(2 - c)) * 6
            if idx == 12: p1_pos += 15 # Center node
        elif piece == 2:
            p2_count += 1
            r = idx // 5
            c = idx % 5
            # Advancement + center column bonus
            p2_pos += (4 - r) * 8 + (2 - abs(2 - c)) * 6
            if idx == 12: p2_pos += 15 # Center node

    # Material difference is dominant (300 per piece)
    score = (p1_count - p2_count) * 300 + (p1_pos - p2_pos)
    return score if player_view == 1 else -score


def minimax_flat(board, depth, alpha, beta, is_maximizing, max_player, is_full):
    """Alpha-Beta minimax search operating in-place with zero memory allocation."""
    p1_count = 0
    p2_count = 0
    for i in range(25):
        if board[i] == 1: p1_count += 1
        elif board[i] == 2: p2_count += 1

    if p1_count == 0:
        return -10000 - depth if max_player == 1 else 10000 + depth
    if p2_count == 0:
        return 10000 + depth if max_player == 1 else -10000 - depth

    if depth == 0:
        return evaluate_flat_board(board, max_player, is_full)

    curr_p = max_player if is_maximizing else (3 - max_player)
    moves = get_flat_moves(board, curr_p, is_full)

    if not moves:
        # No legal moves is a loss for current player
        return -10000 - depth if is_maximizing else 10000 + depth

    # Move ordering: Jumps first, multi-jumps highest priority
    if len(moves) > 1:
        moves.sort(key=lambda m: (1 if m[2] else 0, len(m[3])), reverse=True)

    if is_maximizing:
        max_eval = -999999
        for move in moves:
            make_move_inplace(board, move, curr_p)
            eval_val = minimax_flat(board, depth - 1, alpha, beta, False, max_player, is_full)
            unmake_move_inplace(board, move, curr_p)

            if eval_val > max_eval:
                max_eval = eval_val
            if eval_val > alpha:
                alpha = eval_val
            if beta <= alpha:
                break
        return max_eval
    else:
        min_eval = 999999
        for move in moves:
            make_move_inplace(board, move, curr_p)
            eval_val = minimax_flat(board, depth - 1, alpha, beta, True, max_player, is_full)
            unmake_move_inplace(board, move, curr_p)

            if eval_val < min_eval:
                min_eval = eval_val
            if eval_val < beta:
                beta = eval_val
            if beta <= alpha:
                break
        return min_eval


# ============================================================================
# ALQUERQUE SOLVER CLASS
# ============================================================================

class AlquerqueSolver:
    """Tactical Solver Engine optimized for MicroPython ESP32/WT32."""
    def __init__(self):
        self.grid = [[0] * 5 for _ in range(5)]
        self.prev_grid = [[-1] * 5 for _ in range(5)]
        self.variant = "FULL"         # "FULL" (8-dir + mandatory) or "ORTHO" (4-dir)
        self._user_side = 1           # 1: User is RED, 2: User is BLUE
        self.turn = 1                  # Current turn (1: Red, 2: Blue)
        self.selected = None           # (r, c)
        self.prev_selected = (-1, -1)
        self.valid_targets = []
        self.prev_targets = []
        self.must_continue_jump = False
        self.edit_mode = False         # Manual board state edit mode
        self.best_move = None          # ((fr, fc), (tr, tc), is_jump, captured_pos, captured_tuple)
        self.best_score = 0
        self.prev_eval_score = None
        self.status_msg = "BEST: CALC..."
        self.prev_status_msg = ""
        self.prev_best_from = (-1, -1)
        self.prev_best_to = (-1, -1)
        self.reset()

    @property
    def user_side(self):
        return self._user_side

    @user_side.setter
    def user_side(self, val):
        self._user_side = val
        self.turn = val

    def reset(self):
        # Traditional 12 vs 12 setup with center (2, 2) empty
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
        self.edit_mode = False
        self.best_move = None
        self.best_score = 0
        self.prev_eval_score = None
        self.prev_best_from = (-1, -1)
        self.prev_best_to = (-1, -1)
        self.analyze_position()
        gc.collect()

    def to_dict(self):
        return {
            "grid": [row[:] for row in self.grid],
            "variant": self.variant,
            "user_side": self.user_side,
            "turn": self.turn,
            "selected": list(self.selected) if self.selected else None,
            "must_continue_jump": self.must_continue_jump,
            "edit_mode": self.edit_mode,
            "status_msg": self.status_msg
        }

    def from_dict(self, data):
        if not data: return
        self.grid = [row[:] for row in data.get("grid", self.grid)]
        self.variant = data.get("variant", self.variant)
        self.user_side = data.get("user_side", self.user_side)
        self.turn = data.get("turn", self.turn)
        sel = data.get("selected")
        self.selected = tuple(sel) if sel else None
        self.must_continue_jump = data.get("must_continue_jump", self.must_continue_jump)
        self.edit_mode = data.get("edit_mode", self.edit_mode)
        self.status_msg = data.get("status_msg", self.status_msg)
        self.analyze_position()
        if self.selected:
            force_jumps = (self.variant == "FULL") and self.has_any_jumps_for_player(self.turn)
            moves = self.get_legal_moves_for_piece(self.selected[0], self.selected[1], force_jumps_only=force_jumps)
            self.valid_targets = [m[0] for m in moves]
        else:
            self.valid_targets = []
        self.prev_grid = [[-1] * 5 for _ in range(5)]
        self.prev_selected = (-1, -1)
        self.prev_targets = []
        self.prev_best_from = (-1, -1)
        self.prev_best_to = (-1, -1)
        self.prev_status_msg = ""
        self.prev_eval_score = None

    def count_pieces(self):
        p1, p2 = 0, 0
        for r in range(5):
            for c in range(5):
                if self.grid[r][c] == 1: p1 += 1
                elif self.grid[r][c] == 2: p2 += 1
        return p1, p2

    def get_node_directions(self, r, c):
        dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if self.variant == "FULL" and (r + c) % 2 == 0:
            dirs.extend([(-1, -1), (-1, 1), (1, -1), (1, 1)])
        return dirs

    def get_legal_moves_for_piece(self, r, c, force_jumps_only=False):
        moves = []
        player = self.grid[r][c]
        if player == 0:
            return moves

        opponent = 3 - player
        dirs = self.get_node_directions(r, c)
        jumps = []
        steps = []

        for dr, dc in dirs:
            r_mid, c_mid = r + dr, c + dc
            r_dest, c_dest = r + 2 * dr, c + 2 * dc

            if 0 <= r_dest < 5 and 0 <= c_dest < 5:
                if self.grid[r_mid][c_mid] == opponent and self.grid[r_dest][c_dest] == 0:
                    jumps.append(((r_dest, c_dest), True, (r_mid, c_mid)))

            if not force_jumps_only and not self.must_continue_jump:
                r_step, c_step = r + dr, c + dc
                if 0 <= r_step < 5 and 0 <= c_step < 5:
                    if self.grid[r_step][c_step] == 0:
                        steps.append(((r_step, c_step), False, None))

        if self.must_continue_jump or force_jumps_only:
            return jumps
        if self.variant == "FULL":
            return jumps if jumps else steps
        return jumps + steps

    def has_any_jumps_for_player(self, player):
        for r in range(5):
            for c in range(5):
                if self.grid[r][c] == player:
                    if self.get_legal_moves_for_piece(r, c, force_jumps_only=True):
                        return True
        return False

    def get_all_legal_moves(self, player):
        is_full = (self.variant == "FULL")
        jumps_exist = is_full and self.has_any_jumps_for_player(player)
        all_moves = []
        for r in range(5):
            for c in range(5):
                if self.grid[r][c] == player:
                    p_moves = self.get_legal_moves_for_piece(r, c, force_jumps_only=jumps_exist)
                    for target_pos, is_jump, captured_pos in p_moves:
                        all_moves.append(((r, c), target_pos, is_jump, captured_pos))
        return all_moves

    def select_cell(self, r, c):
        if self.edit_mode:
            # Edit mode: Cycle 0 (EMPTY) -> 1 (RED) -> 2 (BLUE) -> 0
            self.grid[r][c] = (self.grid[r][c] + 1) % 3
            self.selected = None
            self.valid_targets = []
            self.analyze_position()
            return True

        current_p = self.turn
        is_full = (self.variant == "FULL")
        jumps_exist = is_full and self.has_any_jumps_for_player(current_p)

        if self.selected is not None:
            sr, sc = self.selected
            moves = self.get_legal_moves_for_piece(sr, sc, force_jumps_only=jumps_exist)
            for target_pos, is_jump, captured_pos in moves:
                if target_pos == (r, c):
                    return self.execute_move(self.selected, target_pos, is_jump, captured_pos)

        if self.must_continue_jump:
            return False

        if self.grid[r][c] == current_p:
            moves = self.get_legal_moves_for_piece(r, c, force_jumps_only=jumps_exist)
            if moves:
                self.selected = (r, c)
                self.valid_targets = [m[0] for m in moves]
                return True
            else:
                self.selected = None
                self.valid_targets = []
                return False
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

        further_jumps = []
        if is_jump:
            self.must_continue_jump = True
            further_jumps = self.get_legal_moves_for_piece(tr, tc, force_jumps_only=True)
            self.must_continue_jump = False

        if is_jump and further_jumps:
            self.selected = (tr, tc)
            self.must_continue_jump = True
            self.valid_targets = [m[0] for m in further_jumps]
        else:
            self.selected = None
            self.must_continue_jump = False
            self.valid_targets = []
            self.turn = 3 - player

        self.analyze_position()
        gc.collect()
        return True

    # --- Minimax Tactical Position Analyzer ---

    def analyze_position(self):
        # Build flat board representation (25 bytes)
        board = bytearray(25)
        for r in range(5):
            for c in range(5):
                board[r * 5 + c] = self.grid[r][c]

        is_full = (self.variant == "FULL")
        moves = get_flat_moves(board, self.turn, is_full)

        p_name = "RED" if self.turn == 1 else "BLUE"

        if not moves:
            self.best_move = None
            self.best_score = -10000
            self.status_msg = f"{p_name}: NO LEGAL MOVES!"
            gc.collect()
            return

        # Sort candidate root moves: Jumps first, multi-jumps highest
        moves.sort(key=lambda m: (1 if m[2] else 0, len(m[3])), reverse=True)

        best_m = None
        best_val = -999999

        # Search depth 4 provides deep tactical analysis with sub-80ms response on ESP32
        search_depth = 4

        for m in moves:
            make_move_inplace(board, m, self.turn)
            score = minimax_flat(board, search_depth - 1, -999999, 999999, False, self.turn, is_full)
            unmake_move_inplace(board, m, self.turn)

            # Preference for decisive captures on equal score
            adj_score = score
            if m[2]:
                adj_score += 15 * len(m[3])

            if adj_score > best_val:
                best_val = adj_score
                best_m = m

        self.best_score = best_val

        if best_m:
            fr_idx, to_idx, is_j, captured = best_m
            fr = (fr_idx // 5, fr_idx % 5)
            to = (to_idx // 5, to_idx % 5)
            cap_pos = (captured[0] // 5, captured[0] % 5) if captured else None
            self.best_move = (fr, to, is_j, cap_pos, captured)

            num_caps = len(captured) if is_j else 0
            if is_j and num_caps > 1:
                act = f"JUMP x{num_caps}"
            elif is_j:
                act = "JUMP"
            else:
                act = "MOVE"
            self.status_msg = f"{p_name}: {act} ({fr[0]},{fr[1]})->({to[0]},{to[1]})"
        else:
            self.best_move = None
            self.status_msg = f"{p_name}: NO MOVES!"

        gc.collect()
        return self.best_score, self.best_move


# ============================================================================
# MICROPYTHON UI & DISPLAY RENDERING (ST7796S)
# ============================================================================

# 48x48 RGB565 node tile buffer (4,608 bytes) for zero-blink direct SPI rendering
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

def draw_buf_thick_diag(x1, y1, x2, y2, thickness, color):
    steps = max(abs(x2 - x1), abs(y2 - y1))
    if steps == 0:
        return
    dx = (x2 - x1) / steps
    dy = (y2 - y1) / steps
    half_t = thickness // 2
    for i in range(steps + 1):
        cx = int(x1 + i * dx)
        cy = int(y1 + i * dy)
        draw_buf_rect(cx - half_t, cy - half_t, thickness, thickness, color)


def render_solver_tile(tft, game, r, c, val, is_sel, is_target, is_best_from, is_best_to):
    cx = 30 + c * 65
    cy = 110 + r * 68

    fill_tile_buf(COLOR_CARD_BG)

    # Orthogonal grid connections
    if c > 0: draw_buf_rect(0, 23, 24, 3, COLOR_TEXT_MUTED)
    if c < 4: draw_buf_rect(24, 23, 24, 3, COLOR_TEXT_MUTED)
    if r > 0: draw_buf_rect(23, 0, 3, 24, COLOR_TEXT_MUTED)
    if r < 4: draw_buf_rect(23, 24, 3, 24, COLOR_TEXT_MUTED)

    # Diagonal grid lines for even parity nodes when FULL variant is active
    if game.variant == "FULL" and (r + c) % 2 == 0:
        if r > 0 and c > 0: draw_buf_thick_diag(0, 0, 24, 24, 2, COLOR_TEXT_MUTED)
        if r > 0 and c < 4: draw_buf_thick_diag(47, 0, 24, 24, 2, COLOR_TEXT_MUTED)
        if r < 4 and c > 0: draw_buf_thick_diag(0, 47, 24, 24, 2, COLOR_TEXT_MUTED)
        if r < 4 and c < 4: draw_buf_thick_diag(47, 47, 24, 24, 2, COLOR_TEXT_MUTED)

    # Best move highlight ring (EMERALD GREEN)
    if is_best_from or is_best_to:
        draw_buf_circle(24, 24, 23, COLOR_BEST_GREEN)

    if val == 0:
        if is_best_to:
            draw_buf_circle(24, 24, 16, COLOR_BEST_GREEN)
            draw_buf_circle(24, 24, 10, COLOR_CARD_BG)
        elif is_target:
            draw_buf_circle(24, 24, 10, COLOR_GOOGLE_YELLOW)
            draw_buf_circle(24, 24, 6, COLOR_CARD_BG)
        else:
            draw_buf_circle(24, 24, 4, COLOR_TEXT_MUTED)
    elif val == 1: # RED
        border_c = COLOR_WHITE if is_sel else (COLOR_BEST_GREEN if is_best_from else rgb565(180, 40, 30))
        draw_buf_circle(24, 24, 20, border_c)
        draw_buf_circle(24, 24, 16, COLOR_GOOGLE_RED)
        draw_buf_circle(20, 20, 5, rgb565(255, 140, 130))
    elif val == 2: # BLUE
        border_c = COLOR_WHITE if is_sel else (COLOR_BEST_GREEN if is_best_from else rgb565(20, 80, 180))
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


def init_alq_solver_ui(tft, game):
    tft.fill_rect(0, 0, 320, 480, COLOR_DARK_BG)
    draw_header_bar(tft, "ALQ SOLVER")

    role_str = "YOU: RED" if game.user_side == 1 else "YOU: BLUE"
    role_col = COLOR_GOOGLE_RED if game.user_side == 1 else COLOR_GOOGLE_BLUE
    draw_button(tft, 8, 56, 95, 32, role_str, COLOR_CARD_BG, role_col, scale=1)

    var_str = "FULL DIAG" if game.variant == "FULL" else "ORTHO"
    draw_button(tft, 110, 56, 100, 32, var_str, COLOR_CARD_BG, COLOR_GOOGLE_YELLOW, scale=1)

    edit_str = "EDIT: ON" if game.edit_mode else "EDIT: OFF"
    edit_col = COLOR_GOOGLE_GREEN if game.edit_mode else COLOR_TEXT_MUTED
    draw_button(tft, 217, 56, 95, 32, edit_str, COLOR_CARD_BG, edit_col, scale=1)

    # 5x5 Board Background Container
    tft.fill_rect(14, 94, 292, 292, COLOR_CARD_BG)
    tft.fill_rect(14, 94, 292, 2, COLOR_WHITE)
    tft.fill_rect(14, 94, 2, 292, COLOR_WHITE)
    tft.fill_rect(304, 94, 2, 292, rgb565(100, 116, 139))
    tft.fill_rect(14, 384, 292, 2, rgb565(100, 116, 139))

    # Draw Orthogonal Grid Lines
    for r in range(5):
        cy = 110 + r * 68
        tft.fill_rect(30, cy - 1, 260, 3, COLOR_TEXT_MUTED)

    for c in range(5):
        cx = 30 + c * 65
        tft.fill_rect(cx - 1, 110, 3, 272, COLOR_TEXT_MUTED)

    # Draw Full Diagonal Grid Lines for FULL variant
    if game.variant == "FULL":
        for r in range(5):
            for c in range(5):
                if (r + c) % 2 == 0:
                    cx1 = 30 + c * 65
                    cy1 = 110 + r * 68
                    for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                        r2, c2 = r + dr, c + dc
                        if 0 <= r2 < 5 and 0 <= c2 < 5:
                            cx2 = 30 + c2 * 65
                            cy2 = 110 + r2 * 68
                            if (r < r2) or (r == r2 and c < c2):
                                draw_thick_line_diag(tft, cx1, cy1, cx2, cy2, 2, COLOR_TEXT_MUTED)

    # Bottom Status & Tactical Analyzer Banner Area
    tft.fill_rect(10, 396, 300, 75, COLOR_CARD_BG)

    game.prev_grid = [[-1] * 5 for _ in range(5)]
    game.prev_selected = (-1, -1)
    game.prev_targets = []
    game.prev_best_from = (-1, -1)
    game.prev_best_to = (-1, -1)
    game.prev_status_msg = ""
    game.prev_eval_score = None
    update_alq_solver_ui(tft, game)


def update_alq_solver_ui(tft, game):
    sel = game.selected if game.selected else (-1, -1)
    prev_sel = game.prev_selected if game.prev_selected else (-1, -1)

    best_from = game.best_move[0] if game.best_move else (-1, -1)
    best_to = game.best_move[1] if game.best_move else (-1, -1)

    prev_bf = getattr(game, 'prev_best_from', (-1, -1))
    prev_bt = getattr(game, 'prev_best_to', (-1, -1))

    for r in range(5):
        for c in range(5):
            val = game.grid[r][c]
            prev_val = game.prev_grid[r][c]
            pos = (r, c)

            is_sel = (pos == sel)
            was_sel = (pos == prev_sel)
            is_target = (pos in game.valid_targets)
            was_target = (pos in game.prev_targets)
            is_bf = (pos == best_from)
            was_bf = (pos == prev_bf)
            is_bt = (pos == best_to)
            was_bt = (pos == prev_bt)

            if val != prev_val or is_sel != was_sel or is_target != was_target or is_bf != was_bf or is_bt != was_bt:
                render_solver_tile(tft, game, r, c, val, is_sel, is_target, is_bf, is_bt)

    for r in range(5):
        for c in range(5):
            game.prev_grid[r][c] = game.grid[r][c]
    game.prev_selected = sel
    game.prev_targets = list(game.valid_targets)
    game.prev_best_from = best_from
    game.prev_best_to = best_to

    if game.status_msg != game.prev_status_msg or game.best_score != game.prev_eval_score:
        game.prev_status_msg = game.status_msg
        game.prev_eval_score = game.best_score
        tft.fill_rect(15, 402, 290, 63, COLOR_CARD_BG)

        p1, p2 = game.count_pieces()
        tft.draw_text("RED: " + str(p1), 20, 408, COLOR_GOOGLE_RED, bg=COLOR_CARD_BG, scale=1)
        tft.draw_text("BLUE: " + str(p2), 105, 408, COLOR_GOOGLE_BLUE, bg=COLOR_CARD_BG, scale=1)

        # Evaluation score text
        if abs(game.best_score) >= 9000:
            eval_str = "MATE WIN" if game.best_score > 0 else "MATE LOSS"
            eval_col = COLOR_GOOGLE_GREEN if game.best_score > 0 else COLOR_GOOGLE_RED
        else:
            eval_pts = game.best_score / 300.0
            sign = "+" if eval_pts > 0 else ""
            eval_str = f"EVAL: {sign}{eval_pts:.1f}"
            eval_col = COLOR_GOOGLE_GREEN if eval_pts > 0 else (COLOR_GOOGLE_RED if eval_pts < 0 else COLOR_TEXT_LIGHT)

        tft.draw_text(eval_str, 195, 408, eval_col, bg=COLOR_CARD_BG, scale=1)

        scale = 2 if len(game.status_msg) <= 14 else 1
        tft.draw_text(game.status_msg, 20, 432, COLOR_BEST_GREEN, bg=COLOR_CARD_BG, scale=scale)

