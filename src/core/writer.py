import os
import json
import sys
import shutil
from typing import List, Dict, Any
from src.config.loader import config_loader

class FileWriter:
    """文件写入器，用于将翻译后的内容写回到文件中"""
    
    def __init__(self):
        self.config = config_loader.get_config()
    
    def _get_base_path(self) -> str:
        """获取基础路径，支持打包成exe的情况"""
        if getattr(sys, 'frozen', False):
            # 打包成exe的情况
            return os.path.dirname(sys.executable)
        else:
            # 正常运行的情况
            return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    def putback(self, translated_files: List[Dict[str, Any]], pos: str, lang: str) -> None:
        """
        将翻译后的内容合并回原文件
        
        参数:
        translated_files: 翻译后的文件列表
        pos: 配置文件中file_paths的键名
        lang: 语言代码
        """
        # 从config.json中获取目标路径
        target_dir = self.config["file_paths"][pos]
        
        # 检查目标文件夹根目录是否有 Font 文件夹，如果没有则复制项目的 Font 文件夹
        base_path = self._get_base_path()
        source_font_dir = os.path.join(base_path, "Font")
        target_direction = self.config["translation_settings"]["target_direction"]
        target_font_dir = os.path.join(target_dir, target_direction, "Font")
        
        if not os.path.exists(target_font_dir) and os.path.exists(source_font_dir):
            print(f"目标目录中不存在 Font 文件夹，正在复制到 {target_font_dir}...")
            shutil.copytree(source_font_dir, target_font_dir)
            print(f"Font 文件夹复制完成！")
        
        for x in translated_files:
            # 检查x["content"]是否包含"dataList"字段，如果不包含则跳过
            if "dataList" not in x["content"]:
                print(f"跳过文件 {x.get('rel_path', 'Unknown')}，因为内容不包含 dataList 字段")
                continue
            
            # 构造目标文件路径
            rel_path = x["rel_path"]
            
            target_file_path = os.path.join(target_dir, lang, rel_path)
            
            # 确保目标目录存在
            os.makedirs(os.path.dirname(target_file_path), exist_ok=True)
            
            # 读取目标文件
            if os.path.exists(target_file_path):
                with open(target_file_path, 'r', encoding='utf-8') as f:
                    try:
                        target_content = json.load(f)
                    except json.JSONDecodeError:
                        # 如果文件不是有效的JSON，初始化为空对象
                        target_content = {"dataList": []}
            else:
                # 如果文件不存在，初始化为空对象
                target_content = {"dataList": []}
            
            # 获取目标文件的dataList
            target_datalist = target_content.get("dataList", [])
            
            # 获取x中的dataList
            source_datalist = x["content"]["dataList"]
            
            # 合并两个dataList
            merged_datalist = self.merge_datalists(target_datalist, source_datalist)
            
            # 更新目标文件内容
            target_content["dataList"] = merged_datalist
            
            # 写入文件，使用 CRLF 换行符
            with open(target_file_path, 'w', newline='\r\n', encoding='utf-8') as f:
                json.dump(target_content, f, ensure_ascii=False, indent=2)
    
    def merge_datalists(self, target_list: List[Dict[str, Any]], source_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        合并两个dataList数组，避免重复添加
        """
        # 为目标列表创建id索引，避免重复
        target_ids = set()
        for item in target_list:
            if "id" in item and item["id"] is not None:
                target_ids.add(item["id"])
        
        # 添加源列表中不存在于目标列表的项目
        for source_item in source_list:
            if "id" in source_item and source_item["id"] is not None:
                if source_item["id"] not in target_ids:
                    target_list.append(source_item)
                    target_ids.add(source_item["id"])
            else:
                # 如果没有id，则直接添加
                target_list.append(source_item)
        
        return target_list