#!/usr/bin/env python3
"""
配置管理界面 - Streamlit UI
专注配置项的查看和修改
"""
import streamlit as st
import configparser
import os

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


st.set_page_config(page_title="配置管理", page_icon="⚙️", layout="wide")
st.title("⚙️ 配置管理")

config = load_config()

# --- 微信公众号配置 ---
with st.expander("📱 微信公众号", expanded=True):
    wechat = config.get('wechat', {})
    c1, c2 = st.columns(2)
    with c1:
        wechat['app_id'] = st.text_input("AppID", value=wechat.get('app_id', ''), help="微信公众平台的 AppID")
    with c2:
        wechat['app_secret'] = st.text_input("AppSecret", value=wechat.get('app_secret', ''), type="password", help="微信公众平台的 AppSecret")
    config['wechat'] = wechat

# --- AI 配置 ---
with st.expander("🤖 AI 配置", expanded=True):
    ai = config.get('ai', {})
    ai['api_base'] = st.text_input("API 地址", value=ai.get('api_base', ''), help="AI 接口地址")
    ai['api_key'] = st.text_input("API Key", value=ai.get('api_key', ''), type="password", help="AI 接口密钥")
    models = [
        "doubao-seed-2-0-mini-260215",
        "doubao-pro-32k-250115",
        "deepseek-v3-2-251201",
    ]
    current = ai.get('model', '')
    idx = models.index(current) + 1 if current in models else 0
    ai['model'] = st.selectbox("模型", options=models, index=idx)
    config['ai'] = ai

# --- RSS 订阅源 ---
with st.expander("📡 RSS 订阅源", expanded=True):
    feeds = config.get('feeds', {})
    feeds['urls'] = st.text_area(
        "订阅地址（多个用逗号分隔）",
        value=feeds.get('urls', ''),
        height=80,
        help="例如：https://www.appinn.com/feed/"
    )
    config['feeds'] = feeds

# --- 头条热榜 ---
with st.expander("🔥 今日头条热榜", expanded=True):
    toutiao = config.get('toutiao', {'enabled': 'false', 'categories': 'news_hot', 'max_count': '20'})
    toutiao['enabled'] = str(st.checkbox("启用头条热榜", value=toutiao.get('enabled', 'false') == 'true'))
    category_options = {
        "热点榜": "news_hot",
        "科技": "news_tech",
        "财经": "news_finance",
        "汽车": "news_car",
        "娱乐": "news_ent",
        "游戏": "news_game",
        "国际": "news_world",
        "体育": "news_sports",
    }
    selected = st.multiselect(
        "热榜分类",
        options=list(category_options.keys()),
        default=[k for k, v in category_options.items() if v in toutiao.get('categories', 'news_hot')],
    )
    toutiao['categories'] = ','.join([category_options[k] for k in selected])
    toutiao['max_count'] = str(st.number_input("每分类最大篇数", value=int(toutiao.get('max_count', 20)), min_value=1, max_value=50))
    config['toutiao'] = toutiao

# --- 发布设置 ---
with st.expander("📤 发布设置", expanded=True):
    pub = config.get('publish', {})
    pub['enabled_platforms'] = st.text_input("发布平台（逗号分隔）", value=pub.get('enabled_platforms', 'wechat'))
    times = st.text_input("发布时间（逗号分隔，24小时制）", value=pub.get('schedule_times', '08:00,20:00'))
    pub['schedule_times'] = times
    pub['max_articles_per_day'] = str(st.number_input("每日最大发布篇数", value=int(pub.get('max_articles_per_day', 2)), min_value=1, max_value=10))
    pub['fetch_candidate_count'] = str(st.number_input("候选文章数量", value=int(pub.get('fetch_candidate_count', 10)), min_value=1, max_value=30))
    config['publish'] = pub

# --- 存储设置 ---
with st.expander("💾 存储设置", expanded=True):
    storage = config.get('storage', {})
    storage['articles_dir'] = st.text_input("文章缓存目录", value=storage.get('articles_dir', './articles'))
    config['storage'] = storage

# --- 保存按钮 ---
st.markdown("---")
if st.button("💾 保存配置", type="primary", use_container_width=True):
    save_config(config)
    st.success("✅ 配置已保存到 config.ini")
