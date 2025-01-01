#!/bin/bash
/opt/SEGGER/JLink/JLinkGDBServerCLExe -select USB=0 -device STM32F446RE -endian little -if SWD -speed 4000 -noir -noLocalhostOnly -nologtofile -port 2331 -SWOPort 2332 -TelnetPort 2333

