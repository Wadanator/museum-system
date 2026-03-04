@echo off
cd /d "%~dp0"
echo ========================================
echo  ESP32 Flash: esp32_mqtt_button.yaml
echo ========================================
echo.

py -3.11 -m esphome run esp32_mqtt_button.yaml

echo.
echo ========================================
pause