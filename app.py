#!/usr/bin/env python3
"""
自媒体矩阵自动发布系统 - Streamlit UI
配置管理 + 手动测试触发
"""
import sys
import os

# 确保项目模块可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import configparser
import time

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.ini')


def load_config() -> dict:
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_PATH)
    return {s: dict(cfg.items(s)) for s in cfg.sections()}


def save_config(config: dict):
    cfg = configparser.ConfigParser()
    for section, items in config.items():
        cfg.add_section(section)
        for key, value in items.items():
            cfg.set(section, key, value)
    with open(CONFIG_PATH, 'w') as f:
        cfg.write(f)


# --- 页面配置 ---
st.set_page_config(page_title="自媒体自动发布", page_icon="🤖", layout="wide")

# --- 侧边栏导航 ---
page = st.sidebar.radio(
    "功能导航",
    ["🧪 手动测试", "⚙️ 配置管理", "📋 发布历史"],
    index=0
)

# ============================================================
# 手动测试页面
# ============================================================
if page == "🧪 手动测试":
    st.title("🧪 手动测试")

    # 初始化 session state
    st.session_state.setdefault('fetched_articles', [])
    st.session_state.setdefault('rewritten_article', None)
    st.session_state.setdefault('step', 0)  # 0=初始, 1=已抓取, 2=已改写

    # 加载配置
    config = load_config()

    # --- Step 1: 抓取文章 ---
    st.markdown("### Step 1 · 抓取文章")
    c1, c2 = st.columns([1, 1])

    fetch_source = c1.selectbox(
        "抓取来源",
        ["📡 RSS 订阅源", "🔥 今日头条热榜"],
        index=0
    )
    fetch_count = c2.number_input("抓取数量", value=5, min_value=1, max_value=20, step=1)

    if st.button("🔍 开始抓取", type="primary", use_container_width=True):
        with st.spinner("正在抓取..."):
            from fetcher import ArticleFetcher
            fetcher = ArticleFetcher(config)
            try:
                if "头条" in fetch_source:
                    articles = fetcher.fetch_from_toutiao_hot('news_tech')
                else:
                    articles = fetcher.fetch_all()
                articles = articles[:int(fetch_count)]
            except Exception as e:
                articles = []
                st.error(f"抓取失败: {e}")

        st.session_state['fetched_articles'] = articles
        st.session_state['step'] = 1
        st.session_state['rewritten_article'] = None

    # 显示抓取结果
    if st.session_state['fetched_articles']:
        articles = st.session_state['fetched_articles']
        st.success(f"✅ 抓取成功，共 {len(articles)} 篇文章")

        # 选择要改写的文章
        article_titles = [f"[{a.get('source', 'rss')}] {a.get('title', '')[:50]}" for a in articles]
        selected_idx = st.selectbox("选择文章进行改写", range(len(article_titles)), format_func=lambda i: article_titles[i])
        st.session_state['selected_article_idx'] = selected_idx

        with st.expander("📄 抓取预览", expanded=False):
            sel = articles[selected_idx]
            st.markdown(f"**标题**: {sel.get('title', '无')}")
            st.markdown(f"**来源**: {sel.get('source', 'rss')}")
            st.markdown(f"**URL**: {sel.get('url', '无')}")
            if sel.get('summary'):
                st.markdown(f"**摘要**: {sel.get('summary', '')[:200]}...")

        # --- Step 2: AI 改写 ---
        st.markdown("### Step 2 · AI 改写")
        if st.button("✍️ 开始改写", type="primary", use_container_width=True, disabled=(st.session_state['step'] < 1)):
            sel_art = st.session_state['fetched_articles'][st.session_state['selected_article_idx']]
            with st.spinner("正在改写（耗时约10-20秒）..."):
                from rewriter import ArticleRewriter
                try:
                    # 头条文章需要先抓正文
                    if sel_art.get('source') == 'toutiao':
                        import re
                        match = re.search(r'/article/(\d+)', sel_art.get('url', ''))
                        group_id = match.group(1) if match else ''
                        content = fetcher.fetch_toutiao_article_content(sel_art['url'], group_id)
                        sel_art['content'] = content
                    else:
                        sel_art['content'] = fetcher.fetch_article_content(sel_art['url'])

                    if not sel_art.get('content') or len(sel_art.get('content', '')) < 50:
                        st.error("❌ 文章正文太短或抓取失败，跳过")
                    else:
                        rewriter = ArticleRewriter(config)
                        rewritten = rewriter.rewrite(sel_art)
                        if rewritten:
                            st.session_state['rewritten_article'] = rewritten
                            st.session_state['step'] = 2
                            st.success("✅ 改写成功")
                        else:
                            st.error("❌ 改写失败，请检查 AI 配置")
                except Exception as e:
                    st.error(f"改写异常: {e}")

        # 显示改写结果
        if st.session_state['rewritten_article']:
            rw = st.session_state['rewritten_article']
            st.markdown("#### 改写结果预览")
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**原文标题**")
                st.info(rw.get('original_title', '')[:80])
            with col_b:
                st.markdown("**改写标题**")
                st.success(rw.get('rewritten_title', '')[:80])

            with st.expander("📝 改写正文预览（前300字）", expanded=False):
                st.text(rw.get('rewritten_content', '')[:300] + "...")

            # --- Step 3: 发布到微信 ---
            st.markdown("### Step 3 · 发布到微信")
            if st.button("📤 发布到微信公众号草稿箱", type="primary", use_container_width=True):
                with st.spinner("正在发布..."):
                    from publisher import WeChatPublisher
                    try:
                        publisher = WeChatPublisher(config)
                        success = publisher.publish_article(rw)
                        if success:
                            st.success("🎉 发布成功！请到微信公众号后台草稿箱查看")
                        else:
                            st.error("❌ 发布失败，请检查日志")
                    except Exception as e:
                        st.error(f"发布异常: {e}")

        # --- 批量操作 ---
        st.markdown("---")
        if st.button("🗑️ 清空当前测试结果", use_container_width=True):
            st.session_state['fetched_articles'] = []
            st.session_state['rewritten_article'] = None
            st.session_state['step'] = 0
            st.rerun()

