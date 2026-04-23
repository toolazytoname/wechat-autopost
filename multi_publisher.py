#!/usr/bin/env python3
"""
多平台发布管理器

支持的平台：
- wechat: 微信公众号（草稿箱）
- zhihu: 知乎文章
- jianshu: 简书
- csdn: CSDN博客
- weibo: 微博（待研究）
"""

import os
import sys
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import configparser

class BasePublisher(ABC):
    """平台发布器基类"""
    
    def __init__(self, config: dict):
        self.config = config
    
    @abstractmethod
    def publish(self, article: Dict) -> bool:
        """发布文章，返回是否成功"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """返回平台名称"""
        pass
    
    def check_config(self) -> bool:
        """检查配置是否完整"""
        return True

class WeChatPublisher(BasePublisher):
    """微信公众号发布器"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.wechat_config = config.get('wechat', {})
        self.app_id = self.wechat_config.get('app_id', '')
        self.app_secret = self.wechat_config.get('app_secret', '')
    
    def get_name(self) -> str:
        return "微信公众号"
    
    def check_config(self) -> bool:
        return bool(self.app_id and self.app_secret)
    
    def publish(self, article: Dict) -> bool:
        """发布到微信公众号（草稿箱）"""
        # 复用原有的 publisher.py
        from publisher import WeChatPublisher as WCPoster
        poster = WCPoster(self.config)
        return poster.publish_article(article)

