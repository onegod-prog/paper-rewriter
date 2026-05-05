#!/bin/bash
echo "========================================"
echo "  论文AI率降低工具 v1.0"
echo "========================================"
echo

PYTHON="/c/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"

if [ ! -f "$PYTHON" ]; then
    echo "[错误] 找不到 Python"
    exit 1
fi

"$PYTHON" "$(dirname "$0")/main.py"

if [ $? -ne 0 ]; then
    echo ""
    echo "[错误] 程序启动失败，请确认依赖已安装:"
    echo "  pip install -r requirements.txt"
fi
