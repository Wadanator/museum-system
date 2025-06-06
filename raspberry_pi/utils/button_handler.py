#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import atexit
import sys

class ButtonHandler:
    def __init__(self, pin, debounce_time=300):
        self.pin = pin
        self.debounce_time = debounce_time
        self.last_press_time = 0
        self.callback = None
        self._use_polling = False

        # Use GPIO.BCM mode
        try:
            GPIO.setmode(GPIO.BCM)
        except Exception as e:
            print(f"Error setting GPIO mode: {e}")
            sys.exit(1)

        # Attempt to clean up any existing GPIO configuration
        try:
            GPIO.cleanup(self.pin)  # Clean only the specific pin
        except Exception as e:
            print(f"Warning: Failed to clean up GPIO pin {self.pin}: {e}")

        # Setup GPIO pin with pull-up resistor
        try:
            GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        except Exception as e:
            print(f"Error setting up GPIO pin {self.pin}: {e}")
            sys.exit(1)

        # Setup edge detection
        try:
            GPIO.add_event_detect(self.pin, GPIO.FALLING, 
                                 callback=self._button_callback, 
                                 bouncetime=debounce_time)
        except RuntimeError as e:
            print(f"Error setting up edge detection on pin {self.pin}: {e}")
            print("Falling back to polling mode.")
            self._use_polling = True

        # Register cleanup function
        atexit.register(self.cleanup)

    def _button_callback(self, channel):
        current_time = time.time() * 1000  # Convert to milliseconds
        if (current_time - self.last_press_time) > self.debounce_time:
            self.last_press_time = current_time
            if self.callback:
                try:
                    self.callback()
                except Exception as e:
                    print(f"Error in callback: {e}")

    def _check_button_polling(self):
        if not hasattr(self, '_last_state'):
            self._last_state = GPIO.input(self.pin)

        current_state = GPIO.input(self.pin)
        if self._last_state == GPIO.HIGH and current_state == GPIO.LOW:
            current_time = time.time() * 1000
            if (current_time - self.last_press_time) > self.debounce_time:
                self.last_press_time = current_time
                if self.callback:
                    try:
                        self.callback()
                    except Exception as e:
                        print(f"Error in polling callback: {e}")
        self._last_state = current_state

    def set_callback(self, callback_function):
        self.callback = callback_function

    def cleanup(self):
        try:
            if not self._use_polling:
                GPIO.remove_event_detect(self.pin)
            GPIO.cleanup(self.pin)  # Clean only the specific pin
            print(f"Cleaned up GPIO pin {self.pin}")
        except Exception as e:
            print(f"Error during cleanup of pin {self.pin}: {e}")

# Example usage
if __name__ == "__main__":
    def on_button_press():
        print("Button pressed!")

    # Initialize button handler on GPIO27
    try:
        button = ButtonHandler(27)
        button.set_callback(on_button_press)
    except Exception as e:
        print(f"Failed to initialize button handler: {e}")
        sys.exit(1)

    print("Press the button (Ctrl+C to exit)...")
    try:
        while True:
            if button._use_polling:
                button._check_button_polling()
            time.sleep(0.1)  # Reduce CPU usage in polling mode
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        button.cleanup()