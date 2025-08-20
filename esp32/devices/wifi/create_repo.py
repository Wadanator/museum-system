import os

# názov hlavného priečinka (repozitára)
repo_name = "esp32_mqtt_controller"

# zoznam súborov, ktoré chceme vytvoriť
files = [
    "esp32_mqtt_controller.ino",
    "config.h",
    "config.cpp",
    "debug.h",
    "debug.cpp",
    "hardware.h",
    "hardware.cpp",
    "wifi_manager.h",
    "wifi_manager.cpp",
    "mqtt_manager.h",
    "mqtt_manager.cpp",
    "connection_monitor.h",
    "connection_monitor.cpp"
]

def create_repo():
    # vytvoríme hlavný priečinok, ak ešte neexistuje
    os.makedirs(repo_name, exist_ok=True)

    # vytvoríme súbory
    for file in files:
        file_path = os.path.join(repo_name, file)
        # ak súbor ešte neexistuje, vytvoríme ho
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                # môžeme pridať základný obsah podľa prípony
                if file.endswith(".ino"):
                    f.write(f"// Hlavný súbor projektu {repo_name}\n")
                elif file.endswith(".h"):
                    header_guard = file.replace(".", "_").upper()
                    f.write(f"#ifndef {header_guard}\n#define {header_guard}\n\n// Deklarácie funkcií a tried\n\n#endif // {header_guard}\n")
                elif file.endswith(".cpp"):
                    f.write(f"#include \"{file.replace('.cpp', '.h')}\"\n\n// Implementácia funkcií\n")
    print(f"Repozitár '{repo_name}' bol úspešne vytvorený.")

if __name__ == "__main__":
    create_repo()
# Tento skript vytvorí základnú štruktúru repozitára pre ESP32 MQTT Controller