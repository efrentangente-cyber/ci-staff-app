# Copies offline-related web files from MyCi\flask_app into geo_smart_ci.
# Run from PowerShell:  cd ...\MyCi  ;  .\scripts\Copy-OfflineWebFilesToGeoSmart.ps1
# Adjust $GeoRoot if your XAMPP path differs.

$ErrorActionPreference = "Stop"
$MyCiRoot = Split-Path $PSScriptRoot -Parent
$FlaskSrc = Join-Path $MyCiRoot "flask_app"
$GeoRoot = "C:\xampp2\htdocs\geo_smart_ci"

if (-not (Test-Path $GeoRoot)) {
    Write-Error "geo_smart_ci not found: $GeoRoot"
}

$pairs = @(
    @{ Src = "static\offline-sync.js"; Dst = "static\offline-sync.js" }
    @{ Src = "static\indexeddb-manager.js"; Dst = "static\indexeddb-manager.js" }
    @{ Src = "static\service-worker.js"; Dst = "static\service-worker.js" }
    @{ Src = "templates\ci_dashboard.html"; Dst = "templates\ci_dashboard.html" }
    @{ Src = "templates\offline_indicator.html"; Dst = "templates\offline_indicator.html" }
    @{ Src = "templates\base.html"; Dst = "templates\base.html" }
    @{ Src = "templates\ci_application.html"; Dst = "templates\ci_application.html" }
)

foreach ($p in $pairs) {
    $from = Join-Path $FlaskSrc $p.Src
    $to = Join-Path $GeoRoot $p.Dst
    if (Test-Path $from) {
        Copy-Item -LiteralPath $from -Destination $to -Force
        Write-Host "OK: $($p.Src) -> $to"
    } else {
        Write-Warning "Missing: $from"
    }
}

Write-Host "`nDone. Review diffs in geo_smart_ci, then commit + push for Render."
Write-Host "WARNING: Overwriting base.html / ci_application.html may need manual merge if geo_smart_ci was customized."
