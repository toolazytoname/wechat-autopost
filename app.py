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
    """加载配置，优先读取 Streamlit Secrets（云端），fallback 到本地 config.ini"""
    import streamlit as st

    # 优先用 Streamlit Cloud Secrets
    if hasattr(st, 'secrets'):
        try:
            config = {}
            # 微信
            config['wechat'] = {
                'app_id': st.secrets.get('WECHAT_APP_ID', ''),
                'app_secret': st.secrets.get('WECHAT_APP_SECRET', ''),
            }
            # AI
            config['ai'] = {
                'api_base': st.secrets.get('ARK_API_BASE', 'https://ark.cn-beijing.volces.com/api/coding/v3'),
                'api_key': st.secrets.get('ARK_API_KEY', ''),
                'model': st.secrets.get('ARK_MODEL', 'doubao-seed-2-0-mini-260215'),
            }
            # RSS
            config['feeds'] = {
                'urls': st.secrets.get('RSS_URLS', 'https://www.appinn.com/feed/'),
            }
            # 头条
            config['toutiao'] = {
                'enabled': st.secrets.get('TOUTIAO_ENABLED', 'true'),
                'categories': st.secrets.get('TOUTIAO_CATEGORIES', 'news_tech,news_finance'),
                'max_count': st.secrets.get('TOUTIAO_MAX_COUNT', '20'),
            }
            # 发布
            config['publish'] = {
                'enabled_platforms': st.secrets.get('PUBLISH_PLATFORMS', 'wechat'),
                'schedule_times': st.secrets.get('SCHEDULE_TIMES', '08:00,20:00'),
                'max_articles_per_day': st.secrets.get('MAX_ARTICLES_PER_DAY', '2'),
                'fetch_candidate_count': st.secrets.get('FETCH_CANDIDATE_COUNT', '10'),
            }
            # 存储
            config['storage'] = {
                'articles_dir': st.secrets.get('ARTICLES_DIR', './articles'),
            }
            return config
        except Exception:
            pass  # fallback 到本地文件

    # 本地开发：从 config.ini 读取
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_PATH)
    return {s: dict(cfg.items(s)) for s in cfg.sections()}


def save_config(config: dict):
    """保存配置到本地 config.ini（云端不支持写入，仅供本地开发用）"""
    if os.path.exists(CONFIG_PATH) and not os.access(CONFIG_PATH, os.W_OK):
        return  # 云端只读，跳过
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
    ["🎯 赛道管理", "📱 账号管理", "🧪 手动测试", "📊 状态监控", "⚙️ 配置管理", "📋 发布历史"],
    index=0
)

