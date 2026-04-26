#!/usr/bin/env python3
"""
定时调度器 v2 - 每天定时执行抓取、洗稿、发布
"""

import schedule
import time
import threading
import json
import os
from datetime import datetime
from typing import List, Dict

class AutoScheduler:
    def __init__(self, config: dict, fetcher, rewriter, publisher):
        self.config = config
        self.fetcher = fetcher
        self.rewriter = rewriter
        self.publisher = publisher
        
        self.publish_config = config.get('publish', {})
        self.schedule_times = self.publish_config.get('schedule_times', '08:00,20:00').split(',')
        self.max_articles = int(self.publish_config.get('max_articles_per_day', '2'))
        self.candidate_count = int(self.publish_config.get('fetch_candidate_count', '10'))
        self.enabled_platforms = [p.strip() for p in self.publish_config.get('enabled_platforms', 'wechat').split(',')]
        
        self.published_today = []
        self.last_publish_date = None
        
        # 历史记录
        self.history_file = 'published_history.json'
        self.load_history()
    
    def load_history(self):
        """加载历史记录"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    self.published_today = data.get('published_today', [])
                    self.last_publish_date = data.get('last_date', None)
            except:
                pass
    
    def save_history(self):
        """保存历史记录"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump({
                    'published_today': self.published_today,
                    'last_date': self.last_publish_date
                }, f, ensure_ascii=False)
        except:
            pass
    
    def reset_daily(self):
        """重置每日计数"""
        today = datetime.now().strftime('%Y-%m-%d')
        if self.last_publish_date != today:
            self.published_today = []
            self.last_publish_date = today
            self.save_history()
            print(f"[Scheduler] 新的一天({today})，重置发布计数")
    
    def is_already_published(self, article: Dict) -> bool:
        """检查文章是否已经发布过（去重）"""
        url = article.get('original_url', '') or article.get('url', '')
        title = article.get('rewritten_title', '') or article.get('title', '')
        
        for p in self.published_today:
            if p.get('url') == url or p.get('title') == title:
                return True
        return False
    
    def daily_job(self):
        """每日定时任务"""
        self.reset_daily()
        
        if len(self.published_today) >= self.max_articles:
            print(f"[Scheduler] 今日发布已达上限({self.max_articles}篇)，跳过")
            return
        
        print(f"\n{'='*50}")
        print(f"[Scheduler] [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始执行任务")
        print(f"[Scheduler] 目标平台: {', '.join(self.enabled_platforms)}")
        print(f"[Scheduler] 今日已发布: {len(self.published_today)}/{self.max_articles}")
        print(f"{'='*50}")
        
        # 1. 抓取文章
        print("\n[Scheduler] 步骤1: 抓取文章...")
        articles = self.fetcher.fetch_all()
        
        if not articles:
            print("[Scheduler] 没有抓取到文章，跳过")
            return
        
        print(f"[Scheduler] 抓取到 {len(articles)} 篇文章")
        
        # 2. 洗稿
        print("\n[Scheduler] 步骤2: AI洗稿...")
        rewritten_articles = []
        for i, article in enumerate(articles[:self.candidate_count]):
            if len(self.published_today) >= self.max_articles:
                break
            
            # 获取完整内容和图片
            print(f"[Scheduler] 获取文章内容: {article.get('title', '')[:30]}...")
            
            # 头条文章用专门的内容抓取方法
            if article.get('source') == 'toutiao':
                group_id = ''
                # 从URL中提取group_id: /article/7632660610332787241/
                import re
                match = re.search(r'/article/(\d+)', article['url'])
                if match:
                    group_id = match.group(1)
                content = self.fetcher.fetch_toutiao_article_content(article['url'], group_id)
            else:
                content = self.fetcher.fetch_article_content(article['url'])
            
            if not content or len(content) < 100:
                print(f"[Scheduler] 文章内容过短跳过: {article.get('title', '')[:30]}")
                continue
            
            article['content'] = content
            
            # 提取封面图和正文图片
            # 头条文章已在热榜API中提取封面，跳过封面抓取；正文图片同理
            if article.get('source') != 'toutiao':
                images_info = self.fetcher.fetch_article_images(article['url'])
                article['cover_image'] = images_info.get('cover')
                article['body_images'] = images_info.get('images', [])
            
            # 检查是否已发布
            if self.is_already_published(article):
                print(f"[Scheduler] 文章已发布过跳过: {article.get('title', '')[:30]}")
                continue
            
            # 洗稿
            print(f"[Scheduler] 正在洗稿 {i+1}/{min(self.candidate_count, len(articles))}...")
            rewritten = self.rewriter.rewrite(article)
            if rewritten:
                # 传递封面图信息
                rewritten['cover_image'] = article.get('cover_image')
                rewritten['body_images'] = article.get('body_images', [])
                rewritten_articles.append(rewritten)
            else:
                print(f"[Scheduler] 洗稿失败: {article.get('title', '')[:30]}")
        
        if not rewritten_articles:
            print("[Scheduler] 没有成功洗稿的文章，跳过")
            return
        
        print(f"[Scheduler] 成功洗稿 {len(rewritten_articles)} 篇文章")
        
        # 3. 发布
        print(f"\n[Scheduler] 步骤3: 发布到平台...")
        success_count = 0
        for article in rewritten_articles:
            if len(self.published_today) >= self.max_articles:
                break
            
            print(f"\n[Scheduler] --- 发布: {article.get('rewritten_title', '无标题')[:40]}...")
            
            # 发布到各平台
            results = self.publisher.publish_all(article)
            
            # 只要有一个平台成功就算成功
            if any(results.values()):
                self.published_today.append({
                    'title': article.get('rewritten_title'),
                    'url': article.get('original_url'),
                    'platforms': [k for k, v in results.items() if v],
                    'published_at': datetime.now().isoformat()
                })
                success_count += 1
                print(f"[Scheduler] ✅ 发布成功!")
            else:
                print(f"[Scheduler] ❌ 所有平台都失败")
            
            # 保存进度
            self.save_history()
        
        print(f"\n{'='*50}")
        print(f"[Scheduler] 任务完成!")
        print(f"[Scheduler] 今日已发布 {len(self.published_today)}/{self.max_articles} 篇")
        print(f"{'='*50}")
    
    def start(self):
        """启动调度器"""
        print(f"""
╔══════════════════════════════════════════╗
║     微信公众号自动发布系统 v2.0           ║
║     定时调度器                            ║
╚══════════════════════════════════════════╝
        """)
        print(f"[Scheduler] 目标平台: {', '.join(self.enabled_platforms)}")
        print(f"[Scheduler] 计划发布时间: {', '.join([t.strip() for t in self.schedule_times])}")
        print(f"[Scheduler] 每日最大发布: {self.max_articles} 篇")
        
        # 注册定时任务
        for time_str in self.schedule_times:
            time_str = time_str.strip()
            schedule.every().day.at(time_str).do(self.daily_job)
            print(f"[Scheduler] ✅ 已注册: 每天 {time_str}")
        
        print("[Scheduler] 调度器运行中，按 Ctrl+C 停止\n")
        
        # 运行一次先
        self.daily_job()
        
        # 启动调度循环
        def run_schedule():
            while True:
                schedule.run_pending()
                time.sleep(60)
        
        thread = threading.Thread(target=run_schedule, daemon=True)
        thread.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[Scheduler] 调度器已停止")
            self.save_history()
    
    def schedule_track(self, track_id: str = None) -> List[Dict]:
        """按赛道执行定时发布

        Args:
            track_id: 赛道 ID，为 None 则执行所有启用赛道

        Returns:
            发布结果列表
        """
        from track_manager import TrackManager
        tm = TrackManager()
        results = []

        if track_id:
            tracks = [tm.get_track(track_id)] if tm.get_track(track_id) else []
        else:
            tracks = tm.get_enabled_tracks()

        for track in tracks:
            tid = track['id']
            pub = track.get('publish', {})
            max_batch = pub.get('max_per_batch', 2)

            track_feeds = track.get('feeds', [])
            if not track_feeds:
                print(f"[Scheduler] 赛道「{track['name']}」无订阅源，跳过")
                continue

            fetcher = ArticleFetcher(self.config, track_manager=tm)
            rewriter = ArticleRewriter(self.config, track_manager=tm)

            articles = fetcher.fetch_all(track_id=tid)
            if not articles:
                print(f"[Scheduler] 赛道「{track['name']}」抓取为空")
                continue

            articles = articles[:max_batch]

            for art in articles:
                rewritten = rewriter.rewrite(art, track_id=tid)
                if rewritten:
                    pub_result = self.publisher.publish(rewritten)
                    results.append({
                        'track': track['name'],
                        'title': rewritten.get('rewritten_title', ''),
                        'status': 'published' if pub_result else 'failed'
                    })

        return results

if __name__ == '__main__':
    import configparser
    from fetcher import ArticleFetcher
    from rewriter import ArticleRewriter
    from multi_publisher import MultiPublisher
    
    cfg = configparser.ConfigParser()
    cfg.read('config.ini')
    config = {s: dict(cfg.items(s)) for s in cfg.sections()}
    
    fetcher = ArticleFetcher(config)
    rewriter = ArticleRewriter(config)
    publisher = MultiPublisher(config)
    
    scheduler = AutoScheduler(config, fetcher, rewriter, publisher)
    scheduler.run_once()
