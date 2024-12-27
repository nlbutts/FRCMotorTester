from machine import Pin
from pyb import CAN
import pyb
import time
import sys
import struct

VERSION = 0.6

class SparkMax():
    def __init__(self, can, id, enc):
        self.can = can
        self.id = id
        self.enc = enc
        self.prev_button = 1
        self.arm = False
        self.volts = 0
        self.current = 0
        self.motor_output = 0.0
        self.enc.set_counter(0)

    def make_filter(self, class_idx):
        """Make a message filter

        Args:
            class_idx (int): combination of the API class and index
        """
        devtype = 2
        mfg = 5
        can_id = devtype << 24 | mfg << 16 | class_idx << 6 | self.id
        return can_id

    def process_button(self):
        button = self.enc.get_press()
        if not button and self.prev_button:
            self.arm = not self.arm
            if not self.arm:
                self.enc.set_counter(0)

        self.prev_button = button

    def process(self, msg):
        self.process_button()

        can_id = msg[0]
        dev = can_id & 0x3F
        api = (can_id >> 6) & 0x3FF
        if dev == self.id:
            if api == 0x61:
                data = msg[4]
                volts = ((data[6] & 0x0F) << 8) | data[5]
                self.volts = volts / 128.0
                current = data[7] << 4 | (data[6] >> 4) & 0xF
                self.current = current / 20

        if self.enc.get_counter() > 100:
            self.enc.set_counter(100)
        elif self.enc.get_counter() < -100:
            self.enc.set_counter(-100)
        self.motor_output = -(self.enc.get_counter())
        self.motor_output /= 100
        self.drive_motor(self.motor_output)

    def get_arm_str(self):
        if self.arm:
            return 'ARMD'
        return 'SAFE'

    def get_info(self):
        info = {}
        info['id'] = self.id
        info['arm'] = self.get_arm_str()
        info['volt'] = self.volts
        info['current'] = self.current
        info['output'] = self.motor_output
        return info

    def drive_motor(self, output):
        """
        Driving motor 2 uses this message: DevID: 0 idx: 2 cls: 11 mfg: 5 devtype: 2 raw: 02052C80 data: 04 00 00 00 00 00 00 00
        At -0.12 DevID: 2 idx: 2 cls: 0 mfg: 5 devtype: 2 raw: 02050082 data: 8F C2 F5 BD 00 00 00 00
        Driving motor 4 uses this message: DevID: 0 idx: 2 cls: 11 mfg: 5 devtype: 2 raw: 02052C80 data: 10 00 00 00 00 00 00 00
        """
        if self.arm:
            devtype = 2
            mfg = 5
            cls = 0
            idx = 2
            can_id = devtype << 24 | mfg << 16 | cls << 10 | idx << 6 | self.id
            data = struct.pack('<fBBBB', output, 0, 0, 0, 0)  # Format the payload
            self.can.send(data, can_id, extframe=True)  # Send the CAN message

    def debug_can(self, message):
        """Debug the can message

        Args:
            message (_type_): _description_
        """
        id = message[0]
        devtype = id >> 24
        mfg = (id >> 16) & 0xFF
        cls = (id >> 10) & 0x3F
        idx = (id >> 6) & 0xF
        devid = id & 0x3F
        s = f'DevID: {devid} idx: {idx} cls: {cls} mfg: {mfg} devtype: {devtype} raw: {id:08X} data: '
        for b in message[4]:
            s += f'{b:02X} '
        print(s)

def get_spark_max_ids(can):
    try:
        ids = {}
        start = time.time()
        while time.time() - start < 1:
            m = can.recv(0)
            id = m[0] & 0x3F
            if id > 0:
                ids[id] = 1
        print(ids)
        return list(ids.keys())
    except:
        return []

class Encoder():
    def __init__(self, enc_name):
        if 'Left' in enc_name:
            self.pin_a = Pin('ENC2A', Pin.AF_PP, pull=Pin.PULL_UP, af=Pin.AF1_TIM2)
            self.pin_b = Pin('ENC2B', Pin.AF_PP, pull=Pin.PULL_UP, af=Pin.AF1_TIM2)
            self.press = Pin('PRESS2', Pin.IN, pull=Pin.PULL_UP)
            self.tim = pyb.Timer(2, prescaler=0, period=100)
            self.ch = self.tim.channel(1, pyb.Timer.ENC_AB)
        elif 'Right' in enc_name:
            self.pin_a = Pin('ENC1A', Pin.AF_PP, pull=Pin.PULL_UP, af=Pin.AF1_TIM1)
            self.pin_b = Pin('ENC1B', Pin.AF_PP, pull=Pin.PULL_UP, af=Pin.AF1_TIM1)
            self.press = Pin('PRESS1', Pin.IN, pull=Pin.PULL_UP)
            self.tim = pyb.Timer(1, prescaler=0, period=100)
            self.ch = self.tim.channel(1, pyb.Timer.ENC_AB)

    def get_press(self):
        return self.press.value()

    def get_counter(self):
        return self.tim.counter() - 500

    def set_counter(self, value):
        self.tim.counter(500 + value)

sw = Pin('SW', Pin.IN)
prev = sw.value()

lcd = pyb.LCD('X')

# pin_a = Pin('ENC1A', Pin.AF_PP, pull=Pin.PULL_UP, af=Pin.AF1_TIM1)
# pin_b = Pin('ENC1B', Pin.AF_PP, pull=Pin.PULL_UP, af=Pin.AF1_TIM1)

#pin_c = Pin('ENC2A', Pin.AF_PP, pull=Pin.PULL_UP, af=Pin.AF1_TIM2)
#pin_d = Pin('ENC2B', Pin.AF_PP, pull=Pin.PULL_UP, af=Pin.AF1_TIM2)

#press1 = Pin('PRESS1', Pin.IN, pull=Pin.PULL_UP)
#press2 = Pin('PRESS2', Pin.IN, pull=Pin.PULL_UP)

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

leftEnc = Encoder('Left')
rightEnc = Encoder('Right')

def show_boot_screen(can_ids=[]):
    lcd.fill(0)
    lcd.text(f'Brushless Buddy', 0, 0, 1)
    lcd.text(f'Ver: {VERSION}', 0, 10, 1)
    if len(can_ids) > 0:
        s = 'Found: '
        for id in can_ids:
            s += f'{id} '
        lcd.text(s, 0, 20, 1)
    else:
        lcd.text(f'Found: None', 0, 20, 1)
    lcd.show()

show_boot_screen()
ids = sorted(get_spark_max_ids(can))
print(f'Found ids: {ids}')

if len(ids) > 2:
    lcd.fill(0)
    lcd.text('Too many CAN', 0, 0, 1)
    lcd.text('nodes on bus', 0, 10, 1)
    lcd.show()
    time.sleep(5)
    sys.reset()
if len(ids) == 0:
    lcd.fill(0)
    lcd.text('No SparkMaxs', 0, 0, 1)
    lcd.text('detected', 0, 10, 1)
    lcd.text('rebooting', 0, 20, 1)
    lcd.show()
    time.sleep(5)
    machine.reset()

motors = []
if len(ids) == 1:
    motors.append(SparkMax(can, ids[0], leftEnc))
elif len(ids) == 2:
    motors.append(SparkMax(can, ids[0], leftEnc))
    motors.append(SparkMax(can, ids[1], rightEnc))

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

            str = f'{motor_info[0]['output']:5.2f}  | {motor_info[1]['output']:5.2f}'
            lcd.text(str, 0, 10, 1)

            str = f'{motor_info[0]['volt']:.1f}V/ {motor_info[0]['current']:2.1f} / {motor_info[1]['current']:2.1f}'
            lcd.text(str, 0, 20, 1)
        lcd.show()
