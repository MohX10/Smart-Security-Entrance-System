from machine import Pin, SPI
from os import uname

class MFRC522:
    DEBUG = False
    HALTED = 0x00
    OK = 0x01
    NOTAGERR = 0x02
    ERR = 0x03
    REQIDL = 0x26
    REQALL = 0x52
    AUTHENT1A = 0x60
    AUTHENT1B = 0x61

    def __init__(self, spi_id, sck, miso, mosi, cs, rst):
        self.sck = Pin(sck, Pin.OUT)
        self.miso = Pin(miso, Pin.IN)
        self.mosi = Pin(mosi, Pin.OUT)
        self.cs = Pin(cs, Pin.OUT)
        self.rst = Pin(rst, Pin.OUT)
        self.spi = SPI(spi_id, baudrate=1000000, polarity=0, phase=0, sck=self.sck, mosi=self.mosi, miso=self.miso)
        self.init()

    def _wreg(self, reg, val):
        self.cs.value(0)
        self.spi.write(bytearray([reg << 1 & 0x7E, val]))
        self.cs.value(1)

    def _rreg(self, reg):
        self.cs.value(0)
        self.spi.write(bytearray([reg << 1 & 0x7E | 0x80]))
        val = self.spi.read(1)[0]
        self.cs.value(1)
        return val

    def init(self):
        self.rst.value(0)
        time.sleep_ms(5)
        self.rst.value(1)
        time.sleep_ms(5)
        self._wreg(0x01, 0x0F) # SoftReset
        time.sleep_ms(5)
        self._wreg(0x2A, 0x8D) # TMode
        self._wreg(0x2B, 0x3E) # TPrescaler
        self._wreg(0x2D, 30)   # TReloadValueL
        self._wreg(0x2C, 0)    # TReloadValueH
        self._wreg(0x15, 0x40) # TxASK
        self._wreg(0x11, 0x3D) # Mode
        self.antenna_on()

    def antenna_on(self):
        if not (self._rreg(0x14) & 0x03):
            self._wreg(0x14, self._rreg(0x14) | 0x03)

    def request(self, mode):
        self._wreg(0x0D, 0x07) # BitFramingReg
        (stat, recv, bits) = self._tcom(0x0C, [mode]) # Transceive
        if (stat != self.OK) or (bits != 0x10):
            stat = self.NOTAGERR
        return stat, bits

    def _tcom(self, cmd, send):
        recv = []
        bits = 0
        irq_en = 0x77
        wait_irq = 0x30
        self._wreg(0x02, irq_en | 0x80)
        self._wreg(0x04, 0x7F)
        self._wreg(0x01, 0x00) # Idle
        self._wreg(0x0A, 0x80) # FIFOLevelReg
        for i in range(len(send)):
            self._wreg(0x09, send[i])
        self._wreg(0x01, cmd)
        if cmd == 0x0C:
            self._wreg(0x0D, self._rreg(0x0D) | 0x80)
        i = 2000
        while True:
            n = self._rreg(0x04)
            i -= 1
            if ~((i != 0) and ~(n & 0x01) and ~(n & wait_irq)):
                break
        self._wreg(0x0D, self._rreg(0x0D) & 0x7F)
        if i != 0:
            if (self._rreg(0x06) & 0x1B) == 0x00:
                stat = self.OK
                if n & irq_en & 0x01:
                    stat = self.NOTAGERR
                elif cmd == 0x0C:
                    n = self._rreg(0x0A)
                    last_bits = self._rreg(0x0C) & 0x07
                    if last_bits != 0:
                        bits = (n - 1) * 8 + last_bits
                    else:
                        bits = n * 8
                    if n == 0: n = 1
                    if n > 16: n = 16
                    for i in range(n):
                        recv.append(self._rreg(0x09))
            else:
                stat = self.ERR
        else:
            stat = self.ERR
        return stat, recv, bits

    def SelectTagSN(self):
        valid_bits = 0
        self._wreg(0x0D, 0x00) # BitFramingReg
        sn = [0x93, 0x20]
        (stat, recv, bits) = self._tcom(0x0C, sn)
        if stat == self.OK:
            if len(recv) == 5:
                for i in range(5):
                    sn.append(recv[i])
            else:
                stat = self.ERR
        return stat, recv

import time