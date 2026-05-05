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

# 需求 (不锁版本以避免p4a冲突，移除nltk)
requirements = python3,kivy,kivymd,requests,jieba,urllib3,chardet,certifi,idna

# Android 配置
android.api = 34
android.minapi = 21
android.targetapi = 34
android.sdk = 34
android.gradle_dependencies = 'com.google.android.material:material:1.9.0'
android.permissions = INTERNET
android.archs = arm64-v8a
android.allow_backup = true
android.keep_screen_on = false
android.wakelock = false
android.fullscreen = false
android.window_orientation = portrait
android.accept_sdk_license = true
android.google_play_services = false

# 打包配置
p4a.skip_git_check = true
p4a.ignore_requirements = nltk

[buildozer]
log_level = 1
warn_on_root = 1
