#
# Milestone3.py - This is the Python code template used to
# setup the structure for Milestone 3. In this milestone, you need
# to demonstrate the capability to productively display a message
# in Morse code utilizing the Red and Blue LEDs. The message should
# change between SOS and OK when the button is pressed using a state
# machine.
#
# This code works with the test circuit that was built for module 5.
#
#------------------------------------------------------------------
# Change History
#------------------------------------------------------------------
# Version   |   Description
#------------------------------------------------------------------
#    1          Initial Development
#------------------------------------------------------------------

from gpiozero import Button, LED
from statemachine import StateMachine, State
from time import sleep
import board
import digitalio
import adafruit_character_lcd.character_lcd as characterlcd
from threading import Thread

DEBUG = True

class ManagedDisplay():
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

    def cleanupDisplay(self):
        self.lcd.clear()
        self.lcd_rs.deinit()
        self.lcd_en.deinit()
        self.lcd_d4.deinit()
        self.lcd_d5.deinit()
        self.lcd_d6.deinit()
        self.lcd_d7.deinit()

    def clear(self):
        self.lcd.clear()

    def updateScreen(self, message):
        self.lcd.clear()
        self.lcd.message = message

class CWMachine(StateMachine):
    redLight = LED(18)
    blueLight = LED(23)

    def __init__(self):
        super().__init__()
        self.message1 = 'SOS'
        self.message2 = 'OK'
        self.activeMessage = self.message1
        self.endTransmission = False
        self.screen = ManagedDisplay()
        self.morseDict = {
            "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
            "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
            "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
            "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
            "Y": "-.--", "Z": "--..", "0": "-----", "1": ".----", "2": "..---", "3": "...--",
            "4": "....-", "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----."
        }

    off = State(initial=True)
    dot = State()
    dash = State()
    dotDashPause = State()
    letterPause = State()
    wordPause = State()

    doDot = (off.to(dot) | dot.to(off))
    doDash = (off.to(dash) | dash.to(off))
    doDDP = (off.to(dotDashPause) | dotDashPause.to(off))
    doLP = (off.to(letterPause) | letterPause.to(off))
    doWP = (off.to(wordPause) | wordPause.to(off))

    def on_enter_dot(self):
        self.redLight.on()
        sleep(0.5)
        self.redLight.off()
        if(DEBUG): print("* Changing state to red - dot")
        self.doDot()  # Transition back to 'off'

    def on_exit_dot(self):
        self.redLight.off()

    def on_enter_dash(self):
        self.blueLight.on()
        sleep(1.5)
        self.blueLight.off()
        if(DEBUG): print("* Changing state to blue - dash")
        self.doDash()  # Transition back to 'off'

    def on_exit_dash(self):
        self.blueLight.off()

    def on_enter_dotDashPause(self):
        sleep(0.25)
        if(DEBUG): print("* Pausing Between Dots/Dashes - 250ms")
        self.doDDP()  # Transition back to 'off'

    def on_enter_letterPause(self):
        sleep(0.75)
        if(DEBUG): print("* Pausing Between Letters - 750ms")
        self.doLP()  # Transition back to 'off'

    def on_enter_wordPause(self):
        sleep(3)
        if(DEBUG): print("* Pausing Between Words - 3000ms")
        self.doWP()  # Transition back to 'off'

    def toggleMessage(self):
        self.activeMessage = self.message2 if self.activeMessage == self.message1 else self.message1
        if(DEBUG): print(f"* Toggling active message to: {self.activeMessage}")

    def processButton(self):
        self.toggleMessage()

    def run(self):
        Thread(target=self.transmit).start()

    def transmit(self):
        while not self.endTransmission:
            try:
                self.screen.updateScreen(f"Sending:\n{self.activeMessage}")
            except Exception as e:
                if(DEBUG): print(f"LCD Error: {e}")

            for word in self.activeMessage.split():
                for char in word:
                    morse = self.morseDict.get(char.upper(), '')
                    for symbol in morse:
                        if symbol == '.':
                            self.doDot()
                        elif symbol == '-':
                            self.doDash()
                        self.doDDP()
                    self.doLP()
                self.doWP()
        self.screen.cleanupDisplay()

cwMachine = CWMachine()
cwMachine.run()

greenButton = Button(24)
greenButton.when_pressed = cwMachine.processButton

try:
    while True:
        if(DEBUG): print("Killing time in a loop...")
        sleep(20)
except KeyboardInterrupt:
    print("Cleaning up. Exiting...")
    cwMachine.endTransmission = True
    sleep(1)

