import re
import io
import serial


class UartPacketOut:
    def __init__(self, data, on_send=None):
        self.data = self._get_data(data)
        self._on_send = on_send

    @classmethod
    def cmd(cls, cmd):
        return cls(f'{cmd}\n')

    @classmethod
    def long(cls, data, on_send):
        return cls(f'{data}\n', on_send)

    def notify(self, progress):
        if self._on_send:
            self._on_send(progress)

    def chunked(self, chunk_len, offset):
        total = 0
        i = chunk_len - offset
        while len(self.data) > total:
            yield total, self.data[total:total+i]
            total += i
            i = chunk_len

    @staticmethod
    def _get_data(data):
        return bytes(data, encoding='ascii')
    
    def __len__(self):
        return len(self.data)


class UartPacketIn:
    def __init__(self, data):
        self.data = data

    @property
    def cmd(self):
        return self.data[0]


class Uart:
    def __init__(self, fp):
        self._fp = fp
        self._rx_buffer = b''
        self._tx_queue = []

        self._tx_long_chunks = []
        self._tx_long_packet = None

    @classmethod
    def null(cls):
        return cls(io.StringIO())

    @classmethod
    def open(cls, dev, baud=9600):
        if re.search('[^a-zA-Z0-9/]', dev):
            raise ValueError('device name contains illegal characters')
        
        return cls(serial.Serial(dev, baud, timeout=0))

    def receive(self):
        i = 0
        while True:
            data = self._fp.readline()
            if not data:
                break
            i += 1
            self._rx_buffer += data

        if i == 0:
            return 0

        if not self._rx_buffer.endswith(b'\n'):
            return i

        packet = UartPacketIn(self._rx_buffer)
        self._rx_buffer = b''

        return packet
    
    def _enqueue(self, packet):
        self._tx_queue.append(packet)

    def send_halt(self):
        self._enqueue(UartPacketOut.cmd('H'))

    def send_start(self):
        self._enqueue(UartPacketOut.cmd('Z'))

    def send_step(self):
        self._enqueue(UartPacketOut.cmd('S1'))

    def send_cycle(self):
        self._enqueue(UartPacketOut.cmd('S>'))

    def send_reset(self):
        self._enqueue(UartPacketOut.cmd('R'))

    def send_print(self):
        self._enqueue(UartPacketOut.cmd('P'))

    def send_prog(self, dump, on_send):
        instrs = [instr.upper() for instr in dump]
        stream = ','.join(instrs)
        data = f'[{stream}]'
        self._enqueue(UartPacketOut.long(data, on_send))

    def send(self, max_chunk_len=128):
        if len(self._tx_long_chunks) > 0:
            # only push out part of previous long packet
            offset, data = self._tx_long_chunks.pop(0)
            packet = self._tx_long_packet
            if packet:
                total_sent = offset + len(data)
                packet.notify(total_sent / len(packet))
            
            # send long packets
            out_len = self._fp.write(data)
            self._fp.flush()
            return out_len

        chunk = b''

        # long chunks empty, set no long packet
        self._tx_long_packet = None
        while len(self._tx_queue) > 0:
            # try sending short or long packets
            packet = self._tx_queue.pop(0)
            if len(chunk) + len(packet) > max_chunk_len:
                if len(packet) <= max_chunk_len:
                    # short packet, store for next send
                    self._tx_queue.insert(0, packet)
                packet.notify(0.0)
                offset = len(chunk)
                # store long packet
                chunks = list(packet.chunked(max_chunk_len, offset))
                self._tx_long_packet = packet
                self._tx_long_chunks = chunks
                break
            else:
                chunk += packet.data
                packet.notify(1.0)

        # send short packets
        out_len = self._fp.write(chunk)
        self._fp.flush()
        return out_len

    def close(self):
        self._fp.close()
