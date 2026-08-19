# main.py - WT32-SC01 Multi-Game Arcade Hub (2-Page Modular MicroPython Version)
import time
import sys
import gc

gc.enable()
gc.collect()

from machine import Pin, SPI, I2C
import st7796s
import ft6336u
from arcade_common import (
    COLOR_DARK_BG, COLOR_HEADER_BG, COLOR_CARD_BG, COLOR_WHITE,
    COLOR_TEXT_LIGHT, COLOR_TEXT_MUTED, COLOR_GOOGLE_BLUE, COLOR_GOOGLE_RED,
    COLOR_GOOGLE_YELLOW, COLOR_GOOGLE_GREEN, rgb565, draw_button, draw_header_bar,
    scoreboard, SwipeDetector, save_game_state, load_game_state
)


def draw_scoreboard_ui(tft):
    tft.fill_rect(0, 0, 320, 480, COLOR_DARK_BG)
    draw_header_bar(tft, "SCOREBOARD", show_restart=False)

    stats = scoreboard.stats

    # Card 1: 2048 & Tic-Tac-Toe
    tft.fill_rect(10, 54, 300, 44, COLOR_CARD_BG)
    tft.draw_text("2048 BEST: " + str(stats["2048_best"]), 18, 59, COLOR_GOOGLE_YELLOW, scale=1)
    ttt_text = "TTT  P1:" + str(stats["ttt_wins"]) + "  AI:" + str(stats["ttt_ai_wins"]) + "  D:" + str(stats["ttt_draws"])
    tft.draw_text(ttt_text, 18, 77, COLOR_WHITE, scale=1)

    # Card 2: Connect 4 & Uno
    tft.fill_rect(10, 104, 300, 44, COLOR_CARD_BG)
    c4_text = "C4  RED:" + str(stats["c4_wins"]) + "  YEL:" + str(stats["c4_ai_wins"]) + "  D:" + str(stats["c4_draws"])
    tft.draw_text(c4_text, 18, 109, COLOR_GOOGLE_RED, scale=1)
    uno_text = "UNO  YOU:" + str(stats["uno_wins"]) + "  AI:" + str(stats["uno_ai_wins"])
    tft.draw_text(uno_text, 18, 127, COLOR_GOOGLE_GREEN, scale=1)

    # Card 3: Checkers & Chess
    tft.fill_rect(10, 154, 300, 44, COLOR_CARD_BG)
    chk_text = "CHECKERS  W:" + str(stats["checkers_wins"]) + "  AI:" + str(stats["checkers_ai_wins"]) + "  D:" + str(stats["checkers_draws"])
    tft.draw_text(chk_text, 18, 159, COLOR_GOOGLE_YELLOW, scale=1)
    chs_text = "CHESS     W:" + str(stats["chess_wins"]) + "  AI:" + str(stats["chess_ai_wins"]) + "  D:" + str(stats["chess_draws"])
    tft.draw_text(chs_text, 18, 177, COLOR_GOOGLE_BLUE, scale=1)

    # Card 4: Alquerque
    tft.fill_rect(10, 204, 300, 44, COLOR_CARD_BG)
    tft.draw_text("ALQUERQUE (ORTHO & FULL)", 18, 209, COLOR_GOOGLE_GREEN, scale=1)
    alq_text = "RED:" + str(stats["alq_wins"]) + "  BLUE:" + str(stats["alq_ai_wins"]) + "  DRAW:" + str(stats["alq_draws"])
    tft.draw_text(alq_text, 18, 227, COLOR_WHITE, scale=1)

    # Card 5: Dots & Boxes (Squares)
    tft.fill_rect(10, 254, 300, 44, COLOR_CARD_BG)
    tft.draw_text("DOTS & BOXES (SQUARES)", 18, 259, COLOR_GOOGLE_BLUE, scale=1)
    dots_text = "P1:" + str(stats.get("dots_wins", 0)) + "  AI/P2:" + str(stats.get("dots_ai_wins", 0)) + "  D:" + str(stats.get("dots_draws", 0))
    tft.draw_text(dots_text, 18, 277, COLOR_WHITE, scale=1)

    # Card 6: Dots & Triangles
    tft.fill_rect(10, 304, 300, 44, COLOR_CARD_BG)
    tft.draw_text("DOTS & TRIANGLES", 18, 309, COLOR_GOOGLE_YELLOW, scale=1)
    tridots_text = "P1:" + str(stats.get("tridots_wins", 0)) + "  AI/P2:" + str(stats.get("tridots_ai_wins", 0)) + "  D:" + str(stats.get("tridots_draws", 0))
    tft.draw_text(tridots_text, 18, 327, COLOR_WHITE, scale=1)

    # Reset Button
    draw_button(tft, 60, 416, 200, 40, "CLEAR ALL STATS", COLOR_GOOGLE_RED, COLOR_WHITE, scale=1)