class ZhihuPublisher(BasePublisher):
    """知乎发布器"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.zhihu_config = config.get('zhihu', {})
        self.cookies = self.zhihu_config.get('cookies', '')
    
    def get_name(self) -> str:
        return "知乎"
    
    def check_config(self) -> bool:
        return bool(self.cookies)
    
    def publish(self, article: Dict) -> bool:
        """
        发布到知乎专栏
        使用Cookie认证的方式
        """
        import requests
        
        if not self.cookies:
            print(f"[{self.get_name()}] 未配置Cookie，跳过")
            return False
        
        url = "https://www.zhihu.com/api/v4/articles"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Cookie': self.cookies,
            'Content-Type': 'application/json',
            'X-API-VERSION': '3.0.91',
            'Referer': 'https://zhuanlan.zhihu.com/'
        }
        
        # 构建文章数据
        content = article.get('rewritten_content', article.get('content', ''))
        
        # 知乎文章需要HTML格式
        html_content = content.replace('\n', '<br>')
        
        payload = {
            'title': article.get('rewritten_title', article.get('title', '')),
            'content': html_content,
            'cover_url': '',  # 可选
            'permission': 'public',  # public or invite
            'column_id': ''  # 可选，专栏ID
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            result = response.json()
            
            if response.status_code == 201 or 'id' in result:
                print(f"[{self.get_name()}] 发布成功: {result.get('url', result.get('id', ''))}")
                return True
            else:
                print(f"[{self.get_name()}] 发布失败: {result}")
                return False
        except Exception as e:
            print(f"[{self.get_name()}] 发布异常: {e}")
            return False

class JianshuPublisher(BasePublisher):
    """简书发布器"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.jianshu_config = config.get('jianshu', {})
        self.token = self.jianshu_config.get('token', '')
    
    def get_name(self) -> str:
        return "简书"
    
    def check_config(self) -> bool:
        return bool(self.token)
    
    def publish(self, article: Dict) -> bool:
        """发布到简书"""
        import requests
        
        if not self.token:
            print(f"[{self.get_name()}] 未配置Token，跳过")
            return False
        
        url = "https://api.jianshu.com/api/notes"
        
        headers = {
            'User-Agent': 'JianShu/4.20.0 (Android 6.0)',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'title': article.get('rewritten_title', article.get('title', '')),
            'content': article.get('rewritten_content', article.get('content', '')),
            'visibility': 'public',
            'shared_at': '',  # 定时发布，可选
            'tags': ['AI副业', '工具推荐']  # 标签
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            result = response.json()
            
            if response.status_code == 201 or 'id' in result:
                print(f"[{self.get_name()}] 发布成功")
                return True
            else:
                print(f"[{self.get_name()}] 发布失败: {result}")
                return False
        except Exception as e:
            print(f"[{self.get_name()}] 发布异常: {e}")
            return False

class CSDNPublisher(BasePublisher):
    """CSDN发布器"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.csdn_config = config.get('csdn', {})
        self.cookies = self.csdn_config.get('cookies', '')
    
    def get_name(self) -> str:
        return "CSDN"
    
    def check_config(self) -> bool:
        return bool(self.cookies)
    
    def publish(self, article: Dict) -> bool:
        """发布到CSDN博客"""
        import requests
        
        if not self.cookies:
            print(f"[{self.get_name()}] 未配置Cookie，跳过")
            return False
        
        url = "https://mp.csdn.net/mp/blog/creation/article"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Cookie': self.cookies,
            'Content-Type': 'application/json',
            'Referer': 'https://mp.csdn.net/'
        }
        
        content = article.get('rewritten_content', article.get('content', ''))
        
        payload = {
            'title': article.get('rewritten_title', article.get('title', '')),
            'markdowncontent': content,
            'content': content,
            'tags': 'AI副业,工具推荐',
            'type': 'original',
            'status': 'publish'
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            result = response.json()
            
            if result.get('code') == 200 or result.get('data', {}).get('id'):
                print(f"[{self.get_name()}] 发布成功")
                return True
            else:
                print(f"[{self.get_name()}] 发布失败: {result}")
                return False
        except Exception as e:
            print(f"[{self.get_name()}] 发布异常: {e}")
            return False

class MultiPublisher:
    """多平台发布管理器"""
    
    def __init__(self, config: dict):
        self.config = config
        self.publishers: List[BasePublisher] = []
        self._init_publishers()
    
    def _init_publishers(self):
        """初始化所有发布器"""
        # 微信公众号
        wechat = WeChatPublisher(self.config)
        if wechat.check_config():
            self.publishers.append(wechat)
            print(f"[MultiPublisher] 已加载: {wechat.get_name()}")
        
        # 知乎
        zhihu = ZhihuPublisher(self.config)
        if zhihu.check_config():
            self.publishers.append(zhihu)
            print(f"[MultiPublisher] 已加载: {zhihu.get_name()}")
        
        # 简书
        jianshu = JianshuPublisher(self.config)
        if jianshu.check_config():
            self.publishers.append(jianshu)
            print(f"[MultiPublisher] 已加载: {jianshu.get_name()}")
        
        # CSDN
        csdn = CSDNPublisher(self.config)
        if csdn.check_config():
            self.publishers.append(csdn)
            print(f"[MultiPublisher] 已加载: {csdn.get_name()}")
    
    def publish_all(self, article: Dict) -> Dict[str, bool]:
        """发布到所有已配置的平台"""
        results = {}
        for publisher in self.publishers:
            platform_name = publisher.get_name()
            print(f"\n[MultiPublisher] 正在发布到 {platform_name}...")
            try:
                success = publisher.publish(article)
                results[platform_name] = success
                print(f"[MultiPublisher] {platform_name}: {'✅ 成功' if success else '❌ 失败'}")
            except Exception as e:
                print(f"[MultiPublisher] {platform_name} 异常: {e}")
                results[platform_name] = False
        
        return results
    
    def get_supported_platforms(self) -> List[str]:
        """获取所有支持的平台"""
        return [p.get_name() for p in self.publishers]

if __name__ == '__main__':
    # 测试
    cfg = configparser.ConfigParser()
    cfg.read('config.ini')
    config = {s: dict(cfg.items(s)) for s in cfg.sections()}
    
    manager = MultiPublisher(config)
    print(f"\n已配置的平台: {manager.get_supported_platforms()}")
