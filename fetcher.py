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
    def __init__(self, config: dict, track_manager=None):
        self.config = config
        # 按逗号分隔读取URLs（兼容旧配置）
        urls_str = config.get('feeds', {}).get('urls', '')
        self.urls = [u.strip() for u in urls_str.split(',') if u.strip()]
        self.articles_dir = config.get('storage', {}).get('articles_dir', './articles')
        self.toutiao_config = config.get('toutiao', {})
        self.toutiao_categories = [c.strip() for c in self.toutiao_config.get('categories', 'news_hot').split(',') if c.strip()]
        self.toutiao_enabled = self.toutiao_config.get('enabled', 'false').lower() == 'true'
        os.makedirs(self.articles_dir, exist_ok=True)

        # 赛道管理器
        if track_manager is None:
            from track_manager import TrackManager
            track_manager = TrackManager()
        self.track_manager = track_manager
    
    def fetch_from_toutiao_hot(self, category: str = 'news_hot') -> List[Dict]:
        """从今日头条热榜抓取文章
        
        Args:
            category: 热榜分类
                - news_hot: 热点榜（默认）
                - news_world: 国际
                - news_finance: 财经
                - news_tech: 科技
                - news_sports: 体育
                - news_ent: 娱乐
                - news_game: 游戏
        """
        articles = []
        try:
            url = f"https://www.toutiao.com/api/pc/feed/?max_behot_time=0&tab_name={category}&category={category}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.toutiao.com/',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            }
            resp = requests.get(url, headers=headers, timeout=15)
            
            if resp.status_code != 200:
                print(f"[Fetcher] 头条热榜请求失败 HTTP {resp.status_code}: {category}")
                return articles
            
            data = resp.json()
            items = data.get('data', []) if isinstance(data, dict) else []
            
            max_count = int(self.toutiao_config.get('max_count', 20))
            
            for item in items[:max_count]:
                if not item.get('title'):
                    continue
                
                # 过滤视频内容（热榜大部分是视频，不适合图文平台）
                if item.get('has_video') or item.get('tag_url', '').endswith('video'):
                    continue
                
                group_id = item.get('group_id', '')
                article_url = f"https://www.toutiao.com/article/{group_id}/"
                
                # 封面图：优先用 middle_image（大图），其次 image_url（小图）
                cover_url = item.get('middle_image') or item.get('image_url', '')
                if cover_url and cover_url.startswith('//'):
                    cover_url = 'https:' + cover_url
                
                article = {
                    'title': item.get('title', ''),
                    'url': article_url,
                    'summary': item.get('abstract', item.get('description', ''))[:500],
                    'published': item.get('publish_time', datetime.now().isoformat()),
                    'source': 'toutiao',
                    'fetched_at': datetime.now().isoformat(),
                    'chinese_tag': item.get('chinese_tag', category),
                    'article_genre': item.get('article_genre', ''),
                    'cover_image': cover_url if cover_url else None,
                    'body_images': [],
                }
                articles.append(article)
            
            print(f"[Fetcher] 头条热榜({category})获取 {len(articles)} 篇")
            
        except requests.exceptions.RequestException as e:
            print(f"[Fetcher] 头条热榜网络错误 {category}: {e}")
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"[Fetcher] 头条热榜解析错误 {category}: {e}")
        
        return articles
    
    def fetch_from_rss(self, url: str, max_count: int = 10) -> List[Dict]:
        """从RSS源获取文章列表"""
        articles = []
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_count]:  # 限制数量
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

    def fetch_from_track(self, track_id: str = None) -> List[Dict]:
        """从指定赛道配置抓取文章

        Args:
            track_id: 赛道 ID，默认使用活跃赛道

        Returns:
            文章列表，每篇带有 track_id 标识
        """
        if track_id is None:
            track = self.track_manager.get_active_track()
        else:
            track = self.track_manager.get_track(track_id)

        if not track:
            print("[Fetcher] 未找到赛道配置，fallback 到全局 RSS")
            return self.fetch_all()

        feeds = self.track_manager.get_enabled_feeds(track['id'])
        if not feeds:
            print(f"[Fetcher] 赛道 {track['name']} 没有启用订阅源")
            return []

        all_articles = []
        for feed in feeds:
            url = feed['url']
            limit = feed.get('max_articles_per_fetch', 10)
            print(f"[Fetcher] 抓取 {track['name']} / {feed['name']}: {url}")
            articles = self.fetch_from_rss(url, max_count=limit)
            for article in articles:
                article['track_id'] = track['id']
                article['track_name'] = track['name']
                article['feed_name'] = feed['name']
                images = self.fetch_article_images(article['url'])
                article['cover_image'] = images.get('cover')
                article['body_images'] = images.get('images', [])
            all_articles.extend(articles)
            print(f"[Fetcher] 获取到 {len(articles)} 篇")

        # 去重
        seen_urls = set()
        unique = []
        for a in all_articles:
            if a['url'] not in seen_urls:
                seen_urls.add(a['url'])
                unique.append(a)
        print(f"[Fetcher] 赛道 {track['name']} 去重后共 {len(unique)} 篇")
        return unique
    
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
                    # 过滤小图标：宽度小于100像素的跳过
                    width = img.get('width')
                    if width and (int(width) if width else 0) < 100:
                        continue
                    result['images'].append(src)
                    if len(result['images']) >= 5:
                        break
            
            print(f"[Fetcher] 提取到封面图: {result['cover'] is not None}, 正文图片: {len(result['images'])}张")
            
        except Exception as e:
            print(f"[Fetcher] 图片提取失败 {url}: {e}")
        
        return result

    def fetch_toutiao_article_content(self, url: str, group_id: str = '') -> str:
        """
        获取头条文章正文（专门处理头条页面结构）
        
        优先用头条内链API获取原文内容，避免被重定向到登录页。
        """
        # 方法1: 尝试用 m.toutiao.com 移动版（通常不需要登录）
        try:
            mobile_url = url.replace('www.toutiao.com', 'm.toutiao.com')
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 MicroMessenger/7.0.0.14(0x17000d2e) NetType/WIFI Language/zh_CN',
                'Referer': 'https://m.toutiao.com/',
            }
            resp = requests.get(mobile_url, headers=headers, timeout=10)
            if resp.status_code == 200 and len(resp.text) > 500:
                soup = BeautifulSoup(resp.text, 'html.parser')
                # 提取正文段落
                content_div = soup.find('article') or soup.find('div', id='activity-name')
                if content_div:
                    paragraphs = content_div.find_all('p')
                    if paragraphs:
                        content = '\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                        if len(content) > 100:
                            print(f"[Fetcher] 头条文章内容获取成功({len(content)}字)")
                            return content[:3000]
        except Exception as e:
            print(f"[Fetcher] 头条移动版解析失败: {e}")
        
        # 方法2: 尝试抓取 group_id 对应的内容API
        if group_id:
            try:
                content_url = f"https://www.toutiao.com/api/pc/article/{group_id}/"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://www.toutiao.com/',
                    'Accept': 'application/json, text/plain, */*',
                }
                resp = requests.get(content_url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get('data', {}).get('content', '')
                    if content:
                        soup = BeautifulSoup(content, 'html.parser')
                        text = soup.get_text(separator='\n', strip=True)
                        if len(text) > 100:
                            print(f"[Fetcher] 头条内容API获取成功({len(text)}字)")
                            return text[:3000]
            except Exception as e:
                print(f"[Fetcher] 头条内容API失败: {e}")
        
        # 方法3: 回退到通用网页抓取
        return self.fetch_article_content(url)

    def save_article(self, article: Dict) -> str:
        """保存文章到本地"""
        # 用URL生成唯一ID
        article_id = hashlib.md5(article['url'].encode()).hexdigest()[:12]
        filename = f"{article_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        filepath = os.path.join(self.articles_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(article, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    def fetch_all(self, track_id: str = None) -> List[Dict]:
        """从所有配置的源抓取文章

        Args:
            track_id: 可选，指定赛道 ID。使用赛道配置抓取。
                     不指定时 fallback 到全局 RSS + 头条配置（兼容旧行为）。
        """
        # 如果指定了赛道，使用赛道配置
        if track_id is not None:
            return self.fetch_from_track(track_id)

        # 兼容旧行为：全局抓取
        all_articles = []

        # 抓取今日头条热榜
        if self.toutiao_enabled:
            for category in self.toutiao_categories:
                articles = self.fetch_from_toutiao_hot(category)
                all_articles.extend(articles)

        # 抓取RSS源
        for url in self.urls:
            if not url.strip():
                continue
            print(f"[Fetcher] 正在抓取: {url}")
            articles = self.fetch_from_rss(url)
            # 补充图片信息
            for article in articles:
                images = self.fetch_article_images(article['url'])
                article['cover_image'] = images.get('cover')
                article['body_images'] = images.get('images', [])
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
