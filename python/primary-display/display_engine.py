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
        # Platform-specific SDL setup
        headless = sys.platform != "win32" and not os.environ.get("DISPLAY")
        if headless:
            os.environ["SDL_VIDEODRIVER"] = "kmsdrm"

        pygame.init()

        flags = 0
        if headless:
            flags = pygame.FULLSCREEN

        try:
            screen = pygame.display.set_mode((self._width, self._height), flags)
        except pygame.error as e:
            if headless:
                logger.warning("Display init failed (%s), falling back to dummy driver", e)
                pygame.quit()
                os.environ["SDL_VIDEODRIVER"] = "dummy"
                pygame.init()
                screen = pygame.display.set_mode((self._width, self._height))
            else:
                raise
        stamp = datetime.now().strftime("%a-%d %H:%M")
        pygame.display.set_caption(f"MGB Dash 2026 — {stamp}")
        clock = pygame.time.Clock()

        self._running = True
        self._screen = screen

        # SIGUSR1 → save screenshot (Linux only)
        if hasattr(signal, "SIGUSR1"):
            def _screenshot_handler(signum, frame):
                path = "/tmp/mgb-screenshot.png"
                try:
                    pygame.image.save(self._screen, path)
                    logger.info("Screenshot saved to %s", path)
                except Exception as exc:
                    logger.error("Screenshot failed: %s", exc)
            signal.signal(signal.SIGUSR1, _screenshot_handler)

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
