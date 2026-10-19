@echo off
chcp 65001 >nul
cd /d "%~dp0"
title BulkEx - Cai dat

rem Find Python: the "py" launcher first, then python.exe (skip the Microsoft Store stub).
set "PY="
py -3 --version >nul 2>nul && set "PY=py -3"
if not defined PY python --version >nul 2>nul && set "PY=python"
if not defined PY (
  echo.
  echo  Chua co Python tren may nay.
  echo  Trang tai Python se mo ra: cai ban 3.11 tro len, nho tick "Add python.exe to PATH",
  echo  cai xong thi nhay dup lai file CAI-DAT.bat nay.
  start "" https://www.python.org/downloads/
  pause
  exit /b 1
)

echo  Dang cai thu vien can thiet (lan dau mat khoang 1 phut)...
%PY% -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
  echo  Khong cai duoc thu vien. Kiem tra mang Internet roi nhay dup lai file nay.
  pause
  exit /b 1
)

%PY% app\bulkex setup
echo.
pause
