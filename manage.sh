#!/bin/bash
# AI内容自动发布系统 - 管理脚本

cd "$(dirname "$0")"

show_status() {
    echo ""
    echo "╔══════════════════════════════════════════╗"
    echo "║   AI内容自动发布系统 - 状态检查         ║"
    echo "╚══════════════════════════════════════════╝"
    echo ""
    
    # 检查Python依赖
    echo "📦 依赖检查:"
    python3 -c "import requests, feedparser, bs4, schedule" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "  ✅ 所有依赖已安装"
    else
        echo "  ❌ 依赖缺失，正在安装..."
        pip install --break-system-packages -q -r requirements.txt
        echo "  ✅ 依赖安装完成"
    fi
    
    # 检查配置文件
    echo ""
    echo "📋 配置文件:"
    if [ -f config.ini ]; then
        echo "  ✅ config.ini 存在"
    else
        echo "  ❌ config.ini 不存在"
    fi
    
    # 检查历史记录
    echo ""
    echo "📊 今日发布:"
    if [ -f published_history.json ]; then
        count=$(python3 -c "import json; d=json.load(open('published_history.json')); print(len(d.get('published_today', [])))")
        echo "  已发布: $count 篇"
    else
        echo "  无记录"
    fi
    
    # 检查进程
    echo ""
    echo "🔄 运行状态:"
    if pgrep -f "python3 main.py" > /dev/null; then
        echo "  🟢 运行中"
    else
        echo "  ⚪ 未运行"
    fi
    
    echo ""
}

case "$1" in
    start)
        echo "启动调度器..."
        python3 main.py
        ;;
    once)
        echo "单次执行..."
        python3 main.py --once
        ;;
    status)
        show_status
        ;;
    test)
        echo "运行测试..."
        python3 main.py --test-fetch
        echo ""
        python3 main.py --test-rewrite
        echo ""
        python3 main.py --test-publish
        ;;
    log)
        tail -50 logs/service.log 2>/dev/null || echo "暂无日志"
        ;;
    *)
        echo "用法: $0 {start|once|status|test|log}"
        echo ""
        echo "  start   - 启动调度器"
        echo "  once    - 单次执行"
        echo "  status  - 查看状态"
        echo "  test    - 运行测试"
        echo "  log     - 查看日志"
        ;;
esac
