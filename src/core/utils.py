import os
import json
from datetime import datetime
from typing import Dict, List, Any

class FileUtils:
    """文件工具类"""
    
    @staticmethod
    def modify_filename(filename: str) -> str:
        """处理文件名，去除前缀"""
        prefixes = ["KR_", "JP_", "EN_"]
        while True:
            found_prefix = False
            for prefix in prefixes:
                if filename.startswith(prefix):
                    filename = filename[len(prefix):]
                    found_prefix = True
                    break
            if not found_prefix:
                break
        return filename
    
    @staticmethod
    def backup_translation_result(translation_result: List[Dict[str, Any]], prefix: str = "translation_result") -> str:
        """
        将翻译结果备份到文件
        返回备份文件路径
        """
        # 创建备份文件夹
        backup_folder = "backup"
        if not os.path.exists(backup_folder):
            os.makedirs(backup_folder)
        
        # 生成带时间戳的备份文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = os.path.join(backup_folder, f"{prefix}_backup_{timestamp}.json")
        
        # 将翻译结果写入备份文件
        with open(backup_filename, 'w', encoding='utf-8') as f:
            json.dump(translation_result, f, ensure_ascii=False, indent=2)
        
        return backup_filename

class TextUtils:
    """文本工具类"""
    
    @staticmethod
    def extract_text_recursive(data: Any, blacklist: list, current_path: list = None, extract_fields: list = None) -> List[tuple]:
        """
        递归提取数据中的文本，路径上有blacklist中键名的则跳过
        如果指定了extract_fields，则只提取指定字段的文本
        返回: [(完整路径, 文本值), ...]
        """
        if current_path is None:
            current_path = []
        
        texts = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                # 如果当前键在黑名单中，跳过整个分支
                if key in blacklist:
                    continue
                
                # 将当前键添加到路径中（保持原始大小写）
                new_path = current_path + [key]
                
                # 如果指定了提取字段，且当前键是提取字段之一，直接提取值
                if extract_fields and key in extract_fields and isinstance(value, str):
                    texts.append((new_path, value))
                else:
                    # 递归处理值
                    texts.extend(TextUtils.extract_text_recursive(value, blacklist, new_path, extract_fields))
        
        elif isinstance(data, list):
            # 遍历列表，将索引添加到路径中
            for index, item in enumerate(data):
                new_path = current_path + [index]
                texts.extend(TextUtils.extract_text_recursive(item, blacklist, new_path, extract_fields))
        
        elif isinstance(data, str) and not extract_fields:
            # 找到文本，添加到结果中（如果没有指定提取字段）
            texts.append((current_path, data))
        
        return texts
    
    @staticmethod
    def set_text_recursive(data: Any, path: list, value: str) -> None:
        """
        根据路径设置数据中的文本值
        """
        current = data
        # 遍历路径，直到倒数第二个元素
        for p in path[:-1]:
            if isinstance(current, list):
                current = current[p]
            elif isinstance(current, dict):
                current = current[p]
            else:
                raise ValueError(f"无法访问路径 {path}，在位置 {p} 处遇到了非容器类型")
        
        # 设置最后一个元素的值
        last_key = path[-1]
        if isinstance(current, list):
            current[last_key] = value
        elif isinstance(current, dict):
            current[last_key] = value
        else:
            raise ValueError(f"无法设置路径 {path} 的值，最终容器类型不正确")