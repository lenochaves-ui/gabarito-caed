[app]
title = Gabarito CAEd
package.name = gabaritokaed
package.domain = br.gov.croata.educacao

source.dir = .
source.include_exts = py,png,jpg,kv,atlas
source.include_patterns = assets/*,utils/*.py

version = 1.0.0

# Dependências
requirements = python3,kivy==2.3.0,opencv,numpy,openpyxl,pillow,pytesseract

# Orientação retrato
orientation = portrait

# Permissões Android necessárias
android.permissions = CAMERA,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,INTERNET

android.api = 33
android.minapi = 26
android.ndk = 25b
android.ndk_api = 21
android.arch = arm64-v8a

# Ícone e splash (opcional — adicione seus arquivos em assets/)
# icon.filename = %(source.dir)s/assets/icon.png
# presplash.filename = %(source.dir)s/assets/presplash.png

android.presplash_color = #1F4E79
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
