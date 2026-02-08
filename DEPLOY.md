# 智链预测 (Smart Chain Prediction) - 服务器部署指南

本文档详细说明如何将智链预测应用部署到 Linux 服务器（推荐 Ubuntu 22.04 LTS）。

## 1. 环境准备 (Prerequisites)

确保服务器已安装以下基础软件：

*   **操作系统**: Ubuntu 22.04 LTS (或更高版本)
*   **Python**: 3.10+
*   **Node.js**: 18+ (用于构建前端)
*   **Nginx**: 用于反向代理和静态文件服务
*   **Git**: 用于拉取代码

### 1.1 安装基础工具

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv nginx git
```

### 1.2 安装 Node.js (使用 nvm 或直接安装)

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

## 2. 项目代码获取

假设将代码部署在 `/var/www/ai-prediction` 目录：

```bash
# 创建目录并设置权限（假设当前用户为 ubuntu）
sudo mkdir -p /var/www/ai-prediction
sudo chown -R $USER:$USER /var/www/ai-prediction

# 克隆代码 (请替换为实际仓库地址)
git clone <YOUR_GIT_REPO_URL> /var/www/ai-prediction
cd /var/www/ai-prediction
```

## 3. 后端部署 (Backend Setup)

### 3.1 创建虚拟环境并安装依赖

```bash
cd /var/www/ai-prediction/backend

# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3.2 配置环境变量

创建 `.env` 文件：

```bash
cp .env.example .env
nano .env
```

**关键配置项**：
```ini
# DeepSeek API Key (必须)
DEEPSEEK_API_KEY=your_actual_api_key_here

# 代理设置 (如果服务器在国内，可能需要代理访问 Binance)
# HTTP_PROXY=http://127.0.0.1:7890
# HTTPS_PROXY=http://127.0.0.1:7890
```

### 3.3 使用 Systemd 管理后台服务

创建服务文件 `/etc/systemd/system/ai-backend.service`：

```ini
[Unit]
Description=AI Prediction Backend Service
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/var/www/ai-prediction/backend
# 确保路径指向虚拟环境中的 python (或 uvicorn)
ExecStart=/var/www/ai-prediction/backend/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
```

**启动服务**：

```bash
sudo systemctl daemon-reload
sudo systemctl start ai-backend
sudo systemctl enable ai-backend
sudo systemctl status ai-backend
```

## 4. 前端部署 (Frontend Setup)

### 4.1 安装依赖并构建

```bash
cd /var/www/ai-prediction/frontend

# 安装依赖
npm install

# 构建生产环境代码
npm run build
```

构建完成后，会生成 `dist` 目录，这就是我们需要部署的静态文件。

## 5. Nginx 配置 (Reverse Proxy)

配置 Nginx 将前端静态文件和后端 API 整合。

创建配置文件 `/etc/nginx/sites-available/ai-prediction`：

```nginx
server {
    listen 80;
    server_name your_domain.com;  # 替换为你的域名或服务器IP

    # 前端静态文件
    location / {
        root /var/www/ai-prediction/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;  # 支持 Vue Router 的 History 模式
    }

    # 后端 API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # WebSocket 支持 (如果需要)
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**启用配置并重启 Nginx**：

```bash
sudo ln -s /etc/nginx/sites-available/ai-prediction /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 6. 验证部署

1.  访问 `http://your_domain.com` (或 IP)。
2.  应该能看到前端页面。
3.  检查 API 请求是否正常（F12 -> Network，查看 `/api/analysis/health` 或其他接口）。
4.  如果是 https，建议使用 certbot 配置 SSL：
    ```bash
    sudo apt install certbot python3-certbot-nginx
    sudo certbot --nginx -d your_domain.com
    ```

## 7. 维护命令速查

*   **查看后端日志**: `sudo journalctl -u ai-backend -f`
*   **重启后端**: `sudo systemctl restart ai-backend`
*   **更新代码**:
    ```bash
    cd /var/www/ai-prediction
    git pull
    cd backend && pip install -r requirements.txt && sudo systemctl restart ai-backend
    cd ../frontend && npm install && npm run build
    ```
