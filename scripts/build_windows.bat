@echo off
chcp 65001 >nul
title Tool_ASR Inputer - Windows 打包工具

echo ===================================================
echo   Tool_ASR Inputer - 一鍵生成 Windows 執行檔 (.exe)
echo ===================================================

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 系統未安裝 Python 或未加入 PATH。
    pause
    exit /b 1
)

echo 正在安裝打包工具與相依庫...
pip install -r requirements.txt pyinstaller

echo 開始執行 PyInstaller 打包...
python scripts/build.py

if %errorlevel% equ 0 (
    echo.
    echo ===================================================
    echo [成功] 打包完成！
    echo 發布包位置: dist\Tool_ASR_Inputer\
    echo 執行檔: dist\Tool_ASR_Inputer\Tool_ASR_Inputer.exe
    echo ===================================================
    explorer dist\Tool_ASR_Inputer
) else (
    echo.
    echo [錯誤] 打包過程發生錯誤，請檢查上方日誌訊息。
)
pause
