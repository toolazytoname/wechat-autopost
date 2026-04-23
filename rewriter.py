#!/usr/bin/env python3
"""
AI洗稿器 - 使用MiniMax API改写文章
"""

import requests
import json
from typing import Dict, Optional

class ArticleRewriter:
    def __init__(self, config: dict):
        self.config = config
        self.ai_config = config.get('ai', {})
        self.rewrite_config = config.get('rewriter', {})
        
        self.api_key = self.ai_config.get('api_key', '')
        self.api_base = self.ai_config.get('api_base', 'https://ark.cn-beijing.volces.com/api/coding/v3')
        self.model = self.ai_config.get('model', 'MiniMax-M2.7')
        self.system_prompt = self.rewrite_config.get('system_prompt', 
            '你是资深新媒体编辑，擅长将文章改写得更吸引人。请对原文进行改写：1. 优化标题，更吸引人点击 2. 调整文章结构，更易读 3. 保持核心信息不变，但表达更生动 4. 去除AI写作痕迹，让文章读起来像真人写的')
    
    def rewrite(self, article: Dict) -> Optional[Dict]:
        """
        使用AI改写文章
        
        Args:
            article: 原始文章，包含 title, content, url 等
            
        Returns:
            改写后的文章，包含 rewritten_title, rewritten_content 等
        """
        original_title = article.get('title', '')
        original_content = article.get('content', '')
        
        if not original_content:
            print(f"[Rewriter] 文章内容为空: {original_title}")
            return None
        
        # 构建prompt
        # 微信标题限制32字节（约8-9个中文字），必须严格控制
        user_prompt = f"""请改写以下文章：

【原标题】
{original_title}

【原文内容】
{original_content[:2000]}

请直接输出改写后的内容，格式如下：
【新标题】（必须恰好8个汉字以内，如"微软开源神器体验"）
---
【正文】（改写后的文章正文，800-1500字）

【重要提醒】
1. 标题必须恰好8个汉字！例如"微软开源神器体验"是8个字，"绝了！这个工具太好用"是10个字（超过限制）
2. 标题必须是完整的一句话，有头有尾，不能被截断
3. 标题要有悬念或亮点，吸引人点击
4. 正文要有干货，语言口语化"""

        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 3000
                },
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"[Rewriter] API调用失败: {response.status_code} - {response.text}")
                return None
            
            result = response.json()
            rewritten_text = result['choices'][0]['message']['content']
            
            # 解析改写结果
            return self._parse_rewritten(rewritten_text, article)
            
        except Exception as e:
            print(f"[Rewriter] 改写失败: {e}")
            return None
    
    def _parse_rewritten(self, text: str, original: Dict) -> Dict:
        """解析AI返回的改写结果"""
        new_title = original.get('title', '')
        new_content = text
        
        import re
        
        # 尝试提取标题和正文
        # 格式1: 【新标题】实际标题内容---正文
        # 格式2: 【实际标题内容】---正文
        # 格式3: 实际标题---正文
        
        if '---' in text:
            parts = text.split('---', 1)
            before_dash = parts[0].strip()
            after_dash = parts[1].strip()
            
            # 提取标题
            # 先检查是否有【新标题】标记
            if before_dash.startswith('【新标题】'):
                # 格式1: 【新标题】标题---正文
                title_text = before_dash[len('【新标题】'):].strip()
                # 如果标题在【】中
                title_match = re.search(r'【([^】]+)】', title_text)
                if title_match:
                    new_title = title_match.group(1).strip()
                else:
                    new_title = title_text
            else:
                # 格式2或3: 【标题】---正文 或 标题---正文
                title_match = re.search(r'【([^】]+)】', before_dash)
                if title_match:
                    new_title = title_match.group(1).strip()
                elif before_dash:
                    new_title = before_dash
            
            new_content = after_dash
        
        # 清理标题中的引号
        new_title = new_title.strip('"').strip('"').strip()
        
        # 限制标题长度：微信限制34字节（实测），超过会报错45003
        # 使用智能截断，在自然断点处截断
        try:
            max_bytes = 32  # 留2字节余量
            title_bytes = new_title.encode('utf-8')
            if len(title_bytes) > max_bytes:
                # 智能截断：在标点、顿号、逗号处截断
                truncated = ''
                current_bytes = 0
                break_points = ['。', '！', '？', '，', '、', '"', '"', ''', ''']
                
                for i, char in enumerate(new_title):
                    char_bytes = len(char.encode('utf-8'))
                    
                    # 如果加上这个字符会超限
                    if current_bytes + char_bytes > max_bytes:
                        # 如果已经有内容，检查是否是好的截断点
                        if truncated:
                            # 在标点处截断是好的
                            if truncated[-1] in break_points:
                                break
                            # 如果前一个字符是好的截断点，也截断
                            if len(truncated) > 0:
                                break
                        break
                    
                    truncated += char
                    current_bytes += char_bytes
                
                new_title = truncated
                print(f"[Rewriter] 标题过长，已智能截断: {new_title}")
        except:
            pass
        
        return {
            'original_title': original.get('title', ''),
            'original_url': original.get('url', ''),
            'rewritten_title': new_title,
            'rewritten_content': new_content,
            'rewritten_at': original.get('fetched_at', ''),
            'source': original.get('source', '')
        }

if __name__ == '__main__':
    # 测试
    import configparser
    cfg = configparser.ConfigParser()
    cfg.read('config.ini')
    config = {s: dict(cfg.items(s)) for s in cfg.sections()}
    
    rewriter = ArticleRewriter(config)
    
    # 测试文章
    test_article = {
        'title': '测试文章标题',
        'content': '这是测试文章的内容，我们想要改写这篇文章，使其更加吸引人。' * 20,
        'url': 'https://example.com/test',
        'source': 'test'
    }
    
    result = rewriter.rewrite(test_article)
    if result:
        print(f"改写成功!")
        print(f"新标题: {result['rewritten_title']}")
        print(f"新内容: {result['rewritten_content'][:200]}...")