# ============================================================
# 赛道管理页面
# ============================================================
if page == "🎯 赛道管理":
    st.title("🎯 赛道管理")

    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from track_manager import TrackManager

    tm = TrackManager()

    # 初始化 session state
    st.session_state.setdefault('selected_track_id', tm._data.get('active_track'))
    st.session_state.setdefault('editing_track', None)

    # 顶部：赛道切换 + 统计
    all_tracks = tm.get_all_tracks()
    active = tm.get_active_track()
    enabled_tracks = tm.get_enabled_tracks()

    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        st.metric("总赛道数", len(all_tracks))
    with col_stat2:
        st.metric("已启用", len(enabled_tracks))
    with col_stat3:
        st.metric("当前活跃", active['name'] if active else '无')

    st.markdown("---")

    # 赛道选择下拉（用于查看/编辑）
    if all_tracks:
        track_options = {t['id']: f"{'✅ ' if t.get('enabled') else '❌ '}{t['name']}" for t in all_tracks}
        selected = st.selectbox(
            "选择赛道进行查看/编辑",
            options=list(track_options.keys()),
            format_func=lambda k: track_options[k],
            key="track_selector"
        )
        st.session_state['selected_track_id'] = selected
    else:
        st.info("暂无赛道，请新增赛道")
        selected = None

    if selected:
        track = tm.get_track(selected)
        if track:
            # ---- 赛道基本信息 ----
            col1, col2 = st.columns([1, 1])
            with col1:
                new_name = st.text_input("赛道名称", value=track['name'], key="track_name")
            with col2:
                new_desc = st.text_input("赛道描述", value=track.get('description', ''), key="track_desc")
            new_enabled = st.checkbox("✅ 启用此赛道", value=track.get('enabled', True), key="track_enabled")

            # ---- 订阅源管理 ----
            st.markdown("#### 📡 订阅源")
            feeds = track.get('feeds', [])
            feed_table = []
            for f in feeds:
                feed_table.append({
                    "名称": f.get('name', ''),
                    "URL": f['url'],
                    "启用": "✅" if f.get('enabled', True) else "❌",
                    "每次抓取上限": f.get('max_articles_per_fetch', 10)
                })
            if feed_table:
                st.dataframe(feed_table, use_container_width=True)

            # 添加订阅源
            with st.expander("➕ 添加订阅源", expanded=False):
                f_name = st.text_input("订阅源名称（如：36氪）", key="new_feed_name")
                f_url = st.text_input("RSS 地址", key="new_feed_url")
                f_limit = st.number_input("每次最多抓取篇数", value=10, min_value=1, max_value=50, key="new_feed_limit")
                if st.button("添加订阅源", key="add_feed_btn"):
                    if f_url and f_name:
                        ok = tm.add_feed(selected, {
                            "url": f_url,
                            "name": f_name,
                            "enabled": True,
                            "max_articles_per_fetch": f_limit
                        })
                        if ok:
                            st.success("订阅源已添加")
                            st.rerun()
                        else:
                            st.error("该 URL 已存在")
                    else:
                        st.warning("请填写名称和地址")

            # 删除订阅源
            if feeds:
                del_url = st.selectbox(
                    "选择订阅源删除",
                    options=[f['url'] for f in feeds],
                    format_func=lambda u: next((f['name'] for f in feeds if f['url'] == u), u),
                    key="del_feed_select"
                )
                if st.button("🗑️ 删除订阅源", key="del_feed_btn"):
                    if tm.remove_feed(selected, del_url):
                        st.success("订阅源已删除")
                        st.rerun()

            # ---- 发布策略 ----
            st.markdown("#### 📤 发布策略")
            pub = track.get('publish', {})

            # 发布账号选择
            from account_manager import AccountManager
            am = AccountManager()
            wechat_accounts = am.get_wechat_accounts()
            if wechat_accounts:
                account_options = {a['id']: a['name'] for a in wechat_accounts}
                current_account = pub.get('account_id', '')
                # 确保当前账号在选项中
                if current_account and current_account not in account_options:
                    account_options[current_account] = f"{current_account} (已删除)"
                selected_account = st.selectbox(
                    "发布账号",
                    options=list(account_options.keys()),
                    format_func=lambda k: account_options[k],
                    index=list(account_options.keys()).index(current_account) if current_account in account_options else 0,
                    key=f"account_select_{track['id']}"
                )
                pub['account_id'] = selected_account
            else:
                st.warning("⚠️ 暂无可用账号，请先到「账号管理」页面添加")
                pub['account_id'] = ''

            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                max_batch = st.number_input("每批次最多发布", value=pub.get('max_per_batch', 2), min_value=1, max_value=10, key="pub_batch")
            with col_b2:
                max_day = st.number_input("每日最多发布", value=pub.get('max_per_day', 4), min_value=1, max_value=20, key="pub_day")
            with col_b3:
                pub_times = st.text_input("发布时间", value=pub.get('publish_times', '08:00,20:00'), key="pub_times")

            # ---- 改写 Prompt ----
            st.markdown("#### ✍️ AI 改写 Prompt")
            current_prompt = track.get('rewriter_prompt', '')
            new_prompt = st.text_area(
                "赛道专属 Prompt",
                value=current_prompt,
                height=200,
                help="为空则使用全局默认 Prompt",
                key="rewriter_prompt_area"
            )

            st.markdown("---")
            col_save, col_del, col_activate = st.columns([1, 1, 1])
            with col_save:
                if st.button("💾 保存修改", type="primary", use_container_width=True):
                    updates = {
                        'name': new_name,
                        'description': new_desc,
                        'enabled': new_enabled,
                        'rewriter_prompt': new_prompt,
                        'publish': {
                            'max_per_batch': max_batch,
                            'max_per_day': max_day,
                            'publish_times': pub_times,
                            'account_id': pub.get('account_id', '')
                        }
                    }
                    tm.update_track(selected, updates)
                    st.success("赛道配置已保存")
                    st.rerun()
            with col_del:
                if st.button("🗑️ 删除赛道", use_container_width=True):
                    if tm.delete_track(selected):
                        st.success("赛道已删除")
                        st.rerun()
            with col_activate:
                if active and active['id'] == selected:
                    st.info(f"⭐ 当前活跃")
                else:
                    if st.button("⭐ 设为活跃", use_container_width=True):
                        tm.set_active_track(selected)
                        st.success(f"已将「{new_name}」设为活跃赛道")
                        st.rerun()

    # ---- 新增赛道 ----
    st.markdown("---")
    with st.expander("➕ 新增赛道", expanded=False):
        new_track_id = st.text_input("赛道 ID（英文/数字，唯一标识）", key="new_track_id")
        new_track_name = st.text_input("赛道名称", key="new_track_name_input")
        new_track_desc = st.text_input("赛道描述", key="new_track_desc_input")
        if st.button("创建赛道", key="create_track_btn"):
            if new_track_id and new_track_name:
                # 检查ID合法性
                import re
                if not re.match(r'^[a-zA-Z0-9_-]+$', new_track_id):
                    st.error("赛道 ID 只能包含字母、数字、下划线、连字符")
                else:
                    # 默认选择第一个可用账号
                    from account_manager import AccountManager
                    am = AccountManager()
                    wechat_accounts = am.get_wechat_accounts()
                    default_account_id = wechat_accounts[0]['id'] if wechat_accounts else ''

                    ok = tm.add_track({
                        'id': new_track_id,
                        'name': new_track_name,
                        'description': new_track_desc,
                        'enabled': True,
                        'feeds': [],
                        'rewriter_prompt': '',
                        'publish': {
                            'max_per_batch': 2,
                            'max_per_day': 4,
                            'publish_times': '08:00,20:00',
                            'account_id': default_account_id
                        }
                    })
                    if ok:
                        st.success(f"赛道「{new_track_name}」已创建")
                        st.rerun()
                    else:
                        st.error("赛道 ID 已存在")
            else:
                st.warning("赛道 ID 和名称必填")