# ============================================================
# 配置管理页面
# ============================================================
elif page == "⚙️ 配置管理":
    st.title("⚙️ 配置管理")

    config = load_config()
    tab_wechat, tab_ai, tab_feeds, tab_toutiao, tab_publish = st.tabs(
        ["📱 微信", "🤖 AI", "📡 RSS", "🔥 头条", "📤 发布"]
    )

    with tab_wechat:
        wechat = config.get('wechat', {})
        c1, c2 = st.columns(2)
        with c1:
            wechat['app_id'] = st.text_input("AppID", value=wechat.get('app_id', ''), help="微信公众平台的 AppID")
        with c2:
            wechat['app_secret'] = st.text_input("AppSecret", value=wechat.get('app_secret', ''), type="password")
        config['wechat'] = wechat

        # 测试微信连接
        if st.button("🔗 测试微信连接", use_container_width=True):
            with st.spinner("测试中..."):
                try:
                    import requests
                    resp = requests.get(
                        f"https://api.weixin.qq.com/cgi-bin/token",
                        params={
                            "grant_type": "client_credential",
                            "appid": wechat.get('app_id', ''),
                            "secret": wechat.get('app_secret', '')
                        },
                        timeout=10
                    )
                    data = resp.json()
                    if data.get('access_token'):
                        st.success(f"✅ 连接成功！token 有效期 {data.get('expires_in', 0)//60} 分钟")
                    else:
                        err_msg = data.get('errmsg', str(data))
                        st.error(f"❌ 连接失败: {err_msg}")
                except Exception as e:
                    st.error(f"❌ 连接异常: {e}")

    with tab_ai:
        ai = config.get('ai', {})
        ai['api_base'] = st.text_input("API 地址", value=ai.get('api_base', ''))
        ai['api_key'] = st.text_input("API Key", value=ai.get('api_key', ''), type="password")
        models = [
            "doubao-seed-2-0-mini-260215",
            "doubao-pro-32k-250115",
            "deepseek-v3-2-251201",
        ]
        current = ai.get('model', '')
        idx = 0
        try:
            idx = models.index(current)
        except ValueError:
            pass
        ai['model'] = st.selectbox("模型", options=models, index=idx)
        config['ai'] = ai

        # 测试 AI 连接
        if st.button("🔗 测试 AI 连接", use_container_width=True):
            with st.spinner("测试中..."):
                try:
                    import requests
                    resp = requests.post(
                        f"{ai.get('api_base', '')}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {ai.get('api_key', '')}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": ai.get('model', ''),
                            "messages": [{"role": "user", "content": "说hello"}],
                            "max_tokens": 10
                        },
                        timeout=15
                    )
                    if resp.status_code == 200:
                        st.success("✅ AI 连接成功！")
                    else:
                        st.error(f"❌ AI 返回 {resp.status_code}: {resp.text[:200]}")
                except Exception as e:
                    st.error(f"❌ 连接异常: {e}")

    with tab_feeds:
        feeds = config.get('feeds', {})
        feeds['urls'] = st.text_area(
            "订阅地址（多个用逗号分隔）",
            value=feeds.get('urls', ''),
            height=100,
        )
        config['feeds'] = feeds

    with tab_toutiao:
        toutiao = config.get('toutiao', {'enabled': 'false', 'categories': 'news_tech', 'max_count': '20'})
        toutiao['enabled'] = str(st.checkbox("启用头条热榜", value=toutiao.get('enabled', 'false') == 'true'))
        category_options = {
            "热点榜": "news_hot", "科技": "news_tech", "财经": "news_finance",
            "汽车": "news_car", "娱乐": "news_ent", "游戏": "news_game",
            "国际": "news_world", "体育": "news_sports",
        }
        selected = st.multiselect(
            "热榜分类",
            options=list(category_options.keys()),
            default=[k for k, v in category_options.items() if v in toutiao.get('categories', 'news_tech')],
        )
        toutiao['categories'] = ','.join([category_options[k] for k in selected])
        toutiao['max_count'] = str(st.number_input("每分类最大篇数", value=int(toutiao.get('max_count', 20)), min_value=1, max_value=50))
        config['toutiao'] = toutiao

    with tab_publish:
        pub = config.get('publish', {})
        pub['enabled_platforms'] = st.text_input("发布平台（逗号分隔）", value=pub.get('enabled_platforms', 'wechat'))
        pub['schedule_times'] = st.text_input("发布时间（逗号分隔）", value=pub.get('schedule_times', '08:00,20:00'))
        pub['max_articles_per_day'] = str(st.number_input("每日最大发布篇数", value=int(pub.get('max_articles_per_day', 2)), min_value=1, max_value=10))
        pub['fetch_candidate_count'] = str(st.number_input("候选文章数量", value=int(pub.get('fetch_candidate_count', 10)), min_value=1, max_value=30))
        config['publish'] = pub

        storage = config.get('storage', {})
        storage['articles_dir'] = st.text_input("文章缓存目录", value=storage.get('articles_dir', './articles'))
        config['storage'] = storage

    st.markdown("---")
    if st.button("💾 保存配置", type="primary", use_container_width=True):
        save_config(config)
        st.success("✅ 配置已保存到 config.ini")

# ============================================================
# 发布历史页面
# ============================================================
elif page == "📋 发布历史":
    st.title("📋 发布历史")
    history_file = os.path.join(os.path.dirname(__file__), 'published_history.json')
    if os.path.exists(history_file):
        import json
        with open(history_file) as f:
            history = json.load(f)
        today = history.get('published_today', [])
        if today:
            st.success(f"今日已发布 {len(today)} 篇")
            for i, item in enumerate(today):
                with st.expander(f"📄 {item.get('title', '无标题')[:40]}", expanded=False):
                    st.markdown(f"**原文**: {item.get('url', '无')}")
                    st.markdown(f"**平台**: {', '.join(item.get('platforms', []))}")
                    st.markdown(f"**时间**: {item.get('published_at', '无')[:19]}")
        else:
            st.info("今日暂无发布记录")
    else:
        st.info("暂无发布历史")
