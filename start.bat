@echo off
title Candidate Intelligence Platform Launcher
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
