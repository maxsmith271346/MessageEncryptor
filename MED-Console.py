# Message Encryptor and Decryptor
# !THIS IS A CONSOLE VERSION TO HELP WITH DEMONSTRATION, "MED.py" IS THE ACTUAL PROGRAM!
# CSCE 462: Sections 501 and 502 (Spring 2022, Team 8)
# Jackson Hagood (hagoojac@tamu.edu),
# Andrew Imwalle (andrew.imwalle@tamu.edu),
# and Max Smith (maxsmith271346@tamu.edu)

# imports
import board
import digitalio
import numpy as np
import operator as op
import os, sys
import pyaudio
import scipy.fftpack as fft
import signal
import warnings
import wave
from functools import reduce
from pickle import NONE
from scipy.signal import find_peaks
from scipy.io import wavfile
from textwrap import wrap
from time import sleep

# suppress warnings
warnings.filterwarnings("ignore")

cont = True # boolean for signal handling

# signal handler for stopping recording
def sigint_handler(signal, frame):
        global cont
        cont = False

signal.signal(signal.SIGINT, sigint_handler) # signal setup

def encryptor():
    # hamming functionality
    def get_hamming(data, d_bits, p_bits):
        # ensure data is the correct size
        if len(data) != d_bits:
            data = np.append(data, np.zeros(d_bits - len(data)))

        # add space for parity bits
        encoded = np.zeros(2 ** p_bits, dtype = np.ubyte)
        parity_bits = np.zeros(p_bits + 1)
        data_index = 0
        p_place = 4

        # iterate through parity bits
        for i in range(3, 2 ** p_bits):
            # double 4
            if i == p_place:
                p_place *= 2

            else:
                # set data bit and increment index
                data_bit = data[data_index]
                encoded[i] = data_bit
                data_index += 1
                parity_bits[0] += data_bit

                # allow for variable number of parity bits
                if int(i % 2) == 1:
                    parity_bits[1] += data_bit
                if int((i % 4) / 2) == 1:
                    parity_bits[2] += data_bit
                if int((i % 8) / 4) == 1:
                    parity_bits[3] += data_bit
                if int((i % 16) / 8) == 1:
                    parity_bits[4] += data_bit
                if int((i % 32) / 16) == 1:
                    parity_bits[5] += data_bit

        # iterate through parity bits
        for i in range(1, p_bits + 1):
            if parity_bits[i] % 2 == 1:
                encoded[(2 ** (i - 1))] = 1
                parity_bits[0] += data_bit

        # first index
        if parity_bits[0] % 2 == 1:
                encoded[0] = 1

        # return encoding
        return encoded

    # hamming variables
    P_BITS = 5 # number of parity bits per packet (exluding 0)
    D_BITS = 26 # number of data bits per packet
    PACKET_SIZE = 32 # number of total bits per packet (P_BITS + D_BITS + 1; 2^P_BITS >= PACKET_SIZE)

    # wav file variables
    samplerate = 44100
    FREQ0 = 1000 # tone 0
    FREQ1 = 2000 # tone 1
    array = np.array([])
    t = np.linspace(0., (1 / 12), int(samplerate / 12))
    amplitude = np.iinfo(np.int16).max
    high = amplitude * np.sin(2. * np.pi * FREQ1 * t)
    low = amplitude * np.sin(2. * np.pi * FREQ0 * t)
    high[-100 : -1] = 0
    low[-100 : -1] = 0
    space = np.zeros(500)

    # get indexes for key selection from DIP switch
    dip = get_dip_input()
    index1 = dip % 2 # first 5 bits
    index2 = int(dip / 2) # last (6th) bit

    # get affine cipher keys
    key1 = 193 if index2 == 1 else 97
    key2 = [177, 10, 186, 162, 46, 197, 21, 133, 109, 137, 115, 90, 65, 145, 216, 154, 196, 53, 19, 152, 220, 28, 108, 198, 234, 16, 50, 143, 117, 12, 48, 239][index1]

    # accept message from user input
    m = input("\tEnter the message: ")
    c = []
    binary = ""

    # encrypt ASCII characters
    for char in m:
        c.append((key1 * ord(char) + key2) % 256)

    binary += encrypt_char('\0', key1, key2) # start with null

    # convert message to binary
    for char in c:
        temp = bin(char)[2:]
        binary += '0' * (8 - len(temp)) + temp

    binary += encrypt_char('\0', key1, key2) # end with null

    # get bit array
    bit_arr = np.fromstring(binary, dtype = np.ubyte) - 48

    # get hamming foundation
    binary_arr = get_hamming(bit_arr[: D_BITS], D_BITS, P_BITS)

    # get new array with hamming
    for i in range(26, len(bit_arr), D_BITS):
        binary_arr = np.append(binary_arr, get_hamming(bit_arr[i:i+D_BITS], D_BITS, P_BITS))

    # iterate through array with hamming and add signals
    for i in range(0, len(binary_arr), 1):
        if binary_arr[i] == 0:
            array = np.append(array, low) # low
        else:
            array = np.append(array, high) # high

    # format array
    array = np.append(space, array)
    array = np.append(array, space)

    # write to wav file
    wavfile.write("output.wav", samplerate, array.astype(np.int16))

    # wait for keystroke
    input("\tPress <Enter> to play message")

    # play wav file
    print("\tPlaying message\n\t", end = "")
    wav_file = "./output.wav"
    os.system(f'aplay {wav_file}')

