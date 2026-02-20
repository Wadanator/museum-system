#ifndef HARDWARE_H
#define HARDWARE_H

// Inicializácia tlačidla
void initializeHardware();

// Funkcia na kontrolu stlačenia (vracia true, ak bolo práve stlačené)
bool wasButtonPressed();

// Vypnutie (pre OTA bezpečnosť, aj keď tu nemá čo bežať)
void turnOffHardware();

#endif