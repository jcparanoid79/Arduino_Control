"""Test suite for ArduinoIO class."""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from pyfirmata import Arduino, util, OUTPUT, INPUT, PWM
from src.arduino_control import ArduinoIO, SerialConnectionError

# Test constants
TEST_PORT = 'COM_TEST'
DEFAULT_PINS = [8, 13]  # Common output pins
INVALID_PIN = 99  # Pin number that doesn't exist

class MockPin:
    """Mock pin that properly tracks mode and other attributes."""
    def __init__(self, pin_num):
        self.pin_number = pin_num
        self._mode = None
        self._value = None
        self.write = MagicMock(side_effect=self._write)
        self.read = MagicMock(return_value=1)  # Default to HIGH for digital
        self.enable_reporting = MagicMock()

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        self._mode = value

    def _write(self, value):
        self._value = value

@pytest.fixture
def mock_board():
    """Create a mock Arduino board with proper pin handling."""
    board = MagicMock()
    pins = {}
    
    def get_digital_pin(pin_num):
        if pin_num == INVALID_PIN:
            raise IndexError(f"Invalid pin {pin_num}")
        if pin_num not in pins:
            pins[pin_num] = MockPin(pin_num)
        return pins[pin_num]
    
    def get_analog_pin(pin_num):
        if pin_num == INVALID_PIN:
            raise IndexError(f"Invalid analog pin A{pin_num}")
        if f'A{pin_num}' not in pins:
            analog_pin = MockPin(pin_num)
            analog_pin.read = MagicMock(return_value=0.5)  # Default to mid-range
            pins[f'A{pin_num}'] = analog_pin
        return pins[f'A{pin_num}']

    board.digital.__getitem__.side_effect = get_digital_pin
    board.analog.__getitem__.side_effect = get_analog_pin
    board._pins = pins  # Store for test access
    return board

@pytest.fixture
def mock_iterator():
    """Create a mock Iterator."""
    iterator = MagicMock()
    iterator.start = MagicMock()
    iterator.is_alive.return_value = True
    return iterator

@pytest.fixture(autouse=True)
def patch_dependencies(mock_board, mock_iterator):
    """Patch Arduino-related dependencies for all tests."""
    with patch('src.arduino_control.Arduino', return_value=mock_board), \
         patch('src.arduino_control.util.Iterator', return_value=mock_iterator):
        yield

