#!/usr/bin/env python3
import time
import RPi.GPIO as GPIO
from utils.logging_setup import get_logger
class ButtonHandler:
    def __init__(self, pin, debounce_time=300, logger=None):
        self.pin = pin
        self.debounce_time = debounce_time
        self.last_press_time = 0
        self.callback = None
        self.use_polling = True
        self.logger = logger or get_logger('btn_handler')
        
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

if __name__ == "__main__":
    import logging
    Button_pin = 27
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    def button_callback():
        print("Button was pressed!")

    # Create ButtonHandler instance
    try:
        button = ButtonHandler(pin=Button_pin, debounce_time=300, logger=logger)
        button.set_callback(button_callback)
        
        print(f"Testing button on GPIO {Button_pin}. Press the button or Ctrl+C to exit.")
        
        # Main loop for testing
        while True:
            button.check_button_polling()
            time.sleep(0.1)  # Small sleep to prevent CPU overuse
            
    except KeyboardInterrupt:
        print("\nExiting test...")
    finally:
        button.cleanup()