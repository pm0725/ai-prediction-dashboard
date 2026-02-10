# 智链预测 - Vercel & Render 混合部署指南

由于本项目的后端包含 **WebSocket 长连接** 和 **后台轮询任务 (`push_market_data`)**，**Vercel Serverless Functions 不支持** 部署此类后端（会有 10-60秒 超时限制且不支持长连接）。

因此，推荐采用 **前后端分离部署方案**：
- **前端 (Frontend)**: 部署到 **Vercel** (免费、CDN加速、CI/CD)
- **后端 (Backend)**: 部署到 **Render** 或 **Railway** (支持 Docker 和长驻进程)

---

## 第一步：后端部署 (Render)

我们需要先部署后端，获得 API 地址。

1. **准备 Github 仓库**
   - 确保你的代码已推送到 Github。
   - 确保 `backend/Dockerfile` 已存在（我已为你创建）。

2. **注册/登录 Render**
   - 访问 [https://render.com/](https://render.com/) 并使用 Github 登录。

3. **创建 Web Service**
   - 点击 **"New +"** -> **"Web Service"**。
   - 选择你的 `ai-prediction` Github 仓库。

4. **配置服务**
   - **Name**: `ai-prediction-backend` (自选)
   - **Root Directory**: `backend` (重要！必须填 `backend`)
   - **Environment**: Docker (Render 会自动检测 Dockerfile)
   - **Instance Type**: Free (免费版，注意：闲置15分钟会休眠，唤醒需等待)

5. **配置环境变量**
   - `DEEPSEEK_API_KEY`: 填入你的 DeepSeek Key
   - `BINANCE_API_KEY`: (可选)

6. **部署**
   - 点击 **"Create Web Service"**。
   - 部署成功后复制后端 URL，格式如：`https://ai-prediction-backend.onrender.com`。

---

## 第二步：前端部署 (Vercel)

1. **注册/登录 Vercel**
   - 访问 [https://vercel.com/](https://vercel.com/)。

2. **导入项目**
   - 点击 **"Add New..."** -> **"Project"**。
   - 选择你的 `ai-prediction` Github 仓库。

3. **配置项目**
   - **Framework Preset**: Vite
   - **Root Directory**: 点击 Edit，选择 `frontend` 目录。

4. **配置环境变量**
   我们需要告诉前端连接哪个后端。添加以下变量：
   - `VITE_API_BASE_URL`: 等于 Render 的 URL (如 `https://ai-prediction-backend.onrender.com/api`)
   - `VITE_WS_URL`: 等于 Render URL (将 https 改为 wss，如 `wss://ai-prediction-backend.onrender.com/ws`)

5. **部署**
   - 点击 **"Deploy"**。

---

## 第三步：验证

1. 访问 Vercel 生成的前端网址。
2. 打开浏览器的开发者工具 (F12) -> Network。
3. 检查 API 请求是否成功发送到 Render 的域名。
4. **注意**: Render 免费实例会自动休眠。第一次访问可能需要等待 50秒 左右唤醒后端。

---

### Q: 为什么不能后端也用 Vercel?
A: Vercel 是 Serverless 架构，函数执行限时 10秒，不支持 WebSocket 长连接。我们的后端依赖 `push_market_data` 循环任务和 WebSocket 推送，这在 Vercel 上运行几秒后会被强制中断。
