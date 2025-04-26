# Arduino Control Python Interface

A Python interface for controlling Arduino boards using PyFirmata protocol. This project provides a robust and safe way to interact with Arduino boards from Python applications.

## Features

- Easy-to-use wrapper for PyFirmata
- Safe pin state management
- Support for digital and analog I/O
- PWM output support
- Automatic pin configuration
- Error handling and safety features

## Installation

1. Install the required Python packages:
```bash
pip install -r requirements.txt
```

2. Upload StandardFirmata to your Arduino board:
   - Open Arduino IDE
   - File > Examples > Firmata > StandardFirmata
   - Upload to your board

## Usage

Basic example:
```python
from arduino_control import ArduinoIO

# Initialize with your Arduino's port
arduino = ArduinoIO(port='COM4', output_pins=[13, 8])

# Read analog value
analog_value = arduino.analog_read(0)

# Write digital output
arduino.digital_write(13, 1)  # Turn on LED

# Clean up
arduino.close()
```

## Project Structure

- `src/arduino_control/` - Main source code
- `examples/` - Example scripts
- `tests/` - Test files
- `docs/` - Documentation
- `requirements/` - Project dependencies

## Contributing

### Installation

To install the package, run:

```
pip install .
```

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
