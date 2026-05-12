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
echo [WORKFLOW] START 2.txt >> "%WORKFLOW_LOG_PATH%"
python 2.txt
if errorlevel 1 goto :workflow_failed
if not exist url.txt (
    echo [WORKFLOW] INFO no candidate web URLs found, skipping downstream stages >> "%WORKFLOW_LOG_PATH%"
    goto :eof
)

echo [WORKFLOW] START ppp.py >> "%WORKFLOW_LOG_PATH%"
python ppp.py
if errorlevel 1 echo [WORKFLOW] WARN ppp.py failed but workflow will continue >> "%WORKFLOW_LOG_PATH%"
echo [WORKFLOW] START 1.py >> "%WORKFLOW_LOG_PATH%"

:: Step 2: Copy url.txt to finger\url.txt and replace if exists




:: Step 3: Change directory to finger


:: 删除finger目录下的res.json和res_processed.txt
if exist res.json del /F /Q res.json
if exist res_processed.txt del /F /Q res_processed.txt
if exist res_processed.xlsx del /F /Q res_processed.xlsx

:: Step 4: Asynchronously run the Python script 1.py
python 1.py
if errorlevel 1 goto :workflow_failed
goto :eof

:workflow_failed
echo 前置步骤执行失败，已停止后续工作流。
pause