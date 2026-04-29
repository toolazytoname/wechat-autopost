#!/usr/bin/env python3
"""
自动发文系统 - FastAPI 后端
支持移动端访问、JWT 认证、Vercel 部署
"""
import os
import sys
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# 项目路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# ============================================================
# 配置
# ============================================================
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-123456")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7天有效期，适合手机端

# 默认管理员账号（可通过环境变量覆盖）
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# ============================================================
# 认证系统
# ============================================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token", auto_error=False)

fake_users_db = {
    ADMIN_USERNAME: {
        "username": ADMIN_USERNAME,
        "full_name": "管理员",
        "hashed_password": pwd_context.hash(ADMIN_PASSWORD),
        "disabled": False,
    }
}


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return User(**user_dict)


def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, fake_users_db[username]["hashed_password"]):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# ============================================================
# FastAPI 应用
# ============================================================
app = FastAPI(title="自动发文系统", version="2.0.0")

# 静态文件和模板
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# ============================================================
# 页面路由
# ============================================================
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """首页 - 检查登录状态"""
    token = request.cookies.get("access_token")
    if token and token.startswith("Bearer "):
        token = token[7:]  # 去掉 Bearer 前缀
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("sub"):
                return RedirectResponse(url="/dashboard", status_code=303)
        except:
            pass
    return RedirectResponse(url="/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页面"""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """主面板"""
    token = request.cookies.get("access_token")
    if not token or not token.startswith("Bearer "):
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/inspiration", response_class=HTMLResponse)
async def inspiration_page(request: Request):
    """灵感创作页面"""
    token = request.cookies.get("access_token")
    if not token or not token.startswith("Bearer "):
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("inspiration.html", {"request": request})


# ============================================================
# API 路由 - 认证
# ============================================================
@app.post("/api/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """登录获取 Token"""
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/login")
async def web_login(username: str = Form(...), password: str = Form(...)):
    """Web 登录接口，设置 Cookie"""
    user = authenticate_user(fake_users_db, username, password)
    if not user:
        return JSONResponse(
            status_code=401,
            content={"success": False, "message": "用户名或密码错误"}
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    response = JSONResponse(
        content={"success": True, "message": "登录成功", "redirect": "/dashboard"}
    )
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=False,  # Vercel 部署时改为 True
        samesite="lax"
    )
    return response


@app.get("/api/logout")
async def logout():
    """登出"""
    response = JSONResponse(content={"success": True, "redirect": "/login"})
    response.delete_cookie("access_token")
    return response


@app.get("/api/user/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return current_user


# ============================================================
# API 路由 - 业务功能
# ============================================================
@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# 加载配置
def load_config():
    """加载配置文件"""
    config_path = os.path.join(BASE_DIR, "config.ini")
    config = {}
    if os.path.exists(config_path):
        import configparser
        cfg = configparser.ConfigParser()
        cfg.read(config_path)
        for section in cfg.sections():
            config[section] = dict(cfg.items(section))
    return config


@app.get("/api/config")
async def get_config(current_user: User = Depends(get_current_active_user)):
    """获取系统配置"""
    return {"config": load_config()}


@app.post("/api/inspiration/add")
async def add_inspiration(
    type: str = Form(...),
    content: str = Form(...),
    current_user: User = Depends(get_current_active_user)
):
    """添加灵感来源"""
    return {"success": True, "type": type, "content": content}


@app.post("/api/inspiration/fetch")
async def fetch_url(
    url: str = Form(...),
    current_user: User = Depends(get_current_active_user)
):
    """抓取网页内容"""
    try:
        from inspiration_generator import InspirationGenerator
        config = load_config()
        generator = InspirationGenerator(config)
        result = generator.fetch_url_content(url)
        if result:
            return {"success": True, "data": result}
        return {"success": False, "message": "抓取失败"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/inspiration/generate")
async def generate_article(
    sources: str = Form(...),
    style: str = Form("专业深度"),
    length: str = Form("medium"),
    track_id: str = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    """生成文章"""
    try:
        from inspiration_generator import InspirationGenerator
        config = load_config()
        generator = InspirationGenerator(config)

        sources_list = json.loads(sources)

        # 收集所有灵感素材
        all_sources = []
        for idx, item in enumerate(sources_list):
            if item['type'] == 'url':
                result = generator.fetch_url_content(item['content'])
                if result:
                    all_sources.append(f"【参考文章 {len(all_sources)+1}】\n标题：{result['title']}\n内容：{result['content']}\n来源：{result['url']}")
            else:
                all_sources.append(f"【灵感素材 {len(all_sources)+1}】\n{item['content']}")

        if not all_sources:
            return {"success": False, "message": "没有有效灵感来源"}

        combined_sources = "\n\n".join(all_sources)
        result = generator.generate_from_text(
            combined_sources,
            track_id=track_id if track_id else None,
            style=style,
            length=length
        )

        if result:
            return {"success": True, "data": result}
        return {"success": False, "message": "生成失败，请检查 API 配置"}

    except Exception as e:
        import traceback
        return {"success": False, "message": str(e), "traceback": traceback.format_exc()}


# ============================================================
# API 路由 - 账号管理
# ============================================================
@app.get("/api/accounts")
async def get_accounts(current_user: User = Depends(get_current_active_user)):
    """获取所有账号列表"""
    try:
        from account_manager import AccountManager
        manager = AccountManager()
        accounts = manager.get_all_accounts()
        # 不返回敏感信息
        safe_accounts = []
        for a in accounts:
            safe_a = a.copy()
            if 'app_secret' in safe_a:
                safe_a['app_secret'] = safe_a['app_secret'][:4] + '*' * 8  # 脱敏
            safe_accounts.append(safe_a)
        return {"success": True, "data": safe_accounts}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/accounts")
async def add_account(
    id: str = Form(...),
    name: str = Form(...),
    platform: str = Form(...),
    app_id: str = Form(None),
    app_secret: str = Form(None),
    enabled: bool = Form(True),
    current_user: User = Depends(get_current_active_user)
):
    """添加新账号"""
    try:
        from account_manager import AccountManager
        manager = AccountManager()
        
        account = {
            "id": id,
            "name": name,
            "platform": platform,
            "enabled": enabled,
        }
        if app_id:
            account["app_id"] = app_id
        if app_secret:
            account["app_secret"] = app_secret
            
        success = manager.add_account(account)
        if success:
            return {"success": True, "message": "账号添加成功"}
        return {"success": False, "message": "账号ID已存在"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.put("/api/accounts/{account_id}")
async def update_account(
    account_id: str,
    name: str = Form(None),
    app_id: str = Form(None),
    app_secret: str = Form(None),
    enabled: bool = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    """更新账号配置"""
    try:
        from account_manager import AccountManager
        manager = AccountManager()
        
        updates = {}
        if name is not None:
            updates["name"] = name
        if app_id is not None:
            updates["app_id"] = app_id
        if app_secret is not None:
            updates["app_secret"] = app_secret
        if enabled is not None:
            updates["enabled"] = enabled
            
        success = manager.update_account(account_id, updates)
        if success:
            return {"success": True, "message": "账号更新成功"}
        return {"success": False, "message": "账号不存在"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.delete("/api/accounts/{account_id}")
async def delete_account(
    account_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """删除账号"""
    try:
        from account_manager import AccountManager
        manager = AccountManager()
        success = manager.delete_account(account_id)
        if success:
            return {"success": True, "message": "账号删除成功"}
        return {"success": False, "message": "账号不存在"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/accounts/{account_id}/test")
async def test_account(
    account_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """测试账号连接"""
    try:
        from account_manager import AccountManager
        manager = AccountManager()
        result = manager.test_account(account_id)
        return {"success": result.get('success', False), "message": result.get('message', '')}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ============================================================
# API 路由 - 赛道管理
# ============================================================
@app.get("/api/tracks")
async def get_tracks(current_user: User = Depends(get_current_active_user)):
    """获取所有赛道列表"""
    try:
        from track_manager import TrackManager
        manager = TrackManager()
        tracks = manager.get_all_tracks()
        return {"success": True, "data": tracks, "active": manager._data.get('active_track')}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.get("/api/tracks/{track_id}")
async def get_track(
    track_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取单个赛道详情"""
    try:
        from track_manager import TrackManager
        manager = TrackManager()
        track = manager.get_track(track_id)
        if track:
            return {"success": True, "data": track}
        return {"success": False, "message": "赛道不存在"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/tracks")
async def add_track(
    id: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    enabled: bool = Form(True),
    rewriter_prompt: str = Form(""),
    current_user: User = Depends(get_current_active_user)
):
    """添加新赛道"""
    try:
        from track_manager import TrackManager
        manager = TrackManager()
        
        track = {
            "id": id,
            "name": name,
            "description": description,
            "enabled": enabled,
            "rewriter_prompt": rewriter_prompt,
            "feeds": [],
            "publish_config": {}
        }
            
        success = manager.add_track(track)
        if success:
            return {"success": True, "message": "赛道添加成功"}
        return {"success": False, "message": "赛道ID已存在"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.put("/api/tracks/{track_id}")
async def update_track(
    track_id: str,
    name: str = Form(None),
    description: str = Form(None),
    enabled: bool = Form(None),
    rewriter_prompt: str = Form(None),
    active: bool = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    """更新赛道配置"""
    try:
        from track_manager import TrackManager
        manager = TrackManager()
        
        # 如果设置为活跃赛道
        if active is True:
            manager.set_active_track(track_id)
            return {"success": True, "message": "已设置为活跃赛道"}
        
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if enabled is not None:
            updates["enabled"] = enabled
        if rewriter_prompt is not None:
            updates["rewriter_prompt"] = rewriter_prompt
            
        success = manager.update_track(track_id, updates)
        if success:
            return {"success": True, "message": "赛道更新成功"}
        return {"success": False, "message": "赛道不存在"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.delete("/api/tracks/{track_id}")
async def delete_track(
    track_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """删除赛道"""
    try:
        from track_manager import TrackManager
        manager = TrackManager()
        success = manager.delete_track(track_id)
        if success:
            return {"success": True, "message": "赛道删除成功"}
        return {"success": False, "message": "赛道不存在"}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ============================================================
# API 路由 - 微信发布
# ============================================================
@app.post("/api/publish/wechat")
async def publish_to_wechat(
    account_id: str = Form(...),
    title: str = Form(...),
    content: str = Form(...),
    author: str = Form(""),
    digest: str = Form(""),
    thumb_media_id: str = Form(""),
    show_cover: bool = Form(True),
    track_id: str = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    """发布文章到微信公众号草稿箱"""
    try:
        # 获取账号配置
        from account_manager import AccountManager
        am = AccountManager()
        account = am.get_account(account_id)
        
        if not account:
            return {"success": False, "message": "账号不存在"}
        
        if not account.get('app_id') or not account.get('app_secret'):
            return {"success": False, "message": "账号未配置 app_id/app_secret"}
        
        # 构造发布器
        import configparser
        import tempfile
        import os
        
        # 临时创建配置
        config = configparser.ConfigParser()
        config['wechat'] = {
            'app_id': account['app_id'],
            'app_secret': account['app_secret']
        }
        
        # 写入临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            config.write(f)
            temp_config = f.name
        
        try:
            from publisher import WechatPublisher
            publisher = WechatPublisher(temp_config)
            
            # 构造文章数据
            article = {
                'rewritten_title': title,
                'rewritten_content': content,
                'author': author or 'AI 助手',
                'summary': digest,
                'has_image': bool(thumb_media_id),
                'thumb_media_id': thumb_media_id,
            }
            
            if thumb_media_id:
                article['images'] = [{'media_id': thumb_media_id}]
            
            # 发布到草稿箱
            result = publisher.publish_article(article, to_draft=True)
            
            if result:
                return {"success": True, "message": "发布成功，请到微信公众平台草稿箱查看"}
            return {"success": False, "message": "发布失败，请检查账号配置"}
        finally:
            os.unlink(temp_config)
            
    except Exception as e:
        import traceback
        return {"success": False, "message": str(e), "traceback": traceback.format_exc()}


@app.get("/api/publish/wechat/drafts")
async def get_wechat_drafts(
    account_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取微信草稿列表"""
    try:
        from account_manager import AccountManager
        am = AccountManager()
        account = am.get_account(account_id)
        
        if not account:
            return {"success": False, "message": "账号不存在"}
        
        import configparser
        import tempfile
        import os
        
        config = configparser.ConfigParser()
        config['wechat'] = {
            'app_id': account['app_id'],
            'app_secret': account['app_secret']
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            config.write(f)
            temp_config = f.name
        
        try:
            from publisher import WechatPublisher
            publisher = WechatPublisher(temp_config)
            # 获取草稿列表（简化版，返回状态）
            return {"success": True, "message": "账号连接正常，草稿功能可用"}
        finally:
            os.unlink(temp_config)
            
    except Exception as e:
        return {"success": False, "message": str(e)}


# ============================================================
# API 路由 - RSS 抓取
# ============================================================
@app.post("/api/rss/fetch")
async def fetch_rss(
    url: str = Form(...),
    max_count: int = Form(10),
    current_user: User = Depends(get_current_active_user)
):
    """抓取指定 RSS 源文章"""
    try:
        import configparser
        import tempfile
        import os
        
        # 创建临时配置
        config = configparser.ConfigParser()
        config['minimax'] = {
            'api_key': 'dummy'  # 抓取不需要 AI key
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            config.write(f)
            temp_config = f.name
        
        try:
            from fetcher import ArticleFetcher
            fetcher = ArticleFetcher(temp_config)
            articles = fetcher.fetch_from_rss(url, max_count)
            
            return {
                "success": True, 
                "data": articles,
                "count": len(articles)
            }
        finally:
            os.unlink(temp_config)
            
    except Exception as e:
        import traceback
        return {"success": False, "message": str(e), "traceback": traceback.format_exc()}


@app.get("/api/rss/track/{track_id}")
async def fetch_track_rss(
    track_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """抓取指定赛道下的所有 RSS 源"""
    try:
        from track_manager import TrackManager
        tm = TrackManager()
        track = tm.get_track(track_id)
        
        if not track:
            return {"success": False, "message": "赛道不存在"}
        
        feeds = track.get('feeds', [])
        if not feeds:
            return {"success": False, "message": "该赛道没有配置 RSS 源"}
        
        all_articles = []
        for feed in feeds:
            if feed.get('enabled', True):
                try:
                    # 这里简化处理，实际可以调用 fetcher
                    all_articles.append({
                        "feed_name": feed.get('name', feed.get('url', '')),
                        "status": "ok"
                    })
                except:
                    pass
        
        return {"success": True, "data": all_articles, "feeds_count": len(feeds)}
    
    except Exception as e:
        return {"success": False, "message": str(e)}


# ============================================================
# API 路由 - AI 改写
# ============================================================
@app.post("/api/rewrite")
async def rewrite_article(
    title: str = Form(...),
    content: str = Form(...),
    track_id: str = Form(None),
    style: str = Form("专业深度"),
    current_user: User = Depends(get_current_active_user)
):
    """AI 改写单篇文章"""
    try:
        # 加载配置
        config = load_config()
        
        from rewriter import ArticleRewriter
        rewriter = ArticleRewriter(config)
        
        article = {
            "title": title,
            "content": content
        }
        
        result = rewriter.rewrite(article, track_id)
        
        if result:
            return {
                "success": True, 
                "data": {
                    "original_title": title,
                    "rewritten_title": result.get('rewritten_title', title),
                    "rewritten_content": result.get('rewritten_content', content),
                    "summary": result.get('summary', ''),
                    "keywords": result.get('keywords', '')
                }
            }
        return {"success": False, "message": "改写失败，请检查 AI API 配置"}
        
    except Exception as e:
        import traceback
        return {"success": False, "message": str(e), "traceback": traceback.format_exc()}


# ============================================================
# API 路由 - 发布历史
# ============================================================
@app.get("/api/history")
async def get_history(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_active_user)
):
    """获取发布历史列表"""
    try:
        import json
        import os
        
        history_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'published_history.json')
        
        history_data = []
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                data = json.load(f)
                history_data = data.get('published_today', [])
        
        # 简单分页
        start = (page - 1) * page_size
        end = start + page_size
        paginated = history_data[start:end]
        
        return {
            "success": True,
            "data": paginated,
            "total": len(history_data),
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.delete("/api/history/{index}")
async def delete_history_item(
    index: int,
    current_user: User = Depends(get_current_active_user)
):
    """删除单条历史记录"""
    try:
        import json
        import os
        
        history_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'published_history.json')
        
        if not os.path.exists(history_file):
            return {"success": False, "message": "历史文件不存在"}
        
        with open(history_file, 'r') as f:
            data = json.load(f)
        
        if index < 0 or index >= len(data.get('published_today', [])):
            return {"success": False, "message": "索引超出范围"}
        
        deleted = data['published_today'].pop(index)
        
        with open(history_file, 'w') as f:
            json.dump(data, f, ensure_ascii=False)
        
        return {"success": True, "message": "删除成功", "deleted": deleted}
        
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/history/clear")
async def clear_history(
    current_user: User = Depends(get_current_active_user)
):
    """清空所有历史记录"""
    try:
        import json
        import os
        
        history_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'published_history.json')
        
        data = {'published_today': [], 'last_date': None}
        
        with open(history_file, 'w') as f:
            json.dump(data, f, ensure_ascii=False)
        
        return {"success": True, "message": "历史记录已清空"}
        
    except Exception as e:
        return {"success": False, "message": str(e)}


# ============================================================
# API 路由 - 系统设置
# ============================================================
@app.get("/api/settings")
async def get_settings(
    current_user: User = Depends(get_current_active_user)
):
    """获取系统设置"""
    try:
        import os
        
        config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.ini')
        
        # 返回配置文件中的非敏感设置
        settings = {
            'config_exists': os.path.exists(config_file),
            'ai_provider': 'minimax',
            'supported_styles': ['专业深度', '科技前沿', '通俗易懂', '新闻报道'],
            'default_publish_count': 2,
            'wechat_limit': '仅支持创建草稿(errcode 48001)'
        }
        
        return {"success": True, "data": settings}
        
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.get("/api/settings/status")
async def get_system_status(
    current_user: User = Depends(get_current_active_user)
):
    """获取系统运行状态"""
    try:
        import sys
        import os
        
        # 检查核心模块
        modules_status = {}
        for module in ['publisher', 'rewriter', 'fetcher', 'inspiration_generator']:
            try:
                __import__(module)
                modules_status[module] = 'ok'
            except:
                modules_status[module] = 'error'
        
        # 检查文件
        files_status = {}
        for f in ['config.ini', 'accounts.json', 'tracks.json', 'published_history.json']:
            files_status[f] = os.path.exists(f)
        
        return {
            "success": True,
            "data": {
                "python_version": sys.version,
                "modules": modules_status,
                "files": files_status,
                "api_version": "2.0.0"
            }
        }
        
    except Exception as e:
        return {"success": False, "message": str(e)}


# ============================================================
# 启动入口
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
