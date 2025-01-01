import pyb

c = pyb.CAN(1)

c.init(c.NORMAL, prescaler=2, sjw=1, bs1=14, bs2=6, auto_restart=True)
c.setfilter(0, c.MASK32, 0, (0, 0))
c.recv()