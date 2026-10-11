# Output the first existing Devin.exe path, or nothing if not found.
# Detection order: common dirs -> uninstall registry (covers custom drives) ->
# running process path -> Start Menu shortcut -> PATH.
$ErrorActionPreference = 'SilentlyContinue'

$candidates = @(
    "$env:LOCALAPPDATA\Programs\Devin\Devin.exe"
    "$env:ProgramFiles\Devin\Devin.exe"
    "${env:ProgramFiles(x86)}\Devin\Devin.exe"
)

# Uninstall registry entries: NSIS writes real install dir regardless of drive letter
$uninstallRoots = @(
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*'
    'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*'
    'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
Get-ItemProperty $uninstallRoots | Where-Object { $_.DisplayName -match '\bDevin\b' } | ForEach-Object {
    if ($_.DisplayIcon -match '\\Devin\.exe') { $candidates += $_.DisplayIcon }
    if ($_.InstallLocation) { $candidates += (Join-Path $_.InstallLocation.TrimEnd('\') 'Devin.exe') }
}

# Running Devin processes reveal their real path
$candidates += (Get-CimInstance Win32_Process -Filter "Name='Devin.exe'" |
    ForEach-Object { $_.ExecutablePath } |
    Where-Object { $_ -match '\\Devin\.exe$' })

# Start Menu shortcuts (user + all-users)
$wsh = New-Object -ComObject WScript.Shell
$menuRoots = @(
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
    "$env:ProgramData\Microsoft\Windows\Start Menu\Programs"
)
Get-ChildItem $menuRoots -Recurse -Filter '*evin*.lnk' | ForEach-Object {
    $t = $wsh.CreateShortcut($_.FullName).TargetPath
    if ($t -match '\\Devin\.exe$') { $candidates += $t }
}

# PATH
$cmd = Get-Command Devin.exe
if ($cmd) { $candidates += $cmd.Source }

# Multiple installs may coexist (per-user + system-wide). Pick the newest version
# so an upgraded copy wins over a stale one.
$found = $candidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -Unique
if (-not $found) { return }
$best = $found | Sort-Object -Descending {
    try { [version]((Get-Item -LiteralPath $_).VersionInfo.ProductVersion) } catch { [version]'0.0' }
} | Select-Object -First 1
$best
