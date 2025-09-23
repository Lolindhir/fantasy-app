$ProjectName = "fantasy-league-custom-frontend"
$OutputDir = "dist/$ProjectName/browser"
$BaseHref = "/fantasy-app/"

Write-Host "Start Deployment..."

# Angular Projekt bauen
Write-Host "Baue Angular Projekt..."
npx ng build --configuration production --base-href $BaseHref

if (!(Test-Path "$OutputDir/index.html")) {
    Write-Error "Build fehlgeschlagen! index.html nicht gefunden."
    exit 1
}

# JSONs aus public/data kopieren
$SourceData = "public/data/*"
$DestData = "$OutputDir/data"
Write-Host "Kopiere JSONs von $SourceData nach $DestData"
if (!(Test-Path $DestData)) { New-Item -ItemType Directory -Path $DestData -Force | Out-Null }
Copy-Item -Path $SourceData -Destination $DestData -Recurse -Force

Write-Host "Build abgeschlossen! Artefakte liegen in $OutputDir"
