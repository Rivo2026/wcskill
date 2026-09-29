# Jev FS 选择器配置

本文件定义使用 Jev 模型进行 Few-Shot 选择的配置。

## 访问配置

**推荐方式**：OpenRouter
- 模型ID: `typesafe/jev-1.13`
- 价格: $0.042/百万 input tokens
- 或使用 `typesafe/jev-latest` 获取最新版本

**备选方式**：Cloudflare Workers AI
- 模型ID: `typesafe/jev`
- 32K token 上下文窗口

---

## 输入结构

### State（状态）

从正文提取的特征：

```javascript
{
  content: "正文完整内容",
  features: {
    // 结构特征
    has_counterintuitive_relation: boolean,  // 有反常因果关系
    has_success_metrics: boolean,            // 有具体成果数据
    has_enumeration_structure: boolean,      // 有明确列举结构
    
    // 内容特征
    has_why_explanation: boolean,            // 有"为什么"解释
    has_how_to_guide: boolean,               // 有"怎么做"指导
    has_multiple_cases: boolean,             // 有多个案例
    has_person_story: boolean,               // 有人物故事
    
    // 表达特征
    tone: "formal" | "conversational" | "technical",
    word_count: number,
    
    // FS-001 特征
    has_positive_condition: boolean,         // 有"通常被认为是好事"的条件
    has_negative_result: boolean,            // 有可观测负面结果
    has_progressive_relation: boolean,       // 有递进关系（越...越...）
    
    // FS-002 特征
    has_concrete_numbers: boolean,           // 有具体数字（粉丝/收入/播放）
    has_operator_description: boolean,       // 有操作主体描述
    has_simple_method: boolean,              // 有"一个技巧/方法"
    
    // FS-003 特征
    has_self_check_judgment: boolean,        // 有可自审的判断
    has_fear_target: boolean,                // 有恐惧指向目标
    has_numbered_items: boolean              // 有明确数量的项（两个/三个/四个）
  }
}
```

### Questions（问题）

```javascript
{
  // 主问题：选择最佳 FS
  best_fs: {
    type: "choice",
    question: "根据正文特征，哪个 Few-Shot 模板最适合生成开头？",
    choices: {
      "FS-001": "反常归因 → 递进反差 → 问题命名。适合：正文有反常因果关系需要解释，有'为什么会这样'的核心解答。",
      "FS-002": "形象反差 → 价值倒挂 → 技巧承诺。适合：正文有具体成果数据+操作主体+简单方法，能形成'我也能做到'的感觉。",
      "FS-003": "直接判断 → 恐惧强化 → 误区框架。适合：正文列举2-4个误区/问题，需要观众对照自审。"
    }
  },
  
  // 辅助问题：每个 FS 的匹配度
  fs001_match: {
    type: "score",
    question: "FS-001（反常归因）与正文的匹配度（0-100分）",
    scale: { min: 0, max: 100 }
  },
  
  fs002_match: {
    type: "score",
    question: "FS-002（形象反差）与正文的匹配度（0-100分）",
    scale: { min: 0, max: 100 }
  },
  
  fs003_match: {
    type: "score",
    question: "FS-003（判断缺口）与正文的匹配度（0-100分）",
    scale: { min: 0, max: 100 }
  },
  
  // 元问题：是否所有 FS 都不匹配
  need_custom: {
    type: "noul",
    question: "正文特征与所有现有 FS 都不匹配，需要定制开头",
    criteria: "所有 FS 匹配度都低于 60 分"
  }
}
```

---

## 输出结构

```javascript
{
  best_fs: {
    value: "FS-001",              // 推荐的 FS
    confidence: 0.88,             // 置信度（0-1）
    probabilities: {              // 每个选项的概率
      "FS-001": 0.85,
      "FS-002": 0.03,
      "FS-003": 0.12
    }
  },
  fs001_match: {
    value: 85,                    // 匹配度分数
    confidence: 0.92              // 对这个分数的置信度
  },
  fs002_match: {
    value: 15,
    confidence: 0.88
  },
  fs003_match: {
    value: 50,
    confidence: 0.85
  },
  need_custom: {
    probability: 0.05,            // 需要定制的概率
    confidence: 0.90
  }
}
```

---

## 决策规则

根据 Jev 输出决定下一步动作：

### 1. 高置信度推荐（confidence ≥ 0.8）

```
如果 best_fs.confidence ≥ 0.8 且 best_fs.probabilities[推荐] ≥ 0.7：
  → 直接使用推荐的 FS
  → 输出："推荐使用 {FS}（置信度：{confidence}%）"
```

### 2. 中等置信度（0.5 ≤ confidence < 0.8）

