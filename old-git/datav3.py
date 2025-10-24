import serial
import numpy as np
import time

PORT = '/dev/ttyACM0'
BAUDRATE = 2000000
DURATION_SECONDS = 5

FRAME_SIZE = 12
MAGIC_VALUE = 0xBEEF

def read_adc_data():
    ser = serial.Serial(PORT, BAUDRATE, timeout=1)
    time.sleep(2)

    print("Reading binary data with magic word...")

    buffer = bytearray()
    timestamps = []
    all_values = []

    start_time = time.time()

    while time.time() - start_time < DURATION_SECONDS:
        # Read as much as available
        chunk = ser.read(ser.in_waiting or FRAME_SIZE)
        buffer.extend(chunk)

        # Try to extract all complete frames in buffer
        while len(buffer) >= FRAME_SIZE:
            # Peek at the magic value position
            maybe_magic = int.from_bytes(buffer[10:12], byteorder='little')
            if maybe_magic == MAGIC_VALUE:
                # Valid frame, extract ADC values
                frame = buffer[:FRAME_SIZE]
                values = np.frombuffer(frame, dtype='<u2')[0:5]  # take first 5 uint16
                all_values.append(values)
                timestamps.append(time.time() - start_time)
                # Remove the processed frame
                del buffer[:FRAME_SIZE]
            else:
                # Magic word not aligned: discard first byte and retry
                del buffer[0]

    ser.close()
    return np.array(timestamps), np.vstack(all_values)

if __name__ == "__main__":
    t, v = read_adc_data()
    print(f"Captured {len(v)} samples at ~{len(v)/DURATION_SECONDS:.1f} Hz")
    print(v)
