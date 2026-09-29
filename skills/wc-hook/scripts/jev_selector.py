#!/usr/bin/env python3
"""
Jev FS 选择器 V3 - 开头效果评估版
核心逻辑：不是判断正文有什么，而是判断用哪个 FS 写出来的开头更吸引人
"""

import re
import json
import os
import requests
from typing import Dict, Any, Optional

# TypeSafe AI Jev API 配置
TYPESAFE_API_KEY = os.environ.get("TYPESAFE_API_KEY")
TYPESAFE_API_URL = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = "jev-latest"

# FS 效果描述（从开头效果角度描述）
FS_EFFECT_DESCRIPTIONS = {
    "FS-001": "反常归因开头：用'A正面→B负面'的反常关系制造困惑，让观众想知道'为什么会这样'。例如'上班能力越强，创业思维越差'。适合有机制解释的内容。",
    "FS-002": "形象反差开头：用'普通人+大成果+简单方法'制造价值倒挂，让观众想学'我也能做到'。例如'普通中年男人，2000万粉丝账号，一个技巧'。适合有技巧揭秘的内容。",
    "FS-003": "判断缺口开头：用'你符合几条'制造自审焦虑，让观众想对照'我是不是也这样'。例如'能不能做自媒体，取决于这3个前提'。适合有误区/条件列举的内容。",
    "FS-004": "双驱动开头：用'优势变陷阱'制造认知冲击，让观众既想理解又想自审。例如'厌蠢是赚钱的敌人'。适合有心理机制分析的内容。",
    "FS-005": "联系缺口开头：用'看似无关的AB的联系'制造时代洞察感，让观众想知道'它们怎么联系上的'。例如'在2026年，高考热度和自媒体策略有什么关系'。适合有跨领域洞察的内容。"
}


def extract_features(content: str) -> Dict[str, Any]:
    """从正文提取特征"""
    features = {}

    # 结构特征
    features['has_counterintuitive_relation'] = bool(
        ('越' in content and '就越' in content) or '反而' in content or '却' in content
    )
    features['has_success_metrics'] = bool(
        re.search(r'(\d+万|\d+千万|\d+亿)(粉丝|播放|收入|关注)', content)
    )
    features['has_enumeration_structure'] = bool(
        ('第一' in content and '第二' in content) or
        '误区一' in content or
        re.search(r'[两三四五]个(误区|问题|原因|陷阱|前提|条件)', content)
    )

    # 内容特征
    features['has_why_explanation'] = bool(
        '为什么' in content or '原因' in content or '机制' in content
    )
    features['has_how_to_guide'] = bool(
        '怎么' in content or '如何' in content or '方法' in content or '步骤' in content
    )
    features['has_multiple_cases'] = len(re.findall(r'(比如|例如|案例)', content)) >= 2

    features['word_count'] = len(content)

    return features


