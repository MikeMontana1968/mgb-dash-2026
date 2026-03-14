"""
PlatformIO build middleware — exclude ARM/vendor-specific files from LVGL.

LVGL 9.x ships with architecture-specific assembly (ARM Helium, NEON) and
vendor-specific GPU drivers (NXP PXP, Renesas Dave2D, SDL, OpenGLES, VG-Lite)
that fail to compile on Xtensa (ESP32-S3).  This script skips those files.
"""

Import("env")


def skip_non_xtensa_files(env, node):
    path = node.get_path().replace("\\", "/")
    skip_patterns = [
        "/helium/",
        "/neon/",
        "/nxp/",
        "/renesas/",
        "/sdl/",
        "/opengles/",
        "/vg_lite/",
    ]
    for pattern in skip_patterns:
        if pattern in path:
            return None  # skip this file
    return node


env.AddBuildMiddleware(skip_non_xtensa_files)
