from machine import Pin, SPI
from mfrc522 import MFRC522
import ucryptolib
import urandom
from nrf24l01 import NRF24L01

idCheck = ""

# Setup for RFID reader (RC522)
spi = SPI(0, baudrate=1000000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(19), miso=Pin(16))
rfid_reader = MFRC522(spi, Pin(22))

# NRF24L01 send
role = "send"

if role == "send":
    send_pipe = b"\xe1\xf0\xf0\xf0\xf0"
    receive_pipe = b"\xd2\xf0\xf0\xf0\xf0"
else:
    send_pipe = b"\xd2\xf0\xf0\xf0\xf0"
    receive_pipe = b"\xe1\xf0\xf0\xf0\xf0"

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

# Setup DIP Switch (for 4-hex digit user PIN input)
dip_switch_pins = [Pin(i, Pin.IN) for i in (2, 3, 4, 5)]  # Example GPIO pins for DIP switch

# Setup NRF24L01 for communication
csn_pin = Pin(15, mode=Pin.OUT, value=1)
ce_pin = Pin(14, mode=Pin.OUT, value=0)
spi_nrf = SPI(1, baudrate=1000000, polarity=0, phase=0, sck=Pin(10), mosi=Pin(11), miso=Pin(12))
nrf = NRF24L01(spi_nrf, csn_pin, ce_pin, payload_size=32)

# AES Encryption setup (128-bit key)
key = b'16_byte_secret!'  # Example 128-bit key
iv = b'16_byte_iv_init'   # Example Initialization Vector (IV)
cipher = ucryptolib.aes(key, ucryptolib.MODE_CBC, iv)

# Function to read DIP switch as 4-hex digit PIN
def read_dip_switch():
    pin_value = 0
    for i, pin in enumerate(dip_switch_pins):
        pin_value |= (pin.value() << i)
    return hex(pin_value)

# Function to generate random challenge
def generate_random_challenge():
    return urandom.getrandbits(128)

# AES Encryption
def encrypt_data(data):
    return cipher.encrypt(data.ljust(16, b'\x00'))  # Padding for 16-byte blocks

# RFID Authentication Process
def authenticate_rfid():
    (status, tag_type) = rfid_reader.request(rfid_reader.REQIDL)
    if status == rfid_reader.OK:
        print("RFID card detected")
        (status, uid) = rfid_reader.SelectTagSN()
        if status == rfid_reader.OK: # User Auth - NJ
            print("RFID UID:", uid)
            for i in range(0,4): # Get 4 diffrent inputs from dip switch
                pin = read_dip_switch()
                user_pin += pin
            currentUseID = str(uid) + str(user_pin)
            print("ENCRYPTED ID: " encrypt_data(currentUseID)) # This is only needed for us to get the id to hard code- NJ
            if encrypt_data(currentUseID) == idCheck: #Check entered data against the stored data
                return 1 # send auth User cmd - NJ
            elif encrypt_data(currentUseID) not idCheck:
                """ Send un Auth accesss """"
                return -1 # send delete cmd - NJ 
    return 0

# Transmitter to send encrypted challenge
def send_encrypted_challenge():
    challenge = generate_random_challenge()
    encrypted_challenge = encrypt_data(str(challenge).encode())
    nrf.send(encrypted_challenge)

# Main Transmitter loop
while True:
    if authenticate_rfid() == 1:  # Wait for RFID authentication
        send_encrypted_challenge()  # Send encrypted challenge to receiver
    elif authenticate_rfid() == -1:
        """Run Delete"""
