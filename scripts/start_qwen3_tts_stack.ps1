$ErrorActionPreference = "Stop"

$QwenRoot = "D:\models\pinokio\api\Qwen3-TTS-Pinokio.git\app"
$QwenPython = Join-Path $QwenRoot "venv\Scripts\python.exe"
$QwenApp = Join-Path $QwenRoot "app.py"
$BridgePython = $QwenPython
$BridgeApp = "D:\aiData\qwen_tts_bridge.py"

$QwenOut = "D:\aiData\qwen3_tts_lan.out.log"
$QwenErr = "D:\aiData\qwen3_tts_lan.err.log"
$BridgeOut = "D:\aiData\qwen_tts_bridge.out.log"
$BridgeErr = "D:\aiData\qwen_tts_bridge.err.log"
$BridgePid = "D:\aiData\qwen_tts_bridge.pid"

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:HF_ENDPOINT = "https://hf-mirror.com"
$env:HF_HUB_ENABLE_HF_TRANSFER = "0"
$env:QWEN_TTS_MODEL_SIZE = "1.7B"

function Test-Port {
    param([int]$Port)
    try {
        $client = [Net.Sockets.TcpClient]::new()
        $iar = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(1000, $false)
        if ($ok) { $client.EndConnect($iar) }
        $client.Close()
        return $ok
    } catch {
        return $false
    }
}

function Wait-Port {
    param([int]$Port, [int]$TimeoutSeconds)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Port $Port) { return $true }
        Start-Sleep -Seconds 2
    }
    return $false
}

if (!(Test-Path $QwenPython)) { throw "Qwen Python not found: $QwenPython" }
if (!(Test-Path $QwenApp)) { throw "Qwen app.py not found: $QwenApp" }
if (!(Test-Path $BridgeApp)) { throw "Bridge script not found: $BridgeApp" }

if (Test-Port 7860) {
    Write-Host "Qwen3-TTS WebUI already listening on http://127.0.0.1:7860"
} else {
    Write-Host "Starting Qwen3-TTS WebUI..."
    Start-Process -FilePath $QwenPython `
        -ArgumentList @($QwenApp) `
        -WorkingDirectory $QwenRoot `
        -RedirectStandardOutput $QwenOut `
        -RedirectStandardError $QwenErr `
        -WindowStyle Hidden

    if (!(Wait-Port 7860 240)) {
        throw "Qwen3-TTS WebUI did not open port 7860 within 240 seconds. Check $QwenErr"
    }
    Write-Host "Qwen3-TTS WebUI ready: http://127.0.0.1:7860"
}

if (Test-Port 7861) {
    Write-Host "Qwen bridge already listening on http://127.0.0.1:7861"
} else {
    Write-Host "Starting Qwen bridge..."
    $process = Start-Process -FilePath $BridgePython `
        -ArgumentList @($BridgeApp) `
        -WorkingDirectory "D:\aiData" `
        -RedirectStandardOutput $BridgeOut `
        -RedirectStandardError $BridgeErr `
        -WindowStyle Hidden `
        -PassThru
    Set-Content -Path $BridgePid -Value $process.Id -Encoding ASCII

    if (!(Wait-Port 7861 60)) {
        throw "Qwen bridge did not open port 7861 within 60 seconds. Check $BridgeErr"
    }
    Write-Host "Qwen bridge ready: http://127.0.0.1:7861"
}

Write-Host ""
Write-Host "Local:"
Write-Host "  Qwen WebUI: http://127.0.0.1:7860"
Write-Host "  Bridge:     http://127.0.0.1:7861/health"
Write-Host "LAN:"
Write-Host "  Qwen WebUI: http://192.168.31.167:7860"
Write-Host "  Bridge:     http://192.168.31.167:7861/health"
Write-Host ""
Write-Host "Logs:"
Write-Host "  $QwenOut"
Write-Host "  $QwenErr"
Write-Host "  $BridgeOut"
Write-Host "  $BridgeErr"
