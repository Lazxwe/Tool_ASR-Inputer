@echo off
chcp 65001 >nul
title Tool_ASR Inputer - 啟動中...

echo ===================================================
echo   Tool_ASR Inputer (本地繁中 AI 語音打字工具)
echo ===================================================
echo 正在檢查 Python 與相依套件...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 系統未安裝 Python 或未將 Python 加入環境變數 PATH。
    echo 請先至 https://www.python.org 安裝 Python 3.10 以上版本。
    pause
    exit /b 1
)

echo 安裝 / 更新相依套件...
pip install -r requirements.txt

echo 啟動 Tool_ASR Inputer 常駐背景...
echo (按下 F8 鍵即可開始/停止語音輸入)
python -m src.main
pause
