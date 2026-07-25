# Modules
from machine import Pin, PWM, time_pulse_us, I2C, SPI
from i2c_lcd import I2cLcd
from mfrc522 import MFRC522
from secret import correct_id, correct
from time import sleep_us, sleep, ticks_ms, ticks_diff

# Important variables
SCL_PIN = 15
SDA_PIN = 2
LCD_FREQ = 400000 # 400000 Hz = 400 KHz (Good for LCDs)
LCD_WIDTH = 16
LCD_HEIGHT = 2
LCD_ADDR = 0x27 # Default address for LCDs (Use i2c.scan() to check for addresses)
BUZZER_PIN = 22
BUZZER_FREQ = 50 # 50 Hz
TRIG_PIN = 32
ECHO_PIN = 33
R1 = 21
R2 = 25
R3 = 26
R4 = 27
C1 = 14
C2 = 12
C3 = 13
C4 = 16
SPI_ID = 2
SCK = 18
MISO = 19
MOSI = 23
CS = 5
RST = 4
secure_pass = "X"
speed_of_sound = 0.0343 
DIST_THRES = 10
# Speed of sound in air = 343 m/s = 0.0343 cm/μs

# LCD
i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN), freq=LCD_FREQ)
lcd = I2cLcd(i2c, LCD_ADDR, LCD_HEIGHT, LCD_WIDTH)
lcd.clear()

# LCD special function
def lcd_write(x: int, y: int, msg):
    lcd.move_to(x, y)
    msg = str(msg)
    lcd.putstr(msg)

# Buzzer
buzzer = PWM(Pin(BUZZER_PIN, Pin.OUT), freq=BUZZER_FREQ)
buzzer.duty(0) # Inital duty is 0 = buzzer is turned off

# Ultrasonic 
trig = Pin(TRIG_PIN, Pin.OUT)
echo = Pin(ECHO_PIN, Pin.IN)

# Keypad
r_pins = [Pin(x, Pin.OUT) for x in [R1, R2, R3, R4]]
c_pins = [Pin(i, Pin.IN, Pin.PULL_DOWN) for i in [C1, C2, C3, C4]]
matrix = [
    ["1", "2", "3", "A"],
    ["4", "5", "6", "B"],
    ["7", "8", "9", "C"],
    ["*", "0", "#", "D"]
]

# Crucial variables (used in keypad)
guess = []

# System status variable
status = None

# RFID
rfid = MFRC522(spi_id=SPI_ID, sck=SCK, miso=MISO, mosi=MOSI, cs=CS, rst=RST)
card_id = ""

# Functions
def card_config():
    # This function lets us configure the card
    global key, guess, correct, card_id, status

    card_id = ""
    lcd_write(0, 0, "Scan your card")

    rfid.init()
    (stat, tag_type) = rfid.request(rfid.REQIDL) # Requesting an ID from the RFID
    if stat == rfid.OK:
        buzzer.duty(20)
        sleep(0.03)
        buzzer.duty(0)
        (stat, raw_id) = rfid.SelectTagSN()
        if stat == rfid.OK:
            card_id = f"0x{raw_id[0]:02X}{raw_id[1]:02X}{raw_id[2]:02X}{raw_id[3]:02X}"

        # Checking if the id that came from the rfid matches with the stored one
        if card_id == correct_id:
            lcd.clear()
            lcd_write(0, 0, "Correct Card")
            sleep(1)
            lcd.clear()
            lcd_write(0, 0, "PIN code: ")
            status = True
        else:
            lcd.clear()
            lcd_write(0, 0, "DANGER >:(")
            print(card_id)
            for _ in range(3):
                for _ in range(2):
                    buzzer.duty(1000)
                    sleep(0.5)
                    buzzer.duty(0)
            card_id = ""
            status = False

# This function is used for checking the password
def password_config():
    global guess, correct

    while len(guess) < len(correct):
        # Scanning the keypad for button presses
        for r in range(len(r_pins)):
            for c in range(len(c_pins)):
                r_pins[r].on()
                key = None
                if c_pins[c].value():
                    key = matrix[r][c]
                    print(f"Key: {key}")
                    buzzer.duty(20) # Beeps when key is pressed
                    sleep(0.03)
                    buzzer.duty(0)
                    guess.append(key) # Puts the pressed key in the user's guess
                    lcd_write(0, 0,"Pin code: " + (secure_pass * len(guess)))
                    # Displaying a specific character to avoid password leakage
            r_pins[r].off()
            # Resetting the row pins to reactivate the scan
    else:
        # Checks if the password is correct or not
        if len(guess) == len(correct):
            if guess == correct:
                # Correct password grants access
                lcd.clear()
                lcd_write(0, 0, "Correct :)")
                sleep(0.5)
                lcd.clear()
                lcd_write(0, 0, "Access Granted")
                sleep(0.5)

                # Resetting everything
                guess = []
                card_id = ""
                distance = get_distance()
            else:
                # Wrong password alerts guards
                lcd.clear()
                lcd_write(0, 0, "DANGER >:(")
                for _ in range(3):
                    for _ in range(2):
                        buzzer.duty(1000)
                        sleep(0.5)
                        buzzer.duty(0)
                
                # Resetting everything
                sleep(0.5)
                guess = []
                card_id = ""
                distance = get_distance()
                        
# This function gets the distance between the system and a person
def get_distance():
    # Setting up a 10 microsecond pulse on trigger pin
    trig.off()
    sleep_us(2)
    trig.on()
    sleep_us(10)
    trig.off()

    # calculating the time the pulse took to travel between 
    # the sensor and object (back and forth)
    duration = time_pulse_us(echo, 1, 30000)

    # Check for a potential mistake
    if duration < 0:
        return 99999999999
        # This number is just a flag

    # distance = speed * time
    distance = (duration * speed_of_sound) / 2
    # We are dividing by two because we want the distance from one
    # direction only
    return distance # Returning the distance

def main():
    # Latest activity happend
    last_activity = 0
    global status
    auth = False # System authentication flag

    while True:
        # Starting a timer
        now = ticks_ms()

        # Setting up non-blocking logic
        if ticks_diff(now, last_activity) > 20:
            # Getting the distance
            distance = get_distance()

            # Checking if there is anyone nearby
            if distance <= DIST_THRES:
                if not auth:
                    card_config()
                    if status:
                        password_config()
                        sleep(0.02) # Small delay
                    status = False
                    auth = False
            else:
                if not auth:
                    lcd.clear()

            last_activity = now # Resetting last activity to be now

if __name__ == "__main__":
    main() # Code starter
