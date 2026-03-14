/**
 * MGB Dash 2026 — LVGL 9.x Configuration
 *
 * Minimal config for Waveshare ESP32-S3-LCD-1.85 (360x360 round LCD).
 * Only overrides differ from LVGL defaults.
 */

#ifndef LV_CONF_H
#define LV_CONF_H

#include <stdint.h>

// ── Color depth ────────────────────────────────────────────────────────
#define LV_COLOR_DEPTH 16

// ── Memory ─────────────────────────────────────────────────────────────
// Use stdlib malloc (backed by PSRAM when available via menuconfig)
#define LV_USE_STDLIB_MALLOC    LV_STDLIB_CLIB
#define LV_USE_STDLIB_STRING    LV_STDLIB_CLIB
#define LV_USE_STDLIB_SPRINTF   LV_STDLIB_CLIB

// Size of the memory used by lv_malloc() in bytes (>= 2kB)
#define LV_MEM_SIZE (128 * 1024)

// ── Display ────────────────────────────────────────────────────────────
#define LV_DPI_DEF 160

// ── Tick ───────────────────────────────────────────────────────────────
// Set via lv_tick_set_cb() at runtime — no defines needed for LVGL 9

// ── Drawing ────────────────────────────────────────────────────────────
#define LV_DRAW_BUF_STRIDE_ALIGN    1
#define LV_DRAW_BUF_ALIGN           4

// Disable ARM-specific assembly (Xtensa target)
#define LV_USE_DRAW_SW_ASM          LV_DRAW_SW_ASM_NONE

// ── Logging ────────────────────────────────────────────────────────────
#define LV_USE_LOG      1
#define LV_LOG_LEVEL    LV_LOG_LEVEL_WARN
#define LV_LOG_PRINTF   1

// ── Fonts (built-in Montserrat) ────────────────────────────────────────
#define LV_FONT_MONTSERRAT_14  1
#define LV_FONT_MONTSERRAT_20  1
#define LV_FONT_MONTSERRAT_28  1
#define LV_FONT_MONTSERRAT_36  1
#define LV_FONT_MONTSERRAT_48  1
#define LV_FONT_DEFAULT        &lv_font_montserrat_14

// ── FreeType (for custom TTF fonts) ────────────────────────────────────
// Enable when TTF fonts are loaded from LittleFS.
// Requires: lv_fs driver registration + LittleFS mount.
#define LV_USE_FREETYPE             0   // set to 1 when TTF pipeline is ready
#define LV_FREETYPE_CACHE_SIZE      (64 * 1024)

// ── Widgets ────────────────────────────────────────────────────────────
#define LV_USE_CANVAS   1
#define LV_USE_LABEL    1
#define LV_USE_ARC      1
#define LV_USE_LINE     1
#define LV_USE_IMG      1

#endif // LV_CONF_H
