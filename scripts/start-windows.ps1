$ErrorActionPreference = "Stop"

$appName = "pm-app"
$imageName = "pm-app"
$rootDir = Resolve-Path "$PSScriptRoot\.."

if (-not (Test-Path "$rootDir\.env")) {
    throw "Missing $rootDir\.env - create it with OPENROUTER_API_KEY=<your key>"
}

docker build -t $imageName $rootDir
if ($LASTEXITCODE -ne 0) { throw "docker build failed" }

docker rm -f $appName *>$null

docker run --name $appName --env-file "$rootDir\.env" -p 8000:8000 $imageName
