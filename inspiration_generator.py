#!/usr/bin/env python3
"""
灵感来源文章生成器
支持输入一段话或一个链接，AI参考扩展生成图文混排的完整文章
"""
import requests
import re
import json
from typing import Dict, Optional, List
from bs4 import BeautifulSoup
from urllib.parse import urlparse


class InspirationGenerator:
    def __init__(self, config: dict, track_manager=None):
        self.config = config
        self.ai_config = config.get('ai', {})
        self.api_key = self.ai_config.get('api_key', '')
        self.api_base = self.ai_config.get('api_base', 'https://ark.cn-beijing.volces.com/api/coding/v3')
        self.model = self.ai_config.get('model', 'doubao-seed-2-0-mini-260215')

        # 赛道管理器
        if track_manager is None:
            from track_manager import TrackManager
            track_manager = TrackManager()
        self.track_manager = track_manager

    def fetch_url_content(self, url: str) -> Optional[Dict]:
        """
        抓取网页内容，提取标题和正文

        Args:
            url: 网页链接

        Returns:
            {title, content, url}
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.encoding = response.apparent_encoding or 'utf-8'

            soup = BeautifulSoup(response.text, 'html.parser')

            # 提取标题
            title = ''
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)

            # 提取正文 - 尝试多种方式
            content = ''

            # 方式1: 查找主要内容容器
            content_selectors = [
                'article',
                '.article-content',
                '.post-content',
                '.content',
                '.main-content',
                '#content',
                '#article-content',
                'div[class*="content"]',
                'div[class*="article"]',
            ]

            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    # 取最长的内容作为正文
                    texts = []
                    for elem in elements:
                        # 移除脚本和样式标签
                        for s in elem(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                            s.decompose()
                        text = elem.get_text(separator='\n', strip=True)
                        texts.append((len(text), text))
                    if texts:
                        texts.sort(reverse=True)
                        content = texts[0][1]
                        break

            # 方式2: 如果没有找到，提取所有p标签
            if not content or len(content) < 200:
                paragraphs = soup.find_all('p')
                content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])

            # 清理多余空行
            content = re.sub(r'\n\s*\n', '\n\n', content)

            # 截取合理长度
            if len(content) > 5000:
                content = content[:5000] + '...'

            if not title:
                title = '参考文章'

            return {
                'title': title,
                'content': content,
                'url': url,
                'source': self._get_domain(url)
            }

        except Exception as e:
            print(f"[Inspiration] 抓取网页失败: {e}")
            return None

    def _get_domain(self, url: str) -> str:
        """从URL提取域名"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.replace('www.', '')
        except:
            return '网络来源'

    def generate_from_text(self, inspiration_text: str, track_id: str = None,
                          style: str = '专业深度', length: str = 'medium') -> Optional[Dict]:
        """
        根据灵感文字生成文章

        Args:
            inspiration_text: 灵感段落
            track_id: 赛道ID，用于加载赛道专属Prompt
            style: 文章风格 - '专业深度', '轻松幽默', '干货实用', '情感共鸣'
            length: 文章长度 - 'short'(800字), 'medium'(1500字), 'long'(2500字)

        Returns:
            生成的文章 {title, content, image_suggestions, ...}
        """
        # 获取赛道Prompt
        system_prompt = self._get_system_prompt(track_id, style, length)

        user_prompt = self._build_user_prompt(inspiration_text, style, length, is_url=False)

        return self._call_ai_generate(system_prompt, user_prompt, inspiration_text, source_type='text')

    def generate_from_url(self, url: str, track_id: str = None,
                         style: str = '专业深度', length: str = 'medium') -> Optional[Dict]:
        """
        根据链接生成文章

        Args:
            url: 参考链接
            track_id: 赛道ID
            style: 文章风格
            length: 文章长度

        Returns:
            生成的文章
        """
        # 先抓取网页内容
        content_data = self.fetch_url_content(url)
        if not content_data:
            return None

        reference_content = f"【参考标题】{content_data['title']}\n\n【参考内容】\n{content_data['content']}"

        # 获取赛道Prompt
        system_prompt = self._get_system_prompt(track_id, style, length)

        user_prompt = self._build_user_prompt(reference_content, style, length, is_url=True)

        return self._call_ai_generate(system_prompt, user_prompt, url, source_type='url',
                                    original_title=content_data['title'])

    def _get_system_prompt(self, track_id: str, style: str, length: str) -> str:
        """获取系统Prompt"""
        base_prompt = """
你是资深新媒体主编，擅长整合多个来源的信息，进行深度创作和观点提炼。
你的核心能力：
1. 整合多篇文章，提炼共性观点，发现差异化视角
2. 去重存精，将分散的信息整合成逻辑自洽的完整文章
3. 在整合基础上加入行业洞察和深度分析，形成原创内容
4. 识别不同来源的优缺点，取长补短，输出高于原文的优质内容

创作原则：
1. 原创性：不要简单复制粘贴，要进行理解、重组和扩展，加入自己的观点
2. 整合能力：如果有多个参考来源，要有机融合，不要生硬拼接，形成统一叙事
3. 结构清晰：开头引入 → 分点阐述 → 总结升华，逻辑清晰，层层递进
4. 读者友好：语言口语化，避免专业术语堆砌，适合手机阅读，段落不宜过长
5. 价值导向：每篇文章都要有明确的价值点（知识增量、方法技巧、情感共鸣）
6. 图文思维：在合适的位置标注需要配图的地方，为图文混排做准备

输出格式要求（严格遵守）：
【文章标题】
（标题内容，6-12个中文字，吸引人点击）

【文章摘要】
（简短摘要，100字以内）

【正文】
（正文内容，按要求的字数。每段不要太长，3-4行换一段。适当使用小标题如「一、」「二、」或「1.」「2.」）

【配图建议】
1. （配图位置说明）：（具体图片描述）
2. （配图位置说明）：（具体图片描述）
3. （配图位置说明）：（具体图片描述）

【关键词】
关键词1, 关键词2, 关键词3
"""

        # 叠加赛道专属Prompt
        if track_id:
            track_prompt = self.track_manager.get_track_prompt(track_id)
            if track_prompt:
                base_prompt = f"{base_prompt}\n\n【赛道专属风格要求】\n{track_prompt}"

        return base_prompt

    def _build_user_prompt(self, inspiration: str, style: str, length: str, is_url: bool) -> str:
        """构建用户Prompt"""
        length_map = {
            'short': '800-1000字',
            'medium': '1200-1800字',
            'long': '2000-3000字'
        }

        style_map = {
            '专业深度': '专业分析风格，逻辑严密，有深度，适合行业读者',
            '轻松幽默': '轻松幽默风格，多用网络热词和梗，可读性强',
            '干货实用': '实用干货风格，结构清晰，步骤明确，可操作性强',
            '情感共鸣': '情感共鸣风格，故事性强，打动人心'
        }

        source_desc = "链接参考文章" if is_url else "灵感素材"

        prompt = f"""
请参考以下{source_desc}，创作一篇完整的微信公众号文章。

【{source_desc}】
{inspiration}

【创作要求】
1. 文章风格：{style_map.get(style, style_map['专业深度'])}
2. 文章长度：{length_map.get(length, length_map['medium'])}
3. 必须原创：不要直接复制参考内容，要进行理解、扩展和二次创作
4. 加入新观点：在参考内容基础上，加入行业观察、案例补充、方法提炼
5. 段落分明：每段不要太长，适合手机阅读，适当使用小标题

【格式要求】
严格按照以下格式输出：
【文章标题】
xxx

【文章摘要】
xxx

【正文】
xxx（正文内容，适当分段，可以使用小标题：一、xxx，二、xxx 等格式）

【配图建议】
1. xxxxx：xxxx
2. xxxxx：xxxx
3. xxxxx：xxxx

【关键词】
xxx, xxx, xxx

现在开始创作：
"""
        return prompt

    def _call_ai_generate(self, system_prompt: str, user_prompt: str,
                        source: str, source_type: str, original_title: str = None) -> Optional[Dict]:
        """调用AI生成文章"""
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
                    "max_tokens": 4000
                },
                timeout=120
            )

            if response.status_code != 200:
                print(f"[Inspiration] AI调用失败: {response.status_code} - {response.text}")
                return None

            result = response.json()
            generated_text = result['choices'][0]['message']['content']

            return self._parse_generated_result(generated_text, source, source_type, original_title)

        except Exception as e:
            print(f"[Inspiration] 生成文章失败: {e}")
            return None

    def _parse_generated_result(self, text: str, source: str, source_type: str,
                              original_title: str = None) -> Dict:
        """解析AI生成的结果"""
        result = {
            'inspiration_source': source,
            'source_type': source_type,
            'original_title': original_title or '',
            'rewritten_title': '',
            'rewritten_content': '',
            'summary': '',
            'image_suggestions': [],
            'keywords': [],
            'source': '灵感创作'
        }

        # 提取标题
        title_match = re.search(r'【文章标题】\s*\n?(.*?)(?=\n|【|$)', text, re.DOTALL)
        if title_match:
            result['rewritten_title'] = title_match.group(1).strip()

        # 提取摘要
        summary_match = re.search(r'【文章摘要】\s*\n?(.*?)(?=\n【|$)', text, re.DOTALL)
        if summary_match:
            result['summary'] = summary_match.group(1).strip()

        # 提取正文
        content_match = re.search(r'【正文】\s*\n?(.*?)(?=\n【配图建议】|$)', text, re.DOTALL)
        if content_match:
            result['rewritten_content'] = content_match.group(1).strip()

        # 提取配图建议
        images_match = re.search(r'【配图建议】\s*\n?(.*?)(?=\n【关键词】|$)', text, re.DOTALL)
        if images_match:
            images_text = images_match.group(1).strip()
            image_lines = [line.strip() for line in images_text.split('\n') if line.strip()]
            result['image_suggestions'] = image_lines

        # 提取关键词
        keywords_match = re.search(r'【关键词】\s*\n?(.*?)(?=$)', text, re.DOTALL)
        if keywords_match:
            keywords_text = keywords_match.group(1).strip()
            result['keywords'] = [k.strip() for k in keywords_text.split(',') if k.strip()]

        # 兜底：如果标题提取失败，使用第一行
        if not result['rewritten_title']:
            lines = text.strip().split('\n')
            if lines:
                result['rewritten_title'] = lines[0].strip()[:50]

        # 兜底：如果正文提取失败，使用全部文本
        if not result['rewritten_content']:
            result['rewritten_content'] = text

        # 限制标题字数（按中文字符数）
        try:
            def chinese_char_count(s):
                return sum(1 for c in s if '\u4e00' <= c <= '\u9fff')

            title = result['rewritten_title']
            c_count = chinese_char_count(title)
            max_c_chars = 12

            if c_count > max_c_chars:
                count = 0
                cut_idx = len(title)
                for i, c in enumerate(title):
                    if '\u4e00' <= c <= '\u9fff':
                        count += 1
                        if count == max_c_chars:
                            cut_idx = i + 1
                            break
                result['rewritten_title'] = title[:cut_idx]
        except:
            pass

        return result


if __name__ == '__main__':
    # 测试
    import configparser
    cfg = configparser.ConfigParser()
    cfg.read('config.ini')
    config = {s: dict(cfg.items(s)) for s in cfg.sections()}

    generator = InspirationGenerator(config)

    # 测试文本灵感
    result = generator.generate_from_text(
        "AI技术发展迅速，ChatGPT等大模型正在改变各行各业的工作方式。",
        style="专业深度",
        length="medium"
    )
    if result:
        print(f"标题: {result['rewritten_title']}")
        print(f"摘要: {result['summary']}")
        print(f"正文预览: {result['rewritten_content'][:200]}...")
