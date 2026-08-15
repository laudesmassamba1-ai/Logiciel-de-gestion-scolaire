[app]
title = Gestion Scolaire
package.name = gestionscolaire
package.domain = org.gestionscolaire

source.dir = build_src
source.include_exts = py,png,jpg,kv,atlas,ttf,otf
source.exclude_dirs = build,dist,installers

version = 1.2.0

orientation = portrait
fullscreen = 0

requirements = python3,kivy,sqlite3

android.permissions = INTERNET,ACCESS_NETWORK_STATE

android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.allow_backup = 0
android.icon.filename = %(source.dir)s/app/assets/icon.png
android.presplash.filename = %(source.dir)s/app/assets/presplash.png
android.presplash_color = #047857

[buildozer]
log_level = 2
warn_on_root = 1
