#!/bin/bash
PATH=/home/nlbutts/arm-gnu-toolchain-13.3.rel1-x86_64-arm-none-eabi/bin:$PATH
arm-none-eabi-gdb -tui --command=gdbinit  micropython/ports/stm32/build-FRCMOTOR/firmware.elf