# ============================================================
# 手动测试页面
# ============================================================
elif page == "🧪 手动测试":
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
        from track_manager import TrackManager
        tm = TrackManager()
        active_track = tm.get_active_track()
        track_id = active_track['id'] if active_track else None
        track_name = active_track['name'] if active_track else '全局'
        # 记录赛道 ID，发布时使用
        st.session_state['selected_track_id'] = track_id

        with st.spinner(f"正在从「{track_name}」抓取..."):
            from fetcher import ArticleFetcher
            fetcher = ArticleFetcher(config, track_manager=tm)
            try:
                if "头条" in fetch_source:
                    articles = fetcher.fetch_from_toutiao_hot('news_tech')
                else:
                    articles = fetcher.fetch_all(track_id=track_id)
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
        article_titles = [
            f"[{a.get('feed_name', a.get('source', 'rss')[:20])}] {a.get('title', '')[:50]}"
            for a in articles
        ]
        selected_idx = st.selectbox("选择文章进行改写", range(len(article_titles)), format_func=lambda i: article_titles[i])
        st.session_state['selected_article_idx'] = selected_idx

        with st.expander("📄 抓取预览", expanded=False):
            sel = articles[selected_idx]
            st.markdown(f"**标题**: {sel.get('title', '无')}")
            st.markdown(f"**赛道**: {sel.get('track_name', '无')} / {sel.get('feed_name', sel.get('source', '无'))}")
            st.markdown(f"**URL**: {sel.get('url', '无')}")
            if sel.get('summary'):
                st.markdown(f"**摘要**: {sel.get('summary', '')[:200]}...")

        # --- Step 2: AI 改写 ---
        st.markdown("### Step 2 · AI 改写")
        if st.button("✍️ 开始改写", type="primary", use_container_width=True, disabled=(st.session_state['step'] < 1)):
            from track_manager import TrackManager
            tm = TrackManager()
            sel_art = st.session_state['fetched_articles'][st.session_state['selected_article_idx']]
            track_id = sel_art.get('track_id')

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
                        rewriter = ArticleRewriter(config, track_manager=tm)
                        rewritten = rewriter.rewrite(sel_art, track_id=track_id)
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
            # 获取文章关联的赛道账号
            track_account_id = None
            if st.session_state.get('selected_track_id'):
                from track_manager import TrackManager
                tm = TrackManager()
                track = tm.get_track(st.session_state['selected_track_id'])
                if track:
                    track_account_id = track.get('publish', {}).get('account_id', '')
                    account_name = track.get('name', '未知账号')
                    if track_account_id:
                        st.info(f"📌 将发布到赛道绑定账号: **{account_name}**")
                    else:
                        st.warning("⚠️ 赛道未绑定账号，将使用全局配置")

            if st.button("📤 发布到微信公众号草稿箱", type="primary", use_container_width=True):
                with st.spinner("正在发布..."):
                    from publisher import WeChatPublisher
                    try:
                        publisher = WeChatPublisher(config, account_id=track_account_id)
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
# 状态监控页面
# ============================================================
elif page == "📊 状态监控":
    st.title("📊 系统状态监控")
    st.rerun_hook = None  # 用于手动刷新

    import json
    from datetime import datetime

    history_file = os.path.join(os.path.dirname(__file__), 'published_history.json')
    config = load_config()
    pub_cfg = config.get('publish', {})

    # --- 顶部统计卡片 ---
    col_stat1, col_stat2, col_stat3 = st.columns(3)

    # 读取发布历史
    today_articles = []
    if os.path.exists(history_file):
        with open(history_file) as f:
            history_data = json.load(f)
        today_articles = history_data.get('published_today', [])
        last_date = history_data.get('last_date', '无')
    else:
        last_date = '无'
        history_data = {}

    max_daily = int(pub_cfg.get('max_articles_per_day', 2))
    schedule_times = [t.strip() for t in pub_cfg.get('schedule_times', '08:00,20:00').split(',') if t.strip()]
    enabled_platforms = [p.strip() for p in pub_cfg.get('enabled_platforms', 'wechat').split(',') if p.strip()]

    with col_stat1:
        st.metric("今日发布", f"{len(today_articles)} / {max_daily} 篇",
                  delta=f"{len(today_articles) - max_daily}" if len(today_articles) > max_daily else None)
    with col_stat2:
        st.metric("目标平台", ", ".join(enabled_platforms) if enabled_platforms else "未配置")
    with col_stat3:
        st.metric("最近发布日期", last_date)

    # --- 进度条 ---
    progress = min(len(today_articles) / max_daily, 1.0)
    st.progress(progress, text=f"今日发布进度: {len(today_articles)}/{max_daily} 篇")

    # --- 发布进度时间线 ---
    st.markdown("### 📅 今日发布时间线")
    if today_articles:
        for item in today_articles:
            pt = item.get('published_at', '')[:19] if item.get('published_at') else '无时间'
            title_short = (item.get('title') or '无标题')[:40]
            platforms = ', '.join(item.get('platforms', []))
            st.markdown(
                f":green[✅] **{title_short}**  "
                f"| 平台: `{platforms}`  "
                f"| 时间: `{pt}`"
            )
    else:
        st.info("今日暂无发布记录")

    # --- 计划发布时间 ---
    st.markdown("### ⏰ 计划发布时间")
    if schedule_times:
        now = datetime.now()
        upcoming = [t for t in schedule_times if t > now.strftime('%H:%M')]
        passed = [t for t in schedule_times if t <= now.strftime('%H:%M')]
        for t in passed:
            st.markdown(f":gray[✅] `{t}` — 已执行")
        for t in upcoming:
            st.markdown(f":blue[🔔] `{t}` — 等待执行")
    else:
        st.warning("未配置发布时间")

    st.markdown("---")

    # --- 微信公众号连接状态 ---
    st.markdown("### 📱 微信公众号连接状态")
    wechat = config.get('wechat', {})
    app_id = wechat.get('app_id', '')
    app_secret = wechat.get('app_secret', '')

    if app_id and app_secret:
        # 尝试获取 access_token
        token_cache_file = os.path.join(os.path.dirname(__file__), '.token_cache.json')
        cached = {}
        if os.path.exists(token_cache_file):
            with open(token_cache_file) as f:
                cached = json.load(f)

        token_valid = False
        token_info = "未知"
        if cached.get('access_token') and cached.get('expires_at', 0) > time.time():
            token_valid = True
            remaining = int(cached['expires_at'] - time.time())
            token_info = f"有效 (剩余 {remaining // 60} 分 {remaining % 60} 秒)"
        else:
            with st.spinner("查询微信 access_token..."):
                try:
                    import requests
                    resp = requests.get(
                        "https://api.weixin.qq.com/cgi-bin/token",
                        params={
                            "grant_type": "client_credential",
                            "appid": app_id,
                            "secret": app_secret
                        },
                        timeout=10
                    )
                    data = resp.json()
                    if data.get('access_token'):
                        token_valid = True
                        expires_in = data.get('expires_in', 7200)
                        expires_at = time.time() + expires_in - 60
                        cached = {'access_token': data['access_token'], 'expires_at': expires_at}
                        with open(token_cache_file, 'w') as f:
                            json.dump(cached, f)
                        token_info = f"有效 (有效期 {expires_in // 60} 分钟)"
                        st.success(f"✅ access_token 获取成功 — {token_info}")
                    else:
                        err = data.get('errmsg', str(data))
                        token_info = f"❌ 失败: {err}"
                        st.error(f"❌ 获取 access_token 失败: {err}")
                except Exception as e:
                    token_info = f"❌ 异常: {e}"
                    st.error(f"❌ 网络异常: {e}")

        if token_valid:
            st.metric("access_token 状态", token_info)
    else:
        st.warning("⚠️ 未配置微信公众号 AppID / AppSecret，请到「配置管理」页面填写")

    st.markdown("---")

    # --- AI 模型状态 ---
    st.markdown("### 🤖 AI 模型状态")
    ai = config.get('ai', {})
    ai_base = ai.get('api_base', '')
    ai_key = ai.get('api_key', '')
    ai_model = ai.get('model', '')

    if ai_base and ai_key and ai_model:
        with st.spinner("测试 AI 连接..."):
            try:
                import requests
                resp = requests.post(
                    f"{ai_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {ai_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": ai_model,
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 5
                    },
                    timeout=15
                )
                if resp.status_code == 200:
                    st.success(f"✅ AI 模型 `{ai_model}` 连接正常")
                    st.metric("API 地址", ai_base)
                else:
                    st.error(f"❌ AI 返回 {resp.status_code}: {resp.text[:150]}")
                    st.metric("API 地址", ai_base)
            except Exception as e:
                st.error(f"❌ AI 连接异常: {e}")
                st.metric("API 地址", ai_base)
    else:
        st.warning("⚠️ 未完整配置 AI，请到「配置管理」页面填写")

    st.markdown("---")

    # --- 信息总览 ---
    st.markdown("### 🧩 配置总览")
    info_col1, info_col2 = st.columns(2)

    with info_col1:
        st.markdown("**📡 订阅源**")
        feeds = config.get('feeds', {}).get('urls', '未配置')
        for url in feeds.split(','):
            if url.strip():
                st.markdown(f"- `{url.strip()}`")

        st.markdown("")
        st.markdown("**🔥 头条热榜**")
        toutiao = config.get('toutiao', {})
        st.markdown(f"- 启用: `{toutiao.get('enabled', 'false')}`")
        st.markdown(f"- 分类: `{toutiao.get('categories', '未配置')}`")
        st.markdown(f"- 篇数: `{toutiao.get('max_count', '20')}`")

    with info_col2:
        st.markdown("**📤 发布设置**")
        st.markdown(f"- 平台: `{pub_cfg.get('enabled_platforms', 'wechat')}`")
        st.markdown(f"- 时间: `{pub_cfg.get('schedule_times', '08:00,20:00')}`")
        st.markdown(f"- 候选: `{pub_cfg.get('fetch_candidate_count', '10')} 篇/次`")

        st.markdown("")
        st.markdown("**💾 存储**")
        storage = config.get('storage', {})
        st.markdown(f"- 目录: `{storage.get('articles_dir', './articles')}`")

    # --- 刷新按钮 ---
    st.markdown("---")
    if st.button("🔄 刷新状态", use_container_width=True):
        st.rerun()

