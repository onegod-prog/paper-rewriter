"""论文AI率降低工具 - 入口文件"""

import sys
import os

# 确保项目根目录在导入路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import tkinter as tk
except ImportError:
    print("错误: 需要 tkinter 支持。请安装 Python 的 tkinter 模块。")
    sys.exit(1)


def main():
    root = tk.Tk()

    # 设置图标 (如果有)
    try:
        if os.name == "nt":  # Windows
            root.iconbitmap(default=None)
    except Exception:
        pass

    # 设置窗口居中
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = (screen_w - 1100) // 2
    y = (screen_h - 720) // 2
    root.geometry(f"1100x720+{x}+{y}")

    # 导入UI并启动
    from ui import PaperRewriterApp
    app = PaperRewriterApp(root)

    root.mainloop()


if __name__ == "__main__":
    main()
