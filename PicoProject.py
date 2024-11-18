from machine import Pin, SPI, PWM
from nrf24l01 import NRF24L01
import ucryptolib
from time import sleep
import struct

# Setup NRF24L01 for communication
csn_pin = Pin(15, mode=Pin.OUT, value=1)
ce_pin = Pin(14, mode=Pin.OUT, value=0)
spi_nrf = SPI(1, baudrate=1000000, polarity=0, phase=0, sck=Pin(10), mosi=Pin(11), miso=Pin(12))
nrf = NRF24L01(spi_nrf, csn_pin, ce_pin, payload_size=32)

# NRF24L01 recieve
role = "receive"

if role == "send":
    send_pipe = b"\xe1\xf0\xf0\xf0\xf0"
    receive_pipe = b"\xd2\xf0\xf0\xf0\xf0"
else:
    send_pipe = b"\xd2\xf0\xf0\xf0\xf0"
    receive_pipe = b"\xe1\xf0\xf0\xf0\xf0"
    
# - Josh, i need to change the pins, and finish testing it
# Define the pins for each segment of the 7-segment display
segment_pins = [
    Pin(3, Pin.OUT),  # Segment A
    Pin(4, Pin.OUT),  # Segment B
    Pin(5, Pin.OUT),  # Segment C
    Pin(6, Pin.OUT),  # Segment D
    Pin(7, Pin.OUT),  # Segment E
    Pin(8, Pin.OUT),  # Segment F
    Pin(9, Pin.OUT),  # Segment G
    Pin(10, Pin.OUT), # Decimal point (optional)
]

# Define pins for each digit of the 4-digit display
digit_pins = [
    Pin(11, Pin.OUT), # Digit 1
    Pin(12, Pin.OUT), # Digit 2
    Pin(13, Pin.OUT), # Digit 3
    Pin(14, Pin.OUT), # Digit 4
]

# Define the segment values for each digit (common anode logic)
digit_map = {
    '0': [1, 1, 1, 1, 1, 1, 0, 0],  # 0
    '1': [0, 1, 1, 0, 0, 0, 0, 0],  # 1
    '2': [1, 1, 0, 1, 1, 0, 1, 0],  # 2
    '3': [1, 1, 1, 1, 0, 0, 1, 0],  # 3
    '4': [0, 1, 1, 0, 0, 1, 1, 0],  # 4
    '5': [1, 0, 1, 1, 0, 1, 1, 0],  # 5
    '6': [1, 0, 1, 1, 1, 1, 1, 0],  # 6
    '7': [1, 1, 1, 0, 0, 0, 0, 0],  # 7
    '8': [1, 1, 1, 1, 1, 1, 1, 0],  # 8
    '9': [1, 1, 1, 1, 0, 1, 1, 0],  # 9
    '-': [0, 0, 0, 0, 0, 0, 1, 0],  # -
    ' ': [0, 0, 0, 0, 0, 0, 0, 0],  # Blank
}

# Function to clear all segments
def clear_segments():
    for segment in segment_pins:
        segment.value(0)

# Function to display a digit on a specific position
def display_digit(digit, position):
    clear_segments()  # Turn off all segments
    # Activate the selected digit
    for i, dp in enumerate(digit_pins):
        dp.value(1 if i == position else 0)
    
    # Light up the corresponding segments for the digit
    for i, value in enumerate(digit_map.get(digit, digit_map[' '])):
        segment_pins[i].value(value)
    
    sleep(0.005)  # Small delay for multiplexing

# Function to display a number on the 4-digit display
def display_number(number):
    str_number = f"{number:4}"  # Format the number as a 4-character string
    for i, char in enumerate(str_number):
        if i < 4:  # Ensure no overflow
            display_digit(char, i)

def setup():
    print("Initialising the nRF24L0+ Module")
    nrf = NRF24L01(SPI(0), csn, ce, payload_size=payload_size)
    nrf.open_tx_pipe(send_pipe)
    nrf.open_rx_pipe(1, receive_pipe)
    nrf.start_listening()
    return nrf

def flash_led(times:int=None):
    ''' Flashed the built in LED the number of times defined in the times parameter '''
    for _ in range(times):
        led.value(1)
        sleep(0.01)
        led.value(0)
        sleep(0.01)

def send(nrf, msg):
    print("sending message.", msg)
    nrf.stop_listening()
    for n in range(len(msg)):
        try:
            encoded_string = msg[n].encode()
            byte_array = bytearray(encoded_string)
            buf = struct.pack("s", byte_array)
            nrf.send(buf)
            # print(role,"message",msg[n],"sent")
            flash_led(1)
        except OSError:
            print(role,"Sorry message not sent")
    nrf.send("\n")
    nrf.start_listening()

# main code loop
flash_led(1)
nrf = setup()
nrf.start_listening()
msg_string = ""

while True:
    msg = ""
    if role == "send":
        send(nrf, "Yello world")
        send(nrf, "Test")
    else:
        # Check for Messages
        if nrf.any():
            package = nrf.recv()          
            message = struct.unpack("s",package)
            msg = message[0].decode()
            flash_led(1)

            # Check for the new line character
            if (msg == "\n") and (len(msg_string) <= 20):
                print("full message",msg_string, msg)
                msg_string = ""
            else:
                if len(msg_string) <= 20:
                    msg_string = msg_string + msg
                else:
                    msg_string = ""

# AES Decryption setup (128-bit key)
key = b'16_byte_secret!'  # Same key as transmitter
iv = b'16_byte_iv_init'   # Same IV as transmitter
cipher = ucryptolib.aes(key, ucryptolib.MODE_CBC, iv)

# Servo motor setup (for GPS data)
servo_pin = PWM(Pin(0))
servo_pin.freq(50)

# Buzzer setup
buzzer = Pin(2, Pin.OUT)

# Decrypt received data
def decrypt_data(encrypted_data):
    return cipher.decrypt(encrypted_data).strip(b'\x00')

# Function to control servo motor based on decrypted GPS data
def control_servo(gps_data):
    position = int(gps_data) % 180  # Example: convert GPS data to servo position
    duty = int((position / 180) * 1023)
    servo_pin.duty(duty)

# Self-destruct function (wipes encryption keys and data)
def self_destruct():
    print("Self-destruct sequence initiated!")
    buzzer.on()
    cipher = None  # Wipe key and cipher
    # Additional cleanup actions here

# Main Receiver loop
#while True:
#    if nrf.any():
#        encrypted_data = nrf.recv()
#        decrypted_data = decrypt_data(encrypted_data)
#        print("Decrypted data:", decrypted_data)
        
        # Example logic for self-destruct (if unauthorized access detected)
#        if decrypted_data == b"Unauthorized":
#            self_destruct()
        
#        control_servo(decrypted_data)  # Use decrypted data for servo control
