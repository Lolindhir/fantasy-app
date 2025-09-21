$ProjectName = "fantasy-league-custom-frontend"
$OutputDir = "dist/$ProjectName/browser"
$Repo = "Lolindhir/fantasy-app"
$BaseHref = "https://$Repo/"

Write-Host "Baue Angular Projekt..."
ng build --configuration production --base-href $BaseHref

if (!(Test-Path "$OutputDir/index.html")) {
    Write-Error "Build fehlgeschlagen! index.html nicht gefunden."
    exit 1
}

Write-Host "Deployment-Verzeichnis: $OutputDir"
npx angular-cli-ghpages --dir=$OutputDir
