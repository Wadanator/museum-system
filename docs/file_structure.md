# Museum System - Celková štruktúra kódu (File Structure)

Tento dokument slúži pre AI a vývojárov, aby mali dokonalý prehľad o umiestnení všetkých dôležitých súborov v repozitári. Sú vynechané build, module adresáre a automaticky generované súbory (`node_modules`, `__pycache__`, `.esphome` atď.).

```text
museum-system/
├── .gitignore
├── README.md
├── SceneGen
│   ├── eslint.config.js
│   ├── index.html
│   ├── package.json
│   ├── postcss.config.js
│   ├── public
│   │   └── vite.svg
│   ├── readme.md
│   ├── src
│   │   ├── App.css
│   │   ├── App.jsx
│   │   ├── assets
│   │   │   └── react.svg
│   │   ├── components
│   │   │   ├── features
│   │   │   │   ├── editor
│   │   │   │   │   ├── ActionEditor.jsx
│   │   │   │   │   ├── ActionListEditor.jsx
│   │   │   │   │   ├── StateEditor.jsx
│   │   │   │   │   ├── TimelineEditor.jsx
│   │   │   │   │   └── TransitionEditor.jsx
│   │   │   │   ├── graph
│   │   │   │   │   ├── GraphicPreview.jsx
│   │   │   │   │   └── SceneNode.jsx
│   │   │   │   ├── mqtt
│   │   │   │   │   ├── AudioControls.jsx
│   │   │   │   │   ├── CustomTopicEditor.jsx
│   │   │   │   │   ├── MotorControls.jsx
│   │   │   │   │   ├── MqttCommandEditor.jsx
│   │   │   │   │   ├── MqttPreview.jsx
│   │   │   │   │   ├── PresetDeviceEditor.jsx
│   │   │   │   │   ├── SimpleDeviceControls.jsx
│   │   │   │   │   └── VideoControls.jsx
│   │   │   │   └── settings
│   │   │   │       ├── GlobalEventsEditor.jsx
│   │   │   │       └── SettingsPanel.jsx
│   │   │   └── layout
│   │   │       ├── Header.jsx
│   │   │       ├── Sidebar.jsx
│   │   │       └── Toolbar.jsx
│   │   ├── hooks
│   │   │   └── useSceneManager.js
│   │   ├── index.css
│   │   ├── main.jsx
│   │   └── utils
│   │       ├── constants.js
│   │       ├── generators.js
│   │       └── jsonExport.js
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── yarn.lock
├── docs
│   ├── Content_instructions.md
│   ├── General_text_instruction.md
│   ├── Structure
│   │   └── RPI
│   │       └── main
│   │           └── ExampleFlowChart.py
│   ├── TO DO
│   │   ├── DELETE_IN_FUTURE_refactor_plan.md
│   │   └── implementation_plan.md
│   ├── ai_context.md
│   ├── architecture.md
│   ├── audio_playing_tutorial.md
│   ├── dashboard_api.md
│   ├── esp32_hardware_reference.md
│   ├── esp32_setup.md
│   ├── file_structure.md
│   ├── mqtt_topics.md
│   ├── museum_setup_guide.md
│   ├── scene_json_format.md
│   └── video_player_tutorial.md
├── esp32
│   ├── common
│   │   ├── WifiCheck.ino
│   │   ├── WirelessButtonTest
│   │   │   └── WirelessButtonTest.ino
│   │   ├── buttonTest_PIN32
│   │   │   └── buttonTest_PIN32.ino
│   │   └── motorTest
│   │       └── motorTest.ino
│   ├── devices
│   │   └── wifi
│   │       ├── ArduinoIDE
│   │       │   ├── esp32_mqtt_button
│   │       │   │   ├── OTA.md
│   │       │   │   ├── config.cpp
│   │       │   │   ├── config.h
│   │       │   │   ├── connection_monitor.cpp
│   │       │   │   ├── connection_monitor.h
│   │       │   │   ├── debug.cpp
│   │       │   │   ├── debug.h
│   │       │   │   ├── esp32_mqtt_button.ino
│   │       │   │   ├── hardware.cpp
│   │       │   │   ├── hardware.h
│   │       │   │   ├── info.md
│   │       │   │   ├── mqtt_manager.cpp
│   │       │   │   ├── mqtt_manager.h
│   │       │   │   ├── ota_manager.cpp
│   │       │   │   ├── ota_manager.h
│   │       │   │   ├── wdt_manager.cpp
│   │       │   │   ├── wdt_manager.h
│   │       │   │   ├── wifi_manager.cpp
│   │       │   │   └── wifi_manager.h
│   │       │   ├── esp32_mqtt_controller_MOTORS
│   │       │   │   ├── OTA.md
│   │       │   │   ├── config.cpp
│   │       │   │   ├── config.h
│   │       │   │   ├── connection_monitor.cpp
│   │       │   │   ├── connection_monitor.h
│   │       │   │   ├── debug.cpp
│   │       │   │   ├── debug.h
│   │       │   │   ├── esp32_mqtt_controller_MOTORS.ino
│   │       │   │   ├── hardware.cpp
│   │       │   │   ├── hardware.h
│   │       │   │   ├── info.md
│   │       │   │   ├── mqtt_manager.cpp
│   │       │   │   ├── mqtt_manager.h
│   │       │   │   ├── ota_manager.cpp
│   │       │   │   ├── ota_manager.h
│   │       │   │   ├── wdt_manager.cpp
│   │       │   │   ├── wdt_manager.h
│   │       │   │   ├── wifi_manager.cpp
│   │       │   │   └── wifi_manager.h
│   │       │   └── esp32_mqtt_controller_RELAY
│   │       │       ├── config.cpp
│   │       │       ├── config.h
│   │       │       ├── connection_monitor.cpp
│   │       │       ├── connection_monitor.h
│   │       │       ├── debug.cpp
│   │       │       ├── debug.h
│   │       │       ├── effects_config.h
│   │       │       ├── effects_manager.cpp
│   │       │       ├── effects_manager.h
│   │       │       ├── esp32_mqtt_controller_RELAY.ino
│   │       │       ├── hardware.cpp
│   │       │       ├── hardware.h
│   │       │       ├── info.md
│   │       │       ├── mqtt_manager.cpp
│   │       │       ├── mqtt_manager.h
│   │       │       ├── ota_manager.cpp
│   │       │       ├── ota_manager.h
│   │       │       ├── status_led.cpp
│   │       │       ├── status_led.h
│   │       │       ├── wdt_manager.cpp
│   │       │       ├── wdt_manager.h
│   │       │       ├── wifi_manager.cpp
│   │       │       └── wifi_manager.h
│   │       └── EspHome
│   │           ├── .gitignore
│   │           ├── esp32_mqtt_button.yaml
│   │           ├── esp32_mqtt_controller_MOTORS_v2.yaml
│   │           ├── esp32_mqtt_controller_RELAY_v2.yaml
│   │           ├── install.bat
│   │           └── logs.bat
│   └── examples
├── museum-dashboard
│   ├── .gitignore
│   ├── README.md
│   ├── eslint.config.js
│   ├── index.html
│   ├── package-lock.json
│   ├── package.json
│   ├── public
│   │   └── vite.svg
│   ├── src
│   │   ├── App.css
│   │   ├── App.jsx
│   │   ├── assets
│   │   │   └── react.svg
│   │   ├── components
│   │   │   ├── Dashboard
│   │   │   │   ├── BigStatusCard.jsx
│   │   │   │   ├── DashboardControls.jsx
│   │   │   │   ├── HeroCard.jsx
│   │   │   │   └── StatsGrid.jsx
│   │   │   ├── Devices
│   │   │   │   ├── MotorCard.jsx
│   │   │   │   └── RelayCard.jsx
│   │   │   ├── Layout
│   │   │   │   ├── AppLayout.jsx
│   │   │   │   ├── Navigation.jsx
│   │   │   │   └── Sidebar.jsx
│   │   │   ├── Media
│   │   │   │   └── FileItem.jsx
│   │   │   ├── Scenes
│   │   │   │   ├── CustomFlowNode.jsx
│   │   │   │   ├── SceneCard.jsx
│   │   │   │   ├── SceneEditorModal.jsx
│   │   │   │   ├── SceneVisualizer.jsx
│   │   │   │   └── SmartEdge.jsx
│   │   │   ├── Shared
│   │   │   │   └── JsonEditor.jsx
│   │   │   ├── Views
│   │   │   │   ├── CommandsView.jsx
│   │   │   │   ├── LiveView.jsx
│   │   │   │   ├── LoginView.jsx
│   │   │   │   ├── LogsView.jsx
│   │   │   │   ├── MainDashboard.jsx
│   │   │   │   ├── MediaManager.jsx
│   │   │   │   ├── ScenesView.jsx
│   │   │   │   ├── StatsView.jsx
│   │   │   │   └── SystemView.jsx
│   │   │   └── ui
│   │   │       ├── Button.jsx
│   │   │       ├── ButtonGroup.jsx
│   │   │       ├── Card.jsx
│   │   │       ├── Modal.jsx
│   │   │       ├── PageHeader.jsx
│   │   │       └── StatusBadge.jsx
│   │   ├── context
│   │   │   ├── AuthContext.jsx
│   │   │   ├── ConfirmContext.jsx
│   │   │   └── SocketContext.jsx
│   │   ├── hooks
│   │   │   ├── useDashboardData.js
│   │   │   ├── useDeviceControl.js
│   │   │   ├── useDevices.js
│   │   │   ├── useLogs.js
│   │   │   ├── useMedia.js
│   │   │   ├── useSceneActions.js
│   │   │   ├── useScenes.js
│   │   │   ├── useSystemActions.js
│   │   │   └── useSystemStats.js
│   │   ├── index.css
│   │   ├── main.jsx
│   │   ├── services
│   │   │   ├── api.js
│   │   │   └── socket.js
│   │   └── styles
│   │       ├── base.css
│   │       ├── components.css
│   │       ├── controls.css
│   │       ├── feedback.css
│   │       ├── layout.css
│   │       ├── theme.css
│   │       ├── utilities.css
│   │       └── views
│   │           ├── commands-view.css
│   │           ├── live-view.css
│   │           ├── login-view.css
│   │           ├── logs-view.css
│   │           ├── main-dashboard.css
│   │           ├── media-manager.css
│   │           ├── scene-editor.css
│   │           ├── scene-flow.css
│   │           ├── scenes-view.css
│   │           ├── stats-view.css
│   │           └── system-view.css
│   └── vite.config.js
└── raspberry_pi
    ├── Web
    │   ├── __init__.py
    │   ├── app.py
    │   ├── auth.py
    │   ├── config.py
    │   ├── dashboard.py
    │   ├── handlers
    │   │   ├── __init__.py
    │   │   ├── log_handler.py
    │   │   └── route_handler.py
    │   ├── routes
    │   │   ├── __init__.py
    │   │   ├── api.py
    │   │   ├── commands.py
    │   │   ├── main.py
    │   │   ├── media.py
    │   │   ├── scenes.py
    │   │   ├── status.py
    │   │   └── system.py
    │   ├── stats.json
    │   └── utils
    │       ├── __init__.py
    │       └── helpers.py
    ├── broker
    │   └── mosquitto.conf
    ├── config
    │   ├── config.ini
    │   └── config.ini.example
    ├── install.sh
    ├── install_offline.sh
    ├── logs
    │   ├── museum-errors.log
    │   └── museum_logs.db
    ├── main.py
    ├── requirements.txt
    ├── scenes
    │   ├── room1
    │   │   ├── AudioEND_TEST.json
    │   │   ├── ReactFlowTest.json
    │   │   ├── Rele_TEST.json
    │   │   ├── SceneV01.json
    │   │   ├── VideoEND_TEST.json
    │   │   ├── audio
    │   │   ├── audio_stress_test.json
    │   │   ├── audio_transition_test.json
    │   │   ├── buttonTest.json
    │   │   ├── commands
    │   │   │   ├── STOPALL.json
    │   │   │   ├── light_off.json
    │   │   │   ├── motor1_off_json.json
    │   │   │   └── motor1_on_50_left_json.json
    │   │   ├── devices.json
    │   │   ├── motor_test.json
    │   │   ├── test.json
    │   │   ├── test_vyber.json
    │   │   └── videos
    │   │       ├── black.png
    │   │       ├── ghost2.mp4
    │   │       ├── readme.md
    │   │       └── wallpaper_mikael_gustafsson.png
    │   └── room2
    │       ├── intro.json
    │       └── test.json
    ├── services
    │   ├── museum-watchdog.service.template
    │   ├── museum.service.template
    │   └── restart_service.sh
    ├── tempCodeRunnerFile.sh
    ├── tests
    │   └── test_schema_validator.py
    ├── tools
    │   ├── Blackscreen
    │   │   ├── TurnOff.bash
    │   │   └── TurnOn.bash
    │   ├── DailyTasks
    │   │   └── dailyreset.sh
    │   ├── Monitoring
    │   │   ├── RAMCheck.py
    │   │   ├── TaskManager.sh
    │   │   ├── health_check.sh
    │   │   ├── temp_monitor.py
    │   │   └── testifrunning.sh
    │   └── diagnostics
    │       ├── audio_Fix.sh
    │       ├── checkproccess.sh
    │       └── teststop.sh
    ├── utils
    │   ├── audio_handler.py
    │   ├── bootstrap.py
    │   ├── button_handler.py
    │   ├── config_manager.py
    │   ├── info.md
    │   ├── logging_setup.py
    │   ├── mqtt
    │   │   ├── __init__.py
    │   │   ├── info.md
    │   │   ├── mqtt_client.py
    │   │   ├── mqtt_device_registry.py
    │   │   ├── mqtt_feedback_tracker.py
    │   │   ├── mqtt_message_handler.py
    │   │   └── topic_rules.py
    │   ├── scene_parser.py
    │   ├── schema_validator.py
    │   ├── service_container.py
    │   ├── state_executor.py
    │   ├── state_machine.py
    │   ├── system_monitor.py
    │   ├── transition_manager.py
    │   └── video_handler.py
    └── watchdog.py
```
