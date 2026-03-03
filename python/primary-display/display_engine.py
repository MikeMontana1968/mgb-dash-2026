"""MGB Dash 2026 — Display engine: pygame window + cairo rendering bridge."""

import os
import sys
import math
import signal
import logging
from datetime import datetime

import cairo
import numpy as np
import pygame

from rendering.cairo_helpers import clip_circle, fill_background
from rendering.colors import BG_BLACK

logger = logging.getLogger("dash")


class DisplayEngine:
    """Main render loop: cairo surface -> pygame display at ~10 fps."""

    def __init__(self, context_manager, state, width=800, height=800,
                 shift_advisor=None):
        self._cm = context_manager
        self._state = state
        self._width = width
        self._height = height
        self._shift_advisor = shift_advisor
        self._running = False

    def run(self):
        import time as _time

        is_linux = sys.platform != "win32"
        headless = is_linux and not os.environ.get("DISPLAY")

        # Platform-specific SDL setup
        if headless:
            os.environ["SDL_VIDEODRIVER"] = "kmsdrm"

        # Fullscreen on Linux: always (kmsdrm needs it, Xwayland needs it for focus)
        flags = pygame.FULLSCREEN | pygame.NOFRAME if is_linux else 0

        # Retry display init — X server may not be ready at boot
        screen = None
        for attempt in range(1, 11):
            try:
                pygame.init()
                # Find the target display index (prefer HDMI over DSI)
                target_display = self._find_hdmi_display() if is_linux else 0
                logger.info("Display init attempt %d (flags=0x%x, display=%d)",
                            attempt, flags, target_display)
                screen = pygame.display.set_mode(
                    (self._width, self._height), flags,
                    display=target_display)
                logger.info("Display opened on driver: %s (display %d)",
                            pygame.display.get_driver(), target_display)
                break
            except pygame.error as e:
                pygame.quit()
                if attempt < 10:
                    logger.warning("Display init attempt %d failed (%s), "
                                   "retrying in 2s...", attempt, e)
                    _time.sleep(2)
                elif is_linux:
                    logger.warning("All display attempts failed, "
                                   "falling back to dummy driver")
                    os.environ["SDL_VIDEODRIVER"] = "dummy"
                    pygame.init()
                    screen = pygame.display.set_mode(
                        (self._width, self._height))
                else:
                    raise
        stamp = datetime.now().strftime("%a-%d %H:%M")
        pygame.display.set_caption(f"MGB Dash 2026 — {stamp}")
        clock = pygame.time.Clock()

        self._running = True
        self._screen = screen

        # SIGUSR1 → save screenshot (Linux only)
        # SIGUSR2 → toggle diagnostics context (Linux only)
        if hasattr(signal, "SIGUSR1"):
            def _screenshot_handler(signum, frame):
                path = "/tmp/mgb-screenshot.png"
                try:
                    pygame.image.save(self._screen, path)
                    logger.info("Screenshot saved to %s", path)
                except Exception as exc:
                    logger.error("Screenshot failed: %s", exc)
            signal.signal(signal.SIGUSR1, _screenshot_handler)

        if hasattr(signal, "SIGUSR2"):
            def _toggle_diag_handler(signum, frame):
                logger.info("SIGUSR2 received — toggling diagnostics")
                self._cm.toggle_diagnostics(self._state)
            signal.signal(signal.SIGUSR2, _toggle_diag_handler)

        logger.info("Display engine started (%dx%d)", self._width, self._height)

        try:
            while self._running:
                # 1. Auto-transition check + shift advisor
                self._cm.evaluate(self._state)
                if self._shift_advisor:
                    self._shift_advisor.evaluate(self._state)

                # 2. Create cairo surface
                surface = cairo.ImageSurface(
                    cairo.FORMAT_ARGB32, self._width, self._height
                )
                ctx = cairo.Context(surface)

                # 3. Circular clip
                clip_circle(ctx, self._width, self._height)

                # 4. Black background
                fill_background(ctx, BG_BLACK)

                # 5. Render active context
                self._cm.active.render(ctx, self._state, self._width, self._height)

                # 6. Cairo ARGB32 (little-endian BGRA) -> pygame RGBA
                buf = surface.get_data()
                arr = np.frombuffer(buf, dtype=np.uint8).reshape(
                    (self._height, self._width, 4)
                ).copy()
                arr[:, :, [0, 2]] = arr[:, :, [2, 0]]  # swap B <-> R
                pg_surface = pygame.image.frombuffer(
                    arr.tobytes(), (self._width, self._height), "RGBA"
                )
                screen.blit(pg_surface, (0, 0))

                # 7. Flip
                pygame.display.flip()

                # 8. Process events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self._running = False
                    elif event.type == pygame.KEYDOWN:
                        self._handle_key(event.key)
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button == 1:  # left click / tap
                            self._handle_touch(event.pos[0], event.pos[1])
                    elif event.type == pygame.MOUSEWHEEL:
                        self._cm.active.on_scroll(event.y)

                clock.tick(10)  # 10 fps cap
        finally:
            pygame.quit()
            logger.info("Display engine stopped")

    @staticmethod
    def _find_hdmi_display():
        """Find the SDL display index for an HDMI output.

        Iterates SDL displays and picks the first non-800x800 display,
        since the DSI panel is 800x800 and we want HDMI.  Falls back to 0.
        """
        try:
            num = pygame.display.get_num_displays()
            logger.info("SDL sees %d display(s)", num)
            for i in range(num):
                try:
                    r = pygame.display.get_desktop_sizes()[i]
                    logger.info("  display %d: %dx%d", i, r[0], r[1])
                    # DSI panel is exactly 800x800 — skip it
                    if r != (800, 800):
                        return i
                except Exception:
                    pass
        except Exception as e:
            logger.warning("Display enumeration failed: %s", e)
        return 0

    def stop(self):
        self._running = False

    def _handle_key(self, key):
        if key == pygame.K_ESCAPE:
            self._running = False
        elif key == pygame.K_d:
            self._cm.toggle_diagnostics(self._state)

    def _handle_touch(self, x, y):
        # Check if tap is inside the circle
        cx, cy = self._width / 2, self._height / 2
        radius = min(self._width, self._height) / 2
        dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        if dist > radius:
            return
        result = self._cm.active.on_touch(x, y)
        if result:
            self._cm.switch_to(result, self._state)
