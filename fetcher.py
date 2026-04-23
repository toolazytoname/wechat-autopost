#!/usr/bin/env python3
"""
文章抓取器 - 从RSS源抓取爆款文章
"""

import feedparser
import requests
from bs4 import BeautifulSoup
import json
import hashlib
import os
from datetime import datetime
from typing import List, Dict

class ArticleFetcher:
    def __init__(self, config: dict):
        self.config = config
        # 按逗号分隔读取URLs
        urls_str = config.get('feeds', {}).get('urls', '')
        self.urls = [u.strip() for u in urls_str.split(',') if u.strip()]
        self.articles_dir = config.get('storage', {}).get('articles_dir', './articles')
        os.makedirs(self.articles_dir, exist_ok=True)
    
    def fetch_from_rss(self, url: str) -> List[Dict]:
        """从RSS源获取文章列表"""
        articles = []
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:  # 限制数量
                article = {
                    'title': entry.get('title', ''),
                    'url': entry.get('link', ''),
                    'summary': entry.get('summary', '')[:500],
                    'published': entry.get('published', ''),
                    'source': url,
                    'fetched_at': datetime.now().isoformat()
                }
                articles.append(article)
        except Exception as e:
            print(f"[Fetcher] RSS解析失败 {url}: {e}")
        return articles
    
    def fetch_article_content(self, url: str) -> str:
        """获取文章正文内容"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            resp = requests.get(url, headers=headers, timeout=10)
            # 自动检测编码
            if resp.encoding == 'ISO-8859-1' and resp.apparent_encoding:
                resp.encoding = resp.apparent_encoding
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 移除script和style
            for tag in soup(['script', 'style']):
                tag.decompose()
            
            # 获取正文（简单策略：找最大的文本块）
            paragraphs = soup.find_all('p')
            content = '\n'.join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50])
            
            return content[:3000]  # 限制长度
        except Exception as e:
            print(f"[Fetcher] 内容获取失败 {url}: {e}")
            return ""
    
    def fetch_article_images(self, url: str) -> Dict[str, str]:
        """
        获取文章的封面图和正文图片
        
        Returns:
            dict: {
                'cover': 'http://example.com/cover.jpg',  # 封面图URL
                'images': ['http://example.com/img1.jpg', ...],  # 正文图片列表
            }
        """
        result = {
            'cover': None,
            'images': []
        }
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.encoding == 'ISO-8859-1' and resp.apparent_encoding:
                resp.encoding = resp.apparent_encoding
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 提取封面图 (og:image)
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                result['cover'] = og_image['content']
            
            # 如果没有og:image，尝试twitter:image
            if not result['cover']:
                twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
                if twitter_image and twitter_image.get('content'):
                    result['cover'] = twitter_image['content']
            
            # 提取文章正文中的图片
            content_area = soup.find('article') or soup.find('main') or soup.find('div', class_=True)
            if content_area:
                imgs = content_area.find_all('img')
            else:
                imgs = soup.find_all('img')
            
            for img in imgs:
                src = img.get('src') or img.get('data-src') or img.get('data-original')
                if src and not src.startswith('data:'):
                    # 过滤掉小图标和追踪像素
                    width = img.get('width')
                    if width and int(width) if width else 0 < 100:
                        continue
                    result['images'].append(src)
                    if len(result['images']) >= 5:  # 最多5张图片
                        break
            
            print(f"[Fetcher] 提取到封面图: {result['cover'] is not None}, 正文图片: {len(result['images'])}张")
            
        except Exception as e:
            print(f"[Fetcher] 图片提取失败 {url}: {e}")
        
        return result
    
    def save_article(self, article: Dict) -> str:
        """保存文章到本地"""
        # 用URL生成唯一ID
        article_id = hashlib.md5(article['url'].encode()).hexdigest()[:12]
        filename = f"{article_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        filepath = os.path.join(self.articles_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(article, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    def fetch_all(self) -> List[Dict]:
        """从所有配置的源抓取文章"""
        all_articles = []
        
        for url in self.urls:
            if not url.strip():
                continue
            print(f"[Fetcher] 正在抓取: {url}")
            articles = self.fetch_from_rss(url)
            all_articles.extend(articles)
            print(f"[Fetcher] 获取到 {len(articles)} 篇")
        
        # 去重
        seen_urls = set()
        unique_articles = []
        for a in all_articles:
            if a['url'] not in seen_urls:
                seen_urls.add(a['url'])
                unique_articles.append(a)
        
        print(f"[Fetcher] 去重后共 {len(unique_articles)} 篇")
        return unique_articles

if __name__ == '__main__':
    # 测试
    import configparser
    cfg = configparser.ConfigParser()
    cfg.read('config.ini')
    config = {s: dict(cfg.items(s)) for s in cfg.sections()}
    
    fetcher = ArticleFetcher(config)
    articles = fetcher.fetch_all()
    print(f"共抓取 {len(articles)} 篇文章")
