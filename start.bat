@echo off
chcp 65001 > nul
title SMLib Studio Next
echo =======================================================
echo          SMLib Studio Next (AI + CAD + CAE)
echo =======================================================
echo Checking Python env...
python -m pip install -r requirements.txt --quiet

echo Starting Web Server: http://127.0.0.1:8080 ...
start http://127.0.0.1:8080
python server.py
pause
