#!/bin/bash
# ReLab 后端启动脚本

# 设置项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 创建必要的目录
mkdir -p /tmp/relab_uploads
mkdir -p /tmp/relab_reports

# 激活虚拟环境（如果使用）
# source venv/bin/activate

# 安装依赖（如果需要）
# pip install -r requirements.txt

# 启动服务
echo "Starting ReLab API Server..."
python3 backend/app.py
