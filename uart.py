import re
import io
import serial

from data import Page


_rx_buffer = b''


def next_page(ndx, fp):
    global _rx_buffer

    i = 0
    while True:
        data = fp.readline()
        if not data:
            break
        i += 1
        _rx_buffer += data

    if i == 0:
        return 'none', None

    if not _rx_buffer.endswith(b'\n'):
        return 'recv', None

    state = 'init'
    pc = 'N/A'
    regs = ''
    for char in _rx_buffer:
        if chr(char) == 'P':
            if state != 'init':
                raise ValueError('pc field out of bounds')
            state = 'p_sym'
        # if char == 'R':
        #     if state != 'p_val':
        #         raise ValueError('regs field out of bounds')
        #     state = 'r_sym'
        # if state == 'p_val':
        #     pc += char
        if state == 'p_val':
            regs += chr(char)
        if state == 'p_sym':
            state = 'p_val'
        if state == 'r_sym':
            state = 'r_val'
    
    _rx_buffer = b''

    return 'emit', Page(ndx + 1, pc, regs)


def null_uart():
    return io.StringIO()


def open_uart(dev, baud=9600):
    if not dev:
        return null_uart()

    if re.search('[^a-zA-Z0-9/]', dev):
        raise ValueError('device name contains illegal characters')
    
    return serial.Serial(dev, baud, timeout=0)
