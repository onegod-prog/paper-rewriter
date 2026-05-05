"""句式变换规则 - 中英文句子结构变换模式"""

# ==================== 中文句式变换规则 ====================

# 把字句 → 被字句 (和反向)
ZH_BA_BEI_PATTERNS = [
    # 把字句 → 被字句: "A把B怎么样了" → "B被A怎么样了"
    (r"(\w+?)把(\w+?)([^。！？，]+)", r"\2被\1\3"),
    # 被字句 → 把字句: "B被A怎么样了" → "A把B怎么样了"
    (r"(\w+?)被(\w+?)([^。！？，]+)", r"\2把\1\3"),
]

# 中文句子开头变换
ZH_OPENING_VARIATIONS = {
    "这": ["上述", "此", "这一", "该"],
    "这些": ["上述", "诸", "以上"],
    "因此": ["基于此", "鉴于此", "据此", "有鉴于此"],
    "因为": ["由于", "鉴于", "出于"],
    "如果": ["倘若", "假设", "若"],
    "虽然": ["尽管", "虽说"],
    "在": ["于", "就"],
}

# 中文AI高频句式模式
ZH_AI_PATTERNS = [
    (r"值得注意的是[，,]\s*", "需关注的是，"),
    (r"毋庸置疑[，,]\s*", "毫无疑问，"),
    (r"综上所述[，,]\s*", "综合而言，"),
    (r"不可或缺的", "必不可少的"),
    (r"至关重要", "具有关键意义"),
    (r"显而易见[，,]", "不难看出，"),
    (r"从某种意义上说", "在某种程度上"),
]

# 中文学术连接词替换
ZH_CONNECTOR_VARIATIONS = {
    "首先": ["首要", "第一", "一开始"],
    "其次": ["第二", "此外", "另外"],
    "最后": ["最终", "末了", "末尾"],
    "一方面": ["一则", "一者"],
    "另一方面": ["再则", "二者", "另一角度"],
}

# ==================== 英文句式变换规则 ====================

# Active ↔ Passive voice patterns
EN_VOICE_PATTERNS = [
    # Active → Passive: "A [verb]ed B" → "B was [verb]ed by A"
    # Generic active-passive conversion handled in code
]

# 英文句子开头变换
EN_OPENING_VARIATIONS = {
    "This": ["The above", "The aforementioned", "This particular", "The present"],
    "These": ["The above-mentioned", "The foregoing", "Such"],
    "Therefore": ["Consequently", "As a result", "Accordingly", "Hence"],
    "Because": ["Since", "Given that", "As"],
    "However": ["Nevertheless", "Nonetheless", "That said"],
    "Although": ["Even though", "While", "Notwithstanding"],
    "If": ["Provided that", "Assuming that", "Given that"],
    "In": ["Within", "Regarding", "Concerning"],
    "First": ["First of all", "To begin with", "Primarily"],
    "Second": ["Secondly", "Additionally", "Furthermore"],
    "Finally": ["Ultimately", "Lastly", "In closing"],
    "For example": ["For instance", "As an illustration", "To exemplify"],
}

# 英文AI高频句式模式
EN_AI_PATTERNS = [
    (r"\bit is worth noting that\b", "it is noteworthy that"),
    (r"\bit goes without saying that\b", "it is evident that"),
    (r"\bneedless to say\b", "clearly"),
    (r"\bparamount\b", "crucial"),
    (r"\bdelve into\b", "explore"),
    (r"\bcutting[- ]edge\b", "advanced"),
    (r"\bleverage\b", "utilize"),
    (r"\bgroundbreaking\b", "innovative"),
    (r"\bindispensable\b", "essential"),
    (r"\bseamlessly\b", "effectively"),
    (r"\bin a nutshell\b", "in summary"),
    (r"\blast but not least\b", "finally"),
]

# ==================== 通用句式变换模板 ====================

# 长句拆分标记词 (遇到这些词可以考虑拆分)
SPLIT_MARKERS_ZH = ["并且", "而且", "与此同时", "此外", "因此", "从而", "然而"]
SPLIT_MARKERS_EN = ["and", "moreover", "furthermore", "additionally", "therefore", "consequently", "however"]

# 短句合并标记 (以这些词开头的短句可以考虑与上一句合并)
MERGE_MARKERS_ZH = ["这", "该", "其", "此"]
MERGE_MARKERS_EN = ["this", "that", "these", "those", "it", "they"]
