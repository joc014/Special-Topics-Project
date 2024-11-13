from machine import Pin, SPI
from mfrc522 import MFRC522
import ucryptolib
import urandom
from nrf24l01 import NRF24L01
import time

# Setup NRF24L01 for communication
csn_pin = Pin(15, mode=Pin.OUT, value=1)
ce_pin = Pin(14, mode=Pin.OUT, value=0)
spi_nrf = SPI(1, baudrate=1000000, polarity=0, phase=0, sck=Pin(10), mosi=Pin(11), miso=Pin(12))
nrf = NRF24L01(spi_nrf, csn_pin, ce_pin, payload_size=32)

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
        
# AES parameters
key = b'16_byte_secret!!'  # Example of a 16-byte key
iv = b'16_byte_iv_init!'   # Example Initialization Vector (IV)
BLOCK_SIZE = 16  # AES block size in bytes

# NRF24L01 send
role = "send"

# main code loop
flash_led(1)
nrf = setup()
nrf.start_listening()
msg_string = ""
idCheck = b"?\xcc\xb8\x99\rFvl\x00:\x18\xe7\xd6\xa6\xeeN" # DO NOT TOUCH - NJ
current_user_creds = b""

# Setup DIP Switch (for 4-hex digit user PIN input)
dip_switch_pins = [Pin(i, Pin.IN) for i in (19, 20, 21, 22)] # Updated - NJ

button1 = Pin(9, Pin.IN, pull=Pin.PULL_DOWN) # Green Button NJ

# Encrypt data with CBC mode
def xor_bytes(block1, block2): #NJ
    return bytes(b1 ^ b2 for b1, b2 in zip(block1, block2))

class AES: #NJ
    def __init__(self, key):
        if len(key) != 16:  # 16 bytes = 128 bits for AES
            raise ValueError("Key must be 16 bytes long.")
        self.key = key

    def encrypt(self, plaintext):
        blocks = []

        # Encrypt each block
        for i in range(0, len(plaintext), BLOCK_SIZE):
            block = plaintext[i:i + BLOCK_SIZE]
            if len(block) < BLOCK_SIZE:
                # Pad the last block if it's smaller than BLOCK_SIZE
                block = block + b'\x00' * (BLOCK_SIZE - len(block))  # Add padding to make the block size 16

            # Use ucryptolib.aes in ECB mode (default mode is ECB)
            cipher = ucryptolib.aes(self.key, 1)  # Mode 1 is ECB mode
            encrypted_block = cipher.encrypt(block)

            blocks.append(encrypted_block)

        return b''.join(blocks)

# Encrypt data with AES in ECB mode - NJ
def encrypt_data(data):
    if isinstance(data, str):
        data = data.encode()  # Convert string to bytes
    
    # Calculate the necessary padding length to make data a multiple of BLOCK_SIZE
    padding_length = BLOCK_SIZE - (len(data) % BLOCK_SIZE)
    if padding_length == 0:
        padding_length = BLOCK_SIZE  # Always add padding
    
    padded_data = data + (bytes([padding_length]) * padding_length)
    # print("PADDING LEN:", padding_length)
    # print("PADDED DATA:", padded_data)
    # print("PADDED DATA LENGTH:", len(padded_data))  # Should be a multiple of BLOCK_SIZE

    aes = AES(key)
    return aes.encrypt(padded_data)

if role == "send":
    send_pipe = b"\xe1\xf0\xf0\xf0\xf0"
    receive_pipe = b"\xd2\xf0\xf0\xf0\xf0"
else:
    send_pipe = b"\xd2\xf0\xf0\xf0\xf0"
    receive_pipe = b"\xe1\xf0\xf0\xf0\xf0"

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

# Function to read DIP switch as 4-hex digit PIN - UPDATED NJ
def read_dip_switch():
    pin_value = 0
    p1 = Pin(19).value()
    p2 = Pin(20).value()
    p3 = Pin(21).value()
    p4 = Pin(22).value()
    
    pin_value = str(p4) + str(p3) + str(p2) + str(p1)
    return pin_value

# Function to generate random challenge
def generate_random_challenge():
    return urandom.getrandbits(128)

# Transmitter to send encrypted challenge
def send_encrypted_challenge():
    challenge = generate_random_challenge()
    encrypted_challenge = encrypt_data(str(challenge).encode())
    nrf.send(encrypted_challenge)

# Convert binary string to hexadecimal
def binary_to_hex(binary_str): #NJ
    try:
        hex_str = hex(int(binary_str, 2))[2:].upper()  # Convert to hex, remove "0x" prefix, and make uppercase
        return hex_str
    except ValueError:
        print("Invalid binary string provided.")
        return None

# RFID Authentication Process
pinholder = []
# Read RFID Data
pinholder = []
# Read RFID Data
def read_rfid_data():
    # Check for card presence
    (status, tag_type) = rfid_reader.request(rfid_reader.REQIDL)
    if status == rfid_reader.OK:
        print("Card detected")

        # Select the card
        (status, uid) = rfid_reader.SelectTagSN()
        if status == rfid_reader.OK:
            # Convert the UID to a string (hexadecimal format)
            uid_str = ''.join([f'{byte:02X}' for byte in uid])  # Format each byte as a 2-digit uppercase hex string
#             print("Card UID:", uid_str)
            i=0
            while i<4 :
                if button1.value() == 1:
                    i+=1
                    pinholder.append(read_dip_switch())
                    print("PIN HOLDER: ", pinholder)
                    time.sleep(0.5) 
                    
            combined_string = ''.join(pinholder) #F683
            pin_hex = binary_to_hex(combined_string)  # Convert binary string to hex

            # Example PIN in binary
#             pin = 1111011010000011 
#             pin_str = str(pin)  # Convert the number to a string
#             pin_hex = binary_to_hex(pin_str)
            
#             print(f"PIN in Hex: {pin_hex}")

            current_user_creds = (uid_str + pin_hex).encode()  # Convert to bytes
            enc_ID = encrypt_data(current_user_creds)
            
#             print("CURRENT USER: ", current_user_creds)
#             print("ENC USER: ", enc_ID)

            if enc_ID == idCheck:
                # Stop authentication after reading
                rfid_reader.stop_crypto1()
                return 1
            else:
                print("Authentication failed")
                return -1
        else:
            print("Failed to select the card")
            return 0
    else:
#         print("No card detected")
        return 0




# Setup RFID reader (RC522)
rfid_reader = MFRC522(spi_id=0, sck=2, mosi=7, miso=4, cs=5, rst=18)

# Main Transmitter loop
stop = False
while not stop:
    if role == "send":
        state = read_rfid_data()
        if state == idCheck:
            
            print("Yay")
        else:
            print("Bad Guy")
            stop = True
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
