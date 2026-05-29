将会尽快重构代码
# LCLT (Limbus Company LLM Translator)

LCLT 是一个基于 LLM 的《边狱巴士》游戏翻译工具。  
专为高速翻译而生，多线程批量处理，增量翻译节省 API 费用。

## 亮点

1. **翻译速度极快** — 多线程并行，四分钟内翻译开服至第八章全部文本
2. **保留专有名词** — 术语库预替换 + 正则校验，防止歧义
3. **增量翻译** — 每次只翻新增/变更内容，花费低

## 快速开始

```bash
git clone https://github.com/Killian2026/LimbusCompanyLLMTranslator.git
cd LimbusCompanyLLMTranslator
pip install -r requirements.txt
python run.py
```

## 配置说明

### `config.json` — 基础配置

```json
{
  "translation_settings": {
    "origin_language": "jp",
    "target_direction": "LCLT_zh",
    "max_workers": 50,
    "max_chars_per_batch": 8000,
    "max_retries": 4,
    "timeout": 60
  },
  "file_paths": {
    "input_direction": "<游戏目录>/LimbusCompany_Data/Assets/Resources_moved/Localize",
    "output_direction": "<游戏目录>/LimbusCompany_Data/Lang"
  },
  "options": {
    "keep_backup_files": true,
    "confirm_before_translation": true,
    "generate_debug_file": false
  }
}
```

| 参数 | 说明 |
|------|------|
| `origin_language` | 源语言，建议 `jp` |
| `target_direction` | 翻译输出目录名 |
| `max_workers` | 最大线程数（建议 20-100） |
| `max_chars_per_batch` | 每次 API 请求的字符上限 |
| `max_retries` | API 失败重试次数 |
| `timeout` | API 超时秒数 |

### `models.json` — 模型配置

```json
{
  "models": {
    "main": {
      "api_key": "sk-xxxxxxxx",
      "base_url": "https://api.deepseek.com/chat/completions",
      "model": "deepseek-v4-flash",
      "temperature": 0,
      "enable_thinking": false
    }
  }
}
```

支持 OpenAI 兼容接口，可添加多个模型供不同翻译策略使用。

### `translation_configs.json` — 翻译策略

```json
{
  "translation_strategies": [
    {
      "name": "story",
      "priority": 2,
      "file_patterns": [
        {"pattern": "*BattleKeywords*", "extract_fields": ["flavor", "name"]},
        {"pattern": "*Enemies*"},
        {"pattern": "StoryData/*"}
      ],
      "model": "main",
      "prompt_file": "prompts/story_prompt.txt",
      "terminology_file": "terminology/story.json"
    }
  ]
}
```

- `priority` — 越小越优先匹配，`999` 为兜底策略
- `file_patterns` — glob 匹配规则，`extract_fields` 可选指定提取字段
- `model` — 引用 `models.json` 中的模型名称
- `prompt_file` — 翻译提示词文件
- `terminology_file` — 术语库文件（可选）

## 提示词

在 `prompts/` 中编写翻译提示词，策略通过 `prompt_file` 引用。

## 术语库

格式为 `terminology/*.json`，翻译前先替换术语再发送 API：

```json
{
  "terminology": {
    "ドンキホーテ": "堂吉诃德",
    "ファウスト": "浮士德"
  }
}
```

## 翻译流程

1. 递归提取 `Localize` 目录中指定语言的文本
2. 根据含 `"id"` 的块做增量对比
3. 按策略分批，术语预替换后交由 LLM 翻译
4. 解析回复写回 `Lang` 目录

## 项目结构

```plain
LCLT/
├── Font/Context/              # 字体文件 (.ttf)
├── prompts/                   # 翻译提示词 (.txt)
├── terminology/               # 术语库 (.json)
├── src/
│   ├── config/loader.py       # 配置加载器
│   ├── core/
│   │   ├── extractor.py       # 文本提取器
│   │   ├── translator.py      # 翻译器
│   │   ├── utils.py           # 工具函数
│   │   └── writer.py          # 结果写入器
│   └── main.py                # 主程序入口
├── run.py                     # CLI 入口
├── config.json                # 主配置
├── models.json                # 模型配置
├── translation_configs.json   # 翻译策略
├── BlackList.json             # 黑名单
└── requirements.txt
```

## 致谢

- 部分翻译提示词参考了 [零协会](https://github.com/LocalizeLimbusCompany/LocalizeLimbusCompany) 的翻译成果，特别感谢。
