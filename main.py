#!/usr/bin/env python3
"""
微信公众号自动发布系统 v2.0 - 主入口

功能：
1. 定时从RSS源抓取爆款文章
2. AI洗稿改写（支持多平台）
3. 自动发布到多个平台

支持的平台：
- 微信公众号（草稿箱）
- 知乎专栏
- 简书
- CSDN博客

用法：
    python main.py              # 启动调度器
    python main.py --once       # 执行一次然后退出（测试用）
    python main.py --test-rewrite  # 只测试洗稿
    python main.py --test-fetch    # 只测试抓取
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import configparser
from fetcher import ArticleFetcher
from rewriter import ArticleRewriter
from multi_publisher import MultiPublisher
from scheduler import AutoScheduler

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    if not os.path.exists(config_path):
        print(f"错误: 配置文件 {config_path} 不存在!")
        sys.exit(1)
    
    cfg = configparser.ConfigParser()
    cfg.read(config_path)
    return {s: dict(cfg.items(s)) for s in cfg.sections()}

def main():
    parser = argparse.ArgumentParser(description='微信公众号自动发布系统 v2.0')
    parser.add_argument('--once', action='store_true', help='执行一次然后退出（测试用）')
    parser.add_argument('--test-fetch', action='store_true', help='只测试抓取功能')
    parser.add_argument('--test-rewrite', action='store_true', help='只测试洗稿功能')
    parser.add_argument('--test-publish', action='store_true', help='只测试发布功能')
    args = parser.parse_args()
    
    print("""
╔══════════════════════════════════════════╗
║   AI内容自动发布系统 v2.0                ║
║   多平台 · 自动抓取 · AI洗稿             ║
╚══════════════════════════════════════════╝
    """)
    
    config = load_config()
    
    # 显示配置信息
    enabled = config.get('publish', {}).get('enabled_platforms', 'wechat')
    schedule = config.get('publish', {}).get('schedule_times', '08:00,20:00')
    max_articles = config.get('publish', {}).get('max_articles_per_day', '3')
    
    print(f"[配置] 目标平台: {enabled}")
    print(f"[配置] 每日发布时间: {schedule}")
    print(f"[配置] 每日最大发布: {max_articles} 篇")
    print()
    
    # 初始化组件
    fetcher = ArticleFetcher(config)
    rewriter = ArticleRewriter(config)
    publisher = MultiPublisher(config)
    scheduler = AutoScheduler(config, fetcher, rewriter, publisher)
    
    if args.test_fetch:
        print("=== 测试：抓取功能 ===")
        articles = fetcher.fetch_all()
        print(f"抓取结果: {len(articles)} 篇")
        for i, a in enumerate(articles[:5]):
            print(f"  {i+1}. {a['title']}")
        return
    
    if args.test_rewrite:
        print("=== 测试：洗稿功能 ===")
        articles = fetcher.fetch_all()
        if articles:
            article = articles[0]
            content = fetcher.fetch_article_content(article['url'])
            article['content'] = content
            print(f"原文: {article['title'][:50]}...")
            rewritten = rewriter.rewrite(article)
            if rewritten:
                print(f"洗后: {rewritten['rewritten_title'][:50]}...")
                print(f"内容: {rewritten['rewritten_content'][:200]}...")
        return
    
    if args.test_publish:
        print("=== 测试：发布功能 ===")
        articles = fetcher.fetch_all()
        if articles:
            article = articles[0]
            content = fetcher.fetch_article_content(article['url'])
            article['content'] = content
            rewritten = rewriter.rewrite(article)
            if rewritten:
                print(f"发布文章: {rewritten['rewritten_title']}")
                results = publisher.publish_all(rewritten)
                for p, r in results.items():
                    print(f"  {p}: {'✅' if r else '❌'}")
        return
    
    if args.once:
        print("[模式] 单次执行模式\n")
        scheduler.run_once()
    else:
        print("[模式] 调度器模式\n")
        scheduler.start()

if __name__ == '__main__':
    main()
