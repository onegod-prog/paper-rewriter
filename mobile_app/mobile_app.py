"""论文降重工具 - 移动Web APP端
作者: onegod
运行后手机在浏览器访问本机IP:5000 即可使用"""

import sys
import os

# 确保可以引用主项目的模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import socket
from flask import Flask, request, jsonify, render_template

from rewriter_local import LocalRewriter
from rewriter_api import ApiRewriter
from utils import estimate_ai_probability

app = Flask(__name__)
app.config['TEMPLATE_FOLDER'] = os.path.join(os.path.dirname(__file__), 'templates')

local_rewriter = LocalRewriter()
api_rewriter = ApiRewriter()


def get_local_ip():
    """获取本机局域网IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@app.route('/')
def index():
    """移动端主页"""
    return render_template('mobile.html')


# ========== API 接口 ==========

@app.route('/api/rewrite', methods=['POST'])
def api_rewrite():
    """全文改写"""
    data = request.get_json()
    text = data.get('text', '').strip()
    lang = data.get('lang', 'zh')
    intensity = data.get('intensity', 'medium')
    mode = data.get('mode', 'local')
    strategies = data.get('strategies', ['synonym', 'pattern', 'voice', 'connector'])

    if not text:
        return jsonify({'error': '文本不能为空'}), 400

    try:
        if mode == 'api':
            if not api_rewriter.is_configured:
                return jsonify({'error': 'API未配置，请在设置中填写API密钥'}), 400
            rewritten = api_rewriter.rewrite_sync(text, lang, intensity)
            stats = {}
        else:
            result = local_rewriter.rewrite(text, lang, intensity, strategies)
            rewritten = result['text']
            stats = result['stats']

        before = estimate_ai_probability(text, lang)
        after = estimate_ai_probability(rewritten, lang)

        return jsonify({
            'original': text,
            'rewritten': rewritten,
            'stats': stats,
            'evaluation': {
                'before': before['overall'],
                'after': after['overall'],
                'details_before': before.get('details', {}),
                'details_after': after.get('details', {}),
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rewrite_selection', methods=['POST'])
def api_rewrite_selection():
    """选中改写 (局部改写)"""
    data = request.get_json()
    original = data.get('original', '').strip()
    selection = data.get('selection', '').strip()
    lang = data.get('lang', 'zh')
    intensity = data.get('intensity', 'medium')
    mode = data.get('mode', 'local')
    strategies = data.get('strategies', ['synonym', 'pattern', 'voice', 'connector'])

    if not original or not selection:
        return jsonify({'error': '原文和选中内容不能为空'}), 400

    try:
        if mode == 'api':
            if not api_rewriter.is_configured:
                return jsonify({'error': 'API未配置'}), 400
            rewritten_sel = api_rewriter.rewrite_sync(selection, lang, intensity)
            stats = {}
        else:
            result = local_rewriter.rewrite(selection, lang, intensity, strategies)
            rewritten_sel = result['text']
            stats = result['stats']

        # 替换原文中的选中部分
        rewritten_full = original.replace(selection, rewritten_sel, 1)

        before = estimate_ai_probability(original, lang)
        after = estimate_ai_probability(rewritten_full, lang)

        return jsonify({
            'original': original,
            'rewritten': rewritten_full,
            'selection_original': selection,
            'selection_rewritten': rewritten_sel,
            'stats': stats,
            'evaluation': {
                'before': before['overall'],
                'after': after['overall'],
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rewrite_sentences', methods=['POST'])
def api_rewrite_sentences():
    """按句子列表改写 (查重报告模式)"""
    data = request.get_json()
    original = data.get('original', '').strip()
    sentences = data.get('sentences', [])
    lang = data.get('lang', 'zh')
    intensity = data.get('intensity', 'medium')
    mode = data.get('mode', 'local')
    strategies = data.get('strategies', ['synonym', 'pattern', 'voice', 'connector'])

    if not original or not sentences:
        return jsonify({'error': '原文和句子列表不能为空'}), 400

    try:
        result = original
        rewritten_sentences = []
        total_count = 0

        for sentence in sentences:
            if sentence not in result:
                continue

            if mode == 'api':
                new_text = api_rewriter.rewrite_sync(sentence, lang, intensity)
            else:
                r = local_rewriter.rewrite(sentence, lang, intensity, strategies)
                new_text = r['text']

            result = result.replace(sentence, new_text, 1)
            rewritten_sentences.append({
                'original': sentence,
                'rewritten': new_text
            })
            total_count += 1

        before = estimate_ai_probability(original, lang)
        after = estimate_ai_probability(result, lang)

        return jsonify({
            'original': original,
            'rewritten': result,
            'matched_count': total_count,
            'sentences': rewritten_sentences,
            'evaluation': {
                'before': before['overall'],
                'after': after['overall'],
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/evaluate', methods=['POST'])
def api_evaluate():
    """评估AI率"""
    data = request.get_json()
    text = data.get('text', '').strip()
    lang = data.get('lang', 'zh')

    if not text:
        return jsonify({'error': '文本不能为空'}), 400

    result = estimate_ai_probability(text, lang)
    return jsonify({
        'score': result['overall'],
        'details': result['details'],
    })


@app.route('/api/config_api', methods=['POST'])
def api_config():
    """配置API"""
    data = request.get_json()
    api_rewriter.configure(
        api_key=data.get('api_key', ''),
        api_url=data.get('api_url', api_rewriter.api_url),
        model=data.get('model', api_rewriter.model),
        temperature=float(data.get('temperature', 0.8)),
    )
    return jsonify({'status': 'ok'})


@app.route('/api/status')
def api_status():
    """获取服务状态"""
    return jsonify({
        'status': 'running',
        'api_configured': api_rewriter.is_configured,
        'author': 'onegod',
        'version': '1.0',
    })


if __name__ == '__main__':
    ip = get_local_ip()
    banner = f"""
{'='*50}
  论文降重工具 - 移动Web APP
  作者: onegod
{'='*50}

  [手机访问]  http://{ip}:5000
  [本机访问]  http://127.0.0.1:5000

  确保手机和电脑在同一个WiFi下
  按 Ctrl+C 停止服务
{'='*50}
"""
    print(banner.strip())
    app.run(host='0.0.0.0', port=5000, debug=False)