def call_jev_evaluate_opening(content: str, features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    核心：评估用各个 FS 写出来的开头效果
    """
    jev_request = {
        "model": JEV_MODEL,
        "state": {
            "content": content[:2000],
            "features": features
        },
        "questions": {
            "best_opening_fs": {
                "type": "choice",
                "instructions": "假设用这5个 Few-Shot 模板分别给这篇正文写开头。哪个 FS 写出来的开头最能吸引观众停留、让人想继续看？不是判断正文有什么，而是判断开头效果。",
                "criteria": FS_EFFECT_DESCRIPTIONS
            },
            "fs001_opening_appeal": {
                "type": "score",
                "instructions": "如果用 FS-001（反常归因）写开头，这个开头的吸引力有多强？评估：①能否制造强烈的认知冲突②观众会不会想知道'为什么'③开头是否足够简洁有力",
                "criteria": [
                    "吸引力很弱（0-20分）：制造不出反常感，观众不会好奇",
                    "吸引力较弱（21-40分）：有一点反常但不够强，观众可能划走",
                    "吸引力中等（41-60分）：有反常感，部分观众会好奇",
                    "吸引力较强（61-80分）：反常感明显，多数观众想知道原因",
                    "吸引力很强（81-100分）：强烈认知冲击，观众必须看下去"
                ]
            },
            "fs002_opening_appeal": {
                "type": "score",
                "instructions": "如果用 FS-002（形象反差）写开头，这个开头的吸引力有多强？评估：①能否制造价值倒挂感②观众会不会想学'怎么做到'③是否有足够的成果数据可以包装",
                "criteria": [
                    "吸引力很弱（0-20分）",
                    "吸引力较弱（21-40分）",
                    "吸引力中等（41-60分）",
                    "吸引力较强（61-80分）",
                    "吸引力很强（81-100分）"
                ]
            },
            "fs003_opening_appeal": {
                "type": "score",
                "instructions": "如果用 FS-003（判断缺口）写开头，这个开头的吸引力有多强？评估：①能否制造自审焦虑②观众会不会想对照'我符合几条'③是否有足够的误区/条件可以列举",
                "criteria": [
                    "吸引力很弱（0-20分）",
                    "吸引力较弱（21-40分）",
                    "吸引力中等（41-60分）",
                    "吸引力较强（61-80分）",
                    "吸引力很强（81-100分）"
                ]
            },
            "fs004_opening_appeal": {
                "type": "score",
                "instructions": "如果用 FS-004（双驱动）写开头，这个开头的吸引力有多强？评估：①能否制造'优势变陷阱'的认知冲击②观众会不会既想理解又想自审③是否有心理机制可以挖掘",
                "criteria": [
                    "吸引力很弱（0-20分）",
                    "吸引力较弱（21-40分）",
                    "吸引力中等（41-60分）",
                    "吸引力较强（61-80分）",
                    "吸引力很强（81-100分）"
                ]
            },
            "fs005_opening_appeal": {
                "type": "score",
                "instructions": "如果用 FS-005（联系缺口）写开头，这个开头的吸引力有多强？评估：①能否制造'看似无关的联系'②观众会不会想知道'它们怎么联系上的'③是否有跨领域洞察可以呈现",
                "criteria": [
                    "吸引力很弱（0-20分）",
                    "吸引力较弱（21-40分）",
                    "吸引力中等（41-60分）",
                    "吸引力较强（61-80分）",
                    "吸引力很强（81-100分）"
                ]
            }
        }
    }

    return _call_jev_api(jev_request)


def _call_jev_api(jev_request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """调用 Jev API"""
    if not TYPESAFE_API_KEY:
        print("❌ 未配置 TYPESAFE_API_KEY；请设置 TypeSafe AI API key，或按 Skill 规则手动选择 FS。")
        return None
    try:
        response = requests.post(
            TYPESAFE_API_URL,
            headers={
                "Authorization": f"Bearer {TYPESAFE_API_KEY}",
                "Content-Type": "application/json"
            },
            json=jev_request,
            timeout=30
        )

        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"❌ Jev API 调用失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"错误详情: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
            except:
                print(f"错误响应: {e.response.text}")
        return None


def score_to_value(score_result: Dict[str, Any]) -> int:
    """将 Jev 的 score 映射到 0-100 分"""
    score_index = score_result['score']
    return int(score_index * 20 + 10)


def select_fs_by_opening_effect(content: str, force_fs: Optional[str] = None) -> Dict[str, Any]:
    """
    根据开头效果选择 FS
    """
    # 提取特征
    features = extract_features(content)

    # 调用 Jev 评估开头效果
    result = call_jev_evaluate_opening(content, features)

    if not result:
        return {'error': 'Jev API 调用失败', 'recommended_fs': None}

    answers = result['answers']

    # 获取推荐的 FS
    best_fs = answers['best_opening_fs']['choice']
    confidence = answers['best_opening_fs']['confidence']
    probabilities = answers['best_opening_fs']['probabilities']

    # 获取各 FS 的开头吸引力分数
    appeal_scores = {
        'FS-001': score_to_value(answers['fs001_opening_appeal']),
        'FS-002': score_to_value(answers['fs002_opening_appeal']),
        'FS-003': score_to_value(answers['fs003_opening_appeal']),
        'FS-004': score_to_value(answers['fs004_opening_appeal']),
        'FS-005': score_to_value(answers['fs005_opening_appeal'])
    }

    # 如果用户强制指定
    if force_fs:
        appeal = appeal_scores.get(force_fs, 0)
        return {
            'recommended_fs': force_fs,
            'confidence': 1.0,
            'opening_appeal': appeal,
            'all_appeal_scores': appeal_scores,
            'decision': 'use_forced',
            'message': f"✅ 使用指定的 {force_fs}（开头吸引力：{appeal}分）"
        }

    # 决策规则
    recommendation = {
        'recommended_fs': best_fs,
        'confidence': confidence,
        'probabilities': probabilities,
        'opening_appeal': appeal_scores[best_fs],
        'all_appeal_scores': appeal_scores,
        'decision': '',
        'message': ''
    }

    # 根据置信度和吸引力决策
    if confidence >= 0.8 and appeal_scores[best_fs] >= 70:
        recommendation['decision'] = 'use_recommended'
        recommendation['message'] = f"✅ 推荐使用 {best_fs}\n   置信度：{confidence*100:.0f}%\n   开头吸引力：{appeal_scores[best_fs]}分"
    elif confidence >= 0.5 or appeal_scores[best_fs] >= 60:
        recommendation['decision'] = 'use_with_caution'
        recommendation['message'] = f"⚠️ 推荐使用 {best_fs}\n   置信度：{confidence*100:.0f}%\n   开头吸引力：{appeal_scores[best_fs]}分（可用但可能需要打磨）"
    else:
        best_score_fs = max(appeal_scores, key=appeal_scores.get)
        recommendation['decision'] = 'suggest_best_score'
        recommendation['message'] = f"⚠️ 置信度较低（{confidence*100:.0f}%），但可以尝试 {best_score_fs}（吸引力{appeal_scores[best_score_fs]}分）"

    return recommendation


def main():
    """命令行测试入口"""
    import sys

    if len(sys.argv) < 2:
        print("用法: python jev_selector_v3.py <正文文件路径> [强制指定的FS]")
        sys.exit(1)

    content_file = sys.argv[1]
    force_fs = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        with open(content_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ 文件不存在: {content_file}")
        sys.exit(1)

    print(f"\n📄 正文长度: {len(content)} 字")
    print("\n🔍 提取特征中...")

    features = extract_features(content)
    print(f"\n✅ 特征提取完成")

    print("\n" + "="*60)
    print("🎯 评估用各个 FS 写开头的效果...")
    print("="*60)

    result = select_fs_by_opening_effect(content, force_fs)

    if 'error' in result:
        print(f"\n❌ {result['error']}")
        sys.exit(1)

    print(f"\n{result['message']}")
    print(f"\n📊 各 FS 开头吸引力评分:")
    for fs, score in sorted(result['all_appeal_scores'].items(), key=lambda x: x[1], reverse=True):
        prob = result.get('probabilities', {}).get(fs, 0)
        print(f"  {fs}: {score}分 (被选中概率: {prob*100:.0f}%)")


if __name__ == '__main__':
    main()
