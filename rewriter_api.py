"""API改写引擎 - 通过调用AI API进行更深度的改写"""

import json
import requests
import threading


class ApiRewriter:
    """API改写引擎"""

    def __init__(self):
        self.api_key = ""
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.model = "gpt-4o-mini"
        self.temperature = 0.8
        self.max_tokens = 4096

    def configure(self, api_key, api_url, model, temperature=0.8):
        """配置API参数"""
        self.api_key = api_key
        if api_url:
            self.api_url = api_url.rstrip("/")
            if not self.api_url.endswith("/chat/completions"):
                self.api_url = self.api_url.rstrip("/") + "/chat/completions"
        self.model = model
        self.temperature = temperature

    @property
    def is_configured(self):
        """检查API是否已配置"""
        return bool(self.api_key) and bool(self.api_url)

    def _build_prompt(self, text, lang="zh", intensity="medium"):
        """构建改写提示词

        Args:
            text: 待改写文本
            lang: "zh" 或 "en"
            intensity: "light", "medium", "heavy"
        """
        if lang == "zh":
            return self._build_zh_prompt(text, intensity)
        else:
            return self._build_en_prompt(text, intensity)

    def _build_zh_prompt(self, text, intensity):
        """构建中文改写提示词"""
        intensity_desc = {
            "light": "进行轻度改写，替换少量词汇和短语，保持原文结构基本不变。",
            "medium": "进行中度改写，替换同义词、调整句式结构、变换连接词，改变部分句子顺序。",
            "heavy": "进行深度改写，大规模替换词汇、重构句式、变换表达方式，使文本风格显著不同于原文。",
        }.get(intensity, "进行适度改写，使文本更加自然多样。")

        system_prompt = """你是一个专业的学术论文改写助手。你的任务是改写给定的文本，使其看起来更加自然、减少AI检测特征。

## 核心要求
1. 保持原文的学术性和专业性，不得改变事实和数据
2. 保留专业术语和专有名词
3. 以下是重要指示，必须严格遵守:
   - 增加句式多样性：混合使用简单句、复合句、倒装句等
   - 变换句子的开头方式，避免多个句子以相同方式开头
   - 适度使用同义词替换，避免过度晦涩
   - 调整连接词的使用模式和位置
   - 避免AI写作中常见的高频词汇和表达模式
   - 保持学术正式语气"""
        user_prompt = f"""请对以下学术文本{intensity_desc}

文本内容：
```
{text}
```

请只返回改写后的结果，不要添加任何解释、说明或额外内容。"""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _build_en_prompt(self, text, intensity):
        """构建英文改写提示词"""
        intensity_desc = {
            "light": "Apply light rewriting: replace some vocabulary and phrases while keeping the structure largely unchanged.",
            "medium": "Apply moderate rewriting: replace synonyms, adjust sentence structures, vary connectors, and reorder some clauses.",
            "heavy": "Apply heavy rewriting: extensively replace vocabulary, restructure sentences, transform expressions to create a substantially different writing style.",
        }.get(intensity, "Apply moderate rewriting to make the text more natural and varied.")

        system_prompt = """You are a professional academic writing assistant. Your task is to rewrite the given text to make it more natural and reduce AI detection patterns.

## Key Requirements
1. Maintain academic rigor and professionalism — do NOT alter facts, data, or findings
2. Preserve technical terminology and proper nouns
3. CRITICAL instructions:
   - Vary sentence structure: mix simple, compound, and complex sentences
   - Vary how sentences begin — avoid multiple sentences starting the same way
   - Use synonyms appropriately without being overly obscure
   - Adjust the placement and choice of transition words
   - Avoid high-frequency AI writing patterns and vocabulary
   - Maintain formal academic tone throughout"""
        user_prompt = f"""Please rewrite the following academic text. {intensity_desc}

Text:
```
{text}
```

Return ONLY the rewritten text. Do NOT include any explanation, notes, or additional content."""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def rewrite(self, text, lang="zh", intensity="medium", on_success=None, on_error=None):
        """异步调用API改写文本

        Args:
            text: 输入文本
            lang: "zh" 或 "en"
            intensity: "light", "medium", "heavy"
            on_success: 成功回调函数 (result_text)
            on_error: 失败回调函数 (error_message)

        Returns:
            threading.Thread 对象
        """
        def _run():
            try:
                messages = self._build_prompt(text, lang, intensity)

                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                }

                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.temperature,
                    "max_tokens": min(self.max_tokens, max(1024, int(len(text) * 1.5))),
                }

                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=120,
                )

                if response.status_code != 200:
                    error_msg = f"API请求失败 (HTTP {response.status_code})"
                    try:
                        err_data = response.json()
                        if "error" in err_data:
                            error_msg += f": {err_data['error'].get('message', '')}"
                    except Exception:
                        error_msg += f": {response.text[:200]}"
                    if on_error:
                        on_error(error_msg)
                    return

                result = response.json()
                if "choices" not in result or not result["choices"]:
                    if on_error:
                        on_error("API返回格式异常: 缺少choices字段")
                    return

                rewritten = result["choices"][0]["message"]["content"]
                if on_success:
                    on_success(rewritten.strip())

            except requests.exceptions.Timeout:
                if on_error:
                    on_error("API请求超时，请检查网络或尝试缩短文本")
            except requests.exceptions.ConnectionError:
                if on_error:
                    on_error("网络连接失败，请检查API地址和网络设置")
            except Exception as e:
                if on_error:
                    on_error(f"改写失败: {str(e)}")

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return thread

    def rewrite_sync(self, text, lang="zh", intensity="medium"):
        """同步调用API改写 (会阻塞)"""
        messages = self._build_prompt(text, lang, intensity)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": min(self.max_tokens, max(1024, int(len(text) * 1.5))),
        }

        response = requests.post(
            self.api_url,
            headers=headers,
            json=payload,
            timeout=120,
        )

        if response.status_code != 200:
            error_msg = f"API请求失败 (HTTP {response.status_code})"
            try:
                err_data = response.json()
                if "error" in err_data:
                    error_msg += f": {err_data['error'].get('message', '')}"
            except Exception:
                pass
            raise Exception(error_msg)

        result = response.json()
        if "choices" not in result or not result["choices"]:
            raise Exception("API返回格式异常")

        return result["choices"][0]["message"]["content"].strip()
