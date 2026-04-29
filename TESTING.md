# 📋 自测流程文档

## 概述

本文档固化了「自动发文系统」的完整测试流程，确保每次发布前的质量验证。

## 测试流程

### 第一阶段：自动化测试（必跑）

```bash
# 运行完整自动化测试
python3 self_test.py
```

**自动化测试覆盖以下 10 项：**

| 测试项 | 说明 | 验收标准 |
|--------|------|---------|
| 1. Python 语法检查 | 所有核心模块语法检查 | 全部通过 |
| 2. 依赖包检查 | FastAPI 等依赖是否安装 | 全部安装 |
| 3. 前端模板文件 | 登录页/面板/灵感页 HTML 存在 | 全部存在且非空 |
| 4. 配置文件 | vercel.json / requirements.txt 存在 | 格式正确 |
| 5. FastAPI 导入 | 应用能否正常启动 | 导入成功，路由完整 |
| 6. 认证模块 | JWT Token 生成/验证 | 密码验证、Token 生成正常 |
| 7. 灵感生成模块 | InspirationGenerator 核心方法 | 类能实例化，方法存在 |
| 8. API 路由完整性 | 所有预期路由存在 | 关键路由无缺失 |
| 9. 移动端优化 | viewport/Tailwind/safe-area | 核心优化标签存在 |
| 10. 部署文档 | 部署说明文档 | 建议完整 |

---

### 第二阶段：手动功能测试（必跑）

#### 2.1 本地启动测试

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python -m uvicorn web.api.index:app --reload --host 0.0.0.0 --port 8000
```

**验收标准：**
- ✅ 服务正常启动，无报错
- ✅ 访问 `http://localhost:8000` 自动跳转到登录页

#### 2.2 登录流程测试

| 步骤 | 操作 | 预期结果 |
|------|------|---------|
| 1 | 访问登录页 | 显示登录表单，默认账号已填充 |
| 2 | 输入错误密码 | 显示红色 Toast 提示 |
| 3 | 输入正确账号密码 (admin/admin123) | 登录成功，跳转到主面板 |
| 4 | 刷新页面 | 保持登录状态 |
| 5 | 点击右上角退出 | 回到登录页 |

#### 2.3 灵感创作测试

| 步骤 | 操作 | 预期结果 |
|------|------|---------|
| 1 | 点击「💡 灵感创作」卡片 | 进入灵感创作页面 |
| 2 | 切换链接/文字输入方式 | UI 正确切换 |
| 3 | 添加多个灵感来源 | 来源列表正确显示 |
| 4 | 删除某个来源 | 列表更新正确 |
| 5 | 选择文章风格和长度 | 下拉选择正常工作 |
| 6 | 点击「AI 开始创作」 | 显示加载状态，生成后显示结果 |
| 7 | 查看生成结果 | 标题/正文/配图建议/关键词显示正确 |

#### 2.4 移动端适配测试

**使用浏览器开发者工具模拟移动端：**

| 屏幕尺寸 | 测试点 | 验收标准 |
|---------|--------|---------|
| iPhone SE (375px) | 布局适配 | 无横向滚动，按钮可点击 |
| iPhone 14 Pro (393px) | safe-area | 顶部底部无内容遮挡 |
| 安卓大屏 (412px) | 触控区域 | 按钮高度 ≥ 44px，无重叠 |

**手动测试点：**
- ✅ 所有按钮可点击，无重叠
- ✅ 输入框获得焦点时页面不缩放
- ✅ 文字换行正常，无溢出
- ✅ 图片建议区域滚动正常

---

### 第三阶段：API 接口测试（可选，推荐）

使用 curl 或 Postman 测试以下接口：

#### 3.1 健康检查
```bash
curl http://localhost:8000/api/health
# 预期: {"status": "ok", "timestamp": "..."}
```

#### 3.2 获取 Token
```bash
curl -X POST http://localhost:8000/api/token \
  -F "username=admin" \
  -F "password=admin123"
# 预期: 返回 access_token
```

#### 3.3 灵感抓取
```bash
# 先登录获取 Cookie，再测试抓取
curl -X POST http://localhost:8000/api/inspiration/fetch \
  -F "url=https://example.com"
# 预期: 返回抓取结果
```

---

### 第四阶段：部署前检查清单

- [ ] 所有自动化测试通过（`python3 self_test.py`）
- [ ] 手动功能测试完成，无阻断性 Bug
- [ ] 环境变量已准备好（SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD, AI_API_KEY 等）
- [ ] `config.ini` 中敏感信息已替换为环境变量读取
- [ ] Vercel 项目已配置好环境变量
- [ ] GitHub 代码已推送最新版本

---

## 测试报告模板

每次测试完成后，按以下格式记录：

```
测试报告
========
日期: YYYY-MM-DD
测试人: XXX
版本: git commit hash

自动化测试: [PASSED/FAILED] (X/10 通过)
手动功能测试: [PASSED/FAILED]
  - 登录流程: [✅/❌]
  - 灵感创作: [✅/❌]
  - 移动端适配: [✅/❌]
API 测试: [PASSED/FAILED/SKIPPED]

发现问题:
1. XXX
2. XXX

部署建议: [可以部署/修复后部署]
```

---

## 常见问题排查

### Q: 自动化测试中依赖包报错？
A: 运行 `pip install -r requirements.txt` 安装所有依赖。

### Q: FastAPI 启动报错 "No module named 'web'"？
A: 确保在项目根目录运行启动命令。

### Q: 移动端测试时输入框放大？
A: 检查 viewport 标签是否包含 `maximum-scale=1.0, user-scalable=no`。

### Q: 登录后 Cookie 不生效？
A: 检查是否是 HTTP 访问（本地开发时 secure=False），部署到 Vercel HTTPS 后需改为 secure=True。

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v2.0 | 2024-01-XX | FastAPI 重构版本，新增完整自测流程 |
