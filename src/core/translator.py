import json
import requests
import re
from typing import List, Tuple, Dict, Any
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from src.config.loader import config_loader

class Translator:
    """翻译器，用于翻译游戏文本"""
    
    def __init__(self):
        self.config = config_loader.get_config()
        self.terminology = config_loader.get_terminology()
        self._session = None
        self._regex_cache = {}
        self._translation_cache = {}
    
    def get_session(self):
        """获取或创建 requests Session"""
        if self._session is None:
            self._session = requests.Session()
        return self._session
    
    def apply_terminology(self, text: str) -> Tuple[str, bool]:
        """应用语料库翻译，返回翻译后的文本和是否进行了术语替换的标志"""
        if not text or not isinstance(text, str):
            return text, False
        
        if not self.terminology:
            return text, False
        
        # 按长度排序，优先替换较长的术语
        sorted_terms = sorted(self.terminology.items(), key=lambda x: len(x[0]), reverse=True)
        
        # 构建一个大的正则表达式
        patterns = []
        term_map = {}
        for source, target in sorted_terms:
            pattern = r'(?<!\w)' + re.escape(source) + r'(?!\w)'
            patterns.append(pattern)
            term_map[source.lower()] = target
        
        # 编译组合正则表达式
        cache_key = tuple(sorted(self.terminology.items()))
        if cache_key not in self._regex_cache:
            combined_pattern = re.compile('|'.join(patterns), re.IGNORECASE)
            self._regex_cache[cache_key] = combined_pattern
        else:
            combined_pattern = self._regex_cache[cache_key]
        
        # 替换函数
        def replace_term(match):
            matched_term = match.group(0)
            return term_map.get(matched_term.lower(), matched_term)
        
        # 一次性替换所有匹配项
        new_result = combined_pattern.sub(replace_term, text)
        has_replacement = (new_result != text)
        
        return new_result, has_replacement
    
    def translate_batch_of_texts(self, batch_texts: List[str], prompt_template: str, api_key: str, 
                               base_url: str, model: str, temperature: float, enable_thinking: bool = False, 
                               request_counter: Dict[str, int] = None) -> Dict[int, str]:
        """
        翻译一批文本
        """
        # 检查缓存
        cache_key = (tuple(batch_texts), prompt_template, api_key, base_url, model, temperature, enable_thinking)
        if cache_key in self._translation_cache:
            return self._translation_cache[cache_key]
        
        # 构建API请求
        formatted_texts = ""
        for idx, text in enumerate(batch_texts, 1):
            # 使用更独特的分隔符，防止与文本内部的换行符混淆
            formatted_texts += f"{idx}. {text}\n---SPLITTER---\n"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system","content": prompt_template},
                {"role": "user","content": formatted_texts}],
            "temperature": temperature,
            "max_tokens": 8192,
        }

        # 如果启用了思考模式，添加相应参数
        if enable_thinking:
            payload["thinking"] = True

        # 增加请求计数
        if request_counter is not None:
            request_counter["count"] = request_counter.get("count", 0) + 1

        # 实现带有重试机制的API调用
        max_retries = self.config.get("translation_settings", {}).get("max_retries", 3)
        timeout = self.config.get("translation_settings", {}).get("timeout", 60)
        retry_count = 0
        session = self.get_session()
        
        while retry_count <= max_retries:
            try:
                response = session.post(base_url, headers=headers, json=payload, timeout=timeout)
                response.raise_for_status()
                result = response.json()
                ai_response = result['choices'][0]['message']['content'].strip()
                
                # 删除<thinking></thinking>标签内的内容
                import re
                ai_response = re.sub(r'<thinking>.*?</thinking>', '', ai_response, flags=re.DOTALL)

                # 解析API响应 - 使用改进的解析方法
                lines = ai_response.split('\n')
                api_translations = {}

                current_num = None
                current_translation = []

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                        # 检查是否是分隔符
                    if line == "---SPLITTER---":
                        if current_num is not None and current_translation:
                            # 保存当前翻译
                            translation = "\n".join(current_translation).strip()
                            api_translations[current_num] = translation
                            current_num = None
                            current_translation = []
                        continue

                        # 检查是否是带编号的行
                    match = re.match(r'^(\d+)[\.\)）、\s]\s*(.+)?$', line)
                    if match:
                        # 如果已经有当前编号和翻译，先保存
                        if current_num is not None and current_translation:
                            translation = "\n".join(current_translation).strip()
                            api_translations[current_num] = translation

                            # 开始新的翻译
                        current_num = int(match.group(1)) - 1  # 转为0-based索引
                        current_translation = []
                        if match.group(2):  # 如果匹配到了内容
                            current_translation.append(match.group(2).strip())
                    else:
                        # 如果当前有编号，就把这行添加到当前翻译中
                        if current_num is not None:
                            current_translation.append(line)

                            # 处理最后一条翻译
                if current_num is not None and current_translation:
                    translation = "\n".join(current_translation).strip()
                    api_translations[current_num] = translation

                # 缓存结果
                self._translation_cache[cache_key] = api_translations
                return api_translations
            except Exception as e:
                retry_count += 1
                if retry_count <= max_retries:
                    print(f"API翻译失败，正在进行第 {retry_count} 次重试: {e}")
                else:
                    print(f"API翻译最终失败，已达到最大重试次数: {e}")
                    raise  # 重新抛出异常，让调用者处理
    
    def process_batch(self, batch_indices: List[int], pre_translated_texts: List[str], 
                     need_api_translation_flags: List[bool], prompt_template: str, 
                     api_key: str, base_url: str, model: str, temperature: float, enable_thinking: bool = False, 
                     request_counter: Dict[str, int] = None) -> Tuple[Dict[int, str], bool]:
        """处理单个批次的翻译"""
        batch_texts = []
        batch_original_indices = []
        
        for idx in batch_indices:
            batch_texts.append(pre_translated_texts[idx])
            batch_original_indices.append(idx)
        
        try:
            api_translations = self.translate_batch_of_texts(batch_texts, prompt_template, api_key, 
                                                            base_url, model, temperature, enable_thinking, request_counter)
            
            # 构建结果映射
            results = {}
            api_text_idx = 0
            for orig_idx in batch_indices:
                if need_api_translation_flags[orig_idx]:
                    if api_text_idx in api_translations:
                        results[orig_idx] = api_translations[api_text_idx]
                    else:
                        # API翻译失败，保留原文
                        results[orig_idx] = pre_translated_texts[orig_idx]
                    api_text_idx += 1
                else:
                    # 不需要API翻译，使用预翻译结果
                    results[orig_idx] = pre_translated_texts[orig_idx]
            
            return results, True
        except Exception as e:
            print(f"API翻译失败: {e}")
            # API失败时，对于需要翻译的文本保留原文
            results = {}
            for orig_idx in batch_indices:
                results[orig_idx] = pre_translated_texts[orig_idx]
            return results, False
    
    def optimized_translate(self, texts: List[str], max_chars_per_batch: int = None, 
                          api_key: str = None, base_url: str = None, 
                          model: str = None, temperature: float = None, 
                          enable_thinking: bool = False, 
                          prompt_file: str = "prompt.txt") -> Tuple[bool, int, List[str]]:
        """
        优化的批量翻译，按字符数阈值分组发送给AI
        在翻译前，使用语料库进行预翻译
        返回(是否成功, 成功翻译的数量, 翻译结果列表)
        """
        # 调用通用的批量翻译方法
        tasks = []
        for i, text in enumerate(texts):
            tasks.append({
                "text": text,
                "api_key": api_key,
                "base_url": base_url,
                "model": model,
                "temperature": temperature,
                "enable_thinking": enable_thinking,
                "prompt_file": prompt_file,
                "index": i
            })
        
        results_map = self.batch_translate_with_multiple_strategies(tasks, max_chars_per_batch)
        
        # 构建结果列表
        results = [None] * len(texts)
        success_count = 0
        for i, text in enumerate(texts):
            if i in results_map:
                results[i] = results_map[i]
                success_count += 1
            else:
                results[i] = text
        
        return True, success_count, results
    
    def batch_translate_with_multiple_strategies(self, tasks: List[Dict[str, Any]], max_chars_per_batch: int = None) -> Dict[int, str]:
        """
        批量翻译多个使用不同策略的任务
        
        参数:
        tasks: 任务列表，每个任务包含text、api_key、base_url、model、temperature、enable_thinking、prompt_file、index
        max_chars_per_batch: 每批最大字符数
        
        返回:
        翻译结果字典，键为任务索引，值为翻译后的文本
        """
        if not tasks:
            return {}
        
        # 使用默认值
        max_workers = self.config.get("translation_settings", {}).get("max_workers", 5)
        max_chars_per_batch = max_chars_per_batch or self.config.get("translation_settings", {}).get("max_chars_per_batch", 2200)
        
        # 初始化结果
        results_map = {}
        # 初始化全局请求计数器
        global_request_counter = {"count": 0}
        # 记录开始时间
        start_time = time.time()
        
        # 按策略分组任务
        strategy_groups = {}
        for task in tasks:
            # 构建策略键
            strategy_key = (
                task["api_key"],
                task["base_url"],
                task["model"],
                task["temperature"],
                task["enable_thinking"],
                task["prompt_file"]
            )
            
            if strategy_key not in strategy_groups:
                strategy_groups[strategy_key] = {
                    "api_key": task["api_key"],
                    "base_url": task["base_url"],
                    "model": task["model"],
                    "temperature": task["temperature"],
                    "enable_thinking": task["enable_thinking"],
                    "prompt_file": task["prompt_file"],
                    "tasks": []
                }
            
            strategy_groups[strategy_key]["tasks"].append(task)
        
        print(f"\n共发现 {len(strategy_groups)} 个不同的翻译策略组")
        
        # 为每个策略组创建线程池并处理
        all_futures = []
        
        # 使用总线程池处理所有策略组
        total_tasks = sum(len(group["tasks"]) for group in strategy_groups.values())
        total_workers = min(max_workers, total_tasks)
        
        print(f"开始集中处理 {total_tasks} 个翻译任务，使用 {total_workers} 个线程")
        
        with ThreadPoolExecutor(max_workers=total_workers) as executor:
            # 为每个策略组提交任务
            for strategy_key, group in strategy_groups.items():
                # 提取策略信息
                api_key = group["api_key"]
                base_url = group["base_url"]
                model = group["model"]
                temperature = group["temperature"]
                enable_thinking = group["enable_thinking"]
                prompt_file = group["prompt_file"]
                group_tasks = group["tasks"]
                
                print(f"  策略组: {model} 使用 {prompt_file}，处理 {len(group_tasks)} 个任务")
                
                # 加载提示词
                prompt = config_loader.get_prompt(prompt_file)
                
                # 提取文本和索引
                texts = [task["text"] for task in group_tasks]
                indices = [task["index"] for task in group_tasks]
                
                # 对每个策略组的文本进行预翻译
                pre_translated_texts = []
                need_api_translation_flags = []
                
                for text in texts:
                    if not text or not isinstance(text, str):
                        # 非字符串或空值直接保留
                        pre_translated_texts.append(text)
                        need_api_translation_flags.append(False)
                    else:
                        # 尝试使用术语库翻译
                        pre_translated, was_replaced = self.apply_terminology(text)
                        pre_translated_texts.append(pre_translated)
                        need_api_translation_flags.append(True)
                
                # 只为需要API翻译的文本创建批次
                need_api_indices = [i for i in range(len(texts)) if need_api_translation_flags[i]]
                
                if not need_api_indices:
                    # 所有文本都不需要API翻译
                    for i, task in enumerate(group_tasks):
                        results_map[task["index"]] = texts[i]
                    continue
                
                # 重新组织批次：只为需要API翻译的文本按字符数阈值分组
                def create_batches_for_api_texts():
                    """为需要API翻译的文本创建批次"""
                    batches = []  # 每个批次包含索引列表
                    current_batch = []
                    current_chars = 0
                    
                    for idx in need_api_indices:
                        text = pre_translated_texts[idx]
                        if not isinstance(text, str):
                            continue
                            
                        text_chars = len(text.encode('utf-8'))
                        
                        if current_batch and current_chars + text_chars > max_chars_per_batch:
                            # 当前批次已满，保存并开始新批次
                            batches.append(current_batch)
                            current_batch = [idx]
                            current_chars = text_chars
                        else:
                            # 可以添加到当前批次
                            current_batch.append(idx)
                            current_chars += text_chars
                    
                    # 添加最后一个批次
                    if current_batch:
                        batches.append(current_batch)
                    
                    return batches
                
                # 创建批次
                batches = create_batches_for_api_texts()
                
                # 提交批次任务
                for batch_indices in batches:
                    future = executor.submit(
                        self.process_batch,
                        batch_indices,
                        pre_translated_texts,
                        need_api_translation_flags,
                        prompt,
                        api_key,
                        base_url,
                        model,
                        temperature,
                        enable_thinking,
                        global_request_counter
                    )
                    # 保存批次信息
                    all_futures.append((future, indices, batch_indices, pre_translated_texts, need_api_translation_flags))
            
            # 收集所有结果
            completed_tasks = 0
            total_batches = len(all_futures)
            
            for future, group_indices, batch_indices, pre_translated_texts, need_api_translation_flags in all_futures:
                try:
                    batch_results, batch_success = future.result()
                    # 更新结果
                    for orig_idx, translated_text in batch_results.items():
                        # 获取原始任务索引
                        task_index = group_indices[orig_idx]
                        results_map[task_index] = translated_text
                    completed_tasks += len(batch_indices)
                    
                    # 显示整体进度
                    if total_tasks > 0:
                        progress = completed_tasks / total_tasks
                        bar_length = 48
                        filled_length = int(bar_length * progress)
                        bar = '█' * filled_length + '░' * (bar_length - filled_length)
                        
                        # 计算每秒请求量
                        current_time = time.time()
                        elapsed_time = current_time - start_time
                        req_per_sec = global_request_counter["count"] / elapsed_time if elapsed_time > 0 else 0
                        
                        print(f"\r整体翻译进度: [{bar}] {completed_tasks}/{total_tasks} ({progress*100:.1f}%) 请求/秒: {req_per_sec:.2f}               ", end="", flush=True)
                except Exception as e:
                    print(f"处理批次时出错: {e}")
        
        print()  # 换行
        return results_map