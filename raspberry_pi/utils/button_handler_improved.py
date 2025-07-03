#!/usr/bin/env python3
import time
import RPi.GPIO as GPIO

class ButtonHandler:
    def __init__(self, pin, debounce_time=300, logger=None):
        self.pin = pin
        self.debounce_time = debounce_time
        self.last_press_time = 0
        self.callback = None
        self.use_polling = True
        self.logger = logger
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self.last_state = GPIO.input(pin)
    
    def set_callback(self, callback):
        self.callback = callback
    
    def check_button_polling(self):
        current_state = GPIO.input(self.pin)
        
        # Button pressed (HIGH to LOW)
        if self.last_state == GPIO.HIGH and current_state == GPIO.LOW:
            current_time = time.time() * 1000
            if (current_time - self.last_press_time) > self.debounce_time:
                self.last_press_time = current_time
                if self.callback:
                    if self.logger:
                        self.logger.info(f"Button pressed on GPIO {self.pin}")
                    self.callback()
        
        self.last_state = current_state
    
    def cleanup(self):
        GPIO.cleanup()