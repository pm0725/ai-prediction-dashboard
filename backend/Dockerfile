# 使用官方 Python 轻量级镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
# 防止 Python 生成 .pyc 文件
ENV PYTHONDONTWRITEBYTECODE=1
# 确保控制台输出不被缓冲
ENV PYTHONUNBUFFERED=1

# 安装系统依赖 (如果不需编译可省略，但通常建议安装基础库)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口 (FastAPI 默认 8000)
EXPOSE 8000

# 启动命令
# 使用 uvicorn 启动，host 设为 0.0.0.0 以允许外部访问
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
