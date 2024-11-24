from machine import Pin
from pyb import CAN
from sparkmax import SparkMax
import pyb
import time
import sys
import struct

VERSION = 0.5

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
        if filter == -1 or filter == devid:
            print(s)

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
can.setfilter(0, can.MASK32, 0, (0, 0), extframe=True)
can.send('hello', 0, extframe=True)

# The prescaler needs to be 0. When incrementing, the counter will count up-to
# and including the period value, and then reset to 0.
tim1 = pyb.Timer(1, prescaler=0, period=100)
tim2 = pyb.Timer(2, prescaler=0, period=100)
# ENC_AB will increment/decrement on the rising edge of either the A channel or the B
# channel.
ch1 = tim1.channel(1, pyb.Timer.ENC_AB)
ch2 = tim2.channel(1, pyb.Timer.ENC_AB)

def get_spark_max_ids(can):
    ids = {}
    start = time.time()
    while time.time() - start < 1:
        m = can.recv(0)
        id = m[0] & 0x3F
        if id > 0:
            ids[id] = 1
    print(ids)
    return list(ids.keys())

def show_boot_screen(can_ids=[]):
    lcd.fill(0)
    lcd.text(f'Brushless Buddy', 0, 0, 1)
    lcd.text(f'{VERSION}', 0, 10, 1)
    if len(can_ids) > 0:
        s = 'Found: '
        for id in can_ids:
            s += f'{id} '
        lcd.text(s, 0, 20, 1)
    else:
        lcd.text(f'Found: None', 0, 20, 1)
    lcd.show()

show_boot_screen()
found = False
while not found:
    ids = get_spark_max_ids(can)
    if len(ids) > 0:
        found = True

ids = sorted(ids)
print(f'Found ids: {ids}')

if len(ids) > 2:
    lcd.fill(0)
    lcd.text('Too many CAN', 0, 0, 1)
    lcd.text('nodes on bus', 0, 10, 1)
    lcd.show()
    time.sleep(5)
    sys.reset()

motors = []
if len(ids) == 1:
    motors.append(SparkMax(can, ids[0], tim1, press1))
elif len(ids) == 2:
    motors.append(SparkMax(can, ids[0], tim1, press1))
    motors.append(SparkMax(can, ids[1], tim2, press2))

#debug_can(can, 0)

start = time.time()
while True:
    msg = can.recv(0)
    motor_info = []
    arm_field = 0
    for motor in motors:
        motor.process(msg)        
        motor_info.append(motor.get_info())
        if motor.arm:
            arm_field |= 1 << motor.id

    # Send the heartbeat message
    can_id = 0x02052C80
    data = struct.pack('<II', arm_field, 0)
    can.send(data, can_id, extframe=True, timeout=100)

    if time.time() - start > 0.1:
        start = time.time()
        lcd.fill(0)
        if len(motor_info) == 1:
            lcd.text(f'{motor_info[0]['id']}/{motor_info[0]['arm']}', 0, 0, 1)
            lcd.text(f'{motor_info[0]['output']}', 0, 10, 1)
            lcd.text(f'{motor_info[0]['volt']:.1f}/{motor_info[0]['current']}', 0, 20, 1)
        else:
            str = f'{motor_info[0]['id']}/{motor_info[0]['arm']} | {motor_info[1]['arm']}/{motor_info[1]['id']}'
            lcd.text(str, 0, 0, 1)

            str = f'{motor_info[0]['output']:4.2f}   | {motor_info[1]['output']:4.2f}'
            lcd.text(str, 0, 10, 1)

            str = f'{motor_info[0]['volt']:.1f} / {motor_info[0]['current']:2.1f} / {motor_info[1]['current']:2.1f}'
            lcd.text(str, 0, 20, 1)
        lcd.show()