class TestArduinoIO:
    """Test suite for ArduinoIO class."""

    def test_init_success(self, mock_board, mock_iterator):
        """Test successful initialization with output pins."""
        arduino = ArduinoIO(port=TEST_PORT, output_pins=DEFAULT_PINS)
        
        assert arduino.board == mock_board
        assert arduino.it == mock_iterator
        mock_iterator.start.assert_called_once()
        
        # Check pin configuration
        for pin in DEFAULT_PINS:
            pin_obj = mock_board.digital[pin]
            assert pin_obj.mode == OUTPUT
            pin_obj.write.assert_called_once_with(arduino.safe_state)
        
        assert sorted(arduino.output_pins_configured) == sorted(DEFAULT_PINS)

    def test_init_connection_error(self):
        """Test initialization when connection fails."""
        with patch('src.arduino_control.Arduino', side_effect=Exception("Connection failed")), \
             pytest.raises(SerialConnectionError):
            ArduinoIO(port=TEST_PORT)

    def test_init_invalid_safe_state(self, mock_board):
        """Test initialization with invalid safe state."""
        arduino = ArduinoIO(port=TEST_PORT, safe_state=5)
        assert arduino.safe_state == 1  # Should default to HIGH

    def test_analog_read_success(self, mock_board):
        """Test successful analog read."""
        arduino = ArduinoIO(port=TEST_PORT)
        expected_value = 0.75
        pin = mock_board.analog[0]
        pin.read = MagicMock(return_value=expected_value)
        
        value = arduino.analog_read(0)
        assert value == expected_value
        pin.enable_reporting.assert_called_once()

    def test_analog_read_retries(self, mock_board):
        """Test analog read with initial None values."""
        arduino = ArduinoIO(port=TEST_PORT)
        expected_value = 0.5
        pin = mock_board.analog[0]
        pin.read = MagicMock(side_effect=[None, None, expected_value])
        
        value = arduino.analog_read(0)
        assert value == expected_value
        assert pin.read.call_count == 3

    def test_analog_write_success(self, mock_board):
        """Test successful PWM write."""
        arduino = ArduinoIO(port=TEST_PORT)
        test_pin = 9
        test_value = 0.75
        
        arduino.analog_write(test_pin, test_value)
        pin = mock_board.digital[test_pin]
        assert pin.mode == PWM
        pin.write.assert_called_once_with(test_value)

    def test_analog_write_invalid_value(self, mock_board):
        """Test PWM write with invalid value."""
        arduino = ArduinoIO(port=TEST_PORT)
        pin = mock_board.digital[9]
        
        arduino.analog_write(9, 1.5)  # Too high
        pin.write.assert_not_called()
        
        arduino.analog_write(9, -0.1)  # Too low
        pin.write.assert_not_called()

    def test_digital_read_success(self, mock_board):
        """Test successful digital read."""
        arduino = ArduinoIO(port=TEST_PORT)
        pin_num = 2
        expected_value = 1
        pin = mock_board.digital[pin_num]
        pin.read = MagicMock(return_value=expected_value)
        
        value = arduino.digital_read(pin_num)
        assert value == expected_value
        assert pin.mode == INPUT

    def test_digital_write_success(self, mock_board):
        """Test successful digital write."""
        arduino = ArduinoIO(port=TEST_PORT)
        pin_num = 7
        
        # Write HIGH
        result = arduino.digital_write(pin_num, 1)
        pin = mock_board.digital[pin_num]
        assert pin.mode == OUTPUT
        pin.write.assert_called_with(1)
        assert result == 1
        assert pin_num in arduino.output_pins_configured

        # Write LOW
        result = arduino.digital_write(pin_num, 0)
        assert result == 0
        pin.write.assert_called_with(0)

    def test_digital_write_invalid_value(self, mock_board):
        """Test digital write with invalid value."""
        arduino = ArduinoIO(port=TEST_PORT)
        pin = mock_board.digital[7]
        
        result = arduino.digital_write(7, 2)  # Invalid value
        assert result is None
        pin.write.assert_not_called()

    def test_ensure_pin_mode(self, mock_board):
        """Test internal pin mode management."""
        arduino = ArduinoIO(port=TEST_PORT)
        pin_num = 5
        
        # First set to OUTPUT
        pin = arduino._ensure_pin_mode(pin_num, OUTPUT)
        assert pin.mode == OUTPUT
        assert arduino._pin_modes[pin_num] == OUTPUT
        
        # Set to same mode - should not trigger mode change
        mock_board.pass_time.reset_mock()
        arduino._ensure_pin_mode(pin_num, OUTPUT)
        mock_board.pass_time.assert_not_called()
        
        # Change to INPUT
        pin = arduino._ensure_pin_mode(pin_num, INPUT)
        assert pin.mode == INPUT
        assert arduino._pin_modes[pin_num] == INPUT

    def test_close(self, mock_board):
        """Test closing the connection."""
        arduino = ArduinoIO(port=TEST_PORT, output_pins=DEFAULT_PINS)
        arduino.digital_write(7, 1)  # Add another output pin
        
        arduino.close()
        
        # Check all output pins were set to safe state
        for pin_num in DEFAULT_PINS + [7]:
            pin = mock_board.digital[pin_num]
            pin.write.assert_called_with(arduino.safe_state)
        
        mock_board.exit.assert_called_once()
        assert arduino.board is None

    def test_close_no_board(self):
        """Test close when no board is connected."""
        arduino = ArduinoIO(port=TEST_PORT)
        arduino.board = None
        arduino.close()  # Should not raise any errors

    def test_init_multiple_pin_failures(self, mock_board, capsys):
        """Test initialization when multiple pins fail to configure."""
        def pin_error(pin_num):
            pin = MockPin(pin_num)
            if pin_num in [8, 13]:
                pin.write.side_effect = Exception(f"Error on pin {pin_num}")
            return pin
        
        mock_board.digital.__getitem__.side_effect = pin_error
        
        arduino = ArduinoIO(port=TEST_PORT, output_pins=[8, 13])
        
        captured = capsys.readouterr()
        assert "Warning: Could not configure pin 8:" in captured.out
        assert "Warning: Could not configure pin 13:" in captured.out
        assert not arduino.output_pins_configured  # No pins should be configured

    def test_analog_read_invalid_pin(self, mock_board, capsys):
        """Test analog read with invalid pin number."""
        arduino = ArduinoIO(port=TEST_PORT)
        
        # Test invalid pin
        value = arduino.analog_read(INVALID_PIN)
        assert value is None
        captured = capsys.readouterr()
        assert f"Error: Invalid analog pin number A{INVALID_PIN}" in captured.out

    def test_analog_read_enable_reporting_failure(self, mock_board, capsys):
        """Test analog read when enable_reporting fails."""
        arduino = ArduinoIO(port=TEST_PORT)
        pin = mock_board.analog[0]
        pin.enable_reporting.side_effect = Exception("Failed to enable reporting")
        
        value = arduino.analog_read(0)
        assert value is None
        captured = capsys.readouterr()
        assert "Error reading analog pin" in captured.out
        assert "Failed to enable reporting" in captured.out

    def test_analog_read_persistent_none(self, mock_board, capsys):
        """Test analog read when values are persistently None."""
        arduino = ArduinoIO(port=TEST_PORT)
        pin = mock_board.analog[0]
        pin.read = MagicMock(return_value=None)  # Always return None
        
        value = arduino.analog_read(0)
        assert value is None
        captured = capsys.readouterr()
        assert "Warning: Could not get reading from analog pin 0 after retries" in captured.out
        assert pin.read.call_count >= 5  # Should try at least 5 times

    def test_ensure_pin_mode_error(self, mock_board, capsys):
        """Test error handling in _ensure_pin_mode."""
        arduino = ArduinoIO(port=TEST_PORT)
        pin_num = 5

        # Create a pin class that raises an error when mode is set
        class ErrorMockPin(MockPin):
            @property
            def mode(self):
                return None

            @mode.setter
            def mode(self, value):
                raise Exception("Mode set failed")

        # Use the error pin
        error_pin = ErrorMockPin(pin_num)
        mock_board.digital.__getitem__ = MagicMock(return_value=error_pin)
        
        result = arduino._ensure_pin_mode(pin_num, OUTPUT)
        assert result is None
        captured = capsys.readouterr()
        assert f"Error configuring pin {pin_num}: Mode set failed" in captured.out

    def test_board_timing_issues(self, mock_board, capsys):
        """Test handling of board timing issues."""
        arduino = ArduinoIO(port=TEST_PORT)
        mock_board.pass_time.side_effect = Exception("Timing error")
        
        # Try digital read which uses pass_time
        value = arduino.digital_read(2)
        assert value is None
        captured = capsys.readouterr()
        assert f"Error configuring pin 2: Timing error" in captured.out

    def test_write_failures(self, mock_board, capsys):
        """Test handling of write failures."""
        arduino = ArduinoIO(port=TEST_PORT)
        pin_num = 7
        pin = MockPin(pin_num)
        pin.write = MagicMock(side_effect=Exception("Write failed"))
        mock_board.digital.__getitem__ = MagicMock(return_value=pin)
        
        # Test digital write
        result = arduino.digital_write(pin_num, 1)
        assert result is None
        captured = capsys.readouterr()
        assert "Error writing to digital pin 7: Write failed" in captured.out
        
        # Clear captured output and test analog write
        pin.mode = PWM
        arduino._pin_modes[pin_num] = PWM
        arduino.analog_write(pin_num, 0.5)
        captured = capsys.readouterr()
        assert "Error writing PWM to pin 7: Write failed" in captured.out

    def test_close_with_mixed_failures(self, mock_board, capsys):
        """Test close when some pins fail but others succeed."""
        # Create pins with specific behaviors
        pin8 = MockPin(8)
        pin13 = MockPin(13)
        pin13.write = MagicMock(side_effect=Exception("Close error"))
        
        pins = {8: pin8, 13: pin13}
        def get_pin(pin_num):
            return pins[pin_num]
        mock_board.digital.__getitem__.side_effect = get_pin
        
        # Initialize Arduino with both pins
        arduino = ArduinoIO(port=TEST_PORT)
        arduino.output_pins_configured = [8, 13]  # Add pins to configured list
        
        arduino.close()
        
        captured = capsys.readouterr()
        assert "Warning: Could not set pin 13 to safe state on close: Close error" in captured.out
        assert pin8.write.called  # Should have tried to write to pin 8
        mock_board.exit.assert_called_once()

    def test_analog_write_pin_type_error(self, mock_board, capsys):
        """Test analog write to non-PWM pin."""
        arduino = ArduinoIO(port=TEST_PORT)
        pin_num = 7
        pin = MockPin(pin_num)
        pin.write = MagicMock(side_effect=TypeError("Pin does not support PWM"))
        mock_board.digital.__getitem__ = MagicMock(return_value=pin)
        
        arduino.analog_write(pin_num, 0.5)
        captured = capsys.readouterr()
        assert f"Error writing PWM to pin {pin_num}: Pin does not support PWM" in captured.out
