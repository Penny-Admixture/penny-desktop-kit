@echo off
rem penny-desktop-kit launcher -- WINDOWLESS, Build 1.
rem Penny 2026-11-19: console GONE -- no console window at all, not
rem minimized, not flashing. The app runs under pyw and this batch
rem exits immediately after starting it, so no console stays open.
rem Double-click launch-hidden.vbs, same folder, for a zero-flash
rem start: it runs this batch hidden. Double-clicking this .bat
rem directly still shows cmd for the instant it takes to start pyw.
rem ABI law: git pull first, then launch. A startup failure is
rem written to data\crash.log with the full traceback -- there is
rem no console to show it in.
rem Goto-style, ZERO parenthesized blocks. Never put a ")" inside
rem a parenthesized block -- and this file has no blocks at all,
rem so the trap can't come back.
cd /d "%~dp0"
git pull
if not exist data mkdir data
where pyw >nul 2>nul
if errorlevel 1 goto :nopyw
start "" pyw -3 "%~dp0penny_desktop_kit_main.py" %*
exit /b
:nopyw
echo [%date% %time%] FATAL: Python launcher pyw not found on PATH. Install Python 3.10 or newer and re-run. >> data\crash.log
exit /b 1
