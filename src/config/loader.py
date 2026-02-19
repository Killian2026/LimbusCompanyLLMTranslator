import json
import os
from typing import Dict, Any, List
import fnmatch

class ConfigLoader:
    """配置加载器，用于加载和管理项目配置"""
    
    _instance = None
    _config_cache: Dict[str, Any] = None
    _models_cache: Dict[str, Any] = None
    _translation_configs_cache: Dict[str, Any] = None
    _terminology_cache: Dict[str, str] = None
    _prompt_cache: Dict[str, str] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置（带缓存）"""
        if self._config_cache is None:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config_cache = json.load(f)
        return self._config_cache
    
    def get_models(self) -> Dict[str, Any]:
        """获取模型配置（带缓存）"""
        if self._models_cache is None:
            # 从主配置中获取模型配置文件路径
            config = self.get_config()
            config_files = config.get("config_files", {})
            models_file = config_files.get("models", "models.json")
            
            models_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), models_file)
            try:
                with open(models_path, 'r', encoding='utf-8') as f:
                    self._models_cache = json.load(f).get("models", {})
            except FileNotFoundError:
                print(f"警告: 未找到{models_file}文件，将使用空模型配置")
                self._models_cache = {}
        return self._models_cache
    
    def get_translation_configs(self) -> Dict[str, Any]:
        """获取翻译配置（带缓存）"""
        if self._translation_configs_cache is None:
            # 从主配置中获取翻译配置文件路径
            config = self.get_config()
            config_files = config.get("config_files", {})
            translation_configs_file = config_files.get("translation_configs", "translation_configs.json")
            
            translation_configs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), translation_configs_file)
            try:
                with open(translation_configs_path, 'r', encoding='utf-8') as f:
                    self._translation_configs_cache = json.load(f)
            except FileNotFoundError:
                print(f"警告: 未找到{translation_configs_file}文件，将使用空翻译配置")
                self._translation_configs_cache = {}
        return self._translation_configs_cache
    
    def get_terminology(self) -> Dict[str, str]:
        """获取术语库（带缓存）"""
        if self._terminology_cache is None:
            terminology_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "terminology.json")
            try:
                with open(terminology_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._terminology_cache = data.get("terminology", {})
            except FileNotFoundError:
                print("警告: 未找到terminology.json文件，将使用空术语表")
                self._terminology_cache = {}
        return self._terminology_cache
    
    def get_prompt(self, prompt_file: str = "prompt.txt") -> str:
        """获取提示词（带缓存）"""
        if self._prompt_cache is None:
            self._prompt_cache = {}
        
        if prompt_file not in self._prompt_cache:
            prompt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), prompt_file)
            try:
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    self._prompt_cache[prompt_file] = f.read().strip()
            except FileNotFoundError:
                print(f"警告: 未找到{prompt_file}文件，将使用默认提示词")
                # 使用默认提示词
                default_prompt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "prompt.txt")
                try:
                    with open(default_prompt_path, 'r', encoding='utf-8') as f:
                        self._prompt_cache[prompt_file] = f.read().strip()
                except FileNotFoundError:
                    self._prompt_cache[prompt_file] = ""
        return self._prompt_cache[prompt_file]
    
    def get_blacklist(self) -> list:
        """获取黑名单（带缓存）"""
        blacklist_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "BlackList.json")
        try:
            with open(blacklist_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("BlackList", [])
        except FileNotFoundError:
            print("警告: 未找到BlackList.json文件，将使用空黑名单")
            return []
    
    def get_translation_strategies(self) -> List[Dict[str, Any]]:
        """获取翻译策略配置"""
        translation_configs = self.get_translation_configs()
        return translation_configs.get("translation_strategies", [])
    
    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """根据模型名称获取模型配置"""
        models = self.get_models()
        return models.get(model_name, {})
    
    def get_strategy_for_file(self, file_path: str) -> Dict[str, Any]:
        """根据文件路径获取对应的翻译策略"""
        strategies = self.get_translation_strategies()
        
        # 按优先级排序策略
        sorted_strategies = sorted(strategies, key=lambda x: x.get("priority", 999))
        
        # 获取文件名（不包括路径）
        file_name = os.path.basename(file_path)
        
        # 遍历策略，找到第一个匹配的
        for strategy in sorted_strategies:
            file_patterns = strategy.get("file_patterns", [])
            for pattern_config in file_patterns:

                pattern = pattern_config.get("pattern", "")
                extract_fields = pattern_config.get("extract_fields", strategy.get("extract_fields", None))
                
                # 检查路径匹配
                if fnmatch.fnmatch(file_path, pattern):
                    # 返回带有extract_fields的策略副本
                    strategy_copy = strategy.copy()
                    strategy_copy["extract_fields"] = extract_fields
                    return strategy_copy
                # 检查文件名匹配（不包括路径）
                if fnmatch.fnmatch(file_name, pattern):
                    # 返回带有extract_fields的策略副本
                    strategy_copy = strategy.copy()
                    strategy_copy["extract_fields"] = extract_fields
                    return strategy_copy
        
        # 如果没有匹配的策略，返回默认策略
        default_strategy = next((s for s in sorted_strategies if s.get("name") == "default"), None)
        return default_strategy
    
    def get_strategies_for_file(self, file_path: str) -> List[Dict[str, Any]]:
        """根据文件路径获取所有匹配的翻译策略"""
        strategies = self.get_translation_strategies()
        
        # 按优先级排序策略
        sorted_strategies = sorted(strategies, key=lambda x: x.get("priority", 999))
        
        # 获取文件名（不包括路径）
        file_name = os.path.basename(file_path)
        
        # 收集所有匹配的策略
        matching_strategies = []
        for strategy in sorted_strategies:
            file_patterns = strategy.get("file_patterns", [])
            for pattern_config in file_patterns:

                pattern = pattern_config.get("pattern", "")
                extract_fields = pattern_config.get("extract_fields", strategy.get("extract_fields", None))
                
                # 检查路径匹配
                if fnmatch.fnmatch(file_path, pattern):
                    # 创建带有extract_fields的策略副本
                    strategy_copy = strategy.copy()
                    strategy_copy["extract_fields"] = extract_fields
                    matching_strategies.append(strategy_copy)
                # 检查文件名匹配（不包括路径）
                elif fnmatch.fnmatch(file_name, pattern):
                    # 创建带有extract_fields的策略副本
                    strategy_copy = strategy.copy()
                    strategy_copy["extract_fields"] = extract_fields
                    matching_strategies.append(strategy_copy)
        
        # 如果没有匹配的策略，添加默认策略
        if not matching_strategies:
            default_strategy = next((s for s in sorted_strategies if s.get("name") == "default"), None)
            if default_strategy:
                matching_strategies.append(default_strategy)
        
        return matching_strategies

# 创建全局配置加载器实例
config_loader = ConfigLoader()