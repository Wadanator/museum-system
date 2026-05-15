# Museum System - Aktuálna štruktúra kódu (File Structure)

Tento dokument uvádza overené hlavné súbory a priečinky v repozitári. Nezahŕňa build artefakty ani vendor adresáre.

```text
museum-system/
├── README.md
├── questions.md
├── SCENE_LIFECYCLE_LEASE_PROPOSAL.md
├── STABILITY_ANALYSIS.md
├── STABILITY_ANALYSIS2.md
├── docs/
│   ├── 01_project_context.md
│   ├── 02_system_architecture.md
│   ├── 03_file_structure.md
│   ├── 04_mqtt_protocol.md
│   ├── 05_esp32_hardware_reference.md
│   ├── 06_scene_state_machine.md
│   ├── 07_audio_engine.md
│   ├── 08_video_engine.md
│   ├── 09_dashboard_api.md
│   ├── 10_museum_backend_setup.md
│   ├── 11_esp32_firmware_setup.md
│   ├── 12_physical_installation.md
│   ├── 13_rpi_hardware_watchdog_setup.md
│   ├── Content_instructions.md
│   ├── General_text_instruction.md
│   ├── museum_diagrams/
│   │   ├── _template_block.py
│   │   ├── _template_flowchart.py
│   │   ├── DIAGRAM_GUIDE.md
│   │   ├── fsm_architektura.xml
│   │   ├── gv_html.py
│   │   ├── LinearControl.py
│   │   ├── MQTT_FLOW.xml
│   │   ├── NonLinearControl.py
│   │   ├── outputs/
│   │   ├── render.py
│   │   ├── RPI_HW.xml
│   │   ├── scene_json.py
│   │   ├── state_anatomy.py
│   │   ├── system_topology.xml
│   │   └── theme.py
│   └── TO DO/
│       ├── State_Machine_implementation_plan.md
│       └── StateMachine_Plan.md
├── esp32/
│   ├── common/
│   │   ├── WifiCheck.ino
│   │   ├── WirelessButtonTest/
│   │   │   └── WirelessButtonTest.ino
│   │   ├── buttonTest_PIN32/
│   │   │   └── buttonTest_PIN32.ino
│   │   └── motorTest/
│   │       └── motorTest.ino
│   └── devices/
│       └── wifi/
│           ├── ArduinoIDE/
│           │   ├── esp32_mqtt_button/
│           │   ├── esp32_mqtt_controller_MOTORS/
│           │   └── esp32_mqtt_controller_RELAY/
│           └── EspHome/
│               ├── .gitignore
│               ├── esp32_mqtt_button.yaml
│               ├── esp32_mqtt_controller_MOTORS_v2.yaml
│               ├── esp32_mqtt_controller_RELAY_v2.yaml
│               ├── install.bat
│               └── logs.bat
├── museum-dashboard/
│   ├── README.md
│   ├── eslint.config.js
│   ├── index.html
│   ├── package-lock.json
│   ├── package.json
│   ├── public/
│   │   └── vite.svg
│   ├── src/
│   │   ├── App.jsx
│   │   ├── assets/
│   │   │   └── react.svg
│   │   ├── components/
│   │   ├── context/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── styles/
│   │   └── main.jsx
│   └── vite.config.js
└── raspberry_pi/
    ├── Web/
    │   ├── __init__.py
    │   ├── app.py
    │   ├── auth.py
    │   ├── config.py
    │   ├── dashboard.py
    │   ├── handlers/
    │   │   ├── __init__.py
    │   │   └── log_handler.py
    │   ├── routes/
    │   │   ├── __init__.py
    │   │   ├── api.py
    │   │   ├── commands.py
    │   │   ├── device_states.py
    │   │   ├── main.py
    │   │   ├── media.py
    │   │   ├── scenes.py
    │   │   ├── status.py
    │   │   └── system.py
    │   ├── stats.json
    │   └── utils/
    │       ├── __init__.py
    │       └── helpers.py
    ├── broker/
    │   └── mosquitto.conf
    ├── config/
    │   ├── config.ini
    │   └── config.ini.example
    ├── install.sh
    ├── install_offline.sh
    ├── main.py
    ├── requirements.txt
    ├── scenes/
    │   ├── room1/
    │   │   ├── AudioEND_TEST.json
    │   │   ├── ReactFlowTest.json
    │   │   ├── Rele_TEST.json
    │   │   ├── SceneV01.json
    │   │   ├── VideoEND_TEST.json
    │   │   ├── audio/
    │   │   ├── audio_stress_test.json
    │   │   ├── audio_transition_test.json
    │   │   ├── buttonTest.json
    │   │   ├── commands/
    │   │   ├── devices.json
    │   │   ├── motor_test.json
    │   │   ├── test.json
    │   │   ├── test_vyber.json
    │   │   └── videos/
    │   └── room2/
    │       ├── intro.json
    │       └── test.json
    ├── services/
    │   ├── museum-watchdog.service.template
    │   ├── museum.service.template
    │   └── restart_service.sh
    ├── tests/
    │   ├── manual_scene_service_stress.py
    │   ├── manual_web_retry_p03_test.sh
    │   ├── run_scene_stress_scenev01.sh
    │   ├── test_device_status_broadcast.py
    │   ├── test_main_scene_state.py
    │   ├── test_schema_validator.py
    │   └── test_ws_museum.py
    ├── tools/
    │   ├── Blackscreen/
    │   ├── DailyTasks/
    │   ├── Monitoring/
    │   └── diagnostics/
    ├── utils/
    │   ├── audio_handler.py
    │   ├── bootstrap.py
    │   ├── button_handler.py
    │   ├── config_manager.py
    │   ├── logging_setup.py
    │   ├── scene_parser.py
    │   ├── schema_validator.py
    │   ├── service_container.py
    │   ├── state_executor.py
    │   ├── state_machine.py
    │   ├── system_monitor.py
    │   ├── transition_manager.py
    │   ├── video_handler.py
    │   └── mqtt/
    │       ├── __init__.py
    │       ├── mqtt_actuator_state_store.py
    │       ├── mqtt_client.py
    │       ├── mqtt_device_registry.py
    │       ├── mqtt_feedback_tracker.py
    │       ├── mqtt_message_handler.py
    │       └── topic_rules.py
    └── watchdog.py
```