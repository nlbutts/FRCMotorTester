from machine import Pin
from pyb import CAN
import pyb
import struct
import time

def debug_can(can, filter=-1):
    while True:
        message = can.recv(0)
        id = message[0]
        devtype = id >> 24
        mfg = (id >> 16) & 0xFF
        cls = (id >> 10) & 0x3F
        idx = (id >> 6) & 0xF
        devid = id & 0x3F
        s = f'DevID: {devid} idx: {idx} cls: {cls} mfg: {mfg} devtype: {devtype} raw: {id:08X} data: '
        for b in message[4]:
            s += f'{b:02X} '
        if filter == -1 or filter == idx:
            print(s)

def drive_motor(can, devid, output):
    while True:
        devtype = 2
        mfg = 5
        cls = 0
        idx = 0
        can_id = devtype << 24 | mfg << 16 | cls << 10 | idx << 6 | devid
        data = struct.pack('<fB', output, 0x01)  # Format the payload
        print(f'{can_id:08X} {data}')
        can.send(data, can_id)  # Send the CAN message
        time.sleep(0.1)

sw = Pin('SW', Pin.IN)
prev = sw.value()

lcd = pyb.LCD('X')

pin_a = Pin('ENC1A', Pin.AF_PP, pull=Pin.PULL_UP, af=Pin.AF1_TIM1)
pin_b = Pin('ENC1B', Pin.AF_PP, pull=Pin.PULL_UP, af=Pin.AF1_TIM1)

pin_c = Pin('ENC2A', Pin.AF_PP, pull=Pin.PULL_UP, af=Pin.AF1_TIM2)
pin_d = Pin('ENC2B', Pin.AF_PP, pull=Pin.PULL_UP, af=Pin.AF1_TIM2)

press1 = Pin('PRESS1', Pin.IN, pull=Pin.PULL_UP)
press2 = Pin('PRESS2', Pin.IN, pull=Pin.PULL_UP)

can_txd = Pin('CAN_TX', Pin.AF_PP, af=Pin.AF9_CAN1)
can_rxd = Pin('CAN_RX', Pin.AF_PP, af=Pin.AF9_CAN1)

can_en = Pin('CAN_EN', Pin.OUT)
can_fault = Pin('CAN_FAULT', Pin.IN)
can_wake = Pin('CAN_WAKE', Pin.OUT)
can_stb = Pin('CAN_STB', Pin.OUT)

can_en.value(1)
can_fault.value(1)
can_wake.value(1)
can_stb.value(1)

# Initialize CAN bus
can = CAN(1, CAN.NORMAL)

# Configure the CAN bus settings
can.init(CAN.NORMAL, prescaler=2, sjw=1, bs1=14, bs2=6, auto_restart=True)
can.setfilter(0, can.MASK32, 0, (0, 0))
can.send('hello', 123)

# The prescaler needs to be 0. When incrementing, the counter will count up-to
# and including the period value, and then reset to 0.
tim1 = pyb.Timer(1, prescaler=0, period=1000)
tim2 = pyb.Timer(2, prescaler=0, period=1000)
# ENC_AB will increment/decrement on the rising edge of either the A channel or the B
# channel.
ch1 = tim1.channel(1, pyb.Timer.ENC_AB)
ch2 = tim2.channel(1, pyb.Timer.ENC_AB)

while True:
    lcd.fill(0)
    lcd.text(f'{tim1.counter()}  /  {tim2.counter()}', 0, 0, 1)
    lcd.text(f'L/R: {press1.value()}/{press2.value()}', 0, 10, 1)
    lcd.show()
    pyb.delay(100)
    # pyb.delay(200)
    # if sw.value() and not prev:
    #     print('Draw')
    #     lcd.pixel(5, 5, 1)
    #     lcd.show()
    prev = sw.value()
