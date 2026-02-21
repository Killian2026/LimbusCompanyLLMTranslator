import time
import os
import shutil
from typing import List, Dict, Any
from src.core.extractor import TextExtractor
from src.core.translator import Translator
from src.core.writer import FileWriter
from src.core.utils import FileUtils, TextUtils
from src.config.loader import config_loader

class LCLT:
    """Limbus Company Localization Tool 主类"""
    
    def __init__(self):
        # 备份原始配置文件
        self.original_config = config_loader.get_config().copy()
        self.config = self.original_config
        self.extractor = TextExtractor()
        self.translator = Translator()
        self.writer = FileWriter()
        self.blacklist = config_loader.get_blacklist()
    
    def update(self, lang: str = None, target_dir: str = None, test: bool = False, log: bool = False) -> None:
        """
        更新翻译，提取原文内容，比对已有译文，翻译新增内容并写回
        
        参数:
        lang: 源语言代码
        target_dir: 目标语言目录
        test: 是否为测试模式
        log: 是否记录日志
        """
        # 使用默认值或传入参数
        lang = lang or self.config["translation_settings"]["origin_language"]
        target_dir = target_dir or self.config["translation_settings"]["target_direction"]
        
        print(f"正在提取原文内容，此过程可能需要若干分钟")
        
        if test:
            origin = self.extractor.extract_files_content("test_dir_in", lang)
            existing = self.extractor.extract_files_content("test_dir_out", target_dir)
        else:
            origin = self.extractor.extract_files_content("input_direction", lang)
            existing = self.extractor.extract_files_content("output_direction", target_dir)

        print(f"正在比对文件，增量内容")
        delta = self.extractor.find_new_content(origin, existing)
        
        if log:
            FileUtils.backup_translation_result(delta, "Delta")
            FileUtils.backup_translation_result(origin, "Ori")
            FileUtils.backup_translation_result(existing, "Old")
        
        # 计算要翻译的字符总数
        total_chars = 0
        for file in delta:
            if "content" in file and "dataList" in file["content"]:
                for item in file["content"]["dataList"]:
                    # 递归计算所有文本的字符数
                    def count_chars(obj):
                        nonlocal total_chars
                        if isinstance(obj, str):
                            total_chars += len(obj.encode('utf-8'))
                        elif isinstance(obj, dict):
                            for value in obj.values():
                                count_chars(value)
                        elif isinstance(obj, list):
                            for item in obj:
                                count_chars(item)
                    count_chars(item)
        
        print(f"检索完毕，发现 {total_chars} 个字符需要翻译！")
        
        # 检查是否需要用户确认
        confirm_before_translation = self.config.get("options", {}).get("confirm_before_translation", True)
        if confirm_before_translation:
            user_input = input(f"是否确认翻译 {total_chars} 个字符？(y/n): ")
            if user_input.lower() != 'y':
                print("翻译已取消！")
                return
        
        # 记录翻译开始时间
        start_time = time.time()
        translated = self.modify(delta)
        # 计算翻译用时
        elapsed_time = time.time() - start_time
        print(f"翻译耗时: {elapsed_time:.2f}秒 ({elapsed_time/60:.2f}分钟)")

        # 在翻译完成后保存翻译结果到备份文件
        print(f"翻译完成，正在备份翻译文件")
        if log:
            FileUtils.backup_translation_result(translated, "translation_result")
         
        print(f"备份完成，正在汉化接口中写新文件")
        if test:
            self.writer.putback(translated, "test_dir_out", target_dir)
        else:
            self.writer.putback(translated, "output_direction", target_dir)

        # 检测并复制Font文件夹
        print(f"正在检测Font文件夹...")
        if not test:
            # 获取输出目录
            output_dir = self.config["file_paths"].get("output_direction", "")
            # 构建目标Font文件夹路径
            target_font_dir = os.path.join(output_dir, target_dir, "Font")
            # 构建源Font文件夹路径
            source_font_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Font")
            
            # 检查目标Font文件夹是否存在
            if not os.path.exists(target_font_dir):
                print(f"目标Font文件夹不存在，正在复制...")
                try:
                    # 复制Font文件夹
                    shutil.copytree(source_font_dir, target_font_dir)
                    print(f"Font文件夹复制成功！")
                except Exception as e:
                    print(f"Font文件夹复制失败: {e}")
            else:
                print(f"目标Font文件夹已存在，跳过复制。")

        # 检查是否需要删除backup文件
        keep_backup_files = self.config.get("options", {}).get("keep_backup_files", True)
        if not keep_backup_files:
            print(f"正在清理backup文件...")
            import glob
            backup_files = glob.glob("backup_*.json")
            for file in backup_files:
                if os.path.exists(file):
                    try:
                        os.remove(file)
                        print(f"已删除backup文件: {file}")
                    except Exception as e:
                        print(f"删除backup文件 {file} 时出错: {e}")
        
        print(f"工作结束！")
    
    def load(self, lang: str, output_dir: str = "output_direction") -> None:
        """
        从good.json直接提取翻译结果，然后执行putback操作
        
        参数:
        lang: 语言代码
        output_dir: 输出目录
        """
        import json
        with open("good.json", 'r', encoding='utf-8-sig') as f:
            translated = json.load(f)

        self.writer.putback(translated, output_dir, lang)
    
    def modify(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        处理文件列表，提取文本并翻译
        
        参数:
        files: 文件列表
        
        返回:
        翻译后的文件列表
        """
        # 收集所有翻译任务
        all_translation_tasks = []
        # 记录已处理的字段路径，确保每个字段只被一个策略处理
        processed_fields = set()
        # 记录任务位置信息
        task_positions = []
        
        # 第一步：收集所有翻译任务
        for i, file in enumerate(files):
            if "content" not in file or "dataList" not in file["content"]:
                continue

            # 获取文件路径
            file_path = file.get("rel_path", "")
            
            # 获取所有匹配的翻译策略
            strategies = config_loader.get_strategies_for_file(file_path)
            
            data_list = file["content"]["dataList"]
            # 为每个dataList项目创建一个索引
            for j, item in enumerate(data_list):
                # 对每个策略，提取其指定的字段
                for strategy in strategies:
                    strategy_name = strategy.get("name", "default")
                    extract_fields = strategy.get("extract_fields", None)
                    
                    # 从每个dataList项目开始递归提取文本
                    extracted = TextUtils.extract_text_recursive(item, self.blacklist, [j], extract_fields)
                    for path, text in extracted:
                        # 检查该字段是否已经被处理过
                        field_path_tuple = (i, tuple(path))
                        if field_path_tuple in processed_fields:
                            continue
                        
                        # 标记该字段为已处理
                        processed_fields.add(field_path_tuple)
                        
                        # 获取模型配置
                        model_name = strategy.get("model", "deepseek")
                        model_config = config_loader.get_model_config(model_name)
                        
                        # 获取API配置
                        api_key = model_config.get("api_key", "")
                        base_url = model_config.get("base_url", "")
                        model = model_config.get("model", "deepseek-chat")
                        temperature = model_config.get("temperature", 0.1)
                        enable_thinking = model_config.get("enable_thinking", False)
                        prompt_file = strategy.get("prompt_file", "prompt.txt")
                        
                        # 添加到翻译任务列表
                        task = {
                            "text": text,
                            "api_key": api_key,
                            "base_url": base_url,
                            "model": model,
                            "temperature": temperature,
                            "enable_thinking": enable_thinking,
                            "prompt_file": prompt_file,
                            "index": len(all_translation_tasks)  # 任务索引
                        }
                        all_translation_tasks.append(task)
                        task_positions.append((i, path))  # 记录任务对应的文件和路径
        
        # 第二步：集中处理所有翻译任务
        if all_translation_tasks:
            print(f"\n共收集到 {len(all_translation_tasks)} 个翻译任务")
            
            # 使用新的批量翻译方法
            translations_map = self.translator.batch_translate_with_multiple_strategies(all_translation_tasks)
            
            # 第三步：将翻译结果写回到原始数据结构中
            print("\n正在将翻译结果写回文件...")
            for task_idx, (i, path) in enumerate(task_positions):
                if task_idx in translations_map:
                    translated_text = translations_map[task_idx]
                    TextUtils.set_text_recursive(files[i]["content"]["dataList"], path, translated_text)
        else:
            print("\n没有需要翻译的文本")
        
        return files

if __name__ == "__main__":
    lclt = LCLT()
    lclt.update(log=True)