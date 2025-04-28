"""
Arduino Control Package
A Python package for controlling Arduino boards.
"""

__version__ = '0.1.0'

from .arduino_control import (
    ArduinoIO,
    SerialConnectionError
)

__all__ = [
    'ArduinoIO',
    'SerialConnectionError'
]
