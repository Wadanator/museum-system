@echo off
cd /d "C:\Users\Wajdy\Documents\Kodovanie\museum-system\esp32\devices\wifi\EspHome"
py -3.11 -m esphome logs esp32_mqtt_button.yaml
pause