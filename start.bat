@echo off
REM 切换到脚本所在目录，以确保相对导入正常工作
cd /d "%~dp0"
REM 使用 -m 参数以模块方式运行 core 包下的 main_app
py -m core.main_app
pause