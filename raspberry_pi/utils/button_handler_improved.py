#!/usr/bin/env python3
import time
import atexit
import logging

# Try to import RPi.GPIO, fall back to mock if not available
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    
    # Mock GPIO for testing
    class MockGPIO:
        BCM = "BCM"
        IN = "IN"
        HIGH = 1
        LOW = 0
        PUD_UP = "PUD_UP"
        FALLING = "FALLING"
        
        @staticmethod
        def setmode(mode): pass
        @staticmethod
        def setup(pin, mode, pull_up_down=None): pass
        @staticmethod
        def input(pin): return MockGPIO.HIGH
        @staticmethod
        def add_event_detect(pin, edge, callback=None, bouncetime=None): pass
        @staticmethod
        def remove_event_detect(pin): pass
        @staticmethod
        def cleanup(): pass
    
    GPIO = MockGPIO()

class MockButtonHandler:
    def __init__(self, pin, logger=None):
        self.pin = pin
        self.callback = None
        self.use_polling = True
        self.logger = logger or logging.getLogger(__name__)
        self.logger.warning(f"Using mock button handler on pin {pin}")
    
    def set_callback(self, callback): 
        self.callback = callback
    
    def simulate_press(self): 
        if self.callback: 
            self.logger.info(f"Simulated button press on pin {self.pin}")
            self.callback()
    
    def check_button_polling(self):
        pass  # Mock doesn't need polling
    
    def cleanup(self): 
        pass

class ImprovedButtonHandler:
    def __init__(self, pin, debounce_time=300, logger=None):
        self.pin = pin
        self.debounce_time = debounce_time
        self.last_press_time = 0
        self.callback = None
        self.use_polling = False
        self.running = True
        self.logger = logger or logging.getLogger(__name__)
        
        if not GPIO_AVAILABLE:
            self.logger.warning(f"GPIO not available, button on pin {pin} will be simulated")
            self.use_polling = True
            return
        
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Clean any existing detection
            try:
                GPIO.remove_event_detect(pin)
            except:
                pass
            
            time.sleep(0.1)
            
            GPIO.add_event_detect(pin, GPIO.FALLING, 
                                 callback=self._button_callback, 
                                 bouncetime=debounce_time)
            self.logger.info(f"Button handler setup with edge detection on GPIO {pin}")
            
        except Exception as e:
            self.logger.warning(f"Edge detection failed ({e}), using polling method")
            self.use_polling = True
            self._last_state = GPIO.HIGH
        
        atexit.register(self.cleanup)
    
    def _button_callback(self, channel):
        current_time = time.time() * 1000
        if (current_time - self.last_press_time) > self.debounce_time:
            self.last_press_time = current_time
            if self.callback:
                self.logger.info(f"Button pressed on GPIO {self.pin}")
                self.callback()
    
    def check_button_polling(self):
        """Call this method in your main loop if using polling"""
        if not self.use_polling or not GPIO_AVAILABLE:
            return
            
        try:
            current_state = GPIO.input(self.pin)
            
            # Button pressed (HIGH to LOW transition)
            if (hasattr(self, '_last_state') and 
                self._last_state == GPIO.HIGH and 
                current_state == GPIO.LOW):
                
                current_time = time.time() * 1000
                if (current_time - self.last_press_time) > self.debounce_time:
                    self.last_press_time = current_time
                    if self.callback:
                        self.logger.info(f"Button pressed on GPIO {self.pin} (polling)")
                        self.callback()
            
            self._last_state = current_state
        except Exception as e:
            self.logger.error(f"Error in button polling: {e}")
    
    def set_callback(self, callback_function):
        self.callback = callback_function
    
    def cleanup(self):
        self.running = False
        if GPIO_AVAILABLE:
            try:
                GPIO.remove_event_detect(self.pin)
                GPIO.cleanup()
            except:
                pass

# Select appropriate handler based on GPIO availability
ButtonHandler = ImprovedButtonHandler if GPIO_AVAILABLE else MockButtonHandler

# Test function
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    def on_button_press():
        logging.info("Button press detected!")
    
    button = ButtonHandler(17)
    button.set_callback(on_button_press)
    
    logging.info("Testing button handler...")
    logging.info("Press Ctrl+C to exit")
    
    try:
        while True:
            if button.use_polling:
                button.check_button_polling()
            if isinstance(button, MockButtonHandler):
                # Simulate button press for testing
                button.simulate_press()
                time.sleep(2)
            time.sleep(0.1)
    except KeyboardInterrupt:
        logging.info("Test completed")
    finally:
        button.cleanup()