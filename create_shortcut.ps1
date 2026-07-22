# create_shortcut.ps1
# Creates a desktop shortcut that launches the Chord Progression Generator
# GUI directly, with no console window popping up (uses pythonw.exe instead
# of python.exe).
#
# Run this once, from inside your chord-gen project folder:
#   .\create_shortcut.ps1

$ProjectDir = $PSScriptRoot
$PythonwPath = Join-Path $ProjectDir "venv\Scripts\pythonw.exe"
$ScriptPath = Join-Path $ProjectDir "chord_gen_gui.py"

if (-not (Test-Path $PythonwPath)) {
    Write-Host "Couldn't find $PythonwPath" -ForegroundColor Red
    Write-Host "Make sure you're running this from your chord-gen folder, and that the venv exists." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $ScriptPath)) {
    Write-Host "Couldn't find chord_gen_gui.py in $ProjectDir" -ForegroundColor Red
    exit 1
}

$WshShell = New-Object -ComObject WScript.Shell
$ShortcutPath = Join-Path $env:USERPROFILE "Desktop\Chord Generator.lnk"
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $PythonwPath
$Shortcut.Arguments = "`"$ScriptPath`""
$Shortcut.WorkingDirectory = $ProjectDir
$Shortcut.IconLocation = "shell32.dll,42"
$Shortcut.Description = "Chord Progression Generator"
$Shortcut.Save()

Write-Host "Shortcut created: $ShortcutPath" -ForegroundColor Green
Write-Host "Double-click it any time to launch the app directly." -ForegroundColor Green