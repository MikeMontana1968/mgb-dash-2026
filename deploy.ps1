# MGB Dash 2026 — Deploy to Raspberry Pi(s)
#
# Pushes latest code to target Pi(s) via SSH + git pull,
# then restarts the appropriate systemd service.
#
# Usage:
#   .\deploy.ps1 gps          # Deploy to GPS display Pi
#   .\deploy.ps1 primary      # Deploy to primary display Pi
#   .\deploy.ps1 testmon      # Deploy to test monitor Pi
#   .\deploy.ps1 all          # Deploy to all Pis
#   .\deploy.ps1 status       # Check service status on all Pis

param(
    [Parameter(Position=0)]
    [ValidateSet("gps", "primary", "testmon", "all", "status")]
    [string]$Target = "all"
)

# Pi hostnames — update these to match your Raspberry Pi Imager settings
$Pis = @{
    gps     = @{ Host = "gps.local";     Service = "mgb-gps-display" }
    primary = @{ Host = "primary.local";  Service = "mgb-primary-display" }
    testmon = @{ Host = "testmon.local";  Service = $null }
}

function Deploy-Pi {
    param([string]$Name, [hashtable]$Config)

    $host_ = $Config.Host
    $svc   = $Config.Service

    Write-Host "`n--- $Name ($host_) ---" -ForegroundColor Cyan

    # Check reachability
    Write-Host "  Checking connectivity..." -NoNewline
    $ping = ssh -o ConnectTimeout=3 -o BatchMode=yes "pi@$host_" "echo ok" 2>$null
    if ($ping -ne "ok") {
        Write-Host " OFFLINE" -ForegroundColor Red
        return
    }
    Write-Host " OK" -ForegroundColor Green

    # Git pull
    Write-Host "  Pulling latest code..." -NoNewline
    $result = ssh "pi@$host_" "cd ~/mgb-dash-2026 && git pull --ff-only 2>&1"
    if ($LASTEXITCODE -ne 0) {
        Write-Host " FAILED" -ForegroundColor Red
        Write-Host "  $result" -ForegroundColor Yellow
        return
    }

    if ($result -match "Already up to date") {
        Write-Host " Already up to date" -ForegroundColor DarkGray
    } else {
        Write-Host " Updated" -ForegroundColor Green
        $result -split "`n" | ForEach-Object { Write-Host "    $_" }
    }

    # Restart service if this Pi has one
    if ($svc) {
        Write-Host "  Restarting $svc..." -NoNewline
        ssh "pi@$host_" "sudo systemctl restart $svc 2>&1"
        if ($LASTEXITCODE -eq 0) {
            Write-Host " OK" -ForegroundColor Green
        } else {
            Write-Host " FAILED" -ForegroundColor Red
        }
    }
}

function Show-Status {
    foreach ($name in $Pis.Keys | Sort-Object) {
        $config = $Pis[$name]
        $host_ = $config.Host
        $svc   = $config.Service

        Write-Host "`n--- $name ($host_) ---" -ForegroundColor Cyan

        $ping = ssh -o ConnectTimeout=3 -o BatchMode=yes "pi@$host_" "echo ok" 2>$null
        if ($ping -ne "ok") {
            Write-Host "  OFFLINE" -ForegroundColor Red
            continue
        }

        # Git status
        $head = ssh "pi@$host_" "cd ~/mgb-dash-2026 && git log --oneline -1 2>/dev/null"
        Write-Host "  Commit: $head"

        # Service status
        if ($svc) {
            $status = ssh "pi@$host_" "systemctl is-active $svc 2>/dev/null"
            $color = if ($status -eq "active") { "Green" } else { "Red" }
            Write-Host "  Service: $svc = " -NoNewline
            Write-Host "$status" -ForegroundColor $color
        }

        # Uptime + temp
        $info = ssh "pi@$host_" "uptime -p 2>/dev/null; vcgencmd measure_temp 2>/dev/null"
        $info -split "`n" | ForEach-Object { Write-Host "  $_" }
    }
}

# Main
Write-Host "MGB Dash 2026 — Deploy" -ForegroundColor White

if ($Target -eq "status") {
    Show-Status
} elseif ($Target -eq "all") {
    foreach ($name in $Pis.Keys | Sort-Object) {
        Deploy-Pi -Name $name -Config $Pis[$name]
    }
} else {
    Deploy-Pi -Name $Target -Config $Pis[$Target]
}

Write-Host "`nDone." -ForegroundColor White
