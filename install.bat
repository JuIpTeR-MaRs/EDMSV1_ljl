@echo off
title EDMS Project Setup and Installer
chcp 65001 >nul
if exist "%~dp0scripts\install.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install.ps1"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
)
