$ProjectName = "fantasy-league-custom-frontend"
$OutputDir = "dist/$ProjectName/browser"

Write-Host "Baue Angular Projekt..."
npm run build

if (!(Test-Path "$OutputDir/index.html")) {
    Write-Error "Build fehlgeschlagen! index.html nicht gefunden."
    exit 1
}

Write-Host "Deployment-Verzeichnis: $OutputDir"
npx angular-cli-ghpages --dir=$OutputDir --no-silent
