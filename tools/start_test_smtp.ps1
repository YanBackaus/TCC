$pythonPath = "C:\Users\Schenkel_Dell\AppData\Local\Programs\Python\Python312\python.exe"
$scriptPath = Join-Path $PSScriptRoot "test_smtp_server.py"
$outputDir = Join-Path (Split-Path $PSScriptRoot -Parent) ".smtp-test-inbox"
$accountsFile = Join-Path (Split-Path $PSScriptRoot -Parent) ".smtp-test-accounts.json"
$webUrl = "http://127.0.0.1:8025"

if (-not (Test-Path $pythonPath)) {
    throw "Python nao encontrado em $pythonPath"
}

Start-Process $webUrl
& $pythonPath $scriptPath --host 127.0.0.1 --port 1025 --web-host 127.0.0.1 --web-port 8025 --output-dir $outputDir --accounts-file $accountsFile --default-domain teste.local
