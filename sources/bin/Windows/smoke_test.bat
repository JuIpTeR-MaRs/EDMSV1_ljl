@echo off
REM ==============================================================================
REM  EDMS 冒烟测试一键启动脚本 (Windows - bin 目录版本)
REM ==============================================================================
chcp 65001 >nul
cd /d "%~dp0..\..\..\"

echo [EDMS] 正在启动系统冒烟测试 (Smoke Test)...
echo ----------------------------------------------------

REM 优先使用已激活的 Python 或后端虚拟环境中的 Python
if exist "sources\backend\.venv\Scripts\python.exe" (
    "sources\backend\.venv\Scripts\python.exe" smoke_test.py %*
) else (
    python smoke_test.py %*
)

set TEST_EXIT_CODE=%ERRORLEVEL%
echo.
if %TEST_EXIT_CODE% EQU 0 (
    echo [EDMS] 冒烟测试全部通过！系统运行健康。
) else (
    echo [EDMS] 冒烟测试发现异常，请检查上方日志排查。
)

echo.
pause
exit /b %TEST_EXIT_CODE%
