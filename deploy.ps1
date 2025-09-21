# deploy.ps1

$ProjectName = "fantasy-league-custom-frontend"
$OutputDir = "dist/$ProjectName/browser"
$Repo = "https://github.com/Lolindhir/fantasy-app.git"
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

# Deployment auf GitHub Pages
Write-Host "Deploye nach GitHub Pages..."
npx angular-cli-ghpages --dir=$OutputDir --repo=$Repo

Write-Host "Deployment abgeschlossen!"
