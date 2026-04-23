#!/bin/bash
# 微信公众号自动发布系统 - 启动脚本

cd "$(dirname "$0")"

echo "=========================================="
echo "  微信公众号自动发布系统"
echo "=========================================="

# 检查配置
if [ ! -f config.ini ]; then
    echo "错误: config.ini 不存在"
    echo "请检查配置文件"
    exit 1
fi

# 检查依赖
echo "检查Python依赖..."
python3 -c "import requests, feedparser, bs4, schedule" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "安装依赖..."
    pip install --break-system-packages -q -r requirements.txt
fi

# 启动
echo ""
echo "启动中..."
echo "- 按 Ctrl+C 停止"
echo "- 日志输出到 logs/ 目录"
echo ""

mkdir -p logs

python3 main.py "$@"
