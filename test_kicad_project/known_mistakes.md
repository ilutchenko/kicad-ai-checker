1) R13 resistor must be removed
2) LED D1 should be connected to GND instead of +3.3V of should change connection direction
3) LED D2  should be connected to GND instead of +3.3V of should change connection direction
4) LED D3 should be connected to GND instead of +3.3V of should change connection direction
5) LED D4 should be connected to GND instead of +3.3V of should change connection direction
6) LED D5  should be connected to GND instead of +3.3V of should change connection direction
7) MAX_UART1_TX and MAX_UART2_RX must be swapped
8) BOOT1 pin of STM32 must be tied to the ground
9) R10 must be connected to +3.3V
10) D1 LED has 0402 footprint, but if should be 0603
11) Feedback loop of TPS54531DDAR from R2 and R3 is wrong. R3 must be 1.96k to reach 5V DC/DC output
12) SW3 button does nothing - R8 must be tied to ground instead of +3.3V
13) MCU_I2C1_SCL and MCU_I2C1_SDA are swapped when connected to J1
