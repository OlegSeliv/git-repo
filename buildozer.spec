# Конфигурационные файлы для сборки Android APK

[app]

# (str) Название приложения
title = Contract Manager

# (str) Имя пакета
package.name = contractmanager

# (str) Домен пакета (используется для создания android.manifest)
package.domain = com.yourcompany.contractmanager

# (str) Исходный код приложения (где находится main.py)
source.dir = .

# (str) Основной модуль
source.main = mobile_app.py

# (list) Версия приложения
version = 1.0.0

# (list) Требования для приложения
requirements = python3,kivy,kivymd,requests,pyjnius,android

# (list) Разрешения Android
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,CAMERA

# (str) Адаптивная иконка
#icon.adaptive_foreground = data/icon_fg.png
#icon.adaptive_background = data/icon_bg.png

# (str) Обычная иконка
#icon.filename = data/icon.png

# (str) Заставка
#presplash.filename = data/presplash.png

# (str) Ориентация (portrait, landscape, all)
orientation = portrait

# (bool) Включить AndroidX
android.enable_androidx = True

# (str) Bootstrap (только для P4A)
p4a.bootstrap = sdl2

# (str) Архитектура Android
android.archs = arm64-v8a, armeabi-v7a

[buildozer]

# (int) Уровень журнала (0 = только ошибки, 1 = информация, 2 = отладка)
log_level = 2