#!/usr/bin/env python3
"""
微信公众号发布器 - 使用官方API发布文章
"""

import requests
import json
import os
from typing import Dict, Optional, List
from datetime import datetime

class WeChatPublisher:
    def __init__(self, config: dict):
        self.config = config
        self.wechat_config = config.get('wechat', {})
        
        self.app_id = self.wechat_config.get('app_id', '')
        self.app_secret = self.wechat_config.get('app_secret', '')
        
        self.access_token = None
        self.token_expires_at = 0
    
    def _markdown_to_html(self, text: str) -> str:
        """将简单的Markdown转换为HTML"""
        import re
        html = text
        
        # 标题处理
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        
        # 粗体 **text** -> <strong>text</strong>
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        
        # 斜体 *text* -> <em>text</em>
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        
        # 行分割 -> <br>
        html = re.sub(r'\n', '<br>', html)
        
        return html
    
    def get_access_token(self) -> Optional[str]:
        """获取access_token"""
        # 检查是否还有效
        if self.access_token and datetime.now().timestamp() < self.token_expires_at:
            return self.access_token
        
        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self.app_id}&secret={self.app_secret}"
        
        try:
            resp = requests.get(url, timeout=10)
            result = resp.json()
            
            if 'access_token' in result:
                self.access_token = result['access_token']
                # 提前5分钟过期
                self.token_expires_at = datetime.now().timestamp() + result.get('expires_in', 7200) - 300
                print(f"[Publisher] Access token获取成功")
                return self.access_token
            else:
                print(f"[Publisher] Access token获取失败: {result}")
                return None
        except Exception as e:
            print(f"[Publisher] Access token请求失败: {e}")
            return None
    
    def add_draft(self, articles: List[Dict]) -> Optional[str]:
        """
        添加草稿（支持多篇文章）
        
        Args:
            articles: 文章列表，每篇包含 thumb_media_id, title, author, content, digest, etc.
        
        Returns:
            media_id: 草稿的media_id
        """
        access_token = self.get_access_token()
        if not access_token:
            return None
        
        url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}"
        
        # 构建草稿内容
        articles_data = []
        for article in articles:
            articles_data.append({
                "title": article.get('title', '无标题'),
                "digest": article.get('digest', article.get('title', ''))[:50],
                "content": article.get('content', ''),
                "content_source_url": article.get('url', ''),
                "thumb_media_id": article.get('thumb_media_id', ''),
                "need_open_comment": 1,
                "only_fans_can_comment": 0
            })
        
        payload = {
            "articles": articles_data
        }
        
        try:
            # 手动 JSON 编码，使用 ensure_ascii=False 保留中文
            json_data = json.dumps(payload, ensure_ascii=False)
            resp = requests.post(
                url, 
                data=json_data.encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            result = resp.json()
            
            if result.get('media_id'):
                print(f"[Publisher] 草稿创建成功，media_id: {result['media_id']}")
                return result['media_id']
            else:
                print(f"[Publisher] 草稿创建失败: {result}")
                return None
        except Exception as e:
            print(f"[Publisher] 草稿创建请求失败: {e}")
            return None
    
    def publish_draft(self, media_id: str) -> bool:
        """
        发布草稿（提交发布）
        
        注意：此接口只能发布已存在的草稿，
        个人订阅号通常无法通过API自动发布（需要管理员确认）
        """
        access_token = self.get_access_token()
        if not access_token:
            return False
        
        # 尝试发布到已发布列表
        url = f"https://api.weixin.qq.com/cgi-bin/freepublish/submit?access_token={access_token}"
        
        payload = {
            "media_id": media_id
        }
        
        try:
            json_data = json.dumps(payload, ensure_ascii=False)
            resp = requests.post(
                url,
                data=json_data.encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            result = resp.json()
            
            if result.get('errcode') == 0:
                print(f"[Publisher] 草稿发布成功!")
                return True
            else:
                print(f"[Publisher] 草稿发布结果: {result}")
                # 常见错误：errmsg: "api unauthorized" 表示没有权限
                # 个人订阅号通常没有发布权限
                return False
        except Exception as e:
            print(f"[Publisher] 发布请求失败: {e}")
            return False
    
    def upload_thumb_image(self, image_url: str = None) -> Optional[str]:
        """
        上传封面图片获取 thumb_media_id
        使用永久素材接口，避免临时素材过期问题
        
        Args:
            image_url: 可选，封面图片URL。如果不提供则使用默认灰色图
        """
        access_token = self.get_access_token()
        if not access_token:
            return None
        
        import tempfile
        import requests
        import os
        
        temp_path = None
        try:
            # 如果提供了图片URL，下载它
            if image_url:
                print(f"[Publisher] 下载封面图: {image_url}")
                img_resp = requests.get(image_url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }, timeout=15)
                if img_resp.status_code == 200 and len(img_resp.content) > 100:
                    temp_path = tempfile.mktemp(suffix='.jpg')
                    with open(temp_path, 'wb') as f:
                        f.write(img_resp.content)
                    print(f"[Publisher] 封面图下载成功，大小: {len(img_resp.content)} bytes")
                else:
                    print(f"[Publisher] 封面图下载失败，使用默认图")
                    image_url = None
            
            # 如果没有有效的封面图，生成默认图
            if not image_url:
                png_data = self._create_default_thumb_image()
                temp_path = tempfile.mktemp(suffix='.png')
                with open(temp_path, 'wb') as f:
                    f.write(png_data)
                print(f"[Publisher] 使用默认灰色封面图")
            
            # 使用永久素材接口上传封面
            url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={access_token}&type=thumb"
            
            # 根据文件扩展名确定Content-Type
            import mimetypes
            ext = os.path.splitext(temp_path)[1].lower()
            mime_type = mimetypes.types_map.get(ext, 'image/png')
            
            with open(temp_path, 'rb') as f:
                files = {'media': (os.path.basename(temp_path), f, mime_type)}
                resp = requests.post(url, files=files, timeout=30)
            
            result = resp.json()
            if 'media_id' in result:
                print(f"[Publisher] 永久封面上传成功: {result['media_id']}")
                return result['media_id']
            else:
                print(f"[Publisher] 永久封面上传失败: {result}")
                # 尝试临时素材
                return self._upload_thumb_temp(access_token)
                
        except Exception as e:
            print(f"[Publisher] 封面上传出错: {e}")
            return None
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
    
    def _create_default_thumb_image(self) -> bytes:
        """创建一个简单的默认封面图"""
        import struct
        
        # 简单的 200x200 灰色 PNG
        width, height = 200, 200
        
        # PNG 文件头
        png_header = b'\x89PNG\r\n\x1a\n'
        
        # IHDR chunk
        ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
        ihdr_crc = self._crc32(b'IHDR' + ihdr_data)
        ihdr_chunk = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)
        
        # IDAT chunk (简单的灰色图像数据)
        import zlib
        raw_data = b''
        for y in range(height):
            raw_data += b'\x00'  # filter type
            for x in range(width):
                raw_data += b'\xCC' + b'\xCC' + b'\xCC'  # RGB 灰色
        
        compressed = zlib.compress(raw_data)
        idat_crc = self._crc32(b'IDAT' + compressed)
        idat_chunk = struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', idat_crc)
        
        # IEND chunk
        iend_crc = self._crc32(b'IEND')
        iend_chunk = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)
        
        return png_header + ihdr_chunk + idat_chunk + iend_chunk
    
    def _crc32(self, data: bytes) -> int:
        """计算CRC32"""
        import zlib
        return zlib.crc32(data) & 0xffffffff
    
    def _upload_thumb_temp(self, access_token: str) -> Optional[str]:
        """使用临时素材接口上传"""
        import tempfile
        import requests
        import os
        import zlib
        import struct
        
        # 创建默认图
        png_data = self._create_default_thumb_image()
        temp_path = tempfile.mktemp(suffix='.png')
        with open(temp_path, 'wb') as f:
            f.write(png_data)
        
        try:
            url = f"https://api.weixin.qq.com/cgi-bin/media/upload?access_token={access_token}&type=thumb"
            with open(temp_path, 'rb') as f:
                files = {'media': ('thumb.png', f, 'image/png')}
                resp = requests.post(url, files=files, timeout=30)
            
            result = resp.json()
            if 'thumb_media_id' in result:
                print(f"[Publisher] 临时封面上传成功: {result['thumb_media_id']}")
                return result['thumb_media_id']
            else:
                print(f"[Publisher] 临时封面上传失败: {result}")
                return None
        finally:
            os.unlink(temp_path)
    
    def publish_article(self, article: Dict) -> bool:
        """
        发布单篇文章（创建草稿并尝试发布）
        
        Args:
            article: 文章内容，包含 title, content, url 等
            article['cover_image']: 可选的封面图URL
            article['body_images']: 可选的正文图片URL列表
            
        Returns:
            是否发布成功
        """
        print(f"[Publisher] 准备发布文章: {article.get('rewritten_title', '无标题')}")
        
        # 上传封面图（优先使用文章原图）
        cover_url = article.get('cover_image')
        thumb_media_id = self.upload_thumb_image(cover_url) if cover_url else self.upload_thumb_image()
        
        # 构建文章数据
        # 将正文图片插入到内容中（如果有多张图片）
        content = article.get('rewritten_content', article.get('content', ''))
        body_images = article.get('body_images', [])

        # 如果没有正文图片，使用AI生成配图
        if not body_images:
            print("[Publisher] 正在AI生成配图...")
            body_images = self._generate_article_images(
                article.get('rewritten_title', ''),
                article.get('rewritten_content', '')
            )

        # 将外部图片URL上传到微信服务器（微信不支持外部图片）
        if body_images:
            body_images = self._upload_body_images_to_wechat(body_images)

        # 如果有正文图片，在合适的位置插入（先插图片，再转HTML）
        if body_images:
            content = self._insert_images_into_content(content, body_images)
            print(f"[Publisher] 已插入 {len(body_images)} 张配图")

        # 将Markdown转换为HTML（图片已在内容中，用换行分隔）
        content = self._markdown_to_html(content)
        
        article_data = {
            'title': article.get('rewritten_title', article.get('title', '无标题')),
            'digest': article.get('rewritten_title', article.get('title', ''))[:50],
            'content': content,
            'content_source_url': article.get('original_url', article.get('url', '')),
            'thumb_media_id': thumb_media_id or '',
            'need_open_comment': 1,
            'only_fans_can_comment': 0
        }
        
        # 创建草稿
        media_id = self.add_draft([article_data])
        if not media_id:
            print("[Publisher] 草稿创建失败，无法发布")
            return False
        
        # 尝试发布
        success = self.publish_draft(media_id)
        
        if success:
            print(f"[Publisher] ✅ 文章发布成功!")
        else:
            print(f"[Publisher] ⚠️ 草稿已创建但自动发布失败，请登录微信公众平台手动发布")
        
        return success
    
    def _insert_images_into_content(self, content: str, images: List[str]) -> str:
        """
        将图片均匀插入到正文内容中。
        按文本长度等分，每段末尾插入一张图片。
        """
        if not images or not content:
            return content

        # 按自然段落分割（保留空行）
        import re
        # 用至少一个换行+空白来识别段落分隔
        segments = re.split(r'(?<=\n)\s*\n', content)
        # 过滤空段落
        segments = [s for s in segments if s.strip()]
        total_segs = len(segments)

        if total_segs == 0:
            return content

        # 在段间均匀插入图片
        result = []
        img_idx = 0
        # 每个间隙平均分多少段
        gap = max(1, total_segs // (len(images) + 1))

        for i, seg in enumerate(segments):
            result.append(seg)
            # 在每 gap 个段落后插入一张图片
            if (i + 1) % gap == 0 and img_idx < len(images):
                result.append(f'\n<img src="{images[img_idx]}" />\n')
                img_idx += 1

        # 如果还有剩余图片没插完，追加到末尾
        while img_idx < len(images):
            result.append(f'\n<img src="{images[img_idx]}" />\n')
            img_idx += 1

        return '\n'.join(result)
    
    def _generate_article_images(self, title: str, content: str) -> List[str]:
        """
        根据文章内容使用AI生成配图
        
        Args:
            title: 文章标题
            content: 文章内容
            
        Returns:
            生成的图片URL列表
        """
        import subprocess
        import os
        import re
        
        # 根据标题和内容生成合适的图片描述
        prompt = self._create_image_prompt(title, content)
        
        if not prompt:
            print("[Publisher] 无法生成图片提示词")
            return []
        
        print(f"[Publisher] 生成图片提示词: {prompt[:50]}...")
        
        # 调用图片生成脚本
        script_path = '/root/.openclaw/workspace/skills/image-generate/scripts/image_generate.py'
        output_dir = '/root/.openclaw/workspace/wechat-autopost/generated_images'
        
        if not os.path.exists(script_path):
            print(f"[Publisher] 图片生成脚本不存在，跳过AI配图")
            return []
        
        try:
            os.makedirs(output_dir, exist_ok=True)
            # 运行图片生成脚本，设置下载目录
            env = os.environ.copy()
            env['IMAGE_DOWNLOAD_DIR'] = output_dir
            
            result = subprocess.run(
                ['python3', script_path, prompt],
                cwd='/root/.openclaw/workspace/skills/image-generate',
                capture_output=True,
                text=True,
                timeout=120,
                env=env
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                # 解析输出获取图片路径
                if 'Downloaded to:' in output:
                    img_path = output.split('Downloaded to:')[1].strip()
                    # 移动到我们的目录
                    new_name = os.path.join(output_dir, f'generated_{os.path.basename(img_path)}')
                    import shutil
                    shutil.copy(img_path, new_name)
                    
                    # 上传到微信获取永久URL
                    img_url = self._upload_image_to_wechat(new_name)
                    if img_url:
                        print(f"[Publisher] AI配图生成成功: {img_url}")
                        return [img_url]
            else:
                print(f"[Publisher] 图片生成失败: {result.stderr}")
        except Exception as e:
            print(f"[Publisher] 图片生成异常: {e}")
        
        return []
    
    def _create_image_prompt(self, title: str, content: str) -> str:
        """
        根据文章内容创建图片生成提示词
        """
        # 提取前200字作为上下文
        context = (title + ' ' + content)[:300]
        
        # 使用AI分析并生成提示词
        import requests
        import json
        
        api_key = self.config.get('ai', {}).get('api_key', '')
        api_base = self.config.get('ai', {}).get('api_base', 'https://ark.cn-beijing.volces.com/api/coding/v3')
        model = self.config.get('ai', {}).get('model', 'MiniMax-M2.7')
        
        if not api_key:
            return None
        
        try:
            response = requests.post(
                f"{api_base}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "你是一个图片描述专家。根据文章内容，生成一个适合的图片描述prompt，用于AI画图。这个描述应该是简洁、具体、适合作为文章配图的画面。用英文描述。"},
                        {"role": "user", "content": f"文章标题：{title}\n文章内容：{context}\n\n请生成一个适合这篇文章的配图描述（英文，50字以内）："}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 200
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                prompt = result['choices'][0]['message']['content'].strip()
                # 移除引号
                prompt = prompt.strip('"\'')
                return prompt
        except Exception as e:
            print(f"[Publisher] 生成提示词失败: {e}")
        
        return None
    
    def _convert_image_to_jpeg(self, src_path: str, dst_path: str) -> bool:
        """将图片转换为 JPEG 格式"""
        try:
            from PIL import Image
            with Image.open(src_path) as img:
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(dst_path, 'JPEG', quality=85)
            return True
        except ImportError:
            pass
        try:
            import imageio
            img = imageio.imread(src_path)
            imageio.imwrite(dst_path, img)
            return True
        except ImportError:
            pass
        return False

    def _upload_body_images_to_wechat(self, image_urls: List[str]) -> List[str]:
        """
        将外部图片URL列表下载并上传到微信服务器
        
        Args:
            image_urls: 外部图片URL列表
            
        Returns:
            微信服务器上的图片URL列表（可用于正文内容）
        """
        import tempfile
        
        wechat_urls = []
        access_token = self.get_access_token()
        if not access_token:
            print(f"[Publisher] 无法获取access_token，正文图片将使用原始URL")
            return image_urls
        
        for url in image_urls:
            try:
                print(f"[Publisher] 上传正文图片: {url[:60]}...")
                img_resp = requests.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }, timeout=15)
                
                if img_resp.status_code != 200 or len(img_resp.content) < 1000:
                    print(f"[Publisher] 图片下载失败({img_resp.status_code})，跳过: {url[:50]}")
                    continue
                
                # 写入临时文件
                ext = '.jpg'
                content_type = img_resp.headers.get('Content-Type', '')
                if 'webp' in content_type:
                    ext = '.webp'
                elif 'avif' in content_type:
                    ext = '.avif'
                elif 'png' in content_type:
                    ext = '.png'
                elif 'gif' in content_type:
                    ext = '.gif'
                
                # 微信 media/uploadimg 只支持 jpeg/png/gif/bmp，avif/webp需转换
                needs_convert = ext in ('.avif', '.webp')
                temp_path = tempfile.mktemp(suffix=ext)
                with open(temp_path, 'wb') as f:
                    f.write(img_resp.content)
                
                # avif/webp 转 jpeg（微信不支持）
                if needs_convert:
                    converted = tempfile.mktemp(suffix='.jpg')
                    if self._convert_image_to_jpeg(temp_path, converted):
                        os.unlink(temp_path)
                        temp_path = converted
                        ext = '.jpg'
                    else:
                        os.unlink(temp_path)
                        print(f"[Publisher] 图片格式不支持且无法转换，跳过: {url[:50]}")
                        continue
                
                # 上传到微信（使用永久素材接口）
                upload_url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={access_token}"
                with open(temp_path, 'rb') as f:
                    mime = 'image/jpeg' if ext == '.jpg' else f'image/{ext[1:]}'
                    files = {'media': (f'image{ext}', f, mime)}
                    resp = requests.post(upload_url, files=files, timeout=30)
                
                result = resp.json()
                if 'url' in result:
                    wechat_urls.append(result['url'])
                    print(f"[Publisher] 正文图片上传成功: {result['url'][:50]}")
                else:
                    print(f"[Publisher] 正文图片上传失败: {result}")
                
                os.unlink(temp_path)
                
            except Exception as e:
                print(f"[Publisher] 正文图片处理异常: {e}")
        
        if not wechat_urls and image_urls:
            print(f"[Publisher] 所有正文图片上传失败，使用原始URL")
            return image_urls
        
        print(f"[Publisher] 成功上传 {len(wechat_urls)}/{len(image_urls)} 张正文图片")
        return wechat_urls

    def _upload_image_to_wechat(self, local_path: str) -> Optional[str]:
        """
        上传本地图片到微信获取永久URL
        
        Returns:
            微信服务器上的图片URL
        """
        import requests
        import os
        
        access_token = self.get_access_token()
        if not access_token:
            return None
        
        try:
            url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={access_token}"
            
            with open(local_path, 'rb') as f:
                files = {'media': (os.path.basename(local_path), f, 'image/png')}
                resp = requests.post(url, files=files, timeout=30)
            
            result = resp.json()
            if 'url' in result:
                return result['url']
            else:
                print(f"[Publisher] 微信图片上传失败: {result}")
        except Exception as e:
            print(f"[Publisher] 微信图片上传异常: {e}")
        
        return None

if __name__ == '__main__':
    # 测试
    import configparser
    cfg = configparser.ConfigParser()
    cfg.read('config.ini')
    config = {s: dict(cfg.items(s)) for s in cfg.sections()}
    
    publisher = WeChatPublisher(config)
    
    # 测试获取token
    token = publisher.get_access_token()
    if token:
        print(f"Token获取成功: {token[:20]}...")
    else:
        print("Token获取失败")