# ============================================================
# 账号管理页面（新增）
# ============================================================
elif page == "📱 账号管理":
    st.title("📱 多账号管理")

    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from account_manager import AccountManager

    am = AccountManager()

    # 统计卡片
    all_accounts = am.get_all_accounts()
    wechat_accounts = am.get_wechat_accounts()

    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.metric("账号总数", len(all_accounts))
    with col_stat2:
        st.metric("微信公众号", len(wechat_accounts))

    st.markdown("---")

    # ---- 账号列表 ----
    if all_accounts:
        st.markdown("### 📋 账号列表")

        for idx, account in enumerate(all_accounts):
            with st.expander(f"{'✅' if account.get('enabled', True) else '❌'} {account.get('name', account['id'])} ({account.get('platform', '未知')})", expanded=False):
                st.markdown(f"**账号 ID**: `{account['id']}`")
                st.markdown(f"**平台**: `{account.get('platform', 'wechat')}`")

                if account.get('platform') == 'wechat':
                    st.markdown(f"**AppID**: `{account.get('app_id', '')}`")
                    st.markdown(f"**AppSecret**: `{'*' * 20 + account.get('app_secret', '')[-4:] if account.get('app_secret') else '未设置'}`")

                # 测试按钮
                if st.button("🔗 测试连接", key=f"test_{account['id']}"):
                    result = am.test_account(account['id'])
                    if result['success']:
                        st.success(f"✅ {result['message']}")
                    else:
                        st.error(f"❌ {result['message']}")

                # 删除按钮
                if st.button("🗑️ 删除账号", key=f"del_{account['id']}"):
                    if am.delete_account(account['id']):
                        st.success("账号已删除")
                        st.rerun()

        st.markdown("---")
    else:
        st.info("暂无账号，请添加第一个公众号账号")

    # ---- 新增账号表单 ----
    st.markdown("### ➕ 添加新账号")

    platform = st.selectbox("平台类型", options=["微信公众号"], index=0)

    col1, col2 = st.columns(2)
    with col1:
        account_id = st.text_input("账号 ID（英文/数字，唯一标识）", help="例如: tech_official, biz_account")
        account_name = st.text_input("账号显示名称", help="例如: 科技前沿、职场干货")
    with col2:
        app_id = st.text_input("微信 AppID")
        app_secret = st.text_input("微信 AppSecret", type="password")

    enabled = st.checkbox("启用此账号", value=True)

    if st.button("添加账号", type="primary", use_container_width=True):
        if not account_id or not account_name:
            st.warning("请填写账号 ID 和名称")
        elif not app_id or not app_secret:
            st.warning("请填写 AppID 和 AppSecret")
        else:
            import re
            if not re.match(r'^[a-zA-Z0-9_-]+$', account_id):
                st.error("账号 ID 只能包含字母、数字、下划线、连字符")
            else:
                new_account = {
                    'id': account_id,
                    'name': account_name,
                    'platform': 'wechat',
                    'enabled': enabled,
                    'app_id': app_id,
                    'app_secret': app_secret,
                }
                ok = am.add_account(new_account)
                if ok:
                    st.success(f"✅ 账号「{account_name}」已添加！")
                    st.rerun()
                else:
                    st.error("账号 ID 已存在，请换一个")

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
