@echo off
chcp 65001 >nul
title Dung Javis OS
echo Dang tim va tat Javis OS (port 7777)...
set FOUND=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":7777" ^| findstr "LISTENING"') do (
  taskkill /F /T /PID %%a >nul 2>&1
  set FOUND=1
  echo   - Da tat PID %%a
)
if "%FOUND%"=="0" echo   (Khong thay server nao dang chay)
echo Xong.
timeout /t 2 >nul
