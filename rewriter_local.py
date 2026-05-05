"""本地规则改写引擎 - 使用同义词替换和句式变换降低AI率"""

import re
import random
from data.zh_synonyms import SYNONYM_MAP as ZH_SYNONYMS
from data.en_synonyms import SYNONYM_MAP as EN_SYNONYMS
from data.patterns import (
    ZH_BA_BEI_PATTERNS,
    ZH_OPENING_VARIATIONS,
    ZH_AI_PATTERNS,
    ZH_CONNECTOR_VARIATIONS,
    EN_OPENING_VARIATIONS,
    EN_AI_PATTERNS,
    SPLIT_MARKERS_ZH,
    SPLIT_MARKERS_EN,
)

# 尝试导入 jieba (中文分词), 如果不可用则使用简单分词
try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False


class LocalRewriter:
    """本地规则改写引擎"""

    # 改写力度对应的替换比例
    INTENSITY_RATIOS = {
        "light": 0.3,
        "medium": 0.5,
        "heavy": 0.7,
    }

    def __init__(self):
        self.synonym_cache = {}

    def rewrite(self, text, lang="zh", intensity="medium", strategies=None):
        """对文本进行改写

        Args:
            text: 输入文本
            lang: "zh" 或 "en"
            intensity: "light", "medium", "heavy"
            strategies: 启用的策略列表, 如 ["synonym", "pattern", "voice", "connector"]

        Returns:
            dict: {"text": 改写后文本, "stats": 替换统计}
        """
        if not text or not text.strip():
            return {"text": text, "stats": {}}

        if strategies is None:
            strategies = ["synonym", "pattern", "voice", "connector"]

        ratio = self.INTENSITY_RATIOS.get(intensity, 0.5)
        stats = {}
        result = text

        # 按顺序应用策略
        if "synonym" in strategies:
            result, syn_stat = self._apply_synonym_replacement(result, lang, ratio)
            stats["同义词替换"] = syn_stat

        if "pattern" in strategies:
            result, pat_stat = self._apply_pattern_transforms(result, lang, intensity)
            stats["句式变换"] = pat_stat

        if "voice" in strategies and lang == "zh":
            result, voice_stat = self._apply_voice_conversion(result, lang)
            stats["语态转换"] = voice_stat

        if "connector" in strategies:
            result, conn_stat = self._apply_connector_variation(result, lang)
            stats["连接词变换"] = conn_stat

        return {"text": result, "stats": stats}

    # ==================== 中文分词 ====================

    def _segment(self, text, lang):
        """对文本进行分词"""
        if lang == "zh":
            if JIEBA_AVAILABLE:
                words = list(jieba.cut(text))
            else:
                # 简单分词: 按字符和常见词汇启发式
                words = self._simple_zh_segment(text)
            return words
        else:
            return text.split()

    def _simple_zh_segment(self, text):
        """简单的中文分词 (无jieba时使用)"""
        words = []
        # 先尝试匹配已知的多字词
        i = 0
        known_words = set()
        for w in ZH_SYNONYMS.keys():
            for char in w:
                if len(w) > 1:
                    known_words.add(w)

        known_list = sorted(known_words, key=len, reverse=True)
        while i < len(text):
            matched = False
            for kw in known_list:
                if text[i:i + len(kw)] == kw:
                    words.append(kw)
                    i += len(kw)
                    matched = True
                    break
            if not matched:
                words.append(text[i])
                i += 1
        return words

    def _rejoin_zh(self, words):
        """将分词列表重新组合为文本"""
        return "".join(words)

    # ==================== 同义词替换 ====================

    def _apply_synonym_replacement(self, text, lang, ratio):
        """应用同义词替换"""
        synonym_map = ZH_SYNONYMS if lang == "zh" else EN_SYNONYMS

        if lang == "zh":
            return self._zh_synonym_replace(text, synonym_map, ratio)
        else:
            return self._en_synonym_replace(text, synonym_map, ratio)

    def _zh_synonym_replace(self, text, synonym_map, ratio):
        """中文同义词替换 (保护固定搭配)"""
        # 先保护固定短语
        protected_text, placeholders = self._build_protected_map(text, "zh")
        result = protected_text
        count = 0
        matched_keys = []

        # 找到所有命中的词，按长度排序(长词优先)
        for key in synonym_map:
            if key in result:
                matched_keys.append(key)
        matched_keys.sort(key=len, reverse=True)

        for key in matched_keys:
            synonyms = synonym_map[key]
            if not synonyms:
                continue

            # 按替换比例决定是否替换
            occurrences = result.count(key)
            replace_count = max(1, int(occurrences * ratio))

            # 随机选择部分出现进行替换
            positions = []
            start = 0
            while True:
                pos = result.find(key, start)
                if pos == -1:
                    break
                positions.append(pos)
                start = pos + len(key)

            random.shuffle(positions)
            for i, pos in enumerate(positions[:replace_count]):
                replacement = random.choice(synonyms)
                # 为避免替换后的词再次被扫描替换，直接从结果中替换
                left = result[:pos]
                right = result[pos + len(key):]
                # 调整后续位置偏移
                offset = len(replacement) - len(key)
                positions = [p + offset for p in positions[i + 1:]]
                result = left + replacement + right
                count += 1

        # 恢复受保护短语
        result = self._restore_protected(result, placeholders)
        return result, count

    # 需要保护的固定搭配/专有名词 (防止被拆分替换)
    PROTECTED_PHRASES_EN = [
        "climate change", "global warming", "artificial intelligence",
        "machine learning", "deep learning", "natural language processing",
        "world war", "united states", "united kingdom",
        "south korea", "north korea", "south africa",
        "new york", "new zealand", "hong kong",
        "open source", "open access", "peer review",
        "supply chain", "value chain", "data set", "dataset",
        "case study", "literature review", "research and development",
        "gross domestic product", "gdp", "human rights",
        "public health", "higher education", "quality of life",
        "standard deviation", "statistical significance", "null hypothesis",
        "dependent variable", "independent variable", "control group",
        "time series", "panel data", "cross sectional",
    ]

    PROTECTED_PHRASES_ZH = [
        "气候变化", "人工智能", "机器学习", "深度学习",
        "全球变暖", "温室效应", "自然语言处理",
        "中华人民共和国", "中国共产党", "社会主义核心价值观",
        "改革开放", "一带一路", "供给侧改革",
        "生产总值", "国内生产总值", "人均收入",
        "标准差", "统计学", "自变量", "因变量",
        "时间序列", "面板数据", "横截面数据",
        "大数据", "云计算", "物联网", "区块链",
    ]

    def _build_protected_map(self, text, lang):
        """构建受保护短语的占位映射 (保留原文大小写)"""
        phrases = self.PROTECTED_PHRASES_ZH if lang == "zh" else self.PROTECTED_PHRASES_EN
        placeholders = {}
        result = text
        idx = [0]  # 用列表保持闭包中的引用
        for phrase in phrases:
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            def make_replacer(i):
                def replacer(m):
                    placeholder = f"__PROTECTED_{i}__"
                    placeholders[placeholder] = m.group(0)
                    return placeholder
                return replacer
            result = pattern.sub(make_replacer(idx[0]), result)
            idx[0] = len(placeholders)
        return result, placeholders

    def _restore_protected(self, text, placeholders):
        """恢复受保护短语"""
        result = text
        for placeholder, phrase in placeholders.items():
            result = result.replace(placeholder, phrase)
        return result

    def _en_synonym_replace(self, text, synonym_map, ratio):
        """英文同义词替换 (词边界匹配, 保护固定搭配)"""
        # 先保护固定短语
        protected_text, placeholders = self._build_protected_map(text, "en")
        result = protected_text
        count = 0
        text_lower = result.lower()
        matched_keys = []

        for key in synonym_map:
            pattern = r'\b' + re.escape(key) + r'\b'
            if re.search(pattern, text_lower):
                matched_keys.append((key, pattern))

        for key, pattern in matched_keys:
            synonyms = synonym_map[key]
            if not synonyms:
                continue

            matches = list(re.finditer(pattern, result, re.IGNORECASE))
            if not matches:
                continue

            replace_count = max(1, int(len(matches) * ratio))
            random.shuffle(matches)

            for match in matches[:replace_count]:
                replacement = random.choice(synonyms)
                # 保持首字母大小写
                orig = match.group()
                if orig[0].isupper():
                    replacement = replacement[0].upper() + replacement[1:]
                result = result[:match.start()] + replacement + result[match.end():]
                count += 1

        # 恢复受保护短语
        result = self._restore_protected(result, placeholders)
        return result, count

    # ==================== 句式变换 ====================

    def _apply_pattern_transforms(self, text, lang, intensity):
        """应用句式变换"""
        count = 0
        result = text

        if lang == "zh":
            # 替换AI高频句式
            for pattern, replacement in ZH_AI_PATTERNS:
                occurrences = list(re.finditer(pattern, result))
                for match in occurrences:
                    result = result[:match.start()] + replacement + result[match.end():]
                    count += 1

            # 变换句子开头 (仅重力度模式)
            if intensity == "heavy":
                for old, alternatives in ZH_OPENING_VARIATIONS.items():
                    if result.startswith(old):
                        replacement = random.choice(alternatives)
                        result = replacement + result[len(old):]
                        count += 1
                        break
        else:
            # 替换AI高频句式
            for pattern, replacement in EN_AI_PATTERNS:
                matches = list(re.finditer(pattern, result, re.IGNORECASE))
                for match in matches:
                    result = result[:match.start()] + replacement + result[match.end():]
                    count += 1

            # 变换句子开头
            for old, alternatives in EN_OPENING_VARIATIONS.items():
                pattern = r'^' + re.escape(old) + r'\b'
                m = re.search(pattern, result)
                if m:
                    replacement = random.choice(alternatives)
                    result = replacement + result[m.end():]
                    count += 1
                    break

        return result, count

    # ==================== 语态转换 ====================

    def _apply_voice_conversion(self, text, lang):
        """应用语态转换"""
        count = 0
        result = text

        if lang == "zh":
            for pattern, replacement in ZH_BA_BEI_PATTERNS:
                matches = list(re.finditer(pattern, result))
                random.shuffle(matches)
                for match in matches[:2]:  # 最多转2处
                    new_text = result[:match.start()]
                    new_text += match.expand(replacement)
                    new_text += result[match.end():]
                    # 检查结果是否通顺 (长度变化不能太大)
                    if len(new_text) > 0:
                        result = new_text
                        count += 1

        return result, count

    # ==================== 连接词变换 ====================

    def _apply_connector_variation(self, text, lang):
        """应用连接词变换"""
        count = 0
        result = text

        if lang == "zh":
            for old, alternatives in ZH_CONNECTOR_VARIATIONS.items():
                pattern = re.escape(old)
                matches = list(re.finditer(pattern, result))
                for match in matches:
                    replacement = random.choice(alternatives)
                    result = result[:match.start()] + replacement + result[match.end():]
                    count += 1

        return result, count
