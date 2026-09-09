param(
    [string]$PymdfuExe = "C:\Users\I73904\AppData\Roaming\Python\Python311\Scripts\pymdfu.exe",
    [string]$ComPort = "COM29",
    [int[]]$UartBauds = @(2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600),
    [int[]]$SpiSpeeds = @(187500, 375000, 750000, 1500000, 3000000, 6000000, 12000000),
    [int[]]$I2cSpeeds = @(100000, 400000, 1000000),
    [string]$UartImage = "$PSScriptRoot\uart\crc32\avr128da48-application-crc32.X\new_application.img",
    [string]$SpiImage = "$PSScriptRoot\spi\avr128da48-application-crc32.X\new_application.img",
    [string]$I2cImage = "$PSScriptRoot\i2c\avr128da48-application-crc32.X\new_application.img",
    [switch]$ContinueOnFailure = $true,
    [switch]$SkipBootloaderPrompt,
    [string]$UartBootloaderHex = "$PSScriptRoot\uart\crc32\avr128da48-mdfu-client-crc32.X\dist\free\production\avr128da48-mdfu-client-crc32.X.production.hex",
    [string]$SpiBootloaderHex  = "$PSScriptRoot\spi\avr128da48-mdfu-client-crc32.X\dist\free\production\avr128da48-mdfu-client-crc32.X.production.hex",
    [string]$I2cBootloaderHex  = "$PSScriptRoot\i2c\avr128da48-mdfu-client-crc32.X\dist\free\production\avr128da48-mdfu-client-crc32.X.production.hex"
)

$ErrorActionPreference = "Stop"

function New-ReportPaths {
    $reportsDir = Join-Path $PSScriptRoot "reports"
    if (-not (Test-Path $reportsDir)) { New-Item -ItemType Directory -Path $reportsDir | Out-Null }
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    return @{
        ReportsDir = $reportsDir
        LogPath = Join-Path $reportsDir "mdfu_run_$stamp.log"
        HtmlPath = Join-Path $reportsDir "mdfu_run_$stamp.html"
    }
}

function Write-Log([string]$message) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
    $line = "[$ts] $message"
    $line | Add-Content -Path $Global:LogPath
}

function Assert-File($path, $label) {
    if (-not (Test-Path -Path $path -PathType Leaf)) {
        throw "$label not found: $path"
    }
}

function Invoke-Pymdfu($label, [string[]]$pymdfuArgs, [hashtable]$meta) {
    Write-Host "`n==== $label ===="
    Write-Host "$PymdfuExe $($pymdfuArgs -join ' ')"
    Write-Log "COMMAND: $PymdfuExe $($pymdfuArgs -join ' ')"
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & $PymdfuExe @pymdfuArgs 2>&1
        $exit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prev
    }
    $text = $output | Out-String
    if ($text.Trim().Length -gt 0) { Write-Host $text }
    if ($text.Trim().Length -gt 0) { Write-Log $text.TrimEnd() }
    $failed = ($exit -ne 0) -or ($text -match "ERROR\s+-") -or ($text -match "Upgrade failed")
    if ($failed) {
        Write-Warning "$label failed (exit=$exit)"
        $meta.Status = "failed"
        $meta.ExitCode = $exit
        $meta.Output = $text.Trim()
        if (-not $ContinueOnFailure) { exit $exit }
    } else {
        Write-Host "$label succeeded."
        $meta.Status = "success"
        $meta.ExitCode = $exit
        $meta.Output = $text.Trim()
    }
}

