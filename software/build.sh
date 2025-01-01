#!/bin/bash
PATH=/home/nlbutts/arm-gnu-toolchain-13.3.rel1-x86_64-arm-none-eabi/bin:$PATH
BOARD=FRCMOTOR make -C micropython/ports/stm32 -j

