@echo off
cd /d "%~dp0"

set YAML=esp32_mqtt_button_led.yaml

echo ========================================
echo  ESP32 Flash: %YAML%
echo ========================================
echo.

py -3.11 -m esphome run %YAML%

echo.
echo ========================================
pause