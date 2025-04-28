"""
Arduino Control Module
Provides classes and functions for controlling Arduino boards.
"""

from pyfirmata import Arduino, util, OUTPUT, INPUT, PWM

class SerialConnectionError(Exception):
    """Exception raised when there is an error connecting to the Arduino."""
    pass

class ArduinoIO:
    def __init__(self, port, output_pins=None, safe_state=1):
        self.port = port
        self.board = None
        self.it = None
        self._pin_modes = {}
        self.output_pins_configured = []
        
        # Validate and set safe state
        if safe_state not in [0, 1]:
            print("Warning: safe_state must be 0 (LOW) or 1 (HIGH). Defaulting to 1 (HIGH).")
            safe_state = 1
        self.safe_state = safe_state
        
        try:
            # Connect to Arduino
            self.board = Arduino(self.port)
            print(f"Connected to Arduino on {port}")
            
            # Start the Iterator thread for input
            self.it = util.Iterator(self.board)
            self.it.start()
            self.board.pass_time(0.05)  # Give board time to initialize
            
            # Configure output pins if specified
            if output_pins:
                for pin_num in output_pins:
                    try:
                        pin = self.board.digital[pin_num]
                        if pin is not None:
                            pin.mode = OUTPUT
                            self._pin_modes[pin_num] = OUTPUT
                            pin.write(safe_state)
                            self.output_pins_configured.append(pin_num)
                            self.board.pass_time(0.01)
                    except IndexError:
                        print(f"Warning: Invalid pin number {pin_num} for this board.")
                    except Exception as e:
                        print(f"Warning: Could not configure pin {pin_num}: {str(e)}")
        except Exception as e:
            print(f"ERROR: Failed to connect or initialize Arduino: {str(e)}")
            print("Please ensure StandardFirmata is uploaded to your Arduino")
            print("and you have specified the correct port.")
            self.board = None
            self.it = None
            raise SerialConnectionError(str(e))
            
    def _ensure_pin_mode(self, pin_num, mode):
        """Set pin mode if not already set to desired mode."""
        if not self.board:
            print("Error: Not connected to Arduino.")
            return None
            
        try:
            pin = self.board.digital[pin_num]
            current_mode = self._pin_modes.get(pin_num)
            
            if current_mode != mode:
                pin.mode = mode
                self._pin_modes[pin_num] = mode
                self.board.pass_time(0.01)  # Small delay after mode change
                
            return pin
            
        except Exception as e:
            print(f"Error configuring pin {pin_num}: {str(e)}")
            return None
            
    def analog_read(self, pin_num):
        """Read from an analog input pin."""
        if not self.board:
            print("Error: Not connected to Arduino.")
            return None
            
        try:
            pin = self.board.analog[pin_num]
            pin.enable_reporting()
            self.board.pass_time(0.05)  # Give time for first reading
            
            # Sometimes first few readings are None, try a few times
            for _ in range(5):
                value = pin.read()
                if value is not None:
                    return value
                self.board.pass_time(0.05)
                
            print(f"Warning: Could not get reading from analog pin {pin_num} after retries.")
            return None
            
        except IndexError:
            print(f"Error: Invalid analog pin number A{pin_num}.")
            return None
        except Exception as e:
            print(f"Error reading analog pin {pin_num}: {str(e)}")
            return None
            
    def analog_write(self, pin_num, value):
        """Write PWM value to a pin."""
        if not self.board:
            print("Error: Not connected to Arduino.")
            return
            
        if not 0 <= value <= 1:
            print(f"Error: PWM value must be between 0.0 and 1.0, got {value}")
            return
            
        try:
            pin = self._ensure_pin_mode(pin_num, PWM)
            if pin:
                pin.write(value)
                
        except Exception as e:
            print(f"Error writing PWM to pin {pin_num}: {str(e)}")
            
    def digital_read(self, pin_num):
        """Read from a digital input pin."""
        if not self.board:
            return None
            
        try:
            pin = self._ensure_pin_mode(pin_num, INPUT)
            if pin:
                self.board.pass_time(0.02)  # Give time for reading
                return pin.read()
                
        except Exception as e:
            print(f"Error reading digital pin {pin_num}: {str(e)}")
            return None
            
    def digital_write(self, pin_num, value):
        """Write to a digital output pin."""
        if not self.board:
            print("Error: Not connected to Arduino.")
            return None
            
        if value not in [0, 1]:
            print(f"Error: Digital value must be 0 (LOW) or 1 (HIGH), got {value}")
            return None
            
        try:
            pin = self._ensure_pin_mode(pin_num, OUTPUT)
            if pin:
                pin.write(value)
                if pin_num not in self.output_pins_configured:
                    self.output_pins_configured.append(pin_num)
                return value
                
        except Exception as e:
            print(f"Error writing to digital pin {pin_num}: {str(e)}")
            return None
            
    def close(self):
        """Close the connection and clean up."""
        print("Closing Arduino connection...")
        
        if not self.board:
            print("No active Arduino connection to close.")
            return
            
        # Set all configured output pins to safe state
        for pin_num in self.output_pins_configured:
            try:
                pin = self.board.digital[pin_num]  # Get pin directly
                pin.mode = OUTPUT  # Ensure OUTPUT mode
                pin.write(self.safe_state)  # Set safe state
            except Exception as e:
                print(f"Warning: Could not set pin {pin_num} to safe state on close: {str(e)}")
                
        # Close board (this also stops the iterator)
        self.board.exit()
        self.board = None