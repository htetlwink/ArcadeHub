# game_uno.py - Uno Card Game Engine & Renderer (4 Players)
import random
import gc
from arcade_common import (
    COLOR_DARK_BG, COLOR_HEADER_BG, COLOR_CARD_BG, COLOR_WHITE,
    COLOR_TEXT_MUTED, COLOR_GOOGLE_BLUE, COLOR_GOOGLE_RED,
    COLOR_GOOGLE_YELLOW, COLOR_GOOGLE_GREEN, draw_button, draw_header_bar,
    scoreboard
)

UNO_COLOR_MAP = {
    "RED": COLOR_GOOGLE_RED,
    "BLUE": COLOR_GOOGLE_BLUE,
    "GREEN": COLOR_GOOGLE_GREEN,
    "YELLOW": COLOR_GOOGLE_YELLOW,
    "WILD": COLOR_HEADER_BG,
}

class UnoGame:
    def __init__(self):
        self.players = ["YOU", "AI 1", "AI 2", "AI 3"]
        self.deck = []
        self.discard_pile = []
        self.hands = [[], [], [], []] # 0: YOU, 1: AI 1, 2: AI 2, 3: AI 3
        self.active_color = "RED"
        self.current_player = 0 # 0, 1, 2, 3
        self.direction = 1 # 1: clockwise, -1: counter-clockwise
        self.status_msg = ""
        self.game_over = False
        self.winner = None
        self.wild_selecting = False
        self.pending_wild_action = None
        self.recorded = False
        self.page = 0
        self.clear_render_cache()
        self.reset()

    def clear_render_cache(self):
        self.prev_h0_len = -1
        self.prev_h1_len = -1
        self.prev_h2_len = -1
        self.prev_h3_len = -1
        self.prev_current_player = -1
        self.prev_direction = 0
        self.prev_discard_top = None
        self.prev_active_color = None
        self.prev_status_msg = None
        self.prev_hand_cards = [None] * 10
        self.prev_hand_valid = [False] * 10
        self.prev_rendered_page = -1
        self.prev_hand_len = -1
        self.prev_wild_selecting = None
        self.prev_game_over = None

    def reset(self):
        colors = ["RED", "BLUE", "GREEN", "YELLOW"]
        values = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "+2", "SKIP", "REVERSE"]
        self.deck = []
        for c in colors:
            for v in values:
                self.deck.append((c, v))
                if v != "0":
                    self.deck.append((c, v))
        for _ in range(4):
            self.deck.append(("WILD", "WILD"))
            self.deck.append(("WILD", "+4"))
        
        for i in range(len(self.deck) - 1, 0, -1):
            j = random.randint(0, i)
            self.deck[i], self.deck[j] = self.deck[j], self.deck[i]

        self.hands = [[self.deck.pop() for _ in range(7)] for _ in range(4)]
        
        top = self.deck.pop()
        while top[0] == "WILD":
            self.deck.insert(0, top)
            top = self.deck.pop()
            
        self.discard_pile = [top]
        self.active_color = top[0]
        self.current_player = 0
        self.direction = 1
        self.status_msg = "YOUR TURN - TAP A CARD"
        self.game_over = False
        self.winner = None
        self.wild_selecting = False
        self.pending_wild_action = None
        self.recorded = False
        self.page = 0
        self.clear_render_cache()
        gc.collect()

    def to_dict(self):
        return {
            "deck": self.deck,
            "discard_pile": self.discard_pile,
            "hands": self.hands,
            "active_color": self.active_color,
            "current_player": self.current_player,
            "direction": self.direction,
            "status_msg": self.status_msg,
            "game_over": self.game_over,
            "winner": self.winner,
            "wild_selecting": self.wild_selecting,
            "pending_wild_action": self.pending_wild_action,
            "recorded": self.recorded,
            "page": self.page
        }

    def from_dict(self, data):
        if not data: return
        if "deck" in data:
            self.deck = [tuple(c) if isinstance(c, list) else c for c in data["deck"]]
        if "discard_pile" in data:
            self.discard_pile = [tuple(c) if isinstance(c, list) else c for c in data["discard_pile"]]
        if "hands" in data:
            self.hands = [[tuple(c) if isinstance(c, list) else c for c in h] for h in data["hands"]]
        self.active_color = data.get("active_color", self.active_color)
        self.current_player = data.get("current_player", self.current_player)
        self.direction = data.get("direction", self.direction)
        self.status_msg = data.get("status_msg", self.status_msg)
        self.game_over = data.get("game_over", self.game_over)
        self.winner = data.get("winner", self.winner)
        self.wild_selecting = data.get("wild_selecting", self.wild_selecting)
        self.pending_wild_action = data.get("pending_wild_action", self.pending_wild_action)
        self.recorded = data.get("recorded", self.recorded)
        self.page = data.get("page", self.page)
        self.clamp_page()
        self.clear_render_cache()

    @property
    def player_hand(self):
        return self.hands[0]

    @property
    def total_pages(self):
        return max(1, (len(self.hands[0]) + 9) // 10)

    def next_page(self):
        self.page = (self.page + 1) % self.total_pages

    def prev_page(self):
        self.page = (self.page - 1 + self.total_pages) % self.total_pages

    def clamp_page(self):
        tp = self.total_pages
        if self.page >= tp:
            self.page = tp - 1
        if self.page < 0:
            self.page = 0

    def is_valid_play(self, card):
        if not self.discard_pile:
            return True
        top_c, top_v = self.discard_pile[-1]
        c, v = card
        if c == "WILD":
            return True
        if c == self.active_color:
            return True
        if top_c != "WILD" and v == top_v:
            return True
        return False

    def next_player_idx(self, steps=1):
        return (self.current_player + steps * self.direction) % 4

    def advance_turn(self, steps=1):
        self.current_player = self.next_player_idx(steps)

    def choose_wild_color(self, color_name):
        if not self.wild_selecting or self.game_over:
            return False
        if color_name not in ("RED", "BLUE", "GREEN", "YELLOW"):
            return False
        self.active_color = color_name
        self.wild_selecting = False
        action = self.pending_wild_action
        self.pending_wild_action = None

        if action == "+4":
            target_idx = self.next_player_idx(1)
            for _ in range(4):
                self.draw_card(target_idx)
            self.status_msg = "YOU PLAYED +4! COLOR: " + color_name
            self.advance_turn(2)
        else:
            self.status_msg = "YOU PLAYED WILD! COLOR: " + color_name
            self.advance_turn(1)
        gc.collect()
        return True

    def play_card(self, p_idx, card_idx):
        if not (0 <= card_idx < len(self.hands[p_idx])):
            return False
        card = self.hands[p_idx][card_idx]
        if not self.is_valid_play(card):
            return False

        card = self.hands[p_idx].pop(card_idx)
        self.discard_pile.append(card)
        c, v = card
        p_name = self.players[p_idx]
        if p_idx == 0:
            self.clamp_page()

        if len(self.hands[p_idx]) == 0:
            self.game_over = True
            self.winner = p_name
            self.status_msg = "YOU WIN UNO!" if p_idx == 0 else (p_name + " WINS UNO!")
            self.wild_selecting = False
            self.pending_wild_action = None
            if not self.recorded:
                self.recorded = True
                scoreboard.record_uno("PLAYER" if p_idx == 0 else "AI")
            return True

        if c != "WILD":
            self.active_color = c

        if v == "+2":
            target_idx = self.next_player_idx(1)
            for _ in range(2):
                self.draw_card(target_idx)
            self.status_msg = p_name + " PLAYED +2! " + self.players[target_idx] + " +2 & SKIPPED"
            self.advance_turn(2)
            return True
        elif v == "SKIP":
            target_idx = self.next_player_idx(1)
            self.status_msg = p_name + " PLAYED SKIP! " + self.players[target_idx] + " SKIPPED"
            self.advance_turn(2)
            return True
        elif v == "REVERSE":
            self.direction *= -1
            self.status_msg = p_name + " PLAYED REVERSE!"
            self.advance_turn(1)
            return True
        elif v == "+4":
            if p_idx == 0:
                self.wild_selecting = True
                self.pending_wild_action = "+4"
                self.status_msg = "SELECT COLOR FOR +4!"
            else:
                best_color = self._best_ai_color(p_idx)
                self.active_color = best_color
                target_idx = self.next_player_idx(1)
                for _ in range(4):
                    self.draw_card(target_idx)
                self.status_msg = p_name + " PLAYED +4! COLOR: " + best_color
                self.advance_turn(2)
            return True
        elif c == "WILD":
            if p_idx == 0:
                self.wild_selecting = True
                self.pending_wild_action = "WILD"
                self.status_msg = "SELECT WILD COLOR!"
            else:
                best_color = self._best_ai_color(p_idx)
                self.active_color = best_color
                self.status_msg = p_name + " PLAYED WILD! COLOR: " + best_color
                self.advance_turn(1)
            return True

        self.status_msg = p_name + " PLAYED " + c + " " + v
        self.advance_turn(1)
        gc.collect()
        return True

    def _best_ai_color(self, p_idx):
        counts = {"RED": 0, "BLUE": 0, "GREEN": 0, "YELLOW": 0}
        for card in self.hands[p_idx]:
            if card[0] in counts:
                counts[card[0]] += 1
        best = "RED"
        max_c = -1
        for k in ["RED", "BLUE", "GREEN", "YELLOW"]:
            if counts[k] > max_c:
                max_c = counts[k]
                best = k
        return best

    def draw_card(self, p_idx):
        if not self.deck and len(self.discard_pile) > 1:
            top = self.discard_pile.pop()
            self.deck = self.discard_pile[:]
            self.discard_pile = [top]
            for i in range(len(self.deck) - 1, 0, -1):
                j = random.randint(0, i)
                self.deck[i], self.deck[j] = self.deck[j], self.deck[i]

        if self.deck:
            card = self.deck.pop()
            self.hands[p_idx].append(card)
            if p_idx == 0:
                self.clamp_page()
            return card
        return None

    def player_draw(self, p_idx=0):
        drawn = self.draw_card(p_idx)
        p_name = self.players[p_idx]
        if drawn:
            if self.is_valid_play(drawn):
                self.status_msg = p_name + " DREW " + (drawn[0] if drawn[0] != "WILD" else "") + " " + drawn[1]
            else:
                self.status_msg = p_name + " DREW (NO PLAY)"
                self.advance_turn(1)
            return drawn
        else:
            self.status_msg = "NO CARDS TO DRAW - PASS"
            self.advance_turn(1)
            return None

    def ai_turn(self):
        if self.game_over or self.current_player == 0 or self.wild_selecting:
            return

        p_idx = self.current_player
        p_name = self.players[p_idx]
        p_hand = self.hands[p_idx]

        playable = [i for i, card in enumerate(p_hand) if self.is_valid_play(card)]
        if playable:
            idx = playable[0]
            self.play_card(p_idx, idx)
        else:
            drawn = self.draw_card(p_idx)
            if drawn and self.is_valid_play(drawn):
                self.play_card(p_idx, len(p_hand) - 1)
                if not self.game_over and not (self.current_player == 0 and self.wild_selecting):
                    self.status_msg = p_name + " DREW & PLAYED " + (drawn[0] if drawn[0] != "WILD" else "") + " " + drawn[1]
            else:
                self.status_msg = p_name + " DREW A CARD"
                self.advance_turn(1)
        gc.collect()

    def handle_tap(self, tx, ty):
        if self.wild_selecting:
            if 170 <= ty <= 225:
                if 40 <= tx <= 150:
                    return self.choose_wild_color("RED")
                elif 170 <= tx <= 280:
                    return self.choose_wild_color("BLUE")
            elif 240 <= ty <= 295:
                if 40 <= tx <= 150:
                    return self.choose_wild_color("GREEN")
                elif 170 <= tx <= 280:
                    return self.choose_wild_color("YELLOW")
            if 180 <= ty <= 280:
                for idx, color_name in enumerate(["RED", "BLUE", "YELLOW", "GREEN"]):
                    cx = 20 + idx * 72
                    if cx <= tx <= cx + 64:
                        return self.choose_wild_color(color_name)
            return False

        if self.game_over:
            return False

        if 285 <= ty <= 325 and tx >= 200:
            if self.total_pages > 1:
                if tx >= 260:
                    self.next_page()
                else:
                    self.prev_page()
                return True

        if self.current_player == 0:
            if (20 <= tx <= 95 and 115 <= ty <= 220) or (20 <= tx <= 95 and 210 <= ty <= 300):
                return bool(self.player_draw(0))

            if 330 <= ty <= 465 and 10 <= tx <= 315:
                col = (tx - 10) // 61
                row = (ty - 330) // 70
                if 0 <= col < 5 and 0 <= row < 2:
                    slot_idx = row * 5 + col
                    card_idx = self.page * 10 + slot_idx
                    if 0 <= card_idx < len(self.hands[0]):
                        return self.play_card(0, card_idx)

        return False


def draw_uno_card(tft, x, y, w, h, card, selected=False):
    c, v = card
    bg = UNO_COLOR_MAP.get(c, COLOR_CARD_BG)
    border = COLOR_GOOGLE_YELLOW if selected else COLOR_WHITE
    
    tft.fill_rect(x, y, w, h, border)
    tft.fill_rect(x + 2, y + 2, w - 4, h - 4, bg)
    
    ix, iy = x + 6, y + 8
    iw, ih = w - 12, h - 16
    if iw > 8 and ih > 8:
        tft.fill_rect(ix, iy, iw, ih, COLOR_WHITE)
        scale = 2 if len(v) <= 2 and w >= 45 else 1
        char_w = 6 * scale
        char_h = 8 * scale
        tx = ix + (iw - len(v) * char_w) // 2
        ty = iy + (ih - char_h) // 2
        txt_color = bg if c != "WILD" else COLOR_DARK_BG
        tft.draw_text(v, max(ix + 1, tx), max(iy + 1, ty), txt_color, bg=COLOR_WHITE, scale=scale)


def init_uno_ui(tft, game):
    tft.fill_rect(0, 0, 320, 480, COLOR_DARK_BG)
    draw_header_bar(tft, "UNO (4 PLAYERS)")
    
    tft.fill_rect(10, 55, 300, 235, COLOR_HEADER_BG)
    tft.fill_rect(20, 115, 75, 105, COLOR_CARD_BG)
    tft.draw_text("DRAW", 32, 155, COLOR_WHITE, bg=COLOR_CARD_BG, scale=2)
    
    tft.draw_text("ACTIVE:", 115, 115, COLOR_TEXT_MUTED, bg=COLOR_HEADER_BG, scale=1)
    
    tft.fill_rect(0, 290, 320, 30, COLOR_CARD_BG)
    tft.draw_text("YOUR HAND (TAP CARD)", 35, 298, COLOR_WHITE, bg=COLOR_CARD_BG, scale=1)
    
    game.clear_render_cache()
    update_uno_ui(tft, game, force_redraw=True)


def update_uno_ui(tft, game, force_redraw=False):
    # 1. Top Players status bar (y: 58..110)
    h0 = len(game.hands[0])
    h1 = len(game.hands[1])
    h2 = len(game.hands[2])
    h3 = len(game.hands[3])
    cp = game.current_player
    dr = game.direction

    players_changed = (
        force_redraw or
        h0 != game.prev_h0_len or
        h1 != game.prev_h1_len or
        h2 != game.prev_h2_len or
        h3 != game.prev_h3_len or
        cp != game.prev_current_player or
        dr != game.prev_direction
    )

    if players_changed:
        game.prev_h0_len = h0
        game.prev_h1_len = h1
        game.prev_h2_len = h2
        game.prev_h3_len = h3
        game.prev_current_player = cp
        game.prev_direction = dr

        tft.fill_rect(15, 60, 290, 50, COLOR_CARD_BG)
        dir_symbol = "CW >" if dr == 1 else "< CCW"
        tft.draw_text(dir_symbol, 235, 64, COLOR_GOOGLE_YELLOW, bg=COLOR_CARD_BG, scale=1)

        for idx, p_name in enumerate(game.players):
            cnt = len(game.hands[idx])
            color = COLOR_GOOGLE_GREEN if cp == idx else COLOR_WHITE
            tx = 20 + (idx % 2) * 105
            ty = 64 + (idx // 2) * 22
            tag = p_name[:5] + ":" + str(cnt)
            tft.draw_text(tag, tx, ty, color, bg=COLOR_CARD_BG, scale=1)

    # 2. Discard Pile Top Card
    curr_top = game.discard_pile[-1] if game.discard_pile else None
    if force_redraw or game.prev_discard_top != curr_top:
        game.prev_discard_top = curr_top
        if curr_top:
            draw_uno_card(tft, 115, 130, 75, 100, curr_top)

    # 3. Active Color Indicator
    curr_color = game.active_color
    if force_redraw or game.prev_active_color != curr_color:
        game.prev_active_color = curr_color
        active_c = UNO_COLOR_MAP.get(curr_color, COLOR_WHITE)
        tft.fill_rect(205, 130, 85, 35, active_c)
        tft.draw_text(curr_color[:4], 215, 140, COLOR_WHITE, bg=active_c, scale=1)

    # 4. Status Message
    curr_msg = game.status_msg
    if force_redraw or game.prev_status_msg != curr_msg:
        game.prev_status_msg = curr_msg
        tft.fill_rect(10, 260, 300, 25, COLOR_DARK_BG)
        tft.draw_text(curr_msg, 15, 266, COLOR_GOOGLE_YELLOW, bg=COLOR_DARK_BG, scale=1)

    # 5. User Hand Differential Rendering (10 slots)
    hand = game.player_hand
    page_start = game.page * 10
    hand_len = len(hand)
    page_changed = (game.prev_rendered_page != game.page)

    for i in range(10):
        c_idx = page_start + i
        if c_idx < hand_len:
            card = hand[c_idx]
            is_valid = game.is_valid_play(card) and (game.current_player == 0) and not game.wild_selecting and not game.game_over
        else:
            card = None
            is_valid = False

        if force_redraw or page_changed or card != game.prev_hand_cards[i] or is_valid != game.prev_hand_valid[i]:
            row = i // 5
            col = i % 5
            x = 10 + col * 61
            y = 330 + row * 70
            if card is not None:
                draw_uno_card(tft, x, y, 54, 65, card, selected=is_valid)
            else:
                tft.fill_rect(x - 2, y - 2, 58, 69, COLOR_DARK_BG)
            game.prev_hand_cards[i] = card
            game.prev_hand_valid[i] = is_valid

    game.prev_rendered_page = game.page

    # 6. Pagination Controls
    if force_redraw or page_changed or game.prev_hand_len != hand_len:
        game.prev_hand_len = hand_len
        if hand_len > 10:
            total_pages = (hand_len + 9) // 10
            tft.fill_rect(200, 292, 115, 25, COLOR_HEADER_BG)
            pg_str = "< P" + str(game.page + 1) + "/" + str(total_pages) + " >"
            tft.draw_text(pg_str, 205, 298, COLOR_GOOGLE_YELLOW, bg=COLOR_HEADER_BG, scale=1)
        else:
            tft.fill_rect(200, 292, 115, 25, COLOR_CARD_BG)

    # 7. Wild Color Selection Overlay
    curr_wild = game.wild_selecting
    prev_wild = game.prev_wild_selecting
    if force_redraw or prev_wild != curr_wild:
        game.prev_wild_selecting = curr_wild
        if curr_wild:
            tft.fill_rect(20, 120, 280, 200, COLOR_DARK_BG)
            tft.draw_text("SELECT COLOR:", 75, 135, COLOR_WHITE, bg=COLOR_DARK_BG, scale=2)
            draw_button(tft, 40, 170, 110, 55, "RED", COLOR_GOOGLE_RED, scale=2)
            draw_button(tft, 170, 170, 110, 55, "BLUE", COLOR_GOOGLE_BLUE, scale=2)
            draw_button(tft, 40, 240, 110, 55, "GREEN", COLOR_GOOGLE_GREEN, scale=2)
            draw_button(tft, 170, 240, 110, 55, "YELLOW", COLOR_GOOGLE_YELLOW, scale=2)
        elif prev_wild and not curr_wild:
            tft.fill_rect(10, 55, 300, 235, COLOR_HEADER_BG)
            tft.fill_rect(20, 115, 75, 105, COLOR_CARD_BG)
            tft.draw_text("DRAW", 32, 155, COLOR_WHITE, bg=COLOR_CARD_BG, scale=2)
            tft.draw_text("ACTIVE:", 115, 115, COLOR_TEXT_MUTED, bg=COLOR_HEADER_BG, scale=1)
            tft.fill_rect(0, 290, 320, 30, COLOR_CARD_BG)
            tft.draw_text("YOUR HAND (TAP CARD)", 35, 298, COLOR_WHITE, bg=COLOR_CARD_BG, scale=1)
            game.prev_h0_len = -1
            game.prev_discard_top = None
            game.prev_active_color = None
            game.prev_status_msg = None
            game.prev_hand_len = -1
            update_uno_ui(tft, game, force_redraw=False)

    # 8. Game Over Overlay
    curr_go = game.game_over
    prev_go = game.prev_game_over
    if force_redraw or prev_go != curr_go:
        game.prev_game_over = curr_go
        if curr_go:
            tft.fill_rect(20, 160, 280, 100, COLOR_DARK_BG)
            if game.winner == "YOU":
                tft.draw_text("YOU WIN UNO!", 70, 200, COLOR_GOOGLE_GREEN, bg=COLOR_DARK_BG, scale=2)
            else:
                tft.draw_text(str(game.winner) + " WINS UNO!", 50, 200, COLOR_GOOGLE_RED, bg=COLOR_DARK_BG, scale=2)
            if not game.recorded:
                game.recorded = True
                scoreboard.record_uno("PLAYER" if game.winner == "YOU" else "AI")

