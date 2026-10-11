# Requires: Chrome installed, test-page.html in same dir.
Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" |
  Where-Object { $_.CommandLine -like '*chrome-test-profile*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

$profileDir = "$env:TEMP\chrome-test-profile"
$url = 'file:///' + ((Join-Path $PSScriptRoot 'test-page.html') -replace '\\','/')

$chrome = @(
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe"
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
  "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $chrome) { $chrome = (Get-Command chrome.exe -ErrorAction SilentlyContinue).Source }
if (-not $chrome) { Write-Error 'Chrome not found'; exit 1 }

Start-Process $chrome -ArgumentList @(
  "--remote-debugging-port=9223",
  "--user-data-dir=$profileDir",
  $url
)
Start-Sleep -Seconds 2
try { (Invoke-RestMethod http://127.0.0.1:9223/json/version -TimeoutSec 3).Browser } catch { 'PORT_CLOSED' }
