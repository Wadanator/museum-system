#!/bin/bash

TARGET_VOL="97%"

echo "=========================================="
echo "🔊 NASTAVOVANIE ZVUKU NA $TARGET_VOL"
echo "=========================================="

# 1. METÓDA: PulseAudio (pactl)
# Toto je najdôležitejšie, ak ti alsamixer ukazuje "PulseAudio"
if command -v pactl &> /dev/null; then
    echo "[INFO] Detegované PulseAudio, nastavujem..."
    
    # Nájdi defaultný výstup (sink) a nastav hlasitosť
    pactl set-sink-volume @DEFAULT_SINK@ $TARGET_VOL
    
    # Uisti sa, že nie je stíšený (Mute)
    pactl set-sink-mute @DEFAULT_SINK@ 0
    echo "   ✅ PulseAudio nastavené."
else
    echo "[INFO] PulseAudio (pactl) nenájdené, preskakujem."
fi

echo "------------------------------------------"

# 2. METÓDA: ALSA (amixer)
# Toto nastavuje priamo hardvérové "šabľe" pre zvukovú kartu.
# Skúšame bežné názvy pre Raspberry Pi (PCM, HDMI, Headphone, Master).

CONTROLS=("PCM" "Master" "Headphone" "HDMI" "Line Out" "Speaker")
CARDS=(0 1) # Skúsime zvukovú kartu 0 aj 1 (niekedy sa prehodia)

echo "[INFO] Skúšam nastaviť ALSA mixery (HW vrstva)..."

for card in "${CARDS[@]}"; do
    echo "   ➡️ Skúšam zvukovú kartu ID: $card"
    for control in "${CONTROLS[@]}"; do
        # Príkaz nastaví hlasitosť a zároveň zruší MUTE (unmute)
        # > /dev/null zahadzuje chyby, ak daný ovládač neexistuje
        amixer -c "$card" set "$control" $TARGET_VOL unmute > /dev/null 2>&1
        
        # Overíme návratový kód príkazu, ak bol 0 (úspech), vypíšeme to
        if [ $? -eq 0 ]; then
            echo "      ✅ Nastavené: Karta $card -> $control na $TARGET_VOL"
        fi
    done
done

echo "------------------------------------------"

# 3. ULOŽENIE (Aby to prežilo reštart)
echo "[INFO] Ukladám nastavenia..."
sudo alsactl store

echo "=========================================="
echo "🎉 HOTOVO. Skús prehrať zvuk."
echo "=========================================="