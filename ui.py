"""Tkinter GUI界面"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import os
import re

# 尝试导入文档解析库
try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

from rewriter_local import LocalRewriter
from rewriter_api import ApiRewriter
from utils import estimate_ai_probability, format_report


class PaperRewriterApp:
    """论文AI率降低工具 - 主界面"""

    def __init__(self, root):
        self.root = root
        self.root.title("论文AI率降低工具 v1.0")
        self.root.geometry("1200x780")
        self.root.minsize(1000, 680)

        # 设置样式
        self.style = ttk.Style()
        self.style.theme_use("vista" if "vista" in self.style.theme_names() else "clam")

        # 核心引擎
        self.local_rewriter = LocalRewriter()
        self.api_rewriter = ApiRewriter()

        # 状态变量
        self.lang_var = tk.StringVar(value="zh")
        self.intensity_var = tk.StringVar(value="medium")
        self.mode_var = tk.StringVar(value="local")       # local / api
        self.rewrite_mode_var = tk.StringVar(value="full")  # full / selection / report
        self.strategy_vars = {
            "synonym": tk.BooleanVar(value=True),
            "pattern": tk.BooleanVar(value=True),
            "voice": tk.BooleanVar(value=True),
            "connector": tk.BooleanVar(value=True),
        }

        # AI率显示变量
        self.before_score_var = tk.DoubleVar(value=0)
        self.after_score_var = tk.DoubleVar(value=0)

        # 构建界面
        self._build_ui()

        # 自动评估输入区文本
        self._auto_evaluate_timer = None

    def _build_ui(self):
        """构建界面"""
        self._build_toolbar()
        self._build_editor_area()
        self._build_eval_panel()
        self._build_status_bar()

    def _build_toolbar(self):
        """顶部工具栏"""
        toolbar = ttk.Frame(self.root, padding=(10, 8))
        toolbar.pack(fill=tk.X)

        # ---- 第1行: 语言 + 力度 + 引擎 + 降重模式 ----
        row1 = ttk.Frame(toolbar)
        row1.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(row1, text="语言:", width=6).pack(side=tk.LEFT)
        lang_combo = ttk.Combobox(row1, textvariable=self.lang_var, state="readonly",
                                  values=["中文", "English"], width=10)
        lang_combo.pack(side=tk.LEFT, padx=(0, 12))
        lang_combo.bind("<<ComboboxSelected>>", self._on_lang_change)

        ttk.Separator(row1, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)

        ttk.Label(row1, text="改写:", width=5).pack(side=tk.LEFT, padx=(8, 0))
        for value, label in [("light", "轻"), ("medium", "中"), ("heavy", "重")]:
            rb = ttk.Radiobutton(row1, text=label, variable=self.intensity_var, value=value)
            rb.pack(side=tk.LEFT, padx=1)

        ttk.Separator(row1, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)

        ttk.Label(row1, text="引擎:").pack(side=tk.LEFT, padx=(8, 0))
        ttk.Radiobutton(row1, text="本地", variable=self.mode_var, value="local").pack(side=tk.LEFT, padx=1)
        ttk.Radiobutton(row1, text="AI", variable=self.mode_var, value="api").pack(side=tk.LEFT, padx=1)
        ttk.Button(row1, text="API设置", command=self._open_api_settings).pack(side=tk.LEFT, padx=(4, 0))

        ttk.Separator(row1, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        # ---- 降重模式（核心新增） ----
        ttk.Label(row1, text="降重模式:", font=("微软雅黑", 9, "bold")).pack(side=tk.LEFT, padx=(4, 0))
        for value, label in [("full", "全文"), ("selection", "选中"), ("report", "按查重报告")]:
            rb = ttk.Radiobutton(row1, text=label, variable=self.rewrite_mode_var, value=value,
                                 command=self._on_rewrite_mode_change)
            rb.pack(side=tk.LEFT, padx=1)

        # ---- 右边: 醒目改写按钮 ----
        ttk.Separator(row1, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        self.rewrite_btn = ttk.Button(
            row1, text="✏️  开始改写", width=14,
            command=self._start_rewrite
        )
        self.rewrite_btn.pack(side=tk.LEFT, padx=(0, 4))

        # ---- 第2行: 策略复选框 + 字数 ----
        row2 = ttk.Frame(toolbar)
        row2.pack(fill=tk.X)

        ttk.Label(row2, text="改写策略:", width=8).pack(side=tk.LEFT)
        strategy_labels = [
            ("synonym", "同义词替换"),
            ("pattern", "句式重构"),
            ("voice", "语态转换"),
            ("connector", "连接词变换"),
        ]
        for key, label in strategy_labels:
            cb = ttk.Checkbutton(row2, text=label, variable=self.strategy_vars[key])
            cb.pack(side=tk.LEFT, padx=5)

        ttk.Separator(row2, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        self.char_count_label = ttk.Label(row2, text="字数: 0")
        self.char_count_label.pack(side=tk.LEFT, padx=5)

        self.mode_hint_label = ttk.Label(row2, text="", foreground="#1565c0")
        self.mode_hint_label.pack(side=tk.LEFT, padx=10)

    def _build_editor_area(self):
        """中间编辑区 - 左右对照"""
        editor_frame = ttk.Frame(self.root, padding=(10, 0))
        editor_frame.pack(fill=tk.BOTH, expand=True)

        # 左右面板
        left_panel = ttk.Frame(editor_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_panel = ttk.Frame(editor_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # ---- 左侧: 原文 ----
        left_header = ttk.Frame(left_panel)
        left_header.pack(fill=tk.X)

        ttk.Label(left_header, text="📄 原文", font=("微软雅黑", 11, "bold")).pack(side=tk.LEFT)

        btn_frame_left = ttk.Frame(left_header)
        btn_frame_left.pack(side=tk.RIGHT)

        self.btn_upload = ttk.Button(btn_frame_left, text="上传文档", width=8,
                                     command=self._upload_document)
        self.btn_upload.pack(side=tk.LEFT, padx=2)

        self.btn_rewrite_sel = ttk.Button(btn_frame_left, text="改写选中", width=8,
                                          command=self._rewrite_selection)
        self.btn_report = ttk.Button(btn_frame_left, text="导入查重报告", width=10,
                                     command=self._open_plagiarism_dialog)

        ttk.Button(btn_frame_left, text="清空", width=5,
                   command=lambda: self._clear_text(self.input_text)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame_left, text="粘贴", width=5,
                   command=self._paste_text).pack(side=tk.LEFT, padx=2)

        self.input_text = scrolledtext.ScrolledText(
            left_panel, wrap=tk.WORD, font=("微软雅黑", 10),
            padx=8, pady=8, height=18, relief=tk.FLAT, borderwidth=1
        )
        self.input_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        self.input_text.bind("<KeyRelease>", self._on_text_change)
        self.input_text.bind("<<Paste>>", self._on_text_change)

        # ---- 右侧: 改写结果 ----
        right_header = ttk.Frame(right_panel)
        right_header.pack(fill=tk.X)

        ttk.Label(right_header, text="✅ 改写结果", font=("微软雅黑", 11, "bold")).pack(side=tk.LEFT)

        btn_frame_right = ttk.Frame(right_header)
        btn_frame_right.pack(side=tk.RIGHT)
        ttk.Button(btn_frame_right, text="复制", width=5,
                   command=self._copy_result).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame_right, text="保存", width=5,
                   command=self._save_result).pack(side=tk.LEFT, padx=2)

        self.output_text = scrolledtext.ScrolledText(
            right_panel, wrap=tk.WORD, font=("微软雅黑", 10),
            padx=8, pady=8, height=18, relief=tk.FLAT, borderwidth=1,
            state=tk.DISABLED, bg="#f9f9f9"
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # 初始化按钮可见性
        self._on_rewrite_mode_change()

    def _on_rewrite_mode_change(self):
        """降重模式切换——更新按钮和提示"""
        mode = self.rewrite_mode_var.get()

        # 隐藏所有模式专用按钮
        self.btn_rewrite_sel.pack_forget()
        self.btn_report.pack_forget()

        if mode == "selection":
            self.btn_rewrite_sel.pack(side=tk.LEFT, padx=2, before=self.btn_upload)
            self.mode_hint_label.config(text="提示：在原文中选中需要降重的文字，点击「改写选中」")
        elif mode == "report":
            self.btn_report.pack(side=tk.LEFT, padx=2, before=self.btn_upload)
            self.mode_hint_label.config(text="提示：点击「导入查重报告」粘贴重复句子列表")
        else:
            self.mode_hint_label.config(text="")

    def _build_eval_panel(self):
        """AI率评估对比面板"""
        eval_frame = ttk.LabelFrame(
            self.root, text="📊 改写前后 AI 疑似率对比", padding=(10, 6),
        )
        eval_frame.pack(fill=tk.X, padx=10, pady=(8, 2))

        inner = ttk.Frame(eval_frame)
        inner.pack(fill=tk.X, pady=2)

        ttk.Label(inner, text="原文AI率:", font=("微软雅黑", 10)).pack(side=tk.LEFT)

        self.before_bar = ttk.Progressbar(inner, length=180, mode="determinate",
                                          variable=self.before_score_var)
        self.before_bar.pack(side=tk.LEFT, padx=5)

        self.before_label = ttk.Label(inner, text="--", width=6,
                                      font=("微软雅黑", 10, "bold"), foreground="#666")
        self.before_label.pack(side=tk.LEFT)

        ttk.Label(inner, text="  ➡  ", font=("微软雅黑", 14)).pack(side=tk.LEFT, padx=10)

        ttk.Label(inner, text="改写后AI率:", font=("微软雅黑", 10)).pack(side=tk.LEFT)

        self.after_bar = ttk.Progressbar(inner, length=180, mode="determinate",
                                         variable=self.after_score_var)
        self.after_bar.pack(side=tk.LEFT, padx=5)

        self.after_label = ttk.Label(inner, text="--", width=6,
                                     font=("微软雅黑", 10, "bold"), foreground="#666")
        self.after_label.pack(side=tk.LEFT)

        self.reduction_label = ttk.Label(inner, text="", font=("微软雅黑", 10, "bold"),
                                         foreground="green")
        self.reduction_label.pack(side=tk.LEFT, padx=(15, 0))

        self.stats_label = ttk.Label(inner, text="", font=("微软雅黑", 9), foreground="gray")
        self.stats_label.pack(side=tk.RIGHT, padx=(10, 0))

    def _build_status_bar(self):
        """底部状态栏"""
        status_bar = ttk.Frame(self.root, padding=(10, 3))
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = ttk.Label(status_bar, text="就绪 — 上传文档或粘贴文本，点击「开始改写」", foreground="gray")
        self.status_label.pack(side=tk.LEFT)

        self.rewrite_btn2 = ttk.Button(
            status_bar, text="✏️  开始改写",
            command=self._start_rewrite
        )
        self.rewrite_btn2.pack(side=tk.RIGHT)

    # ==================== 交互方法 ====================

    def _on_lang_change(self, event=None):
        lang = "zh" if self.lang_var.get() == "中文" else "en"
        self.lang_var.set("zh" if lang == "zh" else "en")
        self._clear_evaluation()

    def _on_text_change(self, event=None):
        text = self.input_text.get("1.0", tk.END).strip()
        if not text:
            self.char_count_label.config(text="字数: 0")
            self._clear_evaluation()
            return

        chars = len(text.replace(" ", "").replace("\n", ""))
        self.char_count_label.config(text=f"字数: {chars}")

        if self._auto_evaluate_timer:
            self.root.after_cancel(self._auto_evaluate_timer)
        self._auto_evaluate_timer = self.root.after(1500, self._evaluate_input)

    def _evaluate_input(self):
        text = self.input_text.get("1.0", tk.END).strip()
        if not text:
            return
        lang = "zh" if self.lang_var.get() == "中文" else "en"
        result = estimate_ai_probability(text, lang)
        score = result.get("overall", 0)
        self.before_score_var.set(score)
        self.before_label.config(text=f"{score:.0f}%")
        self._update_score_color(self.before_label, score)
        self.status_label.config(text="原文已评估，点击「开始改写」进行降重")

    def _clear_evaluation(self):
        self.before_score_var.set(0)
        self.after_score_var.set(0)
        self.before_label.config(text="--", foreground="#666")
        self.after_label.config(text="--", foreground="#666")
        self.reduction_label.config(text="")
        self.stats_label.config(text="")
        self.status_label.config(text="就绪 — 上传文档或粘贴文本，点击「开始改写」")

    def _update_score_color(self, label, score):
        if score == "--" or score == 0:
            label.config(foreground="#666")
        elif score >= 70:
            label.config(foreground="#d32f2f")
        elif score >= 40:
            label.config(foreground="#f57c00")
        else:
            label.config(foreground="#388e3c")

    def _clear_text(self, widget):
        widget.delete("1.0", tk.END)
        if widget == self.input_text:
            self._clear_evaluation()

    def _paste_text(self):
        try:
            text = self.root.clipboard_get()
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", text)
            self._on_text_change()
        except tk.TclError:
            pass

    # ==================== 文档上传 ====================

    def _upload_document(self):
        filetypes = [
            ("支持的文件", "*.txt *.docx *.pdf"),
            ("文本文件", "*.txt"),
            ("Word文档", "*.docx"),
            ("PDF文件", "*.pdf"),
            ("所有文件", "*.*"),
        ]
        file_path = filedialog.askopenfilename(
            title="选择论文文档",
            filetypes=filetypes,
        )
        if not file_path:
            return

        ext = os.path.splitext(file_path)[1].lower()
        self.status_label.config(text=f"正在读取: {os.path.basename(file_path)}...")
        self.root.update()

        try:
            if ext == ".txt":
                content = self._read_txt(file_path)
            elif ext == ".docx":
                content = self._read_docx(file_path)
            elif ext == ".pdf":
                content = self._read_pdf(file_path)
            else:
                messagebox.showwarning("提示", f"不支持的文件格式: {ext}")
                self.status_label.config(text="就绪")
                return

            if not content or not content.strip():
                messagebox.showwarning("提示", "文档内容为空")
                self.status_label.config(text="就绪")
                return

            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", content)

            cn_chars = sum(1 for c in content if '一' <= c <= '鿿')
            total_chars = len(content.strip().replace(" ", "").replace("\n", ""))
            if total_chars > 0 and cn_chars / total_chars > 0.3:
                self.lang_var.set("中文")
            else:
                self.lang_var.set("English")

            self._on_text_change()
            self.status_label.config(
                text=f"已加载: {os.path.basename(file_path)} ({total_chars}字)"
            )
        except Exception as e:
            messagebox.showerror("读取失败", str(e))
            self.status_label.config(text="读取失败")

    def _read_txt(self, file_path):
        encodings = ["utf-8", "gbk", "gb2312", "gb18030", "utf-16", "ansi"]
        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def _read_docx(self, file_path):
        if not DOCX_AVAILABLE:
            raise ImportError("缺少 python-docx 库\n请运行: pip install python-docx")
        doc = DocxDocument(file_path)
        return "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())

    def _read_pdf(self, file_path):
        if not PDF_AVAILABLE:
            return self._read_pdf_fallback(file_path)
        doc = fitz.open(file_path)
        texts = []
        for page in doc:
            t = page.get_text().strip()
            if t:
                texts.append(t)
        doc.close()
        return "\n".join(texts)

    def _read_pdf_fallback(self, file_path):
        with open(file_path, "rb") as f:
            data = f.read()
        text = data.decode("utf-8", errors="ignore")
        texts = re.findall(r'[一-鿿 -~　-〿＀-￯]+', text)
        return "\n".join(t for t in texts if len(t.strip()) > 10)

    # ==================== 核心改写逻辑 ====================

    def _start_rewrite(self):
        """根据当前降重模式派发改写"""
        rmode = self.rewrite_mode_var.get()

        if rmode == "full":
            self._rewrite_full()
        elif rmode == "selection":
            self._rewrite_selection()
        elif rmode == "report":
            self._rewrite_by_report()

    # ---------- 全文改写 ----------

    def _rewrite_full(self):
        text = self.input_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("提示", "请先输入需要改写的文本")
            return
        self._do_rewrite(text)

    # ---------- 选中改写 ----------

    def _rewrite_selection(self):
        """改写用户选中的文本片段，只替换选中部分"""
        try:
            sel_text = self.input_text.selection_get()
        except tk.TclError:
            messagebox.showinfo("提示", "请先在原文中用鼠标选中需要降重的文字")
            return

        if not sel_text or not sel_text.strip():
            return

        sel_start = self.input_text.index(tk.SEL_FIRST)
        sel_end = self.input_text.index(tk.SEL_LAST)

        # 局部改写选中的文本
        lang = "zh" if self.lang_var.get() == "中文" else "en"
        intensity = self.intensity_var.get()
        strategies = [k for k, v in self.strategy_vars.items() if v.get()]

        status_msg = "正在改写选中部分..."
        self._set_buttons_disabled(True)
        self.status_label.config(text=status_msg)
        self.root.update()

        try:
            mode = self.mode_var.get()
            if mode == "local":
                result = self.local_rewriter.rewrite(sel_text, lang, intensity, strategies)
                rewritten_sel = result["text"]
                stats = result["stats"]
            else:
                if not self.api_rewriter.is_configured:
                    messagebox.showinfo("提示", "请先配置API密钥")
                    self._set_buttons_disabled(False)
                    return
                rewritten_sel = self.api_rewriter.rewrite_sync(sel_text, lang, intensity)
                stats = {}

            # 把改写后的片段放回原文
            full_text = self.input_text.get("1.0", tk.END).strip()
            before = full_text[:len(full_text[:int(sel_start.split('.')[0]) * 100 + int(sel_start.split('.')[1])])]  # wrong
            # 更可靠的替换方式：按位置替换
            full_text = self.input_text.get("1.0", tk.END).strip()
            pos_before = int(sel_start.split('.')[0]) * 100 + int(sel_start.split('.')[1]) - 100
            # 简单方法：用字符串替换
            new_full = full_text.replace(sel_text, rewritten_sel, 1)

            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", new_full)
            self._set_output(rewritten_sel + "\n\n(仅展示改写部分，原文中已自动替换)")
            self._show_evaluation(full_text, new_full, lang, stats)

        except Exception as e:
            messagebox.showerror("改写失败", str(e))
            self._set_buttons_disabled(False)

    # ---------- 按查重报告降重 ----------

    def _open_plagiarism_dialog(self):
        """打开导入查重报告对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("导入查重报告 — 粘贴重复句子")
        dialog.geometry("600x450")
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="📋 按查重报告降重", font=("微软雅黑", 13, "bold")).pack(anchor=tk.W)
        ttk.Label(frame, text="从你的查重报告中复制标红的重复句子，粘贴到下方文本框（每句一行）",
                  foreground="gray").pack(anchor=tk.W, pady=(0, 10))

        # 粘贴区
        report_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("微软雅黑", 10),
                                                height=12, padx=6, pady=6)
        report_text.pack(fill=tk.BOTH, expand=True)
        report_text.insert("1.0", "# 每行粘贴一个重复句子（或一段）\n# 工具会自动在原文中查找并改写这些部分\n")

        # 额外选项
        opt_frame = ttk.Frame(frame)
        opt_frame.pack(fill=tk.X, pady=8)

        fuzzy_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text="模糊匹配（忽略细微差异）", variable=fuzzy_var).pack(side=tk.LEFT)

        sep_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text="保留分隔标记行", variable=sep_var).pack(side=tk.LEFT, padx=15)

        def do_match():
            """在原文中查找并标记重复句子"""
            report_content = report_text.get("1.0", tk.END).strip()
            sentences = []
            for line in report_content.split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if not sep_var.get() and line.startswith(("---", "===", "***")):
                    continue
                sentences.append(line)

            if not sentences:
                messagebox.showwarning("提示", "没有找到有效的重复句子，请先粘贴报告内容")
                return

            original = self.input_text.get("1.0", tk.END).strip()
            if not original:
                messagebox.showwarning("提示", "原文为空，请先上传论文文档")
                return

            matched = 0
            not_found = []
            found_texts = []

            for s in sentences:
                if s in original:
                    found_texts.append(s)
                    matched += 1
                elif fuzzy_var.get():
                    # 尝试去除空格和标点后匹配
                    clean_s = re.sub(r'[\s,，。、；；：！？""（）《》【】\'\']', '', s)
                    clean_o = re.sub(r'[\s,，。、；：！？""（）《》【】\'\']', '', original)
                    if clean_s in clean_o:
                        found_texts.append(s)
                        matched += 1
                    else:
                        # 尝试匹配子串（至少10个字）
                        for length in range(min(len(clean_s), 50), 9, -1):
                            substr = clean_s[:length]
                            if substr in clean_o:
                                found_texts.append(s)
                                matched += 1
                                break
                        else:
                            not_found.append(s)
                else:
                    not_found.append(s)

            dialog.destroy()

            if matched == 0:
                messagebox.showwarning("提示", "未在原文中找到匹配的重复句子。\n请检查查重报告内容是否与原文对应。")
                return

            # 询问是否立即改写
            msg = f"在原文中找到 {matched} 处重复内容"
            if not_found:
                msg += f"\n{len(not_found)} 处未能匹配（可能已在改写范围内）"
            msg += "\n\n是否立即对找到的重复内容进行改写降重？"

            if not messagebox.askyesno("匹配完成", msg):
                self.status_label.config(text=f"已匹配 {matched} 处重复内容（未改写）")
                return

            # 执行改写
            self._rewrite_by_sentences(found_texts)

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(btn_row, text="🔍 查找并改写", width=14, command=do_match).pack(side=tk.RIGHT)
        ttk.Button(btn_row, text="取消", width=8, command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def _rewrite_by_report(self):
        """从查重报告匹配的快捷入口"""
        self._open_plagiarism_dialog()

    def _rewrite_by_sentences(self, sentences):
        """根据查重报告句子列表改写原文中匹配的部分"""
        original = self.input_text.get("1.0", tk.END).strip()
        if not original or not sentences:
            return

        lang = "zh" if self.lang_var.get() == "中文" else "en"
        intensity = self.intensity_var.get()
        strategies = [k for k, v in self.strategy_vars.items() if v.get()]

        self._set_buttons_disabled(True)
        self.status_label.config(text=f"正在改写 {len(sentences)} 处重复...")
        self.root.update()

        try:
            result = original
            rewritten_parts = []
            total_count = 0

            for idx, sentence in enumerate(sentences):
                if sentence not in result:
                    continue

                # 改写这个句子
                mode = self.mode_var.get()
                if mode == "local":
                    r = self.local_rewriter.rewrite(sentence, lang, intensity, strategies)
                    new_text = r["text"]
                else:
                    if not self.api_rewriter.is_configured:
                        messagebox.showinfo("提示", "请先配置API密钥")
                        self._set_buttons_disabled(False)
                        return
                    new_text = self.api_rewriter.rewrite_sync(sentence, lang, intensity)

                result = result.replace(sentence, new_text, 1)
                rewritten_parts.append(f"【原文】{sentence}\n【改写】{new_text}\n")
                total_count += 1

                # 更新进度
                if idx % 2 == 0:
                    self.status_label.config(text=f"改写中... ({idx+1}/{len(sentences)})")
                    self.root.update()

            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", result)

            # 在右侧展示改写对照
            show = "\n".join(rewritten_parts)
            self._set_output(show)
            self._show_evaluation(original, result, lang, {"重复改写": total_count})

        except Exception as e:
            messagebox.showerror("改写失败", str(e))
            self._set_buttons_disabled(False)

    # ---------- 通用改写方法 ----------

    def _do_rewrite(self, text):
        """通用改写：全文"""
        lang = "zh" if self.lang_var.get() == "中文" else "en"
        mode = self.mode_var.get()
        intensity = self.intensity_var.get()
        strategies = [k for k, v in self.strategy_vars.items() if v.get()]

        if not strategies:
            messagebox.showinfo("提示", "请至少选择一个改写策略")
            return

        self._set_buttons_disabled(True)
        self.status_label.config(text="正在改写...")

        if mode == "local":
            self._do_local_rewrite(text, lang, intensity, strategies)
        else:
            if not self.api_rewriter.is_configured:
                messagebox.showinfo("提示", "请先在 API设置 中配置API密钥")
                self._set_buttons_disabled(False)
                return
            self._do_api_rewrite(text, lang, intensity)

    def _set_buttons_disabled(self, disabled):
        state = tk.DISABLED if disabled else tk.NORMAL
        self.rewrite_btn.config(state=state)
        self.rewrite_btn2.config(state=state)

    def _do_local_rewrite(self, text, lang, intensity, strategies):
        try:
            result = self.local_rewriter.rewrite(text, lang, intensity, strategies)
            rewritten_text = result["text"]
            stats = result["stats"]

            self._set_output(rewritten_text)
            self._show_evaluation(text, rewritten_text, lang, stats)

        except Exception as e:
            self._set_buttons_disabled(False)
            self.status_label.config(text="改写失败")
            messagebox.showerror("改写失败", str(e))

    def _do_api_rewrite(self, text, lang, intensity):
        self.status_label.config(text="正在请求API...")

        def on_success(rewritten_text):
            self.root.after(0, lambda: self._handle_api_success(text, rewritten_text, lang))

        def on_error(error_msg):
            self.root.after(0, lambda: self._handle_api_error(error_msg))

        self.api_rewriter.rewrite(text, lang, intensity, on_success, on_error)

    def _handle_api_success(self, original, rewritten, lang):
        self._set_output(rewritten)
        self._show_evaluation(original, rewritten, lang, {})
        self.status_label.config(text="API改写完成 ✅")

    def _handle_api_error(self, error_msg):
        self._set_buttons_disabled(False)
        self.status_label.config(text="API改写失败")
        messagebox.showerror("API改写失败", error_msg)

    def _set_output(self, text):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", text)
        self.output_text.config(state=tk.DISABLED)

    def _show_evaluation(self, original, rewritten, lang, stats=None):
        before = estimate_ai_probability(original, lang)
        after = estimate_ai_probability(rewritten, lang)

        b_score = before.get("overall", 0)
        a_score = after.get("overall", 0)
        reduction = b_score - a_score

        self.before_score_var.set(b_score)
        self.after_score_var.set(a_score)

        self.before_label.config(text=f"{b_score:.0f}%")
        self._update_score_color(self.before_label, b_score)

        self.after_label.config(text=f"{a_score:.0f}%")
        self._update_score_color(self.after_label, a_score)

        if reduction > 0:
            self.reduction_label.config(text=f"降低 ↓ {abs(reduction):.0f}%", foreground="green")
        elif reduction < 0:
            self.reduction_label.config(text=f"升高 ↑ {abs(reduction):.0f}%", foreground="red")
        else:
            self.reduction_label.config(text="→ 0%", foreground="gray")

        if stats:
            parts = [f"{k}: {v}处" for k, v in stats.items() if v]
            self.stats_label.config(text=" | ".join(parts) if parts else "")
        else:
            self.stats_label.config(text="")

        self._set_buttons_disabled(False)

        if reduction > 0:
            self.status_label.config(text=f"改写完成 ✅ AI率降低 {reduction:.0f}%")
        else:
            self.status_label.config(text="改写完成 ✅")

    # ==================== 复制 / 保存 / 设置 ====================

    def _copy_result(self):
        text = self.output_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("提示", "没有可复制的内容")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_label.config(text="已复制到剪贴板")

    def _save_result(self):
        text = self.output_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("提示", "没有可保存的内容")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            title="保存改写结果"
        )
        if file_path:
            try:
                lang = "zh" if self.lang_var.get() == "中文" else "en"
                before = estimate_ai_probability(self.input_text.get("1.0", tk.END).strip(), lang)
                after = estimate_ai_probability(text, lang)
                report = format_report(before, after)

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("=" * 40 + "\n  原文\n" + "=" * 40 + "\n")
                    f.write(self.input_text.get("1.0", tk.END).strip() + "\n\n")
                    f.write("=" * 40 + "\n  改写结果\n" + "=" * 40 + "\n")
                    f.write(text + "\n\n")
                    f.write(report + "\n")
                self.status_label.config(text=f"已保存至: {file_path}")
            except Exception as e:
                messagebox.showerror("保存失败", str(e))

    def _open_api_settings(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("API设置")
        dialog.geometry("550x320")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="API设置", font=("微软雅黑", 13, "bold")).pack(anchor=tk.W)
        ttk.Label(frame, text="支持 OpenAI 兼容接口 (GPT/Claude/DeepSeek等)").pack(anchor=tk.W, pady=(0, 15))

        fields = [
            ("API地址:", "api_url", self.api_rewriter.api_url),
            ("API密钥:", "api_key", self.api_rewriter.api_key),
            ("模型名:", "model", self.api_rewriter.model),
            ("Temperature:", "temperature", str(self.api_rewriter.temperature)),
        ]
        entries = {}
        for label_text, key, default in fields:
            row = ttk.Frame(frame)
            row.pack(fill=tk.X, pady=4)
            ttk.Label(row, text=label_text, width=12).pack(side=tk.LEFT)
            if key == "api_key":
                entry = ttk.Entry(row, show="*", width=50)
            else:
                entry = ttk.Entry(row, width=50)
            entry.insert(0, default)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
            entries[key] = entry

        def save():
            self.api_rewriter.configure(
                api_key=entries["api_key"].get().strip(),
                api_url=entries["api_url"].get().strip(),
                model=entries["model"].get().strip(),
                temperature=float(entries["temperature"].get().strip() or "0.8"),
            )
            dialog.destroy()
            messagebox.showinfo("提示", "API设置已保存")

        def test():
            if not entries["api_key"].get().strip():
                messagebox.showwarning("提示", "请先输入API密钥")
                return
            tw = ApiRewriter()
            tw.configure(entries["api_key"].get().strip(),
                        entries["api_url"].get().strip(),
                        entries["model"].get().strip(), 0.7)

            def ok(t):
                self.root.after(0, lambda: messagebox.showinfo("成功", "API连接正常! " + t[:50] + "..."))
            def fail(m):
                self.root.after(0, lambda: messagebox.showerror("失败", m))
            tw.rewrite("Hello test.", "en", "light", ok, fail)

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, pady=(15, 0))
        ttk.Button(btn_row, text="保存", width=8, command=save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_row, text="测试连接", width=10, command=test).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_row, text="取消", width=8, command=dialog.destroy).pack(side=tk.RIGHT)
