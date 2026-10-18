param([switch]$ConfigureXToken)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$credentialDirectory = Join-Path $env:LOCALAPPDATA 'SerenityWatch'
$credentialFile = Join-Path $credentialDirectory 'x-token.xml'
if ($ConfigureXToken) {
    New-Item -ItemType Directory -Force -Path $credentialDirectory | Out-Null
    Read-Host 'Paste your X Bearer Token (hidden)' -AsSecureString | Export-Clixml -LiteralPath $credentialFile
    Write-Host 'Saved encrypted for this Windows user. Run this script without -ConfigureXToken to collect.'
    exit 0
}
if (!(Test-Path -LiteralPath $credentialFile)) {
    throw 'Configure the X token first: .\scripts\run-local.ps1 -ConfigureXToken'
}
$previousToken = $env:X_BEARER_TOKEN
$previousProvider = $env:CLASSIFIER_PROVIDER
Push-Location $projectRoot
try {
    $dirty = git status --porcelain
    if ($LASTEXITCODE -ne 0 -or $dirty) { throw 'Start with a clean Git checkout; commit or stash your changes first.' }
    git pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw 'Unable to update checkout.' }
    $secureToken = Import-Clixml -LiteralPath $credentialFile
    $env:X_BEARER_TOKEN = [System.Net.NetworkCredential]::new('', $secureToken).Password
    $env:CLASSIFIER_PROVIDER = 'codex'
    python scripts/update.py
    $collectionExit = $LASTEXITCODE
    git add -- site/data/tracker.json
    if ($LASTEXITCODE -ne 0) { throw 'Unable to stage collection result.' }
    git diff --cached --quiet
    if ($LASTEXITCODE -eq 1) {
        git commit -m 'data: update Serenity commentary through subscription classifier'
        if ($LASTEXITCODE -ne 0) { throw 'Unable to commit data.' }
        git push
        if ($LASTEXITCODE -ne 0) { throw 'Unable to push data. The local commit is preserved; retry git push.' }
    } elseif ($LASTEXITCODE -ne 0) { throw 'Unable to inspect staged data.' }
    if ($collectionExit -ne 0) { throw 'Collection failed. Preserved data and failure status were published; check Codex sign-in and X access.' }
} finally {
    $env:X_BEARER_TOKEN = $previousToken
    $env:CLASSIFIER_PROVIDER = $previousProvider
    Pop-Location
}
