@echo off
chcp 65001 > nul
title SMLib Web Studio
echo =======================================================
echo          SMLib Web Studio (smlibpy x cax-viewer)
echo =======================================================
echo 正在检查 Python 环境与依赖...
python -m pip install -r requirements.txt --quiet

echo 正在启动 Web 服务: http://127.0.0.1:8080 ...
start http://127.0.0.1:8080
python server.py
pause
