#!/bin/bash
# Linux/Mac快速启动脚本
# 需要先配置好 config/config.yaml

echo
echo "========== 豆瓣到Notion同步工具 =========="
echo
echo "1. 手动同步一次"
echo "2. 启动自动同步"
echo "3. 手动同步并启动自动同步（含详细信息）"
echo
echo "0. 退出"
echo

read -p "请选择操作 (0-3): " choice

case $choice in
    1)
        python src/main.py --sync-now
        ;;
    2)
        python src/main.py --auto
        ;;
    3)
        python src/main.py --sync-now --auto --with-details
        ;;
    0)
        exit 0
        ;;
    *)
        echo "无效选择！"
        exit 1
        ;;
esac
