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
            '你是资深新媒体编辑，擅长将文章改写成符合中国读者阅读习惯的微信公众号爆款标题。你必须：1. 标题要像真人写的，有节奏感，不要直译或翻译腔 2. 可以用数字、反差对比、情绪共鸣、悬念等方式吸引点击 3. 保持8个汉字以内，严谨控制字数')

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
        user_prompt = (
            f"请改写以下文章的标题，生成一个适合微信公众号的爆款标题。\n\n"
            f"【原标题】\n{original_title}\n\n"
            f"【原文内容】\n{original_content[:2000]}\n\n"
            f"【标题改写要求】\n"
            f"1. 字数：严格控制在6-8个汉字之间（不能少于6个，也不能多于8个）\n"
            f"2. 语言风格：必须是地道的简体中文，像真人写的，不要翻译腔，不要逐字直译英文\n"
            f"3. 技巧：可以适当使用数字（如'3个技巧'）、反差对比（如'这么简单'）、情绪词（如'太绝了'）等吸引点击\n"
            f"4. 格式：标题必须是完整的一句话，有头有尾，不要用省略号结尾，不要被截断\n"
            f"5. 禁止：不要用英文缩写/英文词，不要用生僻字，不要标题党过度夸张\n\n"
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
