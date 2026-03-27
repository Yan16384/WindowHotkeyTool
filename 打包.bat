@echo off
chcp 65001 >nul
echo 正在使用Python官方路径打包...
python -m pip install keyboard
python -m pip install pyinstaller
python -m PyInstaller -F -w WindowTool.py
echo.
echo ==============================
echo ✅ 打包完成！
echo 📁 exe 在 dist 文件夹里面
echo ==============================
pause