# AI内容自动发布系统 v2.0

> 自动抓取爆款文章 → AI洗稿改写 → 一键发布到多个平台

## 功能特性

- ✅ **多平台支持**: 微信公众号、知乎、简书、CSDN
- ✅ **AI洗稿**: 使用 MiniMax 大模型改写，保留核心信息，去除AI痕迹
- ✅ **定时调度**: 每天自动执行，可配置发布时间和数量
- ✅ **去重机制**: 避免重复发布相同内容
- ✅ **历史记录**: 断点续传，程序重启不丢失进度

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

编辑 `config.ini`:

```ini
[wechat]
app_id = 你的AppID
app_secret = 你的AppSecret

[feeds]
urls = https://www.iplaysoft.com/feed, https://www.appinn.com/feed/

[publish]
enabled_platforms = wechat,zhihu,jianshu,csdn
schedule_times = 08:00,12:00,20:00
max_articles_per_day = 3

[ai]
api_key = 你的API密钥
api_base = https://ark.cn-beijing.volces.com/api/coding/v3
model = MiniMax-M2.7
```

### 3. 测试

```bash
# 测试抓取
python main.py --test-fetch

# 测试洗稿
python main.py --test-rewrite

# 测试发布
python main.py --test-publish

# 单次执行
python main.py --once

# 启动调度器
python main.py
```

## 平台配置

### 微信公众号
1. 登录 [微信公众平台](https://mp.weixin.qq.com/)
2. 设置与开发 → 基本配置
3. 添加服务器IP到白名单（115.191.29.26）
4. 获取 AppID 和 AppSecret

### 知乎
1. 登录知乎
2. 打开开发者工具 → Network
3. 找到任意API请求，复制 Cookie
4. 填入配置文件的 `cookies` 字段

### 简书
1. 登录简书
2. 在开发者工具中找 token
3. 填入配置文件的 `token` 字段

### CSDN
1. 登录CSDN
2. 打开开发者工具 → Network
3. 找到任意请求，复制 Cookie
4. 填入配置文件的 `cookies` 字段

## RSS源推荐

### AI/科技类
- 36氪: https://36kr.com/feed
- 虎嗅: https://www.huxiu.com/rss/
- 少数派: https://sspai.com/feed
- Appinn: https://www.appinn.com/feed/
- 小众软件: https://www.iplaysoft.com/feed/

### 综合类
- 知乎热榜: https://www.zhihu.com/rss
- 微博热搜: （需其他方式获取）

## 目录结构

```
wechat-autopost/
├── config.ini          # 配置文件
├── main.py             # 主入口
├── fetcher.py          # 文章抓取
├── rewriter.py          # AI洗稿
├── publisher.py        # 微信公众号发布
├── multi_publisher.py  # 多平台管理器
├── scheduler.py        # 定时调度器
├── articles/           # 缓存文章
├── logs/              # 日志
└── published_history.json  # 发布历史
```

## systemd 部署

```bash
# 复制服务文件
sudo cp wechat-autopost.service /etc/systemd/system/

# 重新加载
sudo systemctl daemon-reload

# 启用并启动
sudo systemctl enable wechat-autopost
sudo systemctl start wechat-autopost

# 查看状态
sudo systemctl status wechat-autopost
```

## 注意事项

1. **微信公众号**只能创建草稿，需要手动发布
2. **各平台Cookie/Token**有效期有限，需要定期更新
3. **知乎**有API频率限制，发布不要太频繁
4. **头条**不支持个人自动发布，建议专注其他平台

## 免责声明

本工具仅供学习和研究使用，请遵守各平台的使用条款。对因使用本工具导致的账号问题概不负责。
