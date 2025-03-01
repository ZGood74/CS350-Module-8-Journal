## Thermostat.py - Corrected and Completed
## This script implements a functional smart thermostat prototype
## for the CS 350 final project, following all requirements.

from time import sleep
from datetime import datetime
from statemachine import StateMachine, State
import board
import adafruit_ahtx0
import digitalio
import adafruit_character_lcd.character_lcd as characterlcd
import serial
from gpiozero import Button, PWMLED
from threading import Thread
from math import floor

DEBUG = True

# Initialize I2C and Temperature Sensor
i2c = board.I2C()
thSensor = adafruit_ahtx0.AHTx0(i2c)

# Initialize Serial Communication
ser = serial.Serial(
    port='/dev/ttyS0', 
    baudrate=115200, 
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
)

# Initialize LED Indicators
redLight = PWMLED(18)
blueLight = PWMLED(23)

class ManagedDisplay():
    """Handles the 16x2 LCD Display"""
    def __init__(self):
        self.lcd_rs = digitalio.DigitalInOut(board.D17)
        self.lcd_en = digitalio.DigitalInOut(board.D27)
        self.lcd_d4 = digitalio.DigitalInOut(board.D5)
        self.lcd_d5 = digitalio.DigitalInOut(board.D6)
        self.lcd_d6 = digitalio.DigitalInOut(board.D13)
        self.lcd_d7 = digitalio.DigitalInOut(board.D26)
        self.lcd_columns = 16
        self.lcd_rows = 2
        self.lcd = characterlcd.Character_LCD_Mono(
            self.lcd_rs, self.lcd_en, self.lcd_d4, self.lcd_d5,
            self.lcd_d6, self.lcd_d7, self.lcd_columns, self.lcd_rows
        )
        self.lcd.clear()
    
    def updateScreen(self, message):
        self.lcd.clear()
        self.lcd.message = message

screen = ManagedDisplay()

class TemperatureMachine(StateMachine):
    """State machine to manage thermostat operation"""
    off = State(initial=True)
    heat = State()
    cool = State()
    setPoint = 72

    cycle = off.to(heat) | heat.to(cool) | cool.to(off)

    def on_enter_heat(self):
        redLight.pulse()
        if DEBUG: print("* Changing state to HEAT")

    def on_exit_heat(self):
        redLight.off()
    
    def on_enter_cool(self):
        blueLight.pulse()
        if DEBUG: print("* Changing state to COOL")

    def on_exit_cool(self):
        blueLight.off()
    
    def on_enter_off(self):
        redLight.off()
        blueLight.off()
        if DEBUG: print("* Changing state to OFF")

    def processTempStateButton(self):
        if DEBUG: print("Cycling Temperature State")
        self.cycle()
        self.updateLights()
    
    def processTempIncButton(self):
        if DEBUG: print("Increasing Set Point")
        self.setPoint += 1
        self.updateLights()
    
    def processTempDecButton(self):
        if DEBUG: print("Decreasing Set Point")
        self.setPoint -= 1
        self.updateLights()
    
    def updateLights(self):
        temp = floor(self.getFahrenheit())
        redLight.off()
        blueLight.off()
        if DEBUG:
            print(f"State: {self.current_state.id}")
            print(f"SetPoint: {self.setPoint}")
            print(f"Temp: {temp}")
        if self.heat.is_active and temp < self.setPoint:
            redLight.pulse()
        elif self.heat.is_active:
            redLight.on()
        if self.cool.is_active and temp > self.setPoint:
            blueLight.pulse()
        elif self.cool.is_active:
            blueLight.on()
    
    def getFahrenheit(self):
        return (((9/5) * thSensor.temperature) + 32)
    
    def setupSerialOutput(self):
        return f"{self.current_state.id},{floor(self.getFahrenheit())},{self.setPoint}"
    
    def run(self):
        myThread = Thread(target=self.manageMyDisplay)
        myThread.start()
    
    endDisplay = False
    def manageMyDisplay(self):
        counter = 1
        altCounter = 1
        while not self.endDisplay:
            current_time = datetime.now()
            lcd_line_1 = current_time.strftime('%m/%d %H:%M')
            if altCounter < 6:
                lcd_line_2 = f"Temp: {floor(self.getFahrenheit())}F"
            else:
                lcd_line_2 = f"{self.current_state.id.upper()} {self.setPoint}F"
                if altCounter >= 11:
                    self.updateLights()
                    altCounter = 1
            screen.updateScreen(lcd_line_1 + "\n" + lcd_line_2)
            if counter % 30 == 0:
                ser.write(self.setupSerialOutput().encode('utf-8'))
                counter = 1
            else:
                counter += 1
            sleep(1)
        screen.lcd.clear()

tsm = TemperatureMachine()
tsm.run()

greenButton = Button(24)
greenButton.when_pressed = tsm.processTempStateButton

redButton = Button(25)
redButton.when_pressed = tsm.processTempIncButton

blueButton = Button(12)
blueButton.when_pressed = tsm.processTempDecButton

repeat = True
while repeat:
    try:
        sleep(30)
    except KeyboardInterrupt:
        print("Cleaning up. Exiting...")
        repeat = False
        tsm.endDisplay = True
        sleep(1)

