#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

class ButtonHandler:
    def __init__(self, pin, debounce_time=300):

        self.pin = pin
        self.debounce_time = debounce_time
        self.last_press_time = 0
        self.callback = None
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Setup edge detection
        GPIO.add_event_detect(pin, GPIO.FALLING, 
                             callback=self._button_callback, 
                             bouncetime=debounce_time)
    
    def _button_callback(self, channel):
        current_time = time.time() * 1000  # Convert to milliseconds
        
        # Check time difference for debouncing
        if (current_time - self.last_press_time) > self.debounce_time:
            self.last_press_time = current_time
            if self.callback:
                self.callback()
    
    def set_callback(self, callback_function):
        self.callback = callback_function
    
    def cleanup(self):
        GPIO.remove_event_detect(self.pin)

# Example usage
if __name__ == "__main__":
    def on_button_press():
        print("Button pressed!")
    
    button = ButtonHandler(17)  # GPIO17
    button.set_callback(on_button_press)
    
    try:
        print("Press the button (Ctrl+C to exit)...")
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Program terminated")
    finally:
        button.cleanup()
        GPIO.cleanup()
