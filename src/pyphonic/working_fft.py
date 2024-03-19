import numpy as np
from numpy.fft import rfft, irfft
from scipy import signal

import pyphonic

BUF_SIZE = 8820

stored_buffer_left = np.zeros((BUF_SIZE, ), dtype=np.float32) # or complex128
stored_buffer_right = np.zeros((BUF_SIZE, ), dtype=np.float32) # or complex128
output_buffer_left = np.zeros((BUF_SIZE, ), dtype=np.float32) # or complex128
output_buffer_right = np.zeros((BUF_SIZE, ), dtype=np.float32) # or complex128

read_stored, write_stored = 0, 0
read_output, write_output = 0, 0
started = False

TAMPER_START, TAMPER_END = 0, 300

def wrapped_write(data, buf, ptr):
    data_len = data.shape[0]
    if ptr + data_len > BUF_SIZE:
        buf[ptr:] = data[:BUF_SIZE - ptr]
        buf[:data_len - (BUF_SIZE - ptr)] = data[BUF_SIZE - ptr:]
    else:
        buf[ptr:ptr + len(data)] = data
    ptr += len(data)
    ptr %= BUF_SIZE
    return ptr

def wrapped_read(read_len, buf, ptr):
    if ptr + read_len > buf.shape[0]:
        data = np.concatenate([buf[ptr:], buf[:ptr + read_len - BUF_SIZE]])
    else:
        data = buf[ptr:ptr + read_len]
    ptr += read_len
    ptr %= BUF_SIZE
    return data, ptr


def process_npy(midi, audio):
    global started
    global read_stored, write_stored, read_output, write_output
    _ = wrapped_write(audio[:pyphonic.getBlockSize()], stored_buffer_left, write_stored)
    write_stored = wrapped_write(audio[pyphonic.getBlockSize():], stored_buffer_right, write_stored)

    started = True
    left, _ = wrapped_read(2048, stored_buffer_left, read_stored)
    right, _ = wrapped_read(2048, stored_buffer_right, read_stored)
    read_stored += pyphonic.getBlockSize()
    read_stored = read_stored % BUF_SIZE

    f, t, Zxxfl = signal.stft(left, fs=pyphonic.getSampleRate(), nperseg=1024)#, noverlap=256)
    Zxxfl[TAMPER_START:TAMPER_END] *= np.linspace(0, 1, TAMPER_END - TAMPER_START).reshape(-1, 1)
    f2, t2, Zxxfr = signal.stft(right, fs=pyphonic.getSampleRate(), nperseg=1024)#, noverlap=256)
    Zxxfr[TAMPER_START:TAMPER_END] *= np.linspace(0, 1, TAMPER_END - TAMPER_START).reshape(-1, 1)

    _, ifl = signal.istft(Zxxfl, fs=pyphonic.getSampleRate(), nperseg=1024)#, noverlap=256)
    _, ifr = signal.istft(Zxxfr, fs=pyphonic.getSampleRate(), nperseg=1024)#, noverlap=256)

    #print(f[:20])

    _ = wrapped_write(ifl[pyphonic.getBlockSize()*2:pyphonic.getBlockSize()*3], output_buffer_left, write_output)
    write_output = wrapped_write(ifr[pyphonic.getBlockSize()*2:pyphonic.getBlockSize()*3], output_buffer_right, write_output)

    retval_left, _ = wrapped_read(pyphonic.getBlockSize(), output_buffer_left, read_output)
    retval_right, read_output = wrapped_read(pyphonic.getBlockSize(), output_buffer_right, read_output)


    return midi, np.concatenate([retval_left, retval_right])