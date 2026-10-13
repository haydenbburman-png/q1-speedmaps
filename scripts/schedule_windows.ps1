# Registers a Windows scheduled task that rebuilds the speedmaps 3x a day
# (morning build + two refreshes to pick up late scratchings).
# Run once from PowerShell in the project folder:  powershell -ExecutionPolicy Bypass -File scripts\schedule_windows.ps1
$root = Split-Path -Parent $PSScriptRoot
$bat  = Join-Path $root "scripts\run_speedmaps.bat"
New-Item -ItemType Directory -Force -Path (Join-Path $root "output") | Out-Null

$action   = New-ScheduledTaskAction -Execute $bat -WorkingDirectory $root
$triggers = @(
  New-ScheduledTaskTrigger -Daily -At 9:00am
  New-ScheduledTaskTrigger -Daily -At 12:30pm
  New-ScheduledTaskTrigger -Daily -At 4:30pm
)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable
Register-ScheduledTask -TaskName "Q1 Lakeside Speedmaps" -Action $action -Trigger $triggers -Settings $settings -Force
Write-Host "Scheduled. Output: $root\output\latest.html"