function Write-HtmlReport($results) {
    $summaryRows = $results | ForEach-Object {
        $status = $_.Status
        $color = if ($status -eq "success") { "#1a7f37" } else { "#d1242f" }
        "<tr><td>$($_.Protocol)</td><td>$($_.Speed)</td><td style='color:$color'>$status</td></tr>"
    }
    $rows = $results | ForEach-Object {
        $status = $_.Status
        $color = if ($status -eq "success") { "#1a7f37" } else { "#d1242f" }
        $detail = ($_.Output -replace "&","&amp;" -replace "<","&lt;" -replace ">","&gt;")
        "<tr><td>$($_.Protocol)</td><td>$($_.Speed)</td><td style='color:$color'>$status</td><td>$($_.Timestamp)</td><td><pre>$detail</pre></td></tr>"
    }
    $html = @"
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>MDFU Update Report</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 8px; vertical-align: top; }
    th { background: #f5f5f5; text-align: left; }
    pre { white-space: pre-wrap; margin: 0; }
  </style>
</head>
<body>
  <h2>MDFU Update Report</h2>
  <p>Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")</p>
  <h3>Summary</h3>
  <table>
    <thead>
      <tr><th>Protocol</th><th>Speed</th><th>Pass/Fail</th></tr>
    </thead>
    <tbody>
      $($summaryRows -join "`n")
    </tbody>
  </table>
  <h3>Details</h3>
  <table>
    <thead>
      <tr><th>Protocol</th><th>Speed</th><th>Status</th><th>Timestamp</th><th>Output</th></tr>
    </thead>
    <tbody>
      $($rows -join "`n")
    </tbody>
  </table>
</body>
</html>
"@
    $html | Set-Content -Path $Global:HtmlPath
}

if (-not $ContinueOnFailure) {
    $ContinueOnFailure = $false
} else {
    $ContinueOnFailure = $true
}

@{ } | Out-Null
$paths = New-ReportPaths
$Global:LogPath = $paths.LogPath
$Global:HtmlPath = $paths.HtmlPath
Write-Log "MDFU update run started"

Assert-File $PymdfuExe "pymdfu.exe"
Assert-File $UartImage "UART image"
Assert-File $SpiImage "SPI image"
Assert-File $I2cImage "I2C image"

Write-Host "Starting MDFU updates..."
Write-Host "UART image: $UartImage"
Write-Host "SPI image:  $SpiImage"
Write-Host "I2C image:  $I2cImage"

$results = @()
foreach ($baud in $UartBauds) {
    if (-not $SkipBootloaderPrompt) {
        Write-Host "`nProgram the UART MDFU bootloader (baud $baud), then press Enter to continue:"
        Write-Host "  $UartBootloaderHex"
        [void](Read-Host)
    }
    $meta = @{
        Protocol = "UART"
        Speed = $baud
        Timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    }
    Invoke-Pymdfu "UART Update @ $baud" @(
        "-v","debug","update","--tool","serial","--port",$ComPort,"--baudrate",$baud.ToString(),
        "--image",$UartImage
    ) $meta
    $results += $meta
}

foreach ($speed in $SpiSpeeds) {
    if (-not $SkipBootloaderPrompt) {
        Write-Host "`nProgram the SPI MDFU bootloader (speed $speed), then press Enter to continue:"
        Write-Host "  $SpiBootloaderHex"
        [void](Read-Host)
    }
    $meta = @{
        Protocol = "SPI"
        Speed = $speed
        Timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    }
    Invoke-Pymdfu "SPI Update @ $speed" @(
        "-v","debug","update","--tool","mcp2222","--interface","spi",
        "--image",$SpiImage,"--clk-speed",$speed.ToString(),
        "--mode","0","--cs-pin","0","--cs-polarity","low","--delay","0"
    ) $meta
    $results += $meta
}

foreach ($speed in $I2cSpeeds) {
    if (-not $SkipBootloaderPrompt) {
        Write-Host "`nProgram the I2C MDFU bootloader (speed $speed), then press Enter to continue:"
        Write-Host "  $I2cBootloaderHex"
        [void](Read-Host)
    }
    $meta = @{
        Protocol = "I2C"
        Speed = $speed
        Timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    }
    Invoke-Pymdfu "I2C Update @ $speed" @(
        "-v","debug","update","--tool","mcp2222","--interface","i2c",
        "--clk-speed",$speed.ToString(),"--address","32",
        "--image",$I2cImage
    ) $meta
    $results += $meta
}

Write-HtmlReport $results
Write-Log "MDFU update run completed"
Write-Host "`nReport written to: $($Global:HtmlPath)"
Write-Host "Log written to:    $($Global:LogPath)"
Write-Host "`nAll requested updates attempted."
