#!/bin/bash
set -e

# Farby pre výpis
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🏛️  MUSEUM SYSTEM - PRODUCTION INSTALLER (CONSOLE MODE)${NC}"
echo "======================================================"

# 1. Cesty a premenné
INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CURRENT_USER=$(whoami)
echo -e "📂 Priečinok: ${YELLOW}$INSTALL_DIR${NC}"
echo -e "👤 Užívateľ: ${YELLOW}$CURRENT_USER${NC}"

# ==========================================
# 2. ČISTENIE STARÝCH SLUŽIEB
# ==========================================
echo -e "\n${YELLOW}🧹 Čistím staré služby...${NC}"
OLD_SERVICES=("museum-service" "museum" "museum-system" "museum-watchdog")
for SERVICE in "${OLD_SERVICES[@]}"; do
    if systemctl list-unit-files | grep -q "^$SERVICE.service"; then
        echo "   -> Odstraňujem: $SERVICE"
        sudo systemctl stop "$SERVICE" 2>/dev/null || true
        sudo systemctl disable "$SERVICE" 2>/dev/null || true
        sudo rm -f "/etc/systemd/system/$SERVICE.service"
    fi
done
sudo systemctl daemon-reload
sudo systemctl reset-failed

# ==========================================
# 3. KONFIGURÁCIA SYSTÉMU (OS, AUDIO, VIDEO)
# ==========================================
echo -e "\n${GREEN}🛠️  Konfigurujem OS (Console Mode, Audio, Video)...${NC}"

# A. Nastavenie bootovania do konzole (bez Desktopu)
echo "   -> Nastavujem boot do CLI (Multi-User Target)..."
sudo systemctl set-default multi-user.target

# B. Pridanie práv pre Hardvér (Kritické pre video v konzole!)
# video, render -> potrebné pre mpv prehrávanie bez X11 (cez DRM)
# gpio -> tlačidlá
# audio -> zvuk
echo "   -> Pridávam užívateľa do skupín (video, audio, gpio)..."
sudo usermod -a -G gpio,audio,video,render,dialout,plugdev "$CURRENT_USER"

# C. Nastavenie Audia (Priorita: JACK)
# 1 = Jack (Headphones), 2 = HDMI, 0 = Auto
echo "   -> Vynucujem Audio výstup na 3.5mm JACK..."
# Skúsime moderný spôsob cez raspi-config
sudo raspi-config nonint do_audio 1
# Poistka: Nastavenie systemovej hlasitosti a unmute.
TARGET_VOL="95%"
echo "   -> Nastavujem systemovu hlasitost na $TARGET_VOL..."
sudo amixer cset numid=1 "$TARGET_VOL" 2>/dev/null || true
for card in 0 1; do
    for control in PCM Master Headphone HDMI "Line Out" Speaker; do
        sudo amixer -c "$card" set "$control" "$TARGET_VOL" unmute >/dev/null 2>&1 || true
    done
done
sudo alsactl store >/dev/null 2>&1 || true

# D. Vypnutie šetriča obrazovky (Console Blanking)
echo "   -> Vypínam zhasínanie obrazovky..."
sudo raspi-config nonint do_blanking 1

# ==========================================
# 4. INŠTALÁCIA ZÁVISLOSTÍ
# ==========================================
echo -e "\n${GREEN}📦 Inštalujem balíčky...${NC}"
sudo apt-get update
# Pridame aj alsa-utils pre zvuk a cec-utils pre HDMI-CEC testy.
sudo apt-get install -y python3-venv python3-pip git mosquitto mosquitto-clients mpv libasound2-dev alsa-utils cec-utils

# Konfigurácia Mosquitto
echo -e "\n${GREEN}📡 Konfigurujem MQTT...${NC}"
MOSQUITTO_CONF="$INSTALL_DIR/broker/mosquitto.conf"
SYSTEM_CONF_DIR="/etc/mosquitto/conf.d"
if [ ! -d "$SYSTEM_CONF_DIR" ]; then sudo mkdir -p "$SYSTEM_CONF_DIR"; fi

if [ -f "$MOSQUITTO_CONF" ]; then
    sudo cp "$MOSQUITTO_CONF" "$SYSTEM_CONF_DIR/museum.conf"
else
    echo -e "listener 1883 0.0.0.0\nallow_anonymous true" | sudo tee "$SYSTEM_CONF_DIR/museum.conf" > /dev/null
fi
sudo systemctl restart mosquitto
sudo systemctl enable mosquitto

# ==========================================
# 5. PYTHON PROSTREDIE
# ==========================================
if [ ! -d "$INSTALL_DIR/venv" ]; then
    echo -e "\n${GREEN}🐍 Vytváram Python VENV...${NC}"
    python3 -m venv "$INSTALL_DIR/venv"
fi

echo -e "\n${GREEN}⬇️  Inštalujem Python knižnice...${NC}"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# ==========================================
# 6. SLUŽBY (SERVICES)
# ==========================================
echo -e "\n${GREEN}⚙️  Inštalujem služby...${NC}"

setup_service() {
    TEMPLATE=$1
    SERVICE_NAME=$2
    DEST="/etc/systemd/system/$SERVICE_NAME"
    
    if [ ! -f "$TEMPLATE" ]; then
        echo -e "${RED}❌ Chyba: Šablóna $TEMPLATE neexistuje!${NC}"
        return
    fi

    echo "   -> Vytváram $SERVICE_NAME"
    # Vymažeme Environment=DISPLAY, pretože sme v konzole
    sed -e "s|{{PATH}}|$INSTALL_DIR|g" \
        -e "s|{{USER}}|$CURRENT_USER|g" \
        "$TEMPLATE" | sudo tee "$DEST" > /dev/null
        
    sudo systemctl enable "$SERVICE_NAME"
}

setup_service "$INSTALL_DIR/services/museum.service.template" "museum-system.service"
setup_service "$INSTALL_DIR/services/museum-watchdog.service.template" "museum-watchdog.service"

sudo systemctl daemon-reload

echo -e "\n${GREEN}✅ HOTOVO!${NC}"
echo "======================================================"
echo "⚠️  JE POTREBNÝ REŠTART PRE APLIKOVANIE PRÁV A ZMENU BOOTU!"
echo "🚀 Reštartuj príkazom: sudo reboot"
