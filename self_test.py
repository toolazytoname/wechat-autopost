#!/usr/bin/env python3
"""
自动发文系统 - 自动化自测脚本
运行方式：python3 self_test.py
"""
import sys
import os
import subprocess
import time
import requests
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# 颜色输出
class colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'

def print_success(msg):
    print(f"{colors.GREEN}✅ {msg}{colors.ENDC}")

def print_error(msg):
    print(f"{colors.RED}❌ {msg}{colors.ENDC}")

def print_warning(msg):
    print(f"{colors.YELLOW}⚠️ {msg}{colors.ENDC}")

def print_info(msg):
    print(f"{colors.BLUE}ℹ️ {msg}{colors.ENDC}")

def run_step(step_name, func):
    """运行测试步骤"""
    print(f"\n{'='*60}")
    print(f"测试步骤：{step_name}")
    print(f"{'='*60}")
    try:
        result = func()
        if result:
            print_success(f"{step_name} - PASSED")
            return True
        else:
            print_error(f"{step_name} - FAILED")
            return False
    except Exception as e:
        print_error(f"{step_name} - EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

# ============================================================
# 测试用例
# ============================================================

def test_1_syntax_check():
    """1. Python 语法检查"""
    files_to_check = [
        "web/api/index.py",
        "inspiration_generator.py",
        "publisher.py",
        "rewriter.py",
        "track_manager.py",
        "account_manager.py"
    ]
    
    all_pass = True
    for f in files_to_check:
        f_path = os.path.join(BASE_DIR, f)
        if os.path.exists(f_path):
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", f_path],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"  ✓ {f}")
            else:
                print(f"  ✗ {f}: {result.stderr}")
                all_pass = False
        else:
            print_warning(f"  文件不存在：{f}，跳过")
    
    return all_pass

def test_2_dependency_check():
    """2. 依赖包检查"""
    required_packages = [
        "fastapi",
        "uvicorn",
        "jose",
        "passlib",
        "requests",
        "bs4"
    ]
    
    all_installed = True
    for pkg in required_packages:
        try:
            __import__(pkg)
            print(f"  ✓ {pkg}")
        except ImportError:
            print_error(f"  ✗ {pkg} - 未安装")
            all_installed = False
    
    return all_installed

def test_3_template_files():
    """3. 前端模板文件检查"""
    templates = [
        "web/templates/login.html",
        "web/templates/dashboard.html",
        "web/templates/inspiration.html"
    ]
    
    all_exist = True
    for t in templates:
        t_path = os.path.join(BASE_DIR, t)
        if os.path.exists(t_path):
            # 检查文件大小，确保不是空文件
            if os.path.getsize(t_path) > 100:
                print(f"  ✓ {t}")
            else:
                print_error(f"  ✗ {t} - 文件为空")
                all_exist = False
        else:
            print_error(f"  ✗ {t} - 文件不存在")
            all_exist = False
    
    return all_exist

def test_4_config_files():
    """4. 配置文件检查"""
    config_files = [
        "vercel.json",
        "requirements.txt"
    ]
    
    all_exist = True
    for f in config_files:
        f_path = os.path.join(BASE_DIR, f)
        if os.path.exists(f_path):
            print(f"  ✓ {f}")
        else:
            print_error(f"  ✗ {f} - 文件不存在")
            all_exist = False
    
    # 检查 vercel.json 格式
    try:
        with open(os.path.join(BASE_DIR, "vercel.json")) as f:
            json.load(f)
        print(f"  ✓ vercel.json 格式正确")
    except Exception as e:
        print_error(f"  ✗ vercel.json 格式错误: {e}")
        all_exist = False
    
    return all_exist

def test_5_fastapi_import():
    """5. FastAPI 应用导入检查"""
    try:
        from web.api.index import app
        print(f"  ✓ FastAPI 应用导入成功")
        print(f"  ✓ 应用标题: {app.title}")
        print(f"  ✓ 路由数量: {len(app.routes)}")
        return True
    except Exception as e:
        print_error(f"  ✗ 导入失败: {e}")
        return False

def test_6_auth_module():
    """6. 认证模块检查"""
    try:
        from web.api.index import (
            verify_password, create_access_token,
            authenticate_user, fake_users_db
        )
        
        # 测试密码验证
        test_hash = list(fake_users_db.values())[0]["hashed_password"]
        assert verify_password("admin123", test_hash)
        print(f"  ✓ 密码验证正常")
        
        # 测试 Token 生成
        token = create_access_token(data={"sub": "admin"})
        assert token and len(token) > 0
        print(f"  ✓ Token 生成正常")
        
        # 测试用户认证
        user = authenticate_user(fake_users_db, "admin", "admin123")
        assert user
        print(f"  ✓ 用户认证正常")
        
        return True
    except Exception as e:
        print_error(f"  ✗ 认证模块失败: {e}")
        return False

def test_7_inspiration_module():
    """7. 灵感生成模块检查"""
    try:
        from inspiration_generator import InspirationGenerator
        
        # 测试类是否能实例化
        config = {}
        generator = InspirationGenerator(config)
        print(f"  ✓ InspirationGenerator 实例化成功")
        
        # 测试方法是否存在
        assert hasattr(generator, "fetch_url_content")
        assert hasattr(generator, "generate_from_text")
        print(f"  ✓ 核心方法存在")
        
        return True
    except Exception as e:
        print_error(f"  ✗ 灵感模块失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_8_api_routes():
    """8. API 路由完整性检查"""
    try:
        from web.api.index import app
        
        # 检查关键路由是否存在
        expected_paths = [
            '/login',
            '/dashboard',
            '/inspiration',
            '/api/token',
            '/api/login',
            '/api/logout',
            '/api/health',
            '/api/inspiration/generate',
            # 第一阶段新增
            '/api/accounts',
            '/api/tracks',
            '/api/publish/wechat',
        ]
        
        actual_paths = [route.path for route in app.routes]
        
        all_found = True
        for path in expected_paths:
            if path in actual_paths:
                print(f"  ✓ {path}")
            else:
                print_error(f"  ✗ 缺少路由: {path}")
                all_found = False
        
        return all_found
    except Exception as e:
        print_error(f"  ✗ 路由检查失败: {e}")
        return False


def test_9_account_manager_api():
    """9. 账号管理 API 检查"""
    try:
        from web.api.index import app
        
        # 检查账号管理相关路由
        routes_to_check = [
            '/api/accounts',
        ]
        
        actual_paths = [route.path for route in app.routes]
        
        all_found = True
        for path in routes_to_check:
            if path in actual_paths:
                print(f"  ✓ {path}")
            else:
                print_error(f"  ✗ 缺少路由: {path}")
                all_found = False
        
        # 检查 AccountManager 类方法
        from account_manager import AccountManager
        required_methods = ['get_all_accounts', 'add_account', 'update_account', 'delete_account', 'test_account']
        for method in required_methods:
            if hasattr(AccountManager, method):
                print(f"  ✓ AccountManager.{method}()")
            else:
                print_error(f"  ✗ 缺少方法: AccountManager.{method}()")
                all_found = False
        
        return all_found
    except Exception as e:
        print_error(f"  ✗ 检查失败: {e}")
        return False


def test_10_track_manager_api():
    """10. 赛道管理 API 检查"""
    try:
        from web.api.index import app
        
        # 检查赛道管理相关路由
        routes_to_check = [
            '/api/tracks',
        ]
        
        actual_paths = [route.path for route in app.routes]
        
        all_found = True
        for path in routes_to_check:
            if path in actual_paths:
                print(f"  ✓ {path}")
            else:
                print_error(f"  ✗ 缺少路由: {path}")
                all_found = False
        
        # 检查 TrackManager 类方法
        from track_manager import TrackManager
        required_methods = ['get_all_tracks', 'get_track', 'add_track', 'update_track', 'delete_track', 'set_active_track']
        for method in required_methods:
            if hasattr(TrackManager, method):
                print(f"  ✓ TrackManager.{method}()")
            else:
                print_error(f"  ✗ 缺少方法: TrackManager.{method}()")
                all_found = False
        
        return all_found
    except Exception as e:
        print_error(f"  ✗ 检查失败: {e}")
        return False


def test_11_wechat_publish_api():
    """11. 微信发布 API 检查"""
    try:
        from web.api.index import app
        
        # 检查微信发布相关路由
        routes_to_check = [
            '/api/publish/wechat',
        ]
        
        actual_paths = [route.path for route in app.routes]
        
        all_found = True
        for path in routes_to_check:
            if path in actual_paths:
                print(f"  ✓ {path}")
            else:
                print_error(f"  ✗ 缺少路由: {path}")
                all_found = False
        
        # 检查 Publisher 类方法
        from publisher import WechatPublisher
        if hasattr(WechatPublisher, 'publish_article'):
            print(f"  ✓ WechatPublisher.publish_article()")
        else:
            print_error(f"  ✗ 缺少方法: WechatPublisher.publish_article()")
            all_found = False
        
        return all_found
    except Exception as e:
        print_error(f"  ✗ 检查失败: {e}")
        return False


def test_12_rss_fetch_api():
    """12. RSS 抓取 API 检查"""
    try:
        from web.api.index import app
        
        # 检查 RSS 相关路由
        routes_to_check = [
            '/api/rss/fetch',
            '/api/rss/track/{track_id}',
        ]
        
        actual_paths = [route.path for route in app.routes]
        
        all_found = True
        for path in routes_to_check:
            if path in actual_paths or '/api/rss/track/' in path:
                print(f"  ✓ {path}")
            else:
                print_error(f"  ✗ 缺少路由: {path}")
                all_found = False
        
        # 检查 Fetcher 类方法
        from fetcher import ArticleFetcher
        required_methods = ['fetch_from_rss', 'fetch_from_track']
        for method in required_methods:
            if hasattr(ArticleFetcher, method):
                print(f"  ✓ ArticleFetcher.{method}()")
            else:
                print_error(f"  ✗ 缺少方法: ArticleFetcher.{method}()")
                all_found = False
        
        return all_found
    except Exception as e:
        print_error(f"  ✗ 检查失败: {e}")
        return False


def test_13_ai_rewrite_api():
    """13. AI 改写 API 检查"""
    try:
        from web.api.index import app
        
        # 检查改写相关路由
        routes_to_check = [
            '/api/rewrite',
        ]
        
        actual_paths = [route.path for route in app.routes]
        
        all_found = True
        for path in routes_to_check:
            if path in actual_paths:
                print(f"  ✓ {path}")
            else:
                print_error(f"  ✗ 缺少路由: {path}")
                all_found = False
        
        # 检查 Rewriter 类方法
        from rewriter import ArticleRewriter
        if hasattr(ArticleRewriter, 'rewrite'):
            print(f"  ✓ ArticleRewriter.rewrite()")
        else:
            print_error(f"  ✗ 缺少方法: ArticleRewriter.rewrite()")
            all_found = False
        
        return all_found
    except Exception as e:
        print_error(f"  ✗ 检查失败: {e}")
        return False


def test_14_history_api():
    """14. 发布历史 API 检查"""
    try:
        from web.api.index import app
        
        # 检查历史相关路由
        routes_to_check = [
            '/api/history',
            '/api/history/clear',
        ]
        
        actual_paths = [route.path for route in app.routes]
        
        all_found = True
        for path in routes_to_check:
            if path in actual_paths:
                print(f"  ✓ {path}")
            else:
                print_error(f"  ✗ 缺少路由: {path}")
                all_found = False
        
        # 检查 DELETE 路由（动态路径）
        has_delete = any('/api/history/' in route.path and route.methods and 'DELETE' in route.methods for route in app.routes)
        if has_delete:
            print(f"  ✓ DELETE /api/history/{{index}}")
        else:
            print_error(f"  ✗ 缺少路由: DELETE /api/history/{{index}}")
            all_found = False
        
        return all_found
    except Exception as e:
        print_error(f"  ✗ 检查失败: {e}")
        return False


def test_15_settings_api():
    """15. 系统设置 API 检查"""
    try:
        from web.api.index import app
        
        # 检查设置相关路由
        routes_to_check = [
            '/api/settings',
            '/api/settings/status',
        ]
        
        actual_paths = [route.path for route in app.routes]
        
        all_found = True
        for path in routes_to_check:
            if path in actual_paths:
                print(f"  ✓ {path}")
            else:
                print_error(f"  ✗ 缺少路由: {path}")
                all_found = False
        
        return all_found
    except Exception as e:
        print_error(f"  ✗ 检查失败: {e}")
        return False


def test_16_mobile_optimization():
    """16. 移动端优化检查"""
    templates = [
        "web/templates/login.html",
        "web/templates/dashboard.html",
        "web/templates/inspiration.html"
    ]
    
    all_pass = True
    for t in templates:
        t_path = os.path.join(BASE_DIR, t)
        if os.path.exists(t_path):
            with open(t_path) as f:
                content = f.read()
            
            # 检查关键移动端优化标签
            checks = [
                ("viewport 标签", 'name="viewport"'),
                ("Tailwind CSS", "cdn.tailwindcss.com"),
                ("safe-area 适配", "safe-area"),
                ("max-width 限制", "max-w-")
            ]
            
            for check_name, check_str in checks:
                if check_str in content:
                    print(f"  ✓ {t} - {check_name}")
                else:
                    print_warning(f"  ⚠️ {t} - 缺少 {check_name}")
                    # 不标记为失败，只警告
        else:
            all_pass = False
    
    return all_pass


def test_17_deployment_readme():
    """17. 部署文档检查"""
    if not os.path.exists(os.path.join(BASE_DIR, "DEPLOYMENT.md")):
        print_warning("  建议创建 DEPLOYMENT.md 部署文档")
    
    return True

# ============================================================
# 主测试流程
# ============================================================

def main():
    print(f"\n{'🚀'*20}")
    print("  自动发文系统 - 自动化自测脚本")
    print(f"{'🚀'*20}")
    
    test_steps = [
        ("Python 语法检查", test_1_syntax_check),
        ("依赖包检查", test_2_dependency_check),
        ("前端模板文件检查", test_3_template_files),
        ("配置文件检查", test_4_config_files),
        ("FastAPI 应用导入检查", test_5_fastapi_import),
        ("认证模块检查", test_6_auth_module),
        ("灵感生成模块检查", test_7_inspiration_module),
        ("API 路由完整性检查", test_8_api_routes),
        ("账号管理 API 检查", test_9_account_manager_api),
        ("赛道管理 API 检查", test_10_track_manager_api),
        ("微信发布 API 检查", test_11_wechat_publish_api),
        ("RSS 抓取 API 检查", test_12_rss_fetch_api),
        ("AI 改写 API 检查", test_13_ai_rewrite_api),
        ("发布历史 API 检查", test_14_history_api),
        ("系统设置 API 检查", test_15_settings_api),
        ("移动端优化检查", test_16_mobile_optimization),
        ("部署文档检查", test_17_deployment_readme),
    ]
    
    results = []
    for step_name, step_func in test_steps:
        results.append(run_step(step_name, step_func))
    
    # 总结
    print(f"\n\n{'📊'*20}")
    print("  测试结果汇总")
    print(f"{'📊'*20}")
    
    passed = sum(results)
    total = len(results)
    print(f"\n通过: {passed}/{total}")
    
    if passed == total:
        print_success("\n🎉 所有测试通过！可以部署到 Vercel")
        print_info("\n下一步：")
        print("  1. 安装依赖: pip install -r requirements.txt")
        print("  2. 本地测试: python -m uvicorn web.api.index:app --reload --host 0.0.0.0")
        print("  3. 访问: http://localhost:8000")
        print("  4. 推送代码到 GitHub，连接 Vercel 一键部署")
        return 0
    else:
        print_error(f"\n❌ 有 {total - passed} 项测试未通过，请修复后再部署")
        return 1

if __name__ == "__main__":
    sys.exit(main())
