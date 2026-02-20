#!/bin/bash
set -e

# Farby pre výpis
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🏛️  MUSEUM SYSTEM - OFFLINE SETUP (CONSOLE MODE)${NC}"
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
# 3. KONFIGURÁCIA SYSTÉMU (OS, AUDIO, VIDEO) - OFFLINE
# ==========================================
echo -e "\n${GREEN}🛠️  Konfigurujem OS (Console Mode, Audio, Video)...${NC}"

# A. Nastavenie bootovania do konzole (bez Desktopu)
echo "   -> Nastavujem boot do CLI (Multi-User Target)..."
sudo systemctl set-default multi-user.target

# B. Pridanie práv pre HW (video/render pre DRM mpv, gpio tlačidlá, audio zvuk, dialout/plugdev periphery)
echo "   -> Pridávam užívateľa do skupín (gpio,audio,video,render,dialout,plugdev)..."
sudo usermod -a -G gpio,audio,video,render,dialout,plugdev "$CURRENT_USER"

# C. Audio: JACK 3.5mm (raspi-config) + hlasitosť
echo "   -> Vynucujem Audio výstup na 3.5mm JACK..."
if command -v raspi-config >/dev/null 2>&1; then
  sudo raspi-config nonint do_audio 1 || true
else
  echo -e "   ${YELLOW}(!) raspi-config nenájdený, preskakujem do_audio${NC}"
fi

# Poistka: nastavenie hlasitosti (ak je karta/numid iná, nepadneme)
sudo amixer cset numid=1 95% 2>/dev/null || true

# D. Vypnutie zhasínania obrazovky
echo "   -> Vypínam zhasínanie obrazovky..."
if command -v raspi-config >/dev/null 2>&1; then
  sudo raspi-config nonint do_blanking 1 || true
else
  echo -e "   ${YELLOW}(!) raspi-config nenájdený, preskakujem do_blanking${NC}"
fi

# ==========================================
# 4. OFFLINE KONTROLA ZÁVISLOSTÍ (nič neinštaluje)
# ==========================================
echo -e "\n${GREEN}🧩 Kontrolujem, že potrebné veci už existujú (offline)...${NC}"

need_cmd() {
  local c="$1"
  if ! command -v "$c" >/dev/null 2>&1; then
    echo -e "${RED}❌ Chýba príkaz: $c${NC}"
    echo -e "${YELLOW}   -> Offline režim nič neinštaluje. Nainštaluj to z image / balíčkov a skús znova.${NC}"
    exit 1
  fi
}

# Minimálne, aby systém fungoval rovnako:
need_cmd systemctl
need_cmd python3
need_cmd mpv
need_cmd mosquitto
need_cmd mosquitto_pub
need_cmd mosquitto_sub
need_cmd amixer

# ==========================================
# 5. MQTT (MOSQUITTO) KONFIGURÁCIA - OFFLINE
# ==========================================
echo -e "\n${GREEN}📡 Konfigurujem MQTT (mosquitto)...${NC}"
MOSQUITTO_CONF="$INSTALL_DIR/broker/mosquitto.conf"
SYSTEM_CONF_DIR="/etc/mosquitto/conf.d"

if [ ! -d "$SYSTEM_CONF_DIR" ]; then
  sudo mkdir -p "$SYSTEM_CONF_DIR"
fi

if [ -f "$MOSQUITTO_CONF" ]; then
    echo "   -> Používam lokálny config: $MOSQUITTO_CONF"
    sudo cp "$MOSQUITTO_CONF" "$SYSTEM_CONF_DIR/museum.conf"
else
    echo -e "${YELLOW}   (!) Lokálny mosquitto.conf nenájdený, vytváram default (anonymous)${NC}"
    echo -e "listener 1883 0.0.0.0\nallow_anonymous true" | sudo tee "$SYSTEM_CONF_DIR/museum.conf" > /dev/null
fi

sudo systemctl enable mosquitto
sudo systemctl restart mosquitto

# ==========================================
# 6. PYTHON PROSTREDIE - OFFLINE (nič neinštaluje)
# ==========================================
echo -e "\n${GREEN}🐍 Python prostredie (offline)...${NC}"

if [ ! -d "$INSTALL_DIR/venv" ]; then
    echo -e "${RED}❌ VENV neexistuje: $INSTALL_DIR/venv${NC}"
    echo -e "${YELLOW}   -> Offline režim ho nevytvára/nenaťahuje balíky. Skopíruj hotový venv alebo ho priprav v online image.${NC}"
    exit 1
fi

if [ ! -x "$INSTALL_DIR/venv/bin/python" ]; then
    echo -e "${RED}❌ Neplatný venv (chýba venv/bin/python).${NC}"
    exit 1
fi

# Voliteľné: rýchla kontrola requirements bez internetu (len info, nie je to 100%)
if [ -f "$INSTALL_DIR/requirements.txt" ]; then
  echo "   -> Kontrolujem, či sú nainštalované aspoň niektoré requirements (len orientačne)..."
  "$INSTALL_DIR/venv/bin/pip" -q check 2>/dev/null || true
fi

# ==========================================
# 7. SLUŽBY (SERVICES) - OFFLINE
# ==========================================
echo -e "\n${GREEN}⚙️  Nastavujem služby...${NC}"

setup_service() {
    local TEMPLATE="$1"
    local SERVICE_NAME="$2"
    local DEST="/etc/systemd/system/$SERVICE_NAME"

    if [ ! -f "$TEMPLATE" ]; then
        echo -e "${RED}❌ Chyba: Šablóna $TEMPLATE neexistuje!${NC}"
        exit 1
    fi

    echo "   -> Vytváram $SERVICE_NAME"
    sed -e "s|{{PATH}}|$INSTALL_DIR|g" \
        -e "s|{{USER}}|$CURRENT_USER|g" \
        "$TEMPLATE" | sudo tee "$DEST" > /dev/null

    sudo systemctl enable "$SERVICE_NAME"
}

setup_service "$INSTALL_DIR/services/museum.service.template" "museum-system.service"
setup_service "$INSTALL_DIR/services/museum-watchdog.service.template" "museum-watchdog.service"

sudo systemctl daemon-reload

# V offline verzii ich aj reálne spustíme/reštartneme:
echo -e "\n${GREEN}🚀 Spúšťam služby...${NC}"
sudo systemctl restart museum-system.service
sudo systemctl restart museum-watchdog.service

echo -e "\n${GREEN}✅ HOTOVO (OFFLINE)!${NC}"
echo "======================================================"
echo "⚠️  Ak si teraz pridal užívateľa do skupín alebo menil boot target, odporúčam reštart."
echo "🚀 Reštart: sudo reboot"
