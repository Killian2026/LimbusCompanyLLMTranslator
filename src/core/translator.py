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
        if not texts:
            return True, 0, []
        
        # 使用传入参数或从配置中获取默认值
        api_key = api_key or ""
        base_url = base_url or ""
        model = model or "deepseek-chat"
        temperature = temperature or 0.1
        enable_thinking = enable_thinking
        max_workers = self.config.get("translation_settings", {}).get("max_workers", 5)
        max_chars_per_batch = max_chars_per_batch or self.config.get("translation_settings", {}).get("max_chars_per_batch", 2200)
        
        # 加载提示词
        prompt = config_loader.get_prompt(prompt_file)
        
        results = [None] * len(texts)  # 初始化结果数组
        success_count = 0
        
        print("正在分析文本...", end="\r")
        
        # 第一步：对所有文本应用语料库预翻译
        pre_translated_texts = []
        need_api_translation_flags = []
        
        # 统计信息
        total_no_api = 0
        total_need_api = 0
        
        for i, text in enumerate(texts):
            if not text or not isinstance(text, str):
                # 非字符串或空值直接保留
                pre_translated_texts.append(text)
                need_api_translation_flags.append(False)
                success_count += 1
                total_no_api += 1
            else:
                # 尝试使用术语库翻译
                pre_translated, was_replaced = self.apply_terminology(text)
                pre_translated_texts.append(pre_translated)
                need_api_translation_flags.append(True)
                total_need_api += 1
        
        print(f"文本分析完成: {total_no_api}个无需翻译, {total_need_api}个需要翻译  ")
        
        # 第二步：先处理所有不需要翻译的文本
        print("正在处理无需翻译的文本...", end="\r")
        for i in range(len(texts)):
            if not need_api_translation_flags[i]:
                results[i] = pre_translated_texts[i]
        
        print(f"已完成无需翻译的文本: {total_no_api}个              ")
        
        # 第三步：只为需要API翻译的文本创建批次
        need_api_indices = [i for i in range(len(texts)) if need_api_translation_flags[i]]
        
        if not need_api_indices:
            print("没有需要API翻译的文本，任务完成！")
            return True, success_count, results
        
        # 计算需要API翻译的总字符数
        total_chars_for_api = 0
        for idx in need_api_indices:
            text = pre_translated_texts[idx]
            if isinstance(text, str):
                total_chars_for_api += len(text.encode('utf-8'))
        
        print(f"\n\n需要API翻译的字符数: {total_chars_for_api}")
        print(f"字符数阈值: {max_chars_per_batch}")
        print("开始翻译需要API处理的文本...")
        
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
        total_batches = len(batches)
        
        if total_batches == 0:
            print("没有需要API翻译的文本批次")
            return True, success_count, results
        
        print(f"需要API翻译的批次数: {total_batches}")
        
        # 初始化请求统计
        request_counter = {"count": 0}
        start_time = time.time()
        last_update_time = start_time
        
        # 进度显示辅助函数
        def print_progress(batch_idx, total_batches, completed_batches, prefix="正在翻译"):
            nonlocal last_update_time
            progress = (batch_idx) / total_batches
            bar_length = 48
            filled_length = int(bar_length * progress)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            # 计算剩余时间
            current_time = time.time()
            elapsed_time = current_time - start_time
            if completed_batches > 0:
                avg_time_per_batch = elapsed_time / completed_batches
                remaining_batches = total_batches - batch_idx
                remaining_time = avg_time_per_batch * remaining_batches
                
                # 格式化剩余时间
                if remaining_time < 60:
                    time_str = f"{remaining_time:.0f}秒"
                elif remaining_time < 3600:
                    minutes = int(remaining_time / 60)
                    seconds = int(remaining_time % 60)
                    time_str = f"{minutes}分{seconds}秒"
                else:
                    hours = int(remaining_time / 3600)
                    minutes = int((remaining_time % 3600) / 60)
                    time_str = f"{hours}小时{minutes}分"
            else:
                time_str = "计算中..."
            
            # 计算每秒请求量
            time_since_last_update = current_time - last_update_time
            if time_since_last_update > 0:
                req_per_sec = request_counter["count"] / elapsed_time if elapsed_time > 0 else 0
            else:
                req_per_sec = 0
            
            print(f"{prefix}: [{bar}] {batch_idx}/{total_batches} ({progress*100:.1f}%) 剩余时间: {time_str} 请求/秒: {req_per_sec:.2f}", end="\r", flush=True)
            last_update_time = current_time
        
        # 第四步：并行处理需要API翻译的文本
        print("开始API翻译...")
        
        # 使用线程池并行处理批次
        max_workers = min(max_workers, total_batches)  # 限制最大线程数
        results_map = {}
        start_time = time.time()  # 记录开始时间
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有批次任务
            future_to_batch = {
                executor.submit(self.process_batch, batch_indices, pre_translated_texts, 
                              need_api_translation_flags, prompt, api_key, base_url, model, temperature, enable_thinking, 
                              request_counter): batch_idx
                for batch_idx, batch_indices in enumerate(batches)
            }
            
            # 收集结果
            completed_batches = 0
            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    batch_results, batch_success = future.result()
                    # 更新结果
                    for orig_idx, translated_text in batch_results.items():
                        results_map[orig_idx] = translated_text
                        if batch_success:
                            success_count += 1
                    # 更新进度
                    completed_batches += 1
                    print_progress(completed_batches, total_batches, completed_batches)
                except Exception as e:
                    print(f"处理批次时出错: {e}")
        
        # 将结果映射回原始列表
        for i in range(len(texts)):
            if i in results_map:
                results[i] = results_map[i]
            elif results[i] is None:
                results[i] = texts[i]  # 保留原文
        
        # 完成进度条
        print_progress(total_batches, total_batches, completed_batches, prefix="翻译完成")
        print()  # 换行
        
        # 确保所有文本都有结果
        for i in range(len(results)):
            if results[i] is None:
                results[i] = texts[i]  # 保留原文
        
        print(f"翻译完成! 总共处理了 {success_count}/{len(texts)} 个字段")
        return True, success_count, results