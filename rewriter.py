#!/usr/bin/env python3
"""
AI洗稿器 - 使用MiniMax API改写文章
"""

import requests
import json
import re
from typing import Dict, Optional

class ArticleRewriter:
    def __init__(self, config: dict, track_manager=None):
        self.config = config
        self.ai_config = config.get('ai', {})
        self.rewrite_config = config.get('rewriter', {})

        self.api_key = self.ai_config.get('api_key', '')
        self.api_base = self.ai_config.get('api_base', 'https://ark.cn-beijing.volces.com/api/coding/v3')
        self.model = self.ai_config.get('model', 'MiniMax-M2.7')
        self.default_prompt = self.rewrite_config.get('system_prompt',
            '你是资深新媒体编辑，擅长将文章改写成符合中国读者阅读习惯的微信公众号爆款标题。你必须：1. 标题要像真人写的，有节奏感，不要直译或翻译腔 2. 可以用数字、反差对比、情绪共鸣、悬念等方式吸引点击 3. 保持8个汉字以内，严谨控制字数')

        # 赛道管理器
        if track_manager is None:
            from track_manager import TrackManager
            track_manager = TrackManager()
        self.track_manager = track_manager

    def rewrite(self, article: Dict, track_id: str = None) -> Optional[Dict]:
        """
        使用AI改写文章

        Args:
            article: 原始文章，包含 title, content, url 等
            track_id: 可选，赛道 ID，用于加载赛道专属 prompt

        Returns:
            改写后的文章，包含 rewritten_title, rewritten_content 等
        """
        original_title = article.get('title', '')
        original_content = article.get('content', '')

        if not original_content:
            print(f"[Rewriter] 文章内容为空: {original_title}")
            return None

        # 优先使用赛道专属 prompt
        if track_id is None:
            track_id = article.get('track_id')
        if track_id:
            system_prompt = self.track_manager.get_track_prompt(track_id) or self.default_prompt
        else:
            system_prompt = self.default_prompt

        user_prompt = (
            f"请改写以下文章的标题，生成一个适合微信公众号的爆款标题。\n\n"
            f"【原标题】\n{original_title}\n\n"
            f"【原文内容】\n{original_content[:2000]}\n\n"
            f"【标题改写要求】\n"
            f"1. 字数：标题中中文字符严格控制在6-10个之间（英文/数字不计入），整体不超过16个字符\n"
            f"2. 语言风格：必须是地道的简体中文，像真人写的，不要翻译腔，不要逐字直译英文\n"
            f"3. 技巧：可以适当使用数字（如'3个技巧'）、反差对比（如'这么简单'）、情绪词（如'太绝了'）等吸引点击\n"
            f"4. 格式：标题必须是完整的一句话，有头有尾，不要用省略号结尾，不要被截断\n"
            f"5. 禁止：不要用英文缩写/英文词（如iCloud），不要用生僻字，不要标题党过度夸张\n\n"
            f"【示例】（仅作参考，格式要严格按下面来）\n"
            f"【新标题】\n绝了！这个AI工具太强大\n"
            f"---\n"
            f"【正文】\n"
            f"（改写后的文章正文，800-1500字，语言口语化，有干货）\n\n"
            f"现在请输出改写结果："
        )

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
                        {"role": "system", "content": system_prompt},
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

            return self._parse_rewritten(rewritten_text, article)

        except Exception as e:
            print(f"[Rewriter] 改写失败: {e}")
            return None

    def _parse_rewritten(self, text: str, original: Dict) -> Dict:
        """解析AI返回的改写结果"""
        new_title = original.get('title', '')
        new_content = text

        # 尝试提取标题和正文
        # 支持格式:
        # 【新标题】标题内容
        # ---
        # 正文
        if '---' in text:
            parts = text.split('---', 1)
            before_dash = parts[0].strip()
            after_dash = parts[1].strip()

            # 提取标题
            if before_dash.startswith('【新标题】'):
                # 【新标题】标题 或 【新标题】【标题】
                title_text = before_dash[len('【新标题】'):].strip()
                title_match = re.search(r'【([^】]+)】', title_text)
                new_title = title_match.group(1).strip() if title_match else title_text
            else:
                # 【标题】 或 标题
                title_match = re.search(r'【([^】]+)】', before_dash)
                new_title = title_match.group(1).strip() if title_match else before_dash

            new_content = after_dash

        # 清理标题中的引号
        new_title = new_title.strip('"').strip('"').strip()

        # 限制标题字数：按中文字符数截断（不含英文/数字/符号）
        # 中文字符范围：\u4e00-\u9fff
        try:
            def chinese_char_count(s):
                return sum(1 for c in s if '\u4e00' <= c <= '\u9fff')
            
            c_count = chinese_char_count(new_title)
            max_c_chars = 12  # 最多12个中文字
            min_c_chars = 5   # 最少5个中文字（英文词可占字符但不计入中文数）
            
            if c_count > max_c_chars:
                # 逐字遍历，找到第max_c_chars个中文字符的位置
                count = 0
                cut_idx = len(new_title)
                for i, c in enumerate(new_title):
                    if '\u4e00' <= c <= '\u9fff':
                        count += 1
                        if count == max_c_chars:
                            cut_idx = i + 1
                            break
                new_title = new_title[:cut_idx]
                print(f"[Rewriter] 标题已截断到{max_c_chars}个中文字: {new_title} ({c_count}字)")
        except Exception as e:
            print(f"[Rewriter] 标题截断失败: {e}")

        return {
            'original_title': original.get('title', ''),
            'original_url': original.get('url', ''),
            'rewritten_title': new_title,
            'rewritten_content': new_content,
            'rewritten_at': original.get('fetched_at', ''),
            'source': original.get('source', '')
        }

if __name__ == '__main__':
    import configparser
    cfg = configparser.ConfigParser()
    cfg.read('config.ini')
    config = {s: dict(cfg.items(s)) for s in cfg.sections()}

    rewriter = ArticleRewriter(config)

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
