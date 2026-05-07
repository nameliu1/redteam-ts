@echo off
setlocal enabledelayedexpansion
echo Starting the process...

set "DATE_DIR=%date:~5,2%%date:~8,2%"
if not exist "%DATE_DIR%" mkdir "%DATE_DIR%"
set "TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TIMESTAMP=%TIMESTAMP: =0%"
set "WORKFLOW_LOG_PATH=%CD%\%DATE_DIR%\workflow_%TIMESTAMP%.log"
echo 日志文件: %WORKFLOW_LOG_PATH%

:: 删除本地目录下的port.txt
if exist port.txt del /F /Q port.txt
if exist url.txt del /F /Q url.txt

:: Step 1: Synchronously run the Python script 2.txt
python 2.txt
python ppp.py


:: Step 2: Copy url.txt to finger\url.txt and replace if exists




:: Step 3: Change directory to finger


:: 删除finger目录下的res.json和res_processed.txt
if exist res.json del /F /Q res.json
if exist res_processed.txt del /F /Q res_processed.txt
if exist res_processed.xlsx del /F /Q res_processed.xlsx

:: Step 4: Asynchronously run the Python script 1.py
start python 1.py

:: Step 5: Pause and wait for user input
pause