def decryptor():
    # suppress ALSA warnings
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    sys.stderr.flush()
    os.dup2(devnull, 2)
    os.close(devnull)

    # wav file variables
    chunk = 1000
    rate = 44100
    channels = 1
    wav_file = "input.wav"
    form = pyaudio.paInt16
    frames = []

    # setup audio listener
    p = pyaudio.PyAudio()
    stream = p.open(format = form, channels = channels, rate = rate, input = True, frames_per_buffer = chunk)
    
    # wait for keystroke
    os.dup2(old_stderr, 2)
    os.close(old_stderr)
    input("\tPress <Enter> to start recording...")
    print("\t* recording")

    # read sound signal
    while cont:
        data = stream.read(chunk)
        frames.append(data)

    # stop recording
    print("\t* done recording")

    # close reader
    stream.stop_stream()
    stream.close()
    p.terminate()

    # write to wav file
    wf = wave.open(wav_file, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(p.get_sample_size(form))
    wf.setframerate(rate)
    wf.writeframes(b''.join(frames))
    wf.close()

    # reading wav file variables
    REL_FREQ = 4
    FREQ0 = 1000 # tone 0
    FREQ1 = 2000 # tone 1

    # open wav file
    freq_sample, sig_audio = wavfile.read("./input.wav")

    if sig_audio.ndim > 1:
            sig_audio = sig_audio[:, 0]

    # get duration
    duration = int(freq_sample / (REL_FREQ * 12))

    # list to store binary value over window
    dirty_bin = []
    x = 0

    # iterate through signal
    for i in range(0, len(sig_audio), duration):
        # get y and x
        yf = fft.rfft(sig_audio[i : i + duration])
        xf = fft.rfftfreq(duration, 1 / freq_sample)

        # determine the dominant frequency
        dominant_freq = xf[np.argmax(np.abs(yf))]

        # determine if the frequency is 0 or 1
        if (abs(FREQ1 - dominant_freq) < 50):
            dirty_bin.append(1)
        elif (abs(FREQ0 - dominant_freq) < 50):
            dirty_bin.append(0)
        else:
            dirty_bin.append(-1)

    # trim array at the front
    for bit in range(len(dirty_bin)):
        if dirty_bin[bit] != -1:
            dirty_bin = dirty_bin[bit + 1 :]
            break

    ciphertext = "" # raw ciphertext

    # add to ciphertext
    for k in range(0, len(dirty_bin), REL_FREQ):
        if int(round(sum(dirty_bin[k : k + REL_FREQ]) / REL_FREQ, 0)) == -1:
            break

        mid_chunk = dirty_bin[int(round(k + (REL_FREQ / 4))):int(round(k + (3 * REL_FREQ / 4)))]

        if len(mid_chunk) == 0:
            break

        ciphertext += str(int(round(sum(mid_chunk) / (len(mid_chunk)), 0))) # append to ciphertext

    # convert ciphertext
    ciphertext += ((32 - len(ciphertext)) % 32) * '0'
    ciphertext = np.fromstring(ciphertext, dtype=np.ubyte) - 48

    # account for hamming
    decoded = ""
    remove = [2 ** i for i in range(5)]
    remove.append(0)

    # iterate through ciphertext
    for i in range(0, len(ciphertext), 32):
        bits = [i for i, bit in enumerate(ciphertext[i : i + 32]) if bit]
        if not bits:
            continue
        index = (reduce(op.xor, bits))

        ciphertext[i + index] = ciphertext[i + index] ^ 1
        decoded += "".join([",".join(item) for item in np.delete(ciphertext[i : i + 32], remove).astype(str)])

    # get actual ciphertext9
    ciphertext = decoded

    # get indexes for key selection from DIP switch
    dip = get_dip_input()
    index1 = dip % 2 # first 5 bits
    index2 = int(dip / 2) # last (6th) bit

    # get affine cipher keys
    key1 = 193 if index2 == 1 else 97
    key1inv = 65 if index2 == 1 else 161
    key2 = [177, 10, 186, 162, 46, 197, 21, 133, 109, 137, 115, 90, 65, 145, 216, 154, 196, 53, 19, 152, 220, 28, 108, 198, 234, 16, 50, 143, 117, 12, 48, 239][index1]
    NULL_BYTE = encrypt_char('\0', key1, key2)

    # initialize message variable
    m = ""

    # search for start of message (null)
    for i in range(len(ciphertext)):
        if ciphertext[i : i + 8] == NULL_BYTE:
            ciphertext = ciphertext[i + 8 :]
            break

    # iterate through message until the null is reached
    for j in range(0, len(ciphertext), 8):
        char = ciphertext[j : j + 8]
        if char == NULL_BYTE:
            break
        else:
            # decode ciphertext with affine cipher
            m += chr((key1inv * (int(char, 2) - key2)) % 256)

    # print message
    print("\tMessage: " + m)

while True:
    i = input("\nSelect Encryptor (1) / Decryptor (2): ")
    print()

    if i == '1':
        encryptor()
    else:
        decryptor()
