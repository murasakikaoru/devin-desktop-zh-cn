@echo off
rem Devin Desktop 中文启动器 — 不修改任何安装文件
rem 本脚本可放在任意路径运行（%~dp0 自动定位脚本目录）

cd /d "%~dp0"

rem ---- 定位 Devin.exe: find_devin.ps1 多层探测（任意安装盘符均可）----
set "DEVIN_EXE="
for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0find_devin.ps1"`) do if not defined DEVIN_EXE set "DEVIN_EXE=%%I"
if not defined DEVIN_EXE (
	echo [devin-zh] 未能自动定位 Devin.exe
	set /p "DEVIN_EXE=请粘贴 Devin.exe 完整路径后回车: "
)
set "DEVIN_EXE=%DEVIN_EXE:"=%"
if not defined DEVIN_EXE (
	echo [devin-zh] 未提供路径，退出。
	pause
	exit /b 1
)
if not exist "%DEVIN_EXE%" (
	echo [devin-zh] 路径无效: %DEVIN_EXE%
	pause
	exit /b 1
)
echo [devin-zh] Devin: %DEVIN_EXE%

rem ---- 定位 Python 完整路径（pythonw 优先，跳过 WindowsApps 商店占位）----
set "PYEXE="
for /f "delims=" %%I in ('where pythonw 2^>nul ^| findstr /v /i "WindowsApps"') do if not defined PYEXE set "PYEXE=%%I"
if not defined PYEXE for /f "delims=" %%I in ('where python 2^>nul ^| findstr /v /i "WindowsApps"') do if not defined PYEXE set "PYEXE=%%I"
if not defined PYEXE for /f "delims=" %%I in ('where py 2^>nul') do if not defined PYEXE set "PYEXE=%%I"
if not defined PYEXE (
	echo [devin-zh] 找不到 Python，请先安装 Python 3 并加入 PATH
	pause
	exit /b 1
)

rem ---- 检查运行文件齐全 ----
if not exist "%~dp0inject.py" (
	echo [devin-zh] 缺少 inject.py，请保持汉化包目录完整
	pause
	exit /b 1
)

rem ---- 首次准备: locale + 语言包（幂等） ----
if exist "%~dp0setup.py" "%PYEXE%" "%~dp0setup.py" "%DEVIN_EXE%"

rem ---- 检查 Devin 运行状态：不带调试端口运行时需先关闭 ----
set "NEED_LAUNCH=1"
tasklist /fi "imagename eq Devin.exe" 2>nul | findstr /i "Devin.exe" >nul
if not errorlevel 1 (
	powershell -NoProfile -Command "exit ((Get-NetTCPConnection -LocalPort 9222 -State Listen -ErrorAction SilentlyContinue) -eq $null)" >nul 2>nul
	if errorlevel 1 (
		echo [devin-zh] 检测到 Devin 正在运行，但未开启调试端口，汉化注入需要重启 Devin。
		choice /c YN /n /m "关闭当前 Devin 并以汉化模式重启？[Y=重启 / N=退出] "
		if errorlevel 2 (
			echo 已退出，未做任何更改。
			pause
			exit /b 0
		)
		echo [devin-zh] 正在关闭 Devin…
		taskkill /f /im Devin.exe >nul 2>nul
		%SystemRoot%\System32\timeout.exe /t 3 /nobreak >nul
	) else (
		echo [devin-zh] Devin 已在调试模式运行，直接挂接注入器。
		set "NEED_LAUNCH="
	)
)

rem ---- 清理旧注入器实例，避免重复 ----
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'inject\.py.*--port 9222' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>nul

rem ---- 隐藏启动注入器（任何 Python 均无窗口，且脱离本控制台） ----
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -WindowStyle Hidden -FilePath '%PYEXE%' -ArgumentList 'inject.py','--port','9222' -WorkingDirectory '%~dp0'"

if defined NEED_LAUNCH (
	%SystemRoot%\System32\timeout.exe /t 1 /nobreak >nul
	rem 通过 WMI 创建 Devin 进程: 完全脱离本控制台，关闭本窗口不影响 Devin
	powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='\"%DEVIN_EXE%\" --remote-debugging-port=9222'} | Out-Null"
)

echo [devin-zh] 完成。Devin 界面将显示简体中文。本窗口可安全关闭。
%SystemRoot%\System32\timeout.exe /t 3 /nobreak >nul
