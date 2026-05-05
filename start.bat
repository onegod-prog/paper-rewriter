@echo off
chcp 65001 >nul
echo ========================================
echo   论文AI率降低工具 v1.0
echo ========================================
echo.

set PYTHON="C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if not exist %PYTHON% (
    echo [错误] 找不到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

%PYTHON% "%~dp0main.py"

if %errorlevel% neq 0 (
    echo.
    echo [错误] 程序启动失败，请确认依赖已安装:
    echo   pip install -r requirements.txt
    pause
)
