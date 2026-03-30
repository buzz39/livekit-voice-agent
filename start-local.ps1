param(
    [int]$ApiPort = 8000,
    [string]$AgentName = "voice-assistant"
)

$ErrorActionPreference = "Stop"

function Get-PythonPath {
    $venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }
    throw "Python executable not found at $venvPython"
}

function Stop-ProcessOnPort {
    param([int]$Port)

    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $connections) {
        return
    }

    foreach ($conn in $connections) {
        $procId = $conn.OwningProcess
        if ($procId -and $procId -ne 0) {
            Write-Host "Stopping process $procId listening on port $Port"
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }

    Start-Sleep -Seconds 1
}

$pythonExe = Get-PythonPath

# Avoid the repeated local startup failure caused by stale listeners.
Stop-ProcessOnPort -Port $ApiPort

$env:OUTBOUND_AGENT_NAME = $AgentName
$env:LIVEKIT_WORKER_LOAD_THRESHOLD = "0.9"

$serverCmd = "cd `"$PSScriptRoot`"; `$env:OUTBOUND_AGENT_NAME=`"$AgentName`"; & `"$pythonExe`" -m uvicorn server:app --host 0.0.0.0 --port $ApiPort"
$agentCmd = "cd `"$PSScriptRoot`"; `$env:OUTBOUND_AGENT_NAME=`"$AgentName`"; & `"$pythonExe`" outbound_agent.py start"

Write-Host "Starting API server on port $ApiPort"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", $serverCmd | Out-Null

Start-Sleep -Seconds 2

Write-Host "Starting outbound worker with agent name '$AgentName'"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", $agentCmd | Out-Null

Write-Host "Launched local stack."
Write-Host "- API: http://localhost:$ApiPort/health"
Write-Host "- Startup checks: http://localhost:$ApiPort/health/startup"