```
如果 0.5 ≤ best_fs.confidence < 0.8：
  → 使用推荐的 FS，但提示匹配度中等
  → 输出："推荐使用 {FS}（置信度：{confidence}%，可能需要一定改写）"
```

### 3. 低置信度（confidence < 0.5）

```
如果 best_fs.confidence < 0.5 或 need_custom.probability > 0.6：
  → 提示所有 FS 匹配度都不高
  → 输出："所有 FS 匹配度都较低，建议定制开头或选择匹配度相对最高的 {FS}（{score}分）"
```

### 4. 用户强制指定

```
如果用户明确指定 FS（例如 "用 FS-003"）：
  → 显示该 FS 的匹配度和置信度
  → 如果匹配度 < 60，提示："FS-003 匹配度较低（{score}分），可能需要较大改写，是否继续？"
  → 用户确认后继续生成
```

---

## 特征提取方法

在调用 Jev 前，需要从正文提取特征。使用简单规则检测：

### 结构特征检测

```python
def extract_features(content: str) -> dict:
    features = {}
    
    # 反常关系检测
    features['has_counterintuitive_relation'] = (
        '越' in content and '就越' in content or
        '反而' in content or
        '却' in content
    )
    
    # 成果数据检测
    features['has_success_metrics'] = bool(
        re.search(r'(\d+万|\d+千万|\d+亿)粉丝|播放|收入', content)
    )
    
    # 列举结构检测
    features['has_enumeration_structure'] = (
        '第一' in content and '第二' in content or
        '误区一' in content or
        bool(re.search(r'[两三四]个(误区|问题|原因|陷阱)', content))
    )
    
    # ... 其他特征检测
    
    return features
```

### 调用 Jev

```python
import requests

def select_fs_with_jev(content: str) -> dict:
    # 1. 提取特征
    features = extract_features(content)
    
    # 2. 构造 Jev 请求
    request = {
        "state": {
            "content": content[:2000],  # 截取前2000字
            "features": features
        },
        "questions": {
            "best_fs": { ... },
            "fs001_match": { ... },
            # ... 其他问题
        }
    }
    
    # 3. 调用 Jev API
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "typesafe/jev-1.13",
            "messages": [{"role": "user", "content": json.dumps(request)}]
        }
    )
    
    # 4. 解析结果
    result = response.json()
    return result
```

---

## 校准置信度

根据 [Can You Trust Jev's Confidence?](https://anth.us/blog/can-you-trust-jev-confidence/) 的建议，需要记录历史数据进行校准：

### 校准数据收集

每次生成后记录：
```json
{
  "content_id": "xxx",
  "jev_recommendation": "FS-001",
  "jev_confidence": 0.88,
  "jev_probabilities": {...},
  "actual_result": "success" | "needs_revision" | "failed",
  "user_feedback": "好" | "需要改" | "完全不对"
}
```

### 校准曲线建立

根据历史数据计算：
- 当 Jev 说 confidence=0.9 时，实际成功率是多少？
- 建立映射：raw_confidence → calibrated_confidence

### 动态调整阈值

根据校准结果调整决策阈值：
```
如果发现 confidence ≥ 0.8 时实际成功率只有 70%：
  → 提高阈值到 confidence ≥ 0.85
```

---

## 集成到 SKILL.md

在 SKILL.md 第0步加入：

```markdown
**0. 选择 FS（使用 Jev）**

如果用户未指定 FS：
  1. 提取正文特征（见 jev-fs-selector.md）
  2. 调用 Jev 获取推荐和置信度
  3. 根据决策规则选择 FS 或提示用户
  
如果用户明确指定 FS：
  1. 直接使用指定的 FS
  2. （可选）显示该 FS 的 Jev 匹配度供参考
```

---

## 成本估算

**OpenRouter 价格**：$0.042/百万 input tokens

**单次 FS 选择成本**：
- 正文 2000 字 ≈ 3000 tokens
- 特征描述 ≈ 500 tokens
- 问题定义 ≈ 500 tokens
- **总计**：~4000 tokens = $0.000168/次

**对比人工判断**：
- 人工读正文 + 判断 FS：约 2-5 分钟
- Jev 响应时间：< 1 秒
- **效率提升**：120x - 300x

---

## 注意事项

1. **Jev 不是 LLM**：它不生成文本，只做决策
2. **置信度需要校准**：初期收集数据，建立校准曲线
3. **特征提取很重要**：Jev 的判断质量取决于输入特征的准确性
4. **保留人工覆盖**：允许用户强制指定 FS，不完全依赖 Jev
5. **持续优化**：根据历史成功率调整特征提取规则和决策阈值
