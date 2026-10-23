@echo off
REM 本機手動測試用。API key 請寫在同資料夾的 .env 檔（參考 .env.example）
cd /d %~dp0
pip install -r requirements.txt >nul
python digest.py >> log.txt 2>&1
start docs\index.html
