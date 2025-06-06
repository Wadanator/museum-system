# Automated Museum with MQTT Control

This project implements an interactive museum where each room has its own guide system
based on timed scenes and automated hardware control using MQTT.

## Overview

- Each room has a button that triggers a specific scene when pressed
- Scenes are defined in JSON files stored on Raspberry Pi
- MQTT messaging is used for communication between devices
- ESP32 devices control various hardware components (lights, audio, motors)

## Directory Structure

- `docs/`: Project documentation
- `broker/`: MQTT broker configuration
- `raspberry-pi/`: Code for the Raspberry Pi scene controllers
- `esp32/`: Code for ESP32 devices
- `tools/`: Utility tools for testing and development
