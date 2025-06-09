#!/usr/bin/env python3
import time
import atexit

# Try to import RPi.GPIO, fall back to mock if not available
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("Warning: RPi.GPIO not available, using mock GPIO")
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

class ImprovedButtonHandler:
    def __init__(self, pin, debounce_time=300):
        self.pin = pin
        self.debounce_time = debounce_time
        self.last_press_time = 0
        self.callback = None
        self.use_polling = False
        self.running = True
        
        if not GPIO_AVAILABLE:
            print(f"Warning: GPIO not available, button on pin {pin} will be simulated")
            self.use_polling = True
            return
        
        try:
            # Clean setup
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Try edge detection first
            try:
                GPIO.remove_event_detect(pin)  # Remove any existing detection
            except:
                pass
            
            time.sleep(0.1)  # Small delay
            
            GPIO.add_event_detect(pin, GPIO.FALLING, 
                                 callback=self._button_callback, 
                                 bouncetime=debounce_time)
            print(f"✅ Button handler setup with edge detection on GPIO {pin}")
            
        except Exception as e:
            print(f"⚠️  Edge detection failed ({e}), using polling method")
            self.use_polling = True
            self._last_state = GPIO.HIGH
        
        atexit.register(self.cleanup)
    
    def _button_callback(self, channel):
        current_time = time.time() * 1000
        if (current_time - self.last_press_time) > self.debounce_time:
            self.last_press_time = current_time
            if self.callback:
                print(f"🔘 Button pressed on GPIO {self.pin}")
                self.callback()
    
    def check_button_polling(self):
        ###Call this method in your main loop if using polling###
        if not self.use_polling or not GPIO_AVAILABLE:
            return
            
        try:
            current_state = GPIO.input(self.pin)
            
            # Button pressed (transition from HIGH to LOW)
            if hasattr(self, '_last_state') and self._last_state == GPIO.HIGH and current_state == GPIO.LOW:
                current_time = time.time() * 1000
                if (current_time - self.last_press_time) > self.debounce_time:
                    self.last_press_time = current_time
                    if self.callback:
                        print(f"🔘 Button pressed on GPIO {self.pin} (polling)")
                        self.callback()
            
            self._last_state = current_state
        except Exception as e:
            print(f"Error in button polling: {e}")
    
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

# Test function
if __name__ == "__main__":
    def on_button_press():
        print("🎉 Button press detected!")
    
    button = ImprovedButtonHandler(17)
    button.set_callback(on_button_press)
    
    print("Testing button handler...")
    print("Press Ctrl+C to exit")
    
    try:
        while True:
            if button.use_polling:
                button.check_button_polling()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nTest completed")
    finally:
        button.cleanup()