def draw_main_menu(tft, page=1):
    """Renders the 2-Page Arcade Hub Main Menu with spacious, high-contrast buttons."""
    tft.fill_rect(0, 0, 320, 480, COLOR_DARK_BG)
    
    # Header Banner
    tft.fill_rect(0, 0, 320, 48, COLOR_HEADER_BG)
    tft.fill_rect(0, 47, 320, 2, COLOR_GOOGLE_BLUE)
    tft.draw_text("WT32 ARCADE HUB", 40, 14, COLOR_WHITE, scale=2)

    if page == 1:
        # Page 1: 6 Classic Games (Height 48px, Step 58px)
        draw_button(tft, 15, 56, 290, 48, "1. 2048 PUZZLE", COLOR_CARD_BG, COLOR_GOOGLE_YELLOW, scale=2)
        draw_button(tft, 15, 114, 290, 48, "2. TIC-TAC-TOE", COLOR_CARD_BG, COLOR_GOOGLE_BLUE, scale=2)
        draw_button(tft, 15, 172, 290, 48, "3. CONNECT 4", COLOR_CARD_BG, COLOR_GOOGLE_RED, scale=2)
        draw_button(tft, 15, 230, 290, 48, "4. UNO CARD GAME", COLOR_CARD_BG, COLOR_GOOGLE_GREEN, scale=2)
        draw_button(tft, 15, 288, 290, 48, "5. CHECKERS / DRAUGHTS", COLOR_CARD_BG, COLOR_GOOGLE_YELLOW, scale=2)
        draw_button(tft, 15, 346, 290, 48, "6. STANDARD CHESS", COLOR_CARD_BG, COLOR_GOOGLE_BLUE, scale=2)

        # Bottom Pagination Bar (y=414..464)
        draw_button(tft, 10, 416, 95, 46, "---", COLOR_HEADER_BG, COLOR_TEXT_MUTED, scale=1)
        draw_button(tft, 112, 416, 95, 46, "PAGE 1 / 2", COLOR_CARD_BG, COLOR_TEXT_LIGHT, scale=1)
        draw_button(tft, 215, 416, 95, 46, "PAGE 2 >", COLOR_GOOGLE_BLUE, COLOR_WHITE, scale=1)

    else:
        # Page 2: 6 Strategy Games, Puzzles & Stats (Height 48px, Step 58px)
        draw_button(tft, 15, 56, 290, 48, "7. ALQUERQUE (ORTHO)", COLOR_CARD_BG, COLOR_GOOGLE_GREEN, scale=2)
        draw_button(tft, 15, 114, 290, 48, "8. ALQUERQUE (FULL DIAG)", COLOR_CARD_BG, COLOR_GOOGLE_YELLOW, scale=2)
        draw_button(tft, 15, 172, 290, 48, "9. DOTS & BOXES", COLOR_CARD_BG, COLOR_GOOGLE_BLUE, scale=2)
        draw_button(tft, 15, 230, 290, 48, "10. DOTS & TRIANGLES", COLOR_CARD_BG, COLOR_GOOGLE_RED, scale=2)
        draw_button(tft, 15, 288, 290, 48, "11. ALQUERQUE SOLVER", COLOR_CARD_BG, COLOR_GOOGLE_YELLOW, scale=2)
        draw_button(tft, 15, 346, 290, 48, "12. SCOREBOARD & STATS", COLOR_HEADER_BG, COLOR_WHITE, scale=2)

        # Bottom Pagination Bar (y=414..464)
        draw_button(tft, 10, 416, 95, 46, "< PAGE 1", COLOR_GOOGLE_BLUE, COLOR_WHITE, scale=1)
        draw_button(tft, 112, 416, 95, 46, "PAGE 2 / 2", COLOR_CARD_BG, COLOR_TEXT_LIGHT, scale=1)
        draw_button(tft, 215, 416, 95, 46, "---", COLOR_HEADER_BG, COLOR_TEXT_MUTED, scale=1)


def unload_active_game_modules():
    for mod_name in ("game_2048", "game_ttt", "game_c4", "game_uno", "game_checkers", "game_chess", "game_alq", "game_alq_full", "game_alq_solver", "game_dots", "game_tri_dots"):
        if mod_name in sys.modules:
            del sys.modules[mod_name]
    gc.collect()


def main():
    gc.collect()
    spi = SPI(2, baudrate=20000000, sck=Pin(14), mosi=Pin(13), miso=Pin(12))
    tft = st7796s.ST7796S(spi, width=320, height=480, reset=22, dc=21, cs=15, backlight=23)

    i2c = I2C(0, sda=Pin(18), scl=Pin(19), freq=400000)
    touch_driver = ft6336u.FT6336U(i2c)
    gesture = SwipeDetector()

    saved = load_game_state()
    current_mode = saved.get("current_mode", "MENU")
    game_data = saved.get("game_data")
    game_obj = None
    menu_page = 1

    def safe_from_dict(obj, data):
        if obj and data:
            try:
                obj.from_dict(data)
            except Exception as err:
                print("Warning: Failed to restore state:", err)

    if current_mode == "2048":
        import game_2048
        game_obj = game_2048.Game2048()
        safe_from_dict(game_obj, game_data)
        game_2048.init_2048_ui(tft, game_obj)
    elif current_mode == "TIC_TAC_TOE":
        import game_ttt
        game_obj = game_ttt.TicTacToe()
        safe_from_dict(game_obj, game_data)
        game_ttt.init_ttt_ui(tft, game_obj)
    elif current_mode == "CONNECT4":
        import game_c4
        game_obj = game_c4.Connect4()
        safe_from_dict(game_obj, game_data)
        game_c4.init_c4_ui(tft, game_obj)
    elif current_mode == "UNO":
        import game_uno
        game_obj = game_uno.UnoGame()
        safe_from_dict(game_obj, game_data)
        game_uno.init_uno_ui(tft, game_obj)
    elif current_mode == "CHECKERS":
        import game_checkers
        game_obj = game_checkers.CheckersGame()
        safe_from_dict(game_obj, game_data)
        game_checkers.init_checkers_ui(tft, game_obj)
    elif current_mode == "CHESS":
        import game_chess
        game_obj = game_chess.ChessGame()
        safe_from_dict(game_obj, game_data)
        game_chess.init_chess_ui(tft, game_obj)
    elif current_mode == "ALQUERQUE":
        import game_alq
        game_obj = game_alq.AlquerqueGame()
        safe_from_dict(game_obj, game_data)
        game_alq.init_alq_ui(tft, game_obj)
    elif current_mode == "ALQUERQUE_FULL":
        import game_alq_full
        game_obj = game_alq_full.AlquerqueFullGame()
        safe_from_dict(game_obj, game_data)
        game_alq_full.init_alq_full_ui(tft, game_obj)
    elif current_mode == "DOTS_BOXES":
        import game_dots
        game_obj = game_dots.DotsAndBoxes()
        safe_from_dict(game_obj, game_data)
        game_dots.init_dots_ui(tft, game_obj)
    elif current_mode == "TRI_DOTS":
        import game_tri_dots
        game_obj = game_tri_dots.DotsAndTriangles()
        safe_from_dict(game_obj, game_data)
        game_tri_dots.init_tridots_ui(tft, game_obj)
    elif current_mode == "ALQ_SOLVER":
        import game_alq_solver
        game_obj = game_alq_solver.AlquerqueSolver()
        safe_from_dict(game_obj, game_data)
        game_alq_solver.init_alq_solver_ui(tft, game_obj)
    elif current_mode == "SCOREBOARD":
        draw_scoreboard_ui(tft)
    else:
        current_mode = "MENU"
        draw_main_menu(tft, menu_page)

    gc.collect()
    print("WT32-SC01 Arcade Hub Ready!")

    while True:
        touches, x, y = touch_driver.read_touch()
        action = gesture.update(touches, x, y)

        if action:
            if isinstance(action, tuple) and action[0] == "TAP":
                tx, ty = action[1], action[2]
                
                # Global Header Controls (Menu & Reset)
                if current_mode != "MENU" and ty <= 50:
                    if tx <= 85:
                        current_mode = "MENU"
                        game_obj = None
                        unload_active_game_modules()
                        save_game_state("MENU", None)
                        draw_main_menu(tft, menu_page)
                        continue
                    elif tx >= 230:
                        if current_mode == "2048" and game_obj:
                            import game_2048
                            game_obj.reset()
                            game_2048.init_2048_ui(tft, game_obj)
                        elif current_mode == "TIC_TAC_TOE" and game_obj:
                            import game_ttt
                            game_obj.reset()
                            game_ttt.init_ttt_ui(tft, game_obj)
                        elif current_mode == "CONNECT4" and game_obj:
                            import game_c4
                            game_obj.reset()
                            game_c4.init_c4_ui(tft, game_obj)
                        elif current_mode == "UNO" and game_obj:
                            import game_uno
                            game_obj.reset()
                            game_uno.init_uno_ui(tft, game_obj)
                        elif current_mode == "CHECKERS" and game_obj:
                            import game_checkers
                            game_obj.reset()
                            game_checkers.init_checkers_ui(tft, game_obj)
                        elif current_mode == "CHESS" and game_obj:
                            import game_chess
                            game_obj.reset()
                            game_chess.init_chess_ui(tft, game_obj)
                        elif current_mode == "ALQUERQUE" and game_obj:
                            import game_alq
                            game_obj.reset()
                            game_alq.init_alq_ui(tft, game_obj)
                        elif current_mode == "ALQUERQUE_FULL" and game_obj:
                            import game_alq_full
                            game_obj.reset()
                            game_alq_full.init_alq_full_ui(tft, game_obj)
                        elif current_mode == "DOTS_BOXES" and game_obj:
                            import game_dots
                            game_obj.reset()
                            game_dots.init_dots_ui(tft, game_obj)
                        elif current_mode == "TRI_DOTS" and game_obj:
                            import game_tri_dots
                            game_obj.reset()
                            game_tri_dots.init_tridots_ui(tft, game_obj)
                        elif current_mode == "ALQ_SOLVER" and game_obj:
                            import game_alq_solver
                            game_obj.reset()
                            game_alq_solver.init_alq_solver_ui(tft, game_obj)
                        elif current_mode == "SCOREBOARD":
                            scoreboard.reset_stats()
                            draw_scoreboard_ui(tft)
                        save_game_state(current_mode, game_obj)
                        continue

            # =========================================================
            # MENU MODE (2 Pages with Swipe & Button Navigation)
            # =========================================================
            if current_mode == "MENU":
                # Swipe gesture navigation between pages
                if isinstance(action, str):
                    if action == "LEFT" and menu_page == 1:
                        menu_page = 2
                        gc.collect()
                        draw_main_menu(tft, menu_page)
                        continue
                    elif action == "RIGHT" and menu_page == 2:
                        menu_page = 1
                        gc.collect()
                        draw_main_menu(tft, menu_page)
                        continue

                # Tap event handling
                if isinstance(action, tuple) and action[0] == "TAP":
                    tx, ty = action[1], action[2]
                    
                    # Bottom Pagination Bar (y >= 405)
                    if ty >= 405:
                        if tx <= 120 and menu_page == 2:
                            menu_page = 1
                            gc.collect()
                            draw_main_menu(tft, menu_page)
                        elif tx >= 200 and menu_page == 1:
                            menu_page = 2
                            gc.collect()
                            draw_main_menu(tft, menu_page)
                        continue

                    # Page 1 Menu Taps (6 Games - Continuous Seamless Hitboxes)
                    if menu_page == 1:
                        if 50 <= ty < 110:
                            current_mode = "2048"
                            unload_active_game_modules()
                            import game_2048
                            game_obj = game_2048.Game2048()
                            game_2048.init_2048_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                        elif 110 <= ty < 168:
                            current_mode = "TIC_TAC_TOE"
                            unload_active_game_modules()
                            import game_ttt
                            game_obj = game_ttt.TicTacToe()
                            game_ttt.init_ttt_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                        elif 168 <= ty < 226:
                            current_mode = "CONNECT4"
                            unload_active_game_modules()
                            import game_c4
                            game_obj = game_c4.Connect4()
                            game_c4.init_c4_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                        elif 226 <= ty < 284:
                            current_mode = "UNO"
                            unload_active_game_modules()
                            import game_uno
                            game_obj = game_uno.UnoGame()
                            game_uno.init_uno_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                        elif 284 <= ty < 342:
                            current_mode = "CHECKERS"
                            unload_active_game_modules()
                            import game_checkers
                            game_obj = game_checkers.CheckersGame()
                            game_checkers.init_checkers_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                        elif 342 <= ty < 405:
                            current_mode = "CHESS"
                            unload_active_game_modules()
                            import game_chess
                            game_obj = game_chess.ChessGame()
                            game_chess.init_chess_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)

                    # Page 2 Menu Taps (Strategy Games, Solver & Stats)
                    elif menu_page == 2:
                        if 50 <= ty < 110:
                            current_mode = "ALQUERQUE"
                            unload_active_game_modules()
                            import game_alq
                            game_obj = game_alq.AlquerqueGame()
                            game_alq.init_alq_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                        elif 110 <= ty < 168:
                            current_mode = "ALQUERQUE_FULL"
                            unload_active_game_modules()
                            import game_alq_full
                            game_obj = game_alq_full.AlquerqueFullGame()
                            game_alq_full.init_alq_full_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                        elif 168 <= ty < 226:
                            current_mode = "DOTS_BOXES"
                            unload_active_game_modules()
                            import game_dots
                            game_obj = game_dots.DotsAndBoxes()
                            game_dots.init_dots_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                        elif 226 <= ty < 284:
                            current_mode = "TRI_DOTS"
                            unload_active_game_modules()
                            import game_tri_dots
                            game_obj = game_tri_dots.DotsAndTriangles()
                            game_tri_dots.init_tridots_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                        elif 284 <= ty < 342:
                            current_mode = "ALQ_SOLVER"
                            unload_active_game_modules()
                            import game_alq_solver
                            game_obj = game_alq_solver.AlquerqueSolver()
                            game_alq_solver.init_alq_solver_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                        elif 342 <= ty < 405:
                            current_mode = "SCOREBOARD"
                            unload_active_game_modules()
                            draw_scoreboard_ui(tft)
                            save_game_state(current_mode, None)

            elif current_mode == "SCOREBOARD":
                if isinstance(action, tuple) and action[0] == "TAP":
                    tx, ty = action[1], action[2]
                    if 40 <= tx <= 280 and 400 <= ty <= 470:
                        scoreboard.reset_stats()
                        draw_scoreboard_ui(tft)

            elif current_mode == "2048" and game_obj:
                import game_2048
                if action in ["LEFT", "RIGHT", "UP", "DOWN"]:
                    if game_obj.move(action):
                        game_2048.update_2048_ui(tft, game_obj)
                        save_game_state(current_mode, game_obj)

            elif current_mode == "TIC_TAC_TOE" and game_obj:
                import game_ttt
                if isinstance(action, tuple) and action[0] == "TAP":
                    tx, ty = action[1], action[2]
                    # Subheader Buttons (y: 50..92)
                    if 50 <= ty <= 92:
                        if tx < 160:
                            game_obj.mode = "2P" if game_obj.mode == "VS_AI" else "VS_AI"
                            game_obj.reset()
                            game_ttt.init_ttt_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                            continue
                        else:
                            diffs = ["EASY", "MEDIUM", "HARD"]
                            idx = (diffs.index(game_obj.difficulty) + 1) % 3
                            game_obj.difficulty = diffs[idx]
                            game_ttt.init_ttt_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                            continue
                    # 3x3 Grid (25 <= x <= 295, 95 <= y <= 365) with safe boundary clamping
                    elif not game_obj.game_over and 20 <= tx <= 300 and 90 <= ty <= 375:
                        c = min(2, max(0, (tx - 25) // 90))
                        r = min(2, max(0, (ty - 95) // 90))
                        if 0 <= r < 3 and 0 <= c < 3:
                            if game_obj.play_move(r, c):
                                game_ttt.update_ttt_ui(tft, game_obj)
                                if game_obj.mode == "VS_AI" and not game_obj.game_over:
                                    time.sleep_ms(150)
                                    game_obj.ai_move()
                                    game_ttt.update_ttt_ui(tft, game_obj)
                                save_game_state(current_mode, game_obj)

            elif current_mode == "CONNECT4" and game_obj:
                import game_c4
                if isinstance(action, tuple) and action[0] == "TAP":
                    tx, ty = action[1], action[2]
                    # Subheader Buttons (y: 50..88)
                    if 50 <= ty <= 88:
                        if tx < 160:
                            game_obj.mode = "2P" if game_obj.mode == "VS_AI" else "VS_AI"
                            game_obj.reset()
                            game_c4.init_c4_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                            continue
                        else:
                            diffs = ["EASY", "MEDIUM", "HARD"]
                            idx = (diffs.index(game_obj.difficulty) + 1) % 3
                            game_obj.difficulty = diffs[idx]
                            game_c4.init_c4_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                            continue
                    # 7-Column Drop Target (6 <= x <= 314, 90 <= y <= 380) with full boundary clamping
                    elif not game_obj.game_over and 0 <= tx <= 320 and 88 <= ty <= 380:
                        col = min(6, max(0, (tx - 6) // 44))
                        if 0 <= col < 7:
                            success, target_row, disc_color = game_obj.drop_disc(col)
                            if success:
                                game_c4.animate_c4_drop(tft, col, target_row, disc_color)
                                game_c4.update_c4_ui(tft, game_obj)
                                if game_obj.mode == "VS_AI" and not game_obj.game_over:
                                    time.sleep_ms(200)
                                    game_obj.ai_move()
                                    game_c4.update_c4_ui(tft, game_obj)
                                save_game_state(current_mode, game_obj)

            elif current_mode == "UNO" and game_obj:
                import game_uno
                if isinstance(action, str):
                    if action == "LEFT" and len(game_obj.player_hand) > 10:
                        game_obj.next_page()
                        game_uno.update_uno_ui(tft, game_obj)
                        save_game_state(current_mode, game_obj)
                    elif action == "RIGHT" and len(game_obj.player_hand) > 10:
                        game_obj.prev_page()
                        game_uno.update_uno_ui(tft, game_obj)
                        save_game_state(current_mode, game_obj)

                elif isinstance(action, tuple) and action[0] == "TAP":
                    tx, ty = action[1], action[2]
                    # Wild Color Selection 2x2 Modal Overlay
                    if game_obj.wild_selecting:
                        chosen_color = None
                        if 160 <= ty <= 232:
                            if tx < 160:
                                chosen_color = "RED"
                            else:
                                chosen_color = "BLUE"
                        elif 233 <= ty <= 305:
                            if tx < 160:
                                chosen_color = "GREEN"
                            else:
                                chosen_color = "YELLOW"
                        if chosen_color:
                            game_obj.choose_wild_color(chosen_color)
                            game_uno.update_uno_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                    elif not game_obj.game_over and game_obj.current_player == 0:
                        # Draw Pile (x: 15..105, y: 110..230)
                        if 15 <= tx <= 105 and 110 <= ty <= 230:
                            game_obj.player_draw(0)
                            game_uno.update_uno_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                        # Hand Pagination Bar (x: 195..320, y: 285..328)
                        elif 285 <= ty <= 328 and len(game_obj.player_hand) > 10 and tx >= 195:
                            if tx < 258:
                                game_obj.prev_page()
                            else:
                                game_obj.next_page()
                            game_uno.update_uno_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                        # Hand Card Slots (2 rows of 5 cards: y: 325..475)
                        elif 325 <= ty <= 475 and 0 <= tx <= 320:
                            row = 0 if ty < 398 else 1
                            col = min(4, max(0, (tx - 10) // 61))
                            slot_idx = row * 5 + col
                            card_idx = game_obj.page * 10 + slot_idx
                            p_hand = game_obj.player_hand
                            if 0 <= card_idx < len(p_hand):
                                card = p_hand[card_idx]
                                if game_obj.is_valid_play(card):
                                    game_obj.play_card(0, card_idx)
                                    game_uno.update_uno_ui(tft, game_obj)
                                    save_game_state(current_mode, game_obj)
                                else:
                                    game_obj.status_msg = "CANNOT PLAY THAT CARD!"
                                    game_uno.update_uno_ui(tft, game_obj)
                                    save_game_state(current_mode, game_obj)

            elif current_mode == "CHECKERS" and game_obj:
                import game_checkers
                if isinstance(action, tuple) and action[0] == "TAP":
                    tx, ty = action[1], action[2]
                    # Subheader Buttons (y: 50..88)
                    if 50 <= ty <= 88:
                        if tx < 160:
                            game_obj.mode = "2P" if game_obj.mode == "VS_AI" else "VS_AI"
                            game_obj.reset()
                            game_checkers.init_checkers_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                            continue
                        else:
                            diffs = ["EASY", "MEDIUM", "HARD"]
                            idx = (diffs.index(game_obj.difficulty) + 1) % 3
                            game_obj.difficulty = diffs[idx]
                            game_checkers.init_checkers_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                            continue
                    # 8x8 Grid Cells (0 <= x < 320, 90 <= y < 410)
                    elif not game_obj.game_over and 0 <= tx < 320 and 90 <= ty < 410:
                        c = min(7, max(0, tx // 40))
                        r = min(7, max(0, (ty - 90) // 40))
                        if 0 <= r < 8 and 0 <= c < 8:
                            if game_obj.select_cell(r, c):
                                game_checkers.update_checkers_ui(tft, game_obj)
                                if game_obj.mode == "VS_AI" and game_obj.turn == 'B' and not game_obj.game_over:
                                    time.sleep_ms(200)
                                    game_obj.ai_move()
                                    game_checkers.update_checkers_ui(tft, game_obj)
                                save_game_state(current_mode, game_obj)

            elif current_mode == "CHESS" and game_obj:
                import game_chess
                if isinstance(action, tuple) and action[0] == "TAP":
                    tx, ty = action[1], action[2]
                    # Subheader Buttons (y: 50..88)
                    if 50 <= ty <= 88:
                        if tx < 160:
                            game_obj.mode = "2P" if game_obj.mode == "VS_AI" else "VS_AI"
                            game_obj.reset()
                            game_chess.init_chess_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                            continue
                        else:
                            diffs = ["EASY", "MEDIUM", "HARD"]
                            idx = (diffs.index(game_obj.difficulty) + 1) % 3
                            game_obj.difficulty = diffs[idx]
                            game_chess.init_chess_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                            continue
                    # 8x8 Grid Cells (0 <= x < 320, 90 <= y < 410)
                    elif not game_obj.game_over and 0 <= tx < 320 and 90 <= ty < 410:
                        c = min(7, max(0, tx // 40))
                        r = min(7, max(0, (ty - 90) // 40))
                        if 0 <= r < 8 and 0 <= c < 8:
                            if game_obj.select_cell(r, c):
                                game_chess.update_chess_ui(tft, game_obj)
                                if game_obj.mode == "VS_AI" and game_obj.turn == 'B' and not game_obj.game_over:
                                    time.sleep_ms(200)
                                    game_obj.ai_move()
                                    game_chess.update_chess_ui(tft, game_obj)
                                save_game_state(current_mode, game_obj)

            elif current_mode == "ALQUERQUE" and game_obj:
                import game_alq
                if isinstance(action, tuple) and action[0] == "TAP":
                    tx, ty = action[1], action[2]
                    # Subheader Buttons (y: 50..92)
                    if 50 <= ty <= 92:
                        if tx < 160:
                            game_obj.mode = "2P" if game_obj.mode == "VS_AI" else "VS_AI"
                            game_obj.reset()
                            game_alq.init_alq_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                            continue
                        else:
                            diffs = ["EASY", "MEDIUM", "HARD"]
                            idx = (diffs.index(game_obj.difficulty) + 1) % 3
                            game_obj.difficulty = diffs[idx]
                            game_alq.init_alq_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                            continue
                    # 5x5 Node Grid (radius-based touch test)
                    elif not game_obj.game_over and 94 <= ty <= 400:
                        c = min(4, max(0, round((tx - 30) / 65)))
                        r = min(4, max(0, round((ty - 110) / 68)))
                        node_x = 30 + c * 65
                        node_y = 110 + r * 68
                        if (tx - node_x)**2 + (ty - node_y)**2 <= 30*30:
                            if game_obj.select_cell(r, c):
                                game_alq.update_alq_ui(tft, game_obj)
                                if game_obj.mode == "VS_AI" and game_obj.turn == 2 and not game_obj.game_over:
                                    time.sleep_ms(200)
                                    game_obj.ai_move()
                                    game_alq.update_alq_ui(tft, game_obj)
                                save_game_state(current_mode, game_obj)

            elif current_mode == "ALQUERQUE_FULL" and game_obj:
                import game_alq_full
                if isinstance(action, tuple) and action[0] == "TAP":
                    tx, ty = action[1], action[2]
                    # Subheader Buttons (y: 50..92)
                    if 50 <= ty <= 92:
                        if tx < 160:
                            game_obj.mode = "2P" if game_obj.mode == "VS_AI" else "VS_AI"
                            game_obj.reset()
                            game_alq_full.init_alq_full_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                            continue
                        else:
                            diffs = ["EASY", "MEDIUM", "HARD"]
                            idx = (diffs.index(game_obj.difficulty) + 1) % 3
                            game_obj.difficulty = diffs[idx]
                            game_alq_full.init_alq_full_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                            continue
                    # 5x5 Node Grid (radius-based touch test)
                    elif not game_obj.game_over and 94 <= ty <= 400:
                        c = min(4, max(0, round((tx - 30) / 65)))
                        r = min(4, max(0, round((ty - 110) / 68)))
                        node_x = 30 + c * 65
                        node_y = 110 + r * 68
                        if (tx - node_x)**2 + (ty - node_y)**2 <= 30*30:
                            if game_obj.select_cell(r, c):
                                game_alq_full.update_alq_full_ui(tft, game_obj)
                                if game_obj.mode == "VS_AI" and game_obj.turn == 2 and not game_obj.game_over:
                                    time.sleep_ms(200)
                                    game_obj.ai_move()
                                    game_alq_full.update_alq_full_ui(tft, game_obj)
                                save_game_state(current_mode, game_obj)

            elif current_mode == "DOTS_BOXES" and game_obj:
                import game_dots
                if isinstance(action, tuple) and action[0] == "TAP":
                    tx, ty = action[1], action[2]
                    # Subheader Buttons (y: 50..88)
                    if 50 <= ty <= 88:
                        if tx < 108: # Button 1: Mode (PVP vs AI)
                            game_obj.game_type = "VS_AI" if game_obj.game_type == "PVP" else "PVP"
                            game_obj.reset()
                            game_dots.init_dots_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                            continue
                        elif tx < 214: # Button 2: Player count (PVP) / Difficulty (AI)
                            if game_obj.game_type == "PVP":
                                counts = [2, 3, 4]
                                c_idx = counts.index(game_obj.player_count) if game_obj.player_count in counts else 0
                                game_obj.player_count = counts[(c_idx + 1) % len(counts)]
                            else:
                                diffs = ["EASY", "MEDIUM", "HARD"]
                                d_idx = diffs.index(game_obj.difficulty) if game_obj.difficulty in diffs else 1
                                game_obj.difficulty = diffs[(d_idx + 1) % len(diffs)]
                            game_obj.reset()
                            game_dots.init_dots_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                            continue
                        else: # Button 3: Grid Size
                            sizes = [3, 4, 5, 6]
                            s_idx = sizes.index(game_obj.grid_size) if game_obj.grid_size in sizes else 1
                            game_obj.grid_size = sizes[(s_idx + 1) % len(sizes)]
                            game_obj.reset()
                            game_dots.init_dots_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                            continue
                    # Board touch with nearest dot hit test
                    elif not game_obj.game_over and ty >= 120:
                        dot = game_obj.find_closest_dot(tx, ty)
                        if dot:
                            res = game_obj.handle_dot_tap(dot[0], dot[1])
                            game_dots.update_dots_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)

                            if game_obj.game_type == "VS_AI" and not game_obj.game_over and game_obj.current_player == 1:
                                while game_obj.current_player == 1 and not game_obj.game_over:
                                    time.sleep_ms(250)
                                    game_obj.ai_move()
                                    game_dots.update_dots_ui(tft, game_obj)
                                    save_game_state(current_mode, game_obj)

            elif current_mode == "TRI_DOTS" and game_obj:
                import game_tri_dots
                if isinstance(action, tuple) and action[0] == "TAP":
                    tx, ty = action[1], action[2]
                    # Subheader Buttons (y: 50..88)
                    if 50 <= ty <= 88:
                        if tx < 108: # Button 1: Mode (PVP vs AI)
                            game_obj.game_type = "VS_AI" if game_obj.game_type == "PVP" else "PVP"
                            game_obj.reset()
                            game_tri_dots.init_tridots_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                            continue
                        elif tx < 214: # Button 2: Player count (PVP) / Difficulty (AI)
                            if game_obj.game_type == "PVP":
                                counts = [2, 3, 4]
                                c_idx = counts.index(game_obj.player_count) if game_obj.player_count in counts else 0
                                game_obj.player_count = counts[(c_idx + 1) % len(counts)]
                            else:
                                diffs = ["EASY", "MEDIUM", "HARD"]
                                d_idx = diffs.index(game_obj.difficulty) if game_obj.difficulty in diffs else 1
                                game_obj.difficulty = diffs[(d_idx + 1) % len(diffs)]
                            game_obj.reset()
                            game_tri_dots.init_tridots_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                            continue
                        else: # Button 3: Grid Size (3, 4, 5)
                            sizes = [3, 4, 5]
                            s_idx = sizes.index(game_obj.grid_size) if game_obj.grid_size in sizes else 1
                            game_obj.grid_size = sizes[(s_idx + 1) % len(sizes)]
                            game_obj.reset()
                            game_tri_dots.init_tridots_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)
                            continue
                    # Board touch with nearest dot hit test
                    elif not game_obj.game_over and ty >= 120:
                        dot = game_obj.find_closest_dot(tx, ty)
                        if dot:
                            res = game_obj.handle_dot_tap(dot[0], dot[1])
                            game_tri_dots.update_tridots_ui(tft, game_obj)
                            save_game_state(current_mode, game_obj)

                            if game_obj.game_type == "VS_AI" and not game_obj.game_over and game_obj.current_player == 1:
                                while game_obj.current_player == 1 and not game_obj.game_over:
                                    time.sleep_ms(250)
                                    ai_move_res = game_obj.ai_move()
                                    game_tri_dots.update_tridots_ui(tft, game_obj)
                                    save_game_state(current_mode, game_obj)
                                    if not ai_move_res:
                                        break

            elif current_mode == "ALQ_SOLVER" and game_obj:
                import game_alq_solver
                if isinstance(action, tuple) and action[0] == "TAP":
                    tx, ty = action[1], action[2]
                    # Subheader Buttons (y: 50..92)
                    if 50 <= ty <= 92:
                        if tx < 107:
                            game_obj.user_side = 3 - game_obj.user_side
                            game_obj.analyze_position()
                            game_alq_solver.init_alq_solver_ui(tft, game_obj)
                        elif tx < 214:
                            game_obj.variant = "ORTHO" if game_obj.variant == "FULL" else "FULL"
                            game_obj.reset()
                            game_alq_solver.init_alq_solver_ui(tft, game_obj)
                        else:
                            game_obj.edit_mode = not game_obj.edit_mode
                            game_alq_solver.init_alq_solver_ui(tft, game_obj)
                        save_game_state(current_mode, game_obj)
                        continue
                    # 5x5 Board Nodes (radius-based touch test)
                    elif 94 <= ty <= 400:
                        c = min(4, max(0, round((tx - 30) / 65)))
                        r = min(4, max(0, round((ty - 110) / 68)))
                        node_x = 30 + c * 65
                        node_y = 110 + r * 68
                        if (tx - node_x)**2 + (ty - node_y)**2 <= 30*30:
                            if game_obj.select_cell(r, c):
                                game_alq_solver.update_alq_solver_ui(tft, game_obj)
                                save_game_state(current_mode, game_obj)

        if current_mode == "UNO" and game_obj and not game_obj.game_over and game_obj.current_player != 0 and not game_obj.wild_selecting:
            import game_uno
            time.sleep_ms(350)
            game_obj.ai_turn()
            game_uno.update_uno_ui(tft, game_obj)
            save_game_state(current_mode, game_obj)

        time.sleep_ms(15)

if __name__ == "__main__":
    main()
