# LCLT (Limbus Company LLM Translator)
LCLT 是一个基于 LLM 的 Limbus Company 游戏翻译工具，使用官方的翻译接口。  
解决游戏没有中文翻译的问题。  

暂不成熟，代码由AI重写过，欢迎反馈。  
# 亮点
1. 翻译速度极快，保守测试一秒可以翻译几万字符（deepseek-chat）  
2. 基本可读，虽然并不是完全准确，但是已经能理解剧情/技能的意思。  
3. 增量翻译，每次只翻一点点，花费低。  
# 快速开始
从 Release 下载最新版本的 ZIP 文件，解压。  
`config.json` 中把`<Puts your Game Directory Here>`替换为您的游戏所在目录。  
`models.json` 中填写您所使用的 LLM （OpenAI 兼容），每个部分都要填，这是一个Deepseek的示例：  
```json
    "skill": {
      "api_key": "sk-********************************",
      "base_url": "https://api.deepseek.com/chat/completions",
      "model": "deepseek-chat",
      "temperature": 0.1,
      "enable_thinking": false
    }
```
在 `Font/Context/` 中放入您希望的字体文件（`.ttf` 格式）。   
然后启动 `LCLT2.exe` 即可。  
# 进阶玩法
## 配置
`config.json` 中填写基础配置:  
```json
{
  "translation_settings": {
    "origin_language": "jp",  //原始语言，推荐日语
    "target_direction": "LCLT_zh", //把翻译后的文本写到哪个文件夹中，会根据这个文件夹增量更新
    "max_workers": 500,  //最大线程数 (如果服务商，网络可以，建议设置为 200~2000，否则10以下）
    "max_chars_per_batch": 2000, //每次请求发送多少文字，建议根据模型输入上限折算，一般 2000 较好。  
    "max_retries": 4, //API请求失败后的最大重试次数（如果仍然失败则复制原文）
    "timeout": 120 //每个API请求的最大等待时间（秒）
  },
  "file_paths": {//两个位置配置
    "input_direction": "<路径>/Limbus Company/LimbusCompany_Data/Assets/Resources_moved/Localize",
    "output_direction": "<路径>/Limbus Company/LimbusCompany_Data/Lang"
  },
  "config_files": {//使用的配置文件
    "models": "models.json",
    "translation_configs": "translation_configs.json"
  },
  "options": {
    "keep_backup_files": false, //开启备份，建议关闭
    "confirm_before_translation": true //在翻译前确认，建议开启
  }
}
```
`models` 填写模型配置：
```json
"origin": { //小名为origin，在translation_configs.json将使用这个名字
  "api_key": "API KEY",
  "base_url": "URL", 
  "model": "Model Name",
  "temperature": 0.3,
  "enable_thinking": false //目前思考未测试，应该可以
},
```
`translation_configs.json` 中填写翻译策略配置：
```json
{ //一个翻译策略
  "name": "story", //翻译策略名称
  "priority": 2, //检索时的优先级，小优先级的将先检索。  
  "file_patterns": [
    // pattern 为匹配文件路径
    // extract_fields 为提取的字段，可选，默认全部提取
    {"pattern": "*BattleKeywords*", "extract_fields": ["flavor", "name"]},
    {"pattern": "*Enemies*"},
    ...
  ],
  "model": "story", //使用模型story
  "prompt_file": "prompts/story_prompt.txt", //使用的提示词
  "terminology_file": "terminology/story.json" //使用的术语库（可选）
},
```
## 提示词
可以在 `prompts/` 中填写提示词。  
## 术语库
`terminology/` 中填写术语库，在翻译前将会尝试把可用的术语先替换。

### 术语库配置
每个翻译策略可以指定自己的术语库文件，通过在 `translation_configs.json` 中添加 `terminology_file` 字段：

```json
{
  "name": "story",
  "priority": 2,
  "file_patterns": [
    {"pattern": "*BattleKeywords*", "extract_fields": ["flavor", "name"]},
    {"pattern": "*Enemies*"}
  ],
  "model": "story",
  "prompt_file": "prompts/story_prompt.txt",
  "terminology_file": "terminology/story.json" // 每个策略可以指定不同的术语库
}
```

### 术语库格式
术语库文件的格式为：

```json
{
  "terminology": {
    "ドンキホーテ": "堂吉诃德",
    "ファウスト": "浮士德",
    "グレゴール": "格里高尔"
  }
}
```

如果翻译策略没有指定术语库文件，系统会默认使用 `terminology.json` 文件。  

# 计划
- [x] 基础术语表功能
- [ ] 使用更智能的术语表。  
- [x] 按照文件名与json键的文本分类翻译。  
- [x] 多线程翻译
- [ ] 使得该项目兼容性增加，可以翻译任何类似接口的软件。
- [ ] 让LLM记录部分剧情以增强翻译
- [ ] 增加GUI
- [ ] 从系统直接获取字体

# 项目
## 翻译流程
1. 递归提取所有`LimbusCompany_Data/Assets/Resources_moved/Localize` 中指定语言的内容。
2. 根据最内层有 `"id"` 的块，比对增量差异。  
3. 集中打包交给 LLM 翻译。  
4. 解析 LLM 回复，将翻译结果写回文件。  

## 项目结构
```plain
LCLT/
├── Font/                    
│   └── Context/              
│       ...                  # 此处存放字体 (.ttf文件)
|
├── prompts/                 
│   ...                      # 此处存放翻译提示词 (.txt文件)
|
├── terminology/             
│   ...                      # 此处存放术语库 (.json文件)
│   ├── default.json         # 默认术语库
│   ├── story.json           # 故事文本术语库
│   └── skill.json           # 技能文本术语库
│   
├── src/                     # 源代码目录
│   ├── config/              
│   │   └── loader.py        # 配置加载器
│   ├── core/                
│   │   ├── extractor.py     # 文本提取器
│   │   ├── translator.py    # 翻译器
│   │   ├── utils.py         # 工具函数
│   │   └── writer.py        # 结果写入器
│   └── main.py              # 主程序入口
├── BlackList.json           # 黑名单配置
├── config.json              # 主配置文件
├── models.json              # 模型配置文件
├── requirements.txt         # 依赖包列表
├── run.py                   # 运行脚本 (Python)
├── terminology.json         # 术语库
|── translation_configs.json # 翻译策略配置
├── README.md                
└── LICENSE
```

# 致谢
- 部分翻译提示词参考了 [零协会](https://github.com/LocalizeLimbusCompany/LocalizeLimbusCompany) 的翻译成果，特别感谢。