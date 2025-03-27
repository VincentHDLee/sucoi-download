#!/bin/bash
# Sucoidownload 启动脚本

# 获取脚本所在的目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# 切换到脚本所在目录
cd "$SCRIPT_DIR"

# 执行 Python 下载器脚本
echo "正在启动 Sucoidownload..."
python sucoidownload.py

echo "Sucoidownload 已退出。"