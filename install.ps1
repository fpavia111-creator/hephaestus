# Install skill-shipper on Windows (PowerShell 5.1+ / 7+). Copies folders; no symlinks.
# Usage:  .\install.ps1                 -> Claude Code user skills (~\.claude\skills)
#         .\install.ps1 -Target cursor  -> ~\.cursor\skills
#         .\install.ps1 -Target project -> .\.claude\skills in the current directory
param([ValidateSet("claude","cursor","codex","project")][string]$Target = "claude")
$ErrorActionPreference = "Stop"
$dest = switch ($Target) {
  "claude"  { Join-Path $HOME ".claude\skills" }
  "cursor"  { Join-Path $HOME ".cursor\skills" }
  "codex"   { Join-Path $HOME ".codex\skills" }
  "project" { Join-Path (Get-Location) ".claude\skills" }
}
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$pairs = @(@{src = Join-Path $here "free\skill-shipper"; name = "skill-shipper"})
foreach ($p in $pairs) {
  $t = Join-Path $dest $p.name
  if (Test-Path $t) { Remove-Item -Recurse -Force $t }
  Copy-Item -Recurse -Path $p.src -Destination $t
  Write-Host "Installed $($p.name) -> $t"
}
