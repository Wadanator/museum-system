# 1. Zastav bežiace služby
sudo systemctl stop museum-system
sudo systemctl stop museum-watchdog

# 2. Zakáž ich automatické spúšťanie
sudo systemctl disable museum-system
sudo systemctl disable museum-watchdog

# 3. Vymaž service súbory zo systému (nie z tvojho priečinka, ale zo systému)
sudo rm /etc/systemd/system/museum-system.service
sudo rm /etc/systemd/system/museum-watchdog.service

# 4. Obnov načítanie systemd, aby vedel, že služby sú preč
sudo systemctl daemon-reload
sudo systemctl reset-failed