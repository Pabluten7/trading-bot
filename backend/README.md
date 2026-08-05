# trading-bot
.
Get-ChildItem -Directory -Recurse | Where-Object { @(Get-ChildItem $_.FullName -Force).Count -eq 0 } | ForEach-Object { New-Item -Path "$($_.FullName)\.gitkeep" -ItemType File }