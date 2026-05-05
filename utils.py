"""工具函数 - AI疑似率估算、文本统计等"""

import re
import random


def estimate_ai_probability(text, lang="zh"):
    """基于规则估算文本的AI生成概率 (仅供参考, 非精确检测)

    Returns:
        dict: 包含各维度评分和综合概率
    """
    if not text or len(text.strip()) < 20:
        return {"overall": 0, "details": {}}

    scores = {}

    # 1. AI高频词检测
    ai_word_score = _check_ai_high_freq_words(text, lang)
    scores["高频AI词汇"] = ai_word_score

    # 2. 句式多样性检查
    diversity_score = _check_sentence_diversity(text, lang)
    scores["句式多样性"] = diversity_score

    # 3. 连接词使用模式
    connector_score = _check_connector_pattern(text, lang)
    scores["连接词模式"] = connector_score

    # 4. 句长分布分析
    length_score = _check_sentence_length_distribution(text, lang)
    scores["句长分布"] = length_score

    # 5. 重复度检查
    repeat_score = _check_repetitiveness(text, lang)
    scores["重复度"] = repeat_score

    # 综合评分 (加权平均)
    weights = {
        "高频AI词汇": 0.30,
        "句式多样性": 0.25,
        "连接词模式": 0.15,
        "句长分布": 0.15,
        "重复度": 0.15,
    }

    overall = sum(
        scores.get(k, 0) * w for k, w in weights.items()
    )
    overall = min(max(overall, 0), 100)

    return {
        "overall": round(overall, 1),
        "details": {k: round(v, 1) for k, v in scores.items()},
    }


def _check_ai_high_freq_words(text, lang):
    """检查AI高频词汇使用频率"""
    if lang == "zh":
        # 中文AI高频词列表
        ai_words = [
            "值得注意的是", "毋庸置疑", "至关重要", "不可或缺",
            "综上所述", "显而易见", "值得一提的是", "从某种意义上说",
            "近年来", "在某种程度上", "delve", "paramount",
        ]
    else:
        ai_words = [
            "delve", "paramount", "testament", "nuanced", "tapestry",
            "ever-evolving", "cutting-edge", "leverage", "holistic",
            "game-changer", "intricate", "meticulous", "synergy",
            "resonate", "paradigm shift", "groundbreaking", "robust",
            "seamlessly", "multifaceted", "indispensable", "nuance",
        ]

    text_lower = text.lower()
    count = sum(1 for w in ai_words if w.lower() in text_lower)
    # 基于文本长度估算频率得分
    rate = count / max(len(text) / 100, 1)
    score = min(rate * 15, 100)
    return score


def _check_sentence_diversity(text, lang):
    """检查句式多样性 (句式单一 → 高AI概率)"""
    if lang == "zh":
        sentences = re.split(r'[。！？；\n]', text)
        # 检查句子开头重复
        openings = []
        for s in sentences:
            s = s.strip()
            if len(s) > 3:
                openings.append(s[:4])  # 前4个字
    else:
        sentences = re.split(r'[.!?;\n]', text)
        openings = []
        for s in sentences:
            s = s.strip()
            if len(s) > 3:
                openings.append(s[:20])  # 前20个字符

    if len(openings) < 3:
        return 0

    unique_openings = len(set(openings))
    diversity_rate = unique_openings / max(len(openings), 1)

    if diversity_rate > 0.7:
        return 20  # 句式多样, 低AI概率
    elif diversity_rate > 0.4:
        return 50
    else:
        return 80  # 句式单一, 高AI概率


def _check_connector_pattern(text, lang):
    """检查连接词使用模式 (过度使用 → 高AI概率)"""
    if lang == "zh":
        connectors = [
            "因此", "然而", "但是", "而且", "所以", "因为",
            "从而", "此外", "同时", "虽然", "如果", "总之",
        ]
    else:
        connectors = [
            "therefore", "however", "moreover", "furthermore",
            "consequently", "additionally", "thus", "hence",
            "nevertheless", "nonetheless", "accordingly",
        ]

    text_lower = text.lower()
    count = sum(1 for c in connectors if c.lower() in text_lower)
    rate = count / max(len(text) / 100, 1)

    if rate > 8:
        return 80  # 连接词过多
    elif rate > 4:
        return 50
    else:
        return 30


def _check_sentence_length_distribution(text, lang):
    """检查句长分布 (过于均匀 → 高AI概率)"""
    if lang == "zh":
        sentences = re.split(r'[。！？\n]', text)
    else:
        sentences = re.split(r'[.!?\n]', text)

    lengths = [len(s.strip()) for s in sentences if len(s.strip()) > 5]
    if len(lengths) < 3:
        return 0

    avg_len = sum(lengths) / len(lengths)
    variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
    std_dev = variance ** 0.5

    # AI文本句长往往比较均匀 (低标准差)
    relative_std = std_dev / max(avg_len, 1)

    if relative_std < 0.3:
        return 70  # 句长过于均匀
    elif relative_std < 0.5:
        return 50
    else:
        return 30


def _check_repetitiveness(text, lang):
    """检查文本重复度"""
    if not text:
        return 0

    # 计算2-gram重复率
    words = list(text) if lang == "zh" else text.split()
    if len(words) < 10:
        return 0

    bigrams = []
    for i in range(len(words) - 1):
        bg = words[i] + (words[i + 1] if lang == "zh" else " " + words[i + 1])
        bigrams.append(bg)

    if not bigrams:
        return 0

    unique_bigrams = len(set(bigrams))
    repeat_rate = 1 - (unique_bigrams / max(len(bigrams), 1))

    if repeat_rate > 0.4:
        return 70
    elif repeat_rate > 0.2:
        return 50
    else:
        return 30


def format_report(result_before, result_after):
    """生成AI率对比报告文本"""
    before_pct = result_before.get("overall", 0)
    after_pct = result_after.get("overall", 0)
    reduction = before_pct - after_pct

    lines = [
        "=" * 40,
        "  AI疑似率评估报告",
        "=" * 40,
        f"  改写前: {before_pct:.1f}%",
        f"  改写后: {after_pct:.1f}%",
        f"  降低:   {reduction:.1f}%",
        "-" * 40,
        "  各维度对比:",
    ]

    for key in result_before.get("details", {}):
        b = result_before["details"].get(key, 0)
        a = result_after["details"].get(key, 0)
        arrow = "↓" if a < b else "↑" if a > b else "→"
        lines.append(f"    {key}: {b:.1f}% → {a:.1f}% {arrow}")

    lines.append("=" * 40)
    return "\n".join(lines)


def count_stats(text, lang="zh"):
    """统计文本基本信息"""
    if not text:
        return {"chars": 0, "words": 0, "sentences": 0}

    if lang == "zh":
        chars = len(text.replace(" ", "").replace("\n", ""))
        sentences = len(re.split(r'[。！？；\n]', text)) - 1
        words = chars  # 中文字符数作为近似
    else:
        chars = len(text)
        words = len(re.split(r'\s+', text.strip()))
        sentences = len(re.split(r'[.!?;\n]', text.strip())) - 1

    return {
        "chars": chars,
        "words": max(words, 0),
        "sentences": max(sentences, 0),
    }
