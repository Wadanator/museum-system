#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import atexit

class ButtonHandler:
    def __init__(self, pin, debounce_time=300):
        self.pin = pin
        self.debounce_time = debounce_time
        self.last_press_time = 0
        self.callback = None
        
        # Clean up any existing GPIO setup first
        try:
            GPIO.cleanup()
        except:
            pass
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Remove any existing edge detection on this pin
        try:
            GPIO.remove_event_detect(pin)
        except:
            pass
        
        # Small delay to ensure cleanup is complete
        time.sleep(0.1)
        
        # Setup edge detection with error handling
        try:
            GPIO.add_event_detect(pin, GPIO.FALLING, 
                                 callback=self._button_callback, 
                                 bouncetime=debounce_time)
        except RuntimeError as e:
            print(f"Error setting up edge detection: {e}")
            # Alternative: use polling method instead
            self._use_polling = True
        else:
            self._use_polling = False
        
        # Register cleanup function to run on exit
        atexit.register(self.cleanup)
    def _button_callback(self, channel):
        current_time = time.time() * 1000  # Convert to milliseconds
        
        # Check time difference for debouncing
        if (current_time - self.last_press_time) > self.debounce_time:
            self.last_press_time = current_time
            if self.callback:
                self.callback()
    
    def _check_button_polling(self):
        """Alternative polling method if edge detection fails"""
        if not hasattr(self, '_last_state'):
            self._last_state = GPIO.input(self.pin)
        
        current_state = GPIO.input(self.pin)
        
        # Button pressed (transition from HIGH to LOW)
        if self._last_state == GPIO.HIGH and current_state == GPIO.LOW:
            current_time = time.time() * 1000
            if (current_time - self.last_press_time) > self.debounce_time:
                self.last_press_time = current_time
                if self.callback:
                    self.callback()
        
        self._last_state = current_state
    
    def set_callback(self, callback_function):
        self.callback = callback_function
    
    def cleanup(self):
        try:
            GPIO.remove_event_detect(self.pin)
        except:
            pass
        try:
            GPIO.cleanup()
        except:
            pass

# Example usage
if __name__ == "__main__":
    def on_button_press():
        print("Button pressed!")
    
    button = ButtonHandler(17)  # GPIO17
    button.set_callback(on_button_press)
    
    try:
        print("Press the button (Ctrl+C to exit)...")
        while True:
            # If edge detection failed, use polling
            if hasattr(button, '_use_polling') and button._use_polling:
                button._check_button_polling()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Program terminated")
    finally:
        button.cleanup()