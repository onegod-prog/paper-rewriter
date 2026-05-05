[app]

# 应用信息
title = 论文降重助手
package.name = paperrewriter
package.domain = com.onegod.paperrewriter
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,otf
version = 1.0.0

# 作者
author = onegod

# 需求
requirements = python3,kivy,kivymd,requests,jieba,nltk,urllib3,chardet,certifi,idna

# Android 配置
android.api = 34
android.minapi = 21
android.targetapi = 34
android.sdk = 34
android.ndk = 27
android.gradle_dependencies = 'com.google.android.material:material:1.9.0'
android.permissions = INTERNET
android.archs = arm64-v8a
android.allow_backup = true
android.keep_screen_on = false
android.wakelock = false
android.fullscreen = false
android.window_orientation = portrait
android.accept_sdk_license = true

# 图标 (可选)
#android.icon = icon.png
#android.splash = splash.png
#android.presplash_color = #1a73e8

# 打包配置
p4a.branch = develop
p4a.skip_git_check = true
#p4a.local_recipes = <path-to-recipes>

# iOS (暂不启用)
#ios.codesign.allowed = false

[buildozer]
log_level = 2
warn_on_root = 1

# 构建输出目录
#bin_dir = ./bin
