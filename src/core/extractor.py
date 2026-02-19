import os
import json
from typing import Dict, List, Any
from src.config.loader import config_loader
from src.core.utils import FileUtils

class TextExtractor:
    """文本提取器，用于提取游戏文件中的文本内容"""
    
    def __init__(self):
        self.config = config_loader.get_config()
        self.blacklist = config_loader.get_blacklist()
    
    def extract_files_content(self, dir_key: str, lang: str) -> Dict[str, Dict[str, Any]]:
        """
        根据配置文件中的路径设置，递归提取指定语言文件夹下所有文件的内容
        
        参数:
        dir_key: 配置文件中file_paths的键名
        lang: 语言代码
        
        返回:
        包含文件路径和内容的字典，键为相对路径
        """
        game_dir = self.config["file_paths"][dir_key]
        lang_dir = os.path.join(game_dir, lang)

        files_content = {}
        
        for dirpath, _, filenames in os.walk(lang_dir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)

                if not filename.lower().endswith('.json'):
                    continue
                
                rel_path = os.path.relpath(dirpath, lang_dir)  # 未修改的相对路径
                modified_filename = FileUtils.modify_filename(filename)  # 去掉前缀的文件名

                # 构建ID，包含去掉前缀的文件名和相对路径
                if rel_path == '.':
                    file_id = modified_filename
                else:
                    file_id = os.path.join(rel_path, modified_filename).replace('/', '\\')
                
                with open(filepath, 'r', encoding='utf-8-sig') as f:
                    content = f.read()
                    try:
                        content_json = json.loads(content)
                    except json.JSONDecodeError:
                        content_json = None
                    
                    files_content[file_id] = {
                        "filename": modified_filename,  # 使用修改后的文件名
                        'full_path': filepath,
                        'content': content_json,
                    }
                    
        return files_content
    
    def find_new_content(self, origin: Dict[str, Dict[str, Any]], existing: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        找出origin有，existing没有的文件列表
        
        参数:
        origin: 原文文件列表，每个元素包含'filename', 'content'等字段
        existing: 已有译文文件列表，格式同origin
        
        返回:
        新增内容的文件列表
        """
        result = []  # 存储结果
        
        for file_id, origin_file in origin.items():
            # 跳过空内容文件
            if not origin_file["content"] or len(origin_file["content"]) == 0:
                continue

            # 如果existing中不存在该文件，或文件内容为None，则直接添加到结果中
            if (file_id not in existing) or (existing[file_id]["content"] is None):
                new_item = origin_file.copy()
                new_item["rel_path"] = file_id
                result.append(new_item)
            else:
                existing_file = existing[file_id]
                
                # 检查是否存在dataList字段
                if "dataList" not in origin_file['content'] or "dataList" not in existing_file['content']:
                    continue
                
                origin_data_list = origin_file['content']['dataList']
                existing_data_list = existing_file['content']['dataList']

                # 如果dataList长度相同，跳过
                if len(origin_data_list) == len(existing_data_list):
                    continue
                
                # 为existing_data_list建立id索引，提高查找效率
                existing_ids = set()
                for item in existing_data_list:
                    if "id" in item and item["id"] is not None:
                        existing_ids.add(item["id"])
                
                # 找出origin_data_list中存在但existing_data_list中不存在的项目
                new_items = []
                for item in origin_data_list:
                    # 仅提取最内层有id的那层
                    if "id" in item and item["id"] is not None:
                        if item["id"] not in existing_ids:
                            new_items.append(item)
                
                if new_items:
                    new_item = origin_file.copy()
                    new_item["rel_path"] = file_id
                    new_item["content"]["dataList"] = new_items
                    result.append(new_item)
        
        return result