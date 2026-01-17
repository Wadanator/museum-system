#!/bin/bash
set -e

# Farby
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🏛️  MUSEUM SYSTEM - AUTO INSTALLER (CLEAN INSTALL)${NC}"
echo "======================================================"

# 1. Cesty a premenné
INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CURRENT_USER=$(whoami)
echo -e "📂 Priečinok: ${YELLOW}$INSTALL_DIR${NC}"

# ==========================================
# 2. ČISTENIE STARÝCH SLUŽIEB (CLEANUP)
# ==========================================
echo -e "\n${YELLOW}🧹 Čistím staré služby a procesy...${NC}"

# Zoznam možných starých názvov služieb, ktoré chceme odstrániť
OLD_SERVICES=("museum-service" "museum" "museum-system" "museum-watchdog")

for SERVICE in "${OLD_SERVICES[@]}"; do
    if systemctl list-unit-files | grep -q "^$SERVICE.service"; then
        echo "   -> Odstraňujem starú službu: $SERVICE"
        sudo systemctl stop "$SERVICE" 2>/dev/null || true
        sudo systemctl disable "$SERVICE" 2>/dev/null || true
        sudo rm -f "/etc/systemd/system/$SERVICE.service"
    fi
done

# Reload aby systém zabudol na staré služby
sudo systemctl daemon-reload
sudo systemctl reset-failed

echo "   -> Čistenie hotové."

# ==========================================
# 3. INŠTALÁCIA NOVÉHO SYSTÉMU
# ==========================================

# A. Systémové balíčky
echo -e "\n${GREEN}📦 Inštalujem systémové balíčky...${NC}"
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip git mosquitto mosquitto-clients mpv libasound2-dev

# B. MQTT Broker
echo -e "\n${GREEN}📡 Konfigurujem MQTT Broker...${NC}"
MOSQUITTO_CONF="$INSTALL_DIR/broker/mosquitto.conf"
SYSTEM_CONF_DIR="/etc/mosquitto/conf.d"

if [ -f "$MOSQUITTO_CONF" ]; then
    echo "   -> Kopírujem config z repozitára"
    sudo cp "$MOSQUITTO_CONF" "$SYSTEM_CONF_DIR/museum.conf"
else
    echo "   -> Vytváram default config"
    echo -e "listener 1883 0.0.0.0\nallow_anonymous true" | sudo tee "$SYSTEM_CONF_DIR/museum.conf" > /dev/null
fi
sudo systemctl restart mosquitto
sudo systemctl enable mosquitto

# C. Python VENV
if [ ! -d "$INSTALL_DIR/venv" ]; then
    echo -e "\n${GREEN}🐍 Vytváram Python VENV...${NC}"
    python3 -m venv "$INSTALL_DIR/venv"
fi

# D. Python Requirements
echo -e "\n${GREEN}⬇️  Inštalujem Python knižnice...${NC}"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# E. Inštalácia Služieb
echo -e "\n${GREEN}⚙️  Inštalujem nové služby...${NC}"

setup_service() {
    TEMPLATE=$1
    SERVICE_NAME=$2
    DEST="/etc/systemd/system/$SERVICE_NAME"
    
    if [ ! -f "$TEMPLATE" ]; then
        echo -e "${RED}❌ Chyba: Šablóna $TEMPLATE neexistuje!${NC}"
        return
    fi

    echo "   -> Vytváram $SERVICE_NAME"
    sed -e "s|{{PATH}}|$INSTALL_DIR|g" \
        -e "s|{{USER}}|$CURRENT_USER|g" \
        "$TEMPLATE" | sudo tee "$DEST" > /dev/null
        
    sudo systemctl enable "$SERVICE_NAME"
}

# Inštalujeme pod správnymi názvami
setup_service "$INSTALL_DIR/services/museum.service.template" "museum-system.service"
setup_service "$INSTALL_DIR/services/museum-watchdog.service.template" "museum-watchdog.service"

sudo systemctl daemon-reload

# F. Audio Fix
echo -e "\n${GREEN}🔊 Nastavujem audio...${NC}"
sudo amixer cset numid=3 1 2>/dev/null || true

echo -e "\n${GREEN}✅ HOTOVO! Systém je čistý a nainštalovaný.${NC}"
echo "======================================================"
echo "🚀 Spusti príkazom: sudo systemctl start museum-system"