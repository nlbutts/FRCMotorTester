import struct

def cb0(bus, reason):
    print(f'callback {bus} {reason}')

class SparkMax():
    def __init__(self, can, id, tim, button):
        self.can = can
        self.id = id
        self.tim = tim
        self.button = button
        #can.setfilter(0, can.MASK32, 0, (self.make_filter(0x60), self.make_filter(0x60)), extframe=True)
        #can.setfilter(1, can.MASK32, 0, (self.make_filter(0x61), self.make_filter(0x61)), extframe=True)
        self.prev_button = 1
        self.arm = False
        self.volts = 0
        self.current = 0
        self.motor_output = 0.0
        self.tim.counter(500)

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
        button = self.button.value()
        if not button and self.prev_button:
            self.arm = not self.arm
            if not self.arm:
                self.tim.counter(500)

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

        if self.tim.counter() > 600:
            self.tim.counter(600)
        elif self.tim.counter() < 400:
            self.tim.counter(400)
        self.motor_output = -(self.tim.counter() - 500)
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

