#!/bin/bash
# 智链预测 - 开发环境启动脚本

echo "🚀 智链预测 - 启动开发环境"
echo "================================"

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查Python虚拟环境
check_venv() {
    if [ ! -d "backend/venv" ]; then
        echo -e "${BLUE}创建Python虚拟环境...${NC}"
        cd backend
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        cd ..
    fi
}

# 检查Node模块
check_node_modules() {
    if [ ! -d "frontend/node_modules" ]; then
        echo -e "${BLUE}安装前端依赖...${NC}"
        cd frontend
        npm install
        cd ..
    fi
}

# 检查环境变量
check_env() {
    if [ ! -f "backend/.env" ]; then
        echo -e "${BLUE}创建环境变量文件...${NC}"
        cp backend/.env.example backend/.env
        echo "⚠️  请编辑 backend/.env 文件，填入 DEEPSEEK_API_KEY"
    fi
}

# 启动后端
start_backend() {
    echo -e "${GREEN}启动后端服务 (端口 8000)...${NC}"
    cd backend
    source venv/bin/activate
    uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    cd ..
}

# 启动前端
start_frontend() {
    echo -e "${GREEN}启动前端服务 (端口 5173)...${NC}"
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    cd ..
}

# 主流程
main() {
    check_venv
    check_node_modules
    check_env
    
    echo ""
    echo "================================"
    echo -e "${GREEN}✅ 启动服务...${NC}"
    echo "================================"
    
    start_backend
    sleep 2
    start_frontend
    
    echo ""
    echo "================================"
    echo -e "${GREEN}🎉 服务启动完成！${NC}"
    echo "================================"
    echo ""
    echo "📊 前端地址: http://localhost:5173"
    echo "📡 后端API: http://localhost:8000"
    echo "📚 API文档: http://localhost:8000/docs"
    echo ""
    echo "按 Ctrl+C 停止所有服务"
    
    # 等待用户中断
    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
    wait
}

main
