@echo off
REM Windows快速启动脚本
REM 需要先配置好 config/config.yaml

echo.
echo ========== 豆瓣到Notion同步工具 ==========
echo.
echo 1. 手动同步一次
echo 2. 启动自动同步
echo 3. 手动同步并启动自动同步（含详细信息）
echo.
echo 0. 退出
echo.

set /p choice="请选择操作 (0-3): "

if "%choice%"=="1" (
    python src/main.py --sync-now
) else if "%choice%"=="2" (
    python src/main.py --auto
) else if "%choice%"=="3" (
    python src/main.py --sync-now --auto --with-details
) else if "%choice%"=="0" (
    exit /b 0
) else (
    echo 无效选择！
    exit /b 1
)

pause