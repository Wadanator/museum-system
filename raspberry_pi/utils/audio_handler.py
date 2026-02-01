#!/usr/bin/env python3
import pygame
import os
import time
from utils.logging_setup import get_logger

class AudioHandler:
    def __init__(self, audio_dir, logger=None, max_init_attempts=3, init_retry_delay=5):
        self.audio_dir = audio_dir
        self.logger = logger or get_logger('audio')
        
        # Nastavenia
        self.max_init_attempts = max_init_attempts
        self.init_retry_delay = init_retry_delay
        
        # Hranica pre automatické streamovanie (ak nie je sfx_ prefix)
        self.STREAM_THRESHOLD = 5 * 1024 * 1024 

        # Stav
        self.audio_available = False
        self.initialization_attempts = 0
        self.last_init_attempt = 0
        
        # Tracking
        self.current_music_file = None      # Práve hrajúca hudba (stream)
        self.music_was_playing = False
        
        # --- NOVÉ: RAM Cache pre SFX (Zvuky načítané v pamäti) ---
        self.sound_cache = {} 
        
        # Dictionary pre aktívne efekty: { "nazov_suboru": [channel_objekt, channel_objekt...] }
        # Toto slúži na sledovanie stavu pre Dashboard a pre STOP:konkretny_subor
        self.active_effects = {} 
        
        self.end_callback = None
        
        self._initialize_audio_system()
    
    def _initialize_audio_system(self):
        """Inicializácia mixéra s viacerými kanálmi."""
        self.initialization_attempts += 1
        self.last_init_attempt = time.time()
        
        audio_configs = [
            {"freq": 48000, "size": -16, "channels": 2, "buffer": 4096, "env": "default"},
            {"freq": 44100, "size": -16, "channels": 2, "buffer": 4096, "env": "hw:0,0"},
            {"freq": 22050, "size": -16, "channels": 1, "buffer": 2048, "env": None}
        ]
        
        for i, config in enumerate(audio_configs):
            try:
                if config["env"]:
                    os.environ["ALSA_DEFAULT_PCM"] = config["env"]
                elif "ALSA_DEFAULT_PCM" in os.environ:
                    del os.environ["ALSA_DEFAULT_PCM"]
                
                try:
                    pygame.mixer.quit()
                except:
                    pass
                
                pygame.mixer.pre_init(
                    frequency=config["freq"], 
                    size=config["size"], 
                    channels=config["channels"], 
                    buffer=config["buffer"]
                )
                pygame.mixer.init()
                
                # ZMENA: Zvýšenie počtu kanálov pre polyfóniu (viac SFX naraz)
                pygame.mixer.set_num_channels(32) 
                
                self.audio_available = True
                device_info = "3.5mm jack (default)" if config["env"] == "default" else f"device config {i+1}"
                self.logger.info(f"Audio initialized successfully using {device_info}")
                return
                
            except Exception as e:
                self.logger.debug(f"Audio config {i+1} failed: {e}")
                continue
        
        self.audio_available = False
        self.logger.error("Audio initialization failed completely")

    # --- NOVÁ FUNKCIA: PRELOADING ---
    def preload_files_for_scene(self, file_list):
        """
        Vyčistí RAM a načíta nové 'sfx_' súbory pred spustením scény.
        """
        if not self.audio_available:
            return

        self.logger.info("Starting Dynamic Preload for Scene...")
        
        # 1. Zastaviť všetko
        self.stop_all()
        
        # 2. Vyčistiť starú RAM cache
        cleaned_count = len(self.sound_cache)
        self.sound_cache.clear()
        
        # 3. Načítať nové SFX
        loaded_count = 0
        for filename in file_list:
            # Načítame len súbory začínajúce na "sfx_"
            if filename.lower().startswith("sfx_"):
                resolved_file, full_path = self._resolve_audio_file(filename)
                
                if resolved_file and self._validate_audio_file(resolved_file, full_path):
                    try:
                        # Load into RAM as Sound object
                        sound_obj = pygame.mixer.Sound(full_path)
                        self.sound_cache[resolved_file] = sound_obj
                        loaded_count += 1
                        self.logger.debug(f"Loaded to RAM: {resolved_file}")
                    except Exception as e:
                        self.logger.error(f"Failed to preload {filename}: {e}")
        
        self.logger.info(f"Preload complete. {loaded_count} SFX files ready in RAM. (Cleared {cleaned_count})")

    # --- UPRAVENÁ HLAVNÁ FUNKCIA PREHRÁVANIA ---
    def play_audio_file(self, filename, volume=1.0):
        self._retry_audio_init()
        if not self.audio_available: return False

        try:
            resolved_name, full_path = self._resolve_audio_file(filename)
            if not resolved_name: return False

            # --- CESTA 1: Je súbor v RAM Cache? (SFX) ---
            if resolved_name in self.sound_cache:
                try:
                    sound = self.sound_cache[resolved_name]
                    sound.set_volume(volume)
                    # Play returns a Channel object
                    channel = sound.play()
                    
                    if channel:
                        # Uložíme channel do active_effects pre Dashboard a STOP príkazy
                        if resolved_name not in self.active_effects:
                            self.active_effects[resolved_name] = []
                        self.active_effects[resolved_name].append(channel)
                        
                        self.logger.info(f"Playing SFX (RAM): {resolved_name} (Vol: {volume})")
                        return True
                    else:
                        self.logger.warning(f"No free channels for SFX: {resolved_name}")
                        return False
                except Exception as e:
                    self.logger.error(f"Failed to play RAM SFX {resolved_name}: {e}")
                    return False

            # --- CESTA 2: Nie je v RAM -> Stream z disku (Hudba) ---
            file_size = os.path.getsize(full_path)
            
            # Ak beží iná hudba, stopneme ju (Stream je len jeden)
            if self.current_music_file:
                pygame.mixer.music.stop()

            try:
                pygame.mixer.music.load(full_path)
                pygame.mixer.music.set_volume(volume)
                pygame.mixer.music.play()
                
                self.current_music_file = resolved_name
                self.music_was_playing = True
                self.logger.info(f"Playing MUSIC (Stream): {resolved_name} (Vol: {volume})")
                return True
            except Exception as e:
                self.logger.error(f"Failed to stream music {resolved_name}: {e}")
                return False

        except Exception as e:
            self.logger.error(f"Error in play_audio_file: {e}")
            return False

    def handle_command(self, message):
        """Spracovanie príkazov z MQTT/JSON"""
        if not message: return False
            
        try:
            if message.startswith("PLAY:"):
                parts = message.split(":")
                filename = parts[1]
                volume = float(parts[2]) if len(parts) > 2 else 1.0
                return self.play_audio_file(filename, max(0.0, min(1.0, volume)))
                                
            elif message == "STOP":
                return self.stop_all()
                
            elif message.startswith("STOP:"):
                # Zastaví konkrétny súbor (či už je to hudba alebo efekt)
                target = message.split(":")[1]
                return self.stop_specific(target)
                
            elif message == "PAUSE":
                return self.pause_audio()
                
            elif message == "RESUME":
                return self.resume_audio()
                
            elif message.startswith("VOLUME:"):
                try:
                    vol = float(message.split(":")[1])
                    return self.set_volume(vol)
                except:
                    return False
            
            else:
                return self.play_audio_file(message)
                
        except Exception as e:
            self.logger.error(f"Failed to handle audio command '{message}': {e}")
            return False

    def stop_all(self):
        """Zastaví všetko - ticho v miestnosti"""
        if not self.audio_available: return True
        
        try:
            # 1. Stop Hudby
            pygame.mixer.music.stop()
            self.current_music_file = None
            
            # 2. Stop všetkých SFX kanálov
            pygame.mixer.stop() 
            
            # Vyčistiť tracking
            self.active_effects.clear()
            
            self.logger.info("Stopped ALL audio")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping all: {e}")
            return False

    def stop_specific(self, filename):
        """Zastaví konkrétny zvuk"""
        resolved_name, _ = self._resolve_audio_file(filename)
        if not resolved_name: resolved_name = filename 

        # 1. Je to hudba?
        if self.current_music_file == resolved_name:
            pygame.mixer.music.stop()
            self.current_music_file = None
            self.logger.info(f"Stopped specific MUSIC: {resolved_name}")

        # 2. Je to efekt?
        if resolved_name in self.active_effects:
            for ch in self.active_effects[resolved_name]:
                ch.stop()
            del self.active_effects[resolved_name]
            self.logger.info(f"Stopped specific SFX: {resolved_name}")
            
        return True

    # --- POMOCNÉ METÓDY ---

    def pause_audio(self):
        if not self.audio_available: return False
        pygame.mixer.music.pause()
        pygame.mixer.pause() # Pause all SFX channels
        return True

    def resume_audio(self):
        if not self.audio_available: return False
        pygame.mixer.music.unpause()
        pygame.mixer.unpause() # Resume all SFX channels
        return True

    def set_volume(self, volume):
        if not self.audio_available: return False
        volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(volume)
        # Poznámka: pygame.mixer.Sound.set_volume sa nastavuje per-objekt,
        # globálne nastavenie hlasitosti pre SFX v Pygame Mixer priamo neexistuje (iba per kanál).
        return True

    def _resolve_audio_file(self, audio_file):
        clean_name = audio_file.replace("PLAY_", "")
        full_path = os.path.join(self.audio_dir, clean_name)
        if os.path.exists(full_path):
            return clean_name, full_path
            
        base, ext = os.path.splitext(clean_name)
        if not ext:
            for try_ext in ['.mp3', '.wav', '.ogg']:
                test_path = os.path.join(self.audio_dir, base + try_ext)
                if os.path.exists(test_path):
                    return base + try_ext, test_path
        
        # Ak sme nenašli, len logneme warning, ale vrátime None
        # (Volajúci to ošetrí)
        return None, None

    def _validate_audio_file(self, audio_file, full_path):
        if not os.path.exists(full_path):
            self.logger.warning(f"Audio file not found: {full_path}")
            return False
        return True

    def _can_retry_init(self):
        if self.audio_available: return False
        if self.initialization_attempts >= self.max_init_attempts: return False
        if time.time() - self.last_init_attempt < self.init_retry_delay: return False
        return True
    
    def _retry_audio_init(self):
        if self._can_retry_init():
            self.logger.info("Retrying audio initialization...")
            self._initialize_audio_system()

    # --- KOMPATIBILITA ---
    
    def play_audio(self, message):
        """Alias pre handle_command"""
        return self.handle_command(message)

    def stop_audio(self):
        """Alias pre stop_all"""
        return self.stop_all()

    # --- DETEKCIA KONCA (PRE TRANSITIONS A DASHBOARD) ---
    def set_end_callback(self, callback):
        self.end_callback = callback
    
    def check_if_ended(self):
        """Volané cyklicky z hlavného loopu"""
        if not self.audio_available: return

        # 1. Kontrola HUDBY (Stream)
        is_music_playing = pygame.mixer.music.get_busy()
        if self.music_was_playing and not is_music_playing:
            if self.current_music_file:
                self.logger.info(f"Music finished: {self.current_music_file}")
                if self.end_callback:
                    self.end_callback(self.current_music_file)
                self.current_music_file = None
        self.music_was_playing = is_music_playing

        # 2. Kontrola EFEKTOV (RAM)
        # Prechádzame zoznam aktívnych efektov a čistíme tie, ktoré dohrali
        ended_effects = []
        for filename, channels in self.active_effects.items():
            # Filtrujeme len kanály, ktoré stále hrajú (get_busy() == True)
            active_channels = [ch for ch in channels if ch.get_busy()]
            self.active_effects[filename] = active_channels
            
            # Ak zoznam kanálov ostal prázdny, zvuk kompletne dohral
            if not active_channels:
                ended_effects.append(filename)

        for filename in ended_effects:
            # self.logger.info(f"SFX finished: {filename}") # Voliteľné logovanie
            del self.active_effects[filename]
            if self.end_callback:
                self.end_callback(filename)

    def cleanup(self):
        try:
            self.stop_all()
            pygame.mixer.quit()
        except:
            pass

    # Metódy pre dashboard (status)
    def is_playing(self):
        music_busy = False
        if self.audio_available:
            try: music_busy = pygame.mixer.music.get_busy()
            except: pass
        return music_busy or bool(self.active_effects)

    def get_audio_status(self):
        return {
            'available': self.audio_available,
            'playing': self.is_playing(),
            'current_music': self.current_music_file,
            'active_sfx_count': len(self.active_effects),
            'ram_cached_files': list(self.sound_cache.keys()) # Pridané info pre debug
        }