$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Port = if ($env:STOCK_SERVER_PORT) { [int]$env:STOCK_SERVER_PORT } else { 8080 }
$BaseUrl = "http://127.0.0.1:$Port"

function Test-Route($Path) {
    $Url = "$BaseUrl$Path"
    try {
        $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        [pscustomobject]@{
            path = $Path
            ok = ($Response.StatusCode -eq 200)
            status_code = $Response.StatusCode
        }
    } catch {
        [pscustomobject]@{
            path = $Path
            ok = $false
            status_code = "error"
            error = $_.Exception.Message
        }
    }
}

Set-Location $Root
$Status = Invoke-RestMethod -Uri "$BaseUrl/api/status" -TimeoutSec 3
$Routes = @(
    Test-Route "/chat"
    Test-Route "/dashboard/account"
    Test-Route "/dashboard/market"
    Test-Route "/dashboard/orders"
    Test-Route "/dashboard/wall"
)

$Result = [pscustomobject]@{
    checked_at = (Get-Date).ToUniversalTime().ToString("o")
    status_ok = $true
    view_model_schema = $Status.view_model_schema
    health = $Status.health
    safe_to_trade = $Status.safe_to_trade
    server_pid = $Status.server_pid
    executed_order_count = $Status.core.executed_order_count
    auto_trade_enabled = $Status.core.auto_trade_enabled
    HOLD = $Status.core.HOLD
    price_feed_available = $Status.core.price_feed_available
    market_data_limited = $Status.core.market_data_limited
    resident_status = $Status.resident.status
    watchdog_status = $Status.watchdog.status
    routes = $Routes
}

$Result | ConvertTo-Json -Depth 8

if ($Status.view_model_schema -ne "StatusViewModel.v1") {
    throw "Unexpected view_model_schema: $($Status.view_model_schema)"
}
if ($Status.core.executed_order_count -ne 0) {
    throw "executed_order_count invariant failed"
}
if ($Status.core.auto_trade_enabled -ne $false) {
    throw "auto_trade_enabled invariant failed"
}
