param(
    [string]$RootDir = ".\benchmarks"
)

$destDir = Join-Path $RootDir "RedCode-Exec"
New-Item -ItemType Directory -Force -Path $destDir | Out-Null

Write-Host "Target directory: $destDir"
Write-Host "Please download RedCode-Exec dataset manually from:"
Write-Host "https://github.com/AI-secure/RedCode"
Write-Host "Then place py2text_dataset_json under:"
Write-Host (Join-Path $destDir "py2text_dataset_json")
Write-Host "No data downloaded automatically to avoid license/compliance issues."
