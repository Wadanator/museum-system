param([string]$Compiler = 'g++')
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$testOutput = Join-Path ([System.IO.Path]::GetTempPath()) 'museum_espnow_tests'
New-Item -ItemType Directory -Path $testOutput -Force | Out-Null
$library = Join-Path $repoRoot 'esp32/libraries/MuseumEspNow/src'
$testExe = Join-Path $testOutput 'link_tests.exe'
& $Compiler -std=c++11 -Wall -Wextra -Werror -pedantic -I $library `
    (Join-Path $PSScriptRoot 'link_tests.cpp') (Join-Path $library 'MuseumEspNow.cpp') -o $testExe
if ($LASTEXITCODE -ne 0) { throw 'Host test compilation failed' }
& $testExe
if ($LASTEXITCODE -ne 0) { throw 'Host link/parser tests failed' }

$motor = Join-Path $repoRoot 'esp32/devices/wifi/ArduinoIDE/esp32_mqtt_controller_MOTORS_ESPNOW/espnow_config.h'
$relay = Join-Path $repoRoot 'esp32/devices/lan/ArduinoIDE/esp32_mqtt_controller_RELAY_ESPNOW/espnow_config.h'
$cases = @(
    @{ Name='motor_bridge'; Header=$motor; Defines=@('-DESPNOW_ENABLED=1','-DMOTOR_DIRECT_MQTT_COMMANDS_ENABLED=0'); Valid=$true },
    @{ Name='motor_legacy'; Header=$motor; Defines=@('-DESPNOW_ENABLED=0','-DMOTOR_DIRECT_MQTT_COMMANDS_ENABLED=1'); Valid=$true },
    @{ Name='relay_bridge'; Header=$relay; Defines=@('-DESPNOW_ENABLED=1','-DRELAY_MOTOR_BRIDGE_ENABLED=1','-DRELAY_WIFI_FALLBACK_ENABLED=0'); Valid=$true },
    @{ Name='relay_bridge_wifi'; Header=$relay; Defines=@('-DESPNOW_ENABLED=1','-DRELAY_MOTOR_BRIDGE_ENABLED=1','-DRELAY_WIFI_FALLBACK_ENABLED=1'); Valid=$true },
    @{ Name='relay_legacy'; Header=$relay; Defines=@('-DESPNOW_ENABLED=0','-DRELAY_MOTOR_BRIDGE_ENABLED=0','-DRELAY_WIFI_FALLBACK_ENABLED=1'); Valid=$true },
    @{ Name='motor_dual'; Header=$motor; Defines=@('-DESPNOW_ENABLED=1','-DMOTOR_DIRECT_MQTT_COMMANDS_ENABLED=1'); Valid=$false },
    @{ Name='motor_no_transport'; Header=$motor; Defines=@('-DESPNOW_ENABLED=0','-DMOTOR_DIRECT_MQTT_COMMANDS_ENABLED=0'); Valid=$false },
    @{ Name='relay_mismatch'; Header=$relay; Defines=@('-DESPNOW_ENABLED=1','-DRELAY_MOTOR_BRIDGE_ENABLED=0','-DRELAY_WIFI_FALLBACK_ENABLED=0'); Valid=$false },
    @{ Name='relay_invalid_channel'; Header=$relay; Defines=@('-DESPNOW_ENABLED=1','-DESPNOW_CHANNEL=0'); Valid=$false },
    @{ Name='relay_unbounded_attempt'; Header=$relay; Defines=@('-DRELAY_WIFI_CONNECT_TIMEOUT_MS=0'); Valid=$false }
)
foreach ($case in $cases) {
    $compilerArgs = @('-E','-x','c++','-I',(Join-Path $PSScriptRoot 'preprocessor')) +
        $case.Defines + @($case.Header,'-o',(Join-Path $testOutput ($case.Name + '.i')))
    $ErrorActionPreference = 'Continue'
    $diagnostics = & $Compiler @compilerArgs 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if (($case.Valid -and $code -ne 0) -or (!$case.Valid -and $code -eq 0)) {
        throw "Unexpected mode-guard result for $($case.Name): $diagnostics"
    }
    if (!$case.Valid -and ($diagnostics -join "`n") -notmatch '#error') {
        throw "Expected a mode #error for $($case.Name), got: $diagnostics"
    }
}
Write-Output "PASS: all $($cases.Count) real mode-header preprocessor cases"
