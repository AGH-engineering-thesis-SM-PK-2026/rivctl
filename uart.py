import re
import io
import serial


_rx_buffer = b''
_tx_buffer = b''


def uart_recv(fp):
    global _rx_buffer

    i = 0
    while True:
        data = fp.readline()
        if not data:
            break
        i += 1
        _rx_buffer += data

    if i == 0:
        return 'none', 0

    if not _rx_buffer.endswith(b'\n'):
        return 'none', i

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

    return 'page', (pc, regs)


def send_halt():
    global _tx_buffer
    _tx_buffer += b'H\n'


def send_start():
    global _tx_buffer
    _tx_buffer += b'Z\n'


def send_step():
    global _tx_buffer
    _tx_buffer += b'S1\n'


def send_cycle():
    global _tx_buffer
    _tx_buffer += b'S>\n'


def send_reset():
    global _tx_buffer
    _tx_buffer += b'R\n'


def send_prog(dump):
    global _tx_buffer
    instrs = [instr.upper() for instr in dump]
    stream = ','.join(instrs)
    cmd = f'[{stream}]\n'
    _tx_buffer += bytes(cmd, encoding='ascii')


def uart_emit(fp, max_chunk_len=128):
    global _tx_buffer
    chunk, tail = _tx_buffer[:max_chunk_len], _tx_buffer[max_chunk_len:]
    _tx_buffer = tail
    if chunk:
        out_len = fp.write(chunk)
        fp.flush()
        return out_len
    
    return 0


def null_uart():
    return io.StringIO()


def open_uart(dev, baud=9600):
    if not dev:
        return null_uart()

    if re.search('[^a-zA-Z0-9/]', dev):
        raise ValueError('device name contains illegal characters')
    
    return serial.Serial(dev, baud, timeout=0)
