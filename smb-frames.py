import numpy as np
import tensorflow as tf
import subprocess
import matplotlib.pyplot as plt
import os
import argparse
import re


def uint8absdiff(x, axis):
    return np.minimum(np.diff(x, axis=axis),
                      np.diff(255-x, axis=axis))


def timestamp(s):
    mo = re.match(r'^(?:(\d+):)?(\d+(?:\.\d+)?)$', s)
    if not mo:
        raise ValueError(s)
    return float(mo.group(1) or '0') * 60 + float(mo.group(2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('from_', type=timestamp)
    parser.add_argument('to', type=timestamp)
    args = parser.parse_args()

    framerate = 30
    f1 = None if args.from_ is None else int(args.from_ * framerate)
    f2 = None if args.to is None else int(args.to * framerate)

    input_filename = (
        '/home/rav/Videos/SMB -LL(SNES) Warpless D-4 (Mario) ' +
        'RTA 36_37(Axe 36_21)-v132979603.mp4')

    # Location of time in video, width:height:left:top
    digits = 3
    width, height, left, top = 42, 14, 374, 37
    digit_width, extra = divmod(width, digits)
    assert extra == 0, 'Width of three digits must be div. by three'
    crop = 'crop=%s:%s:%s:%s' % (width, height, left, top)

    tmp_file = 'zzz_pc_20170402_%sx%s+%s+%s.dat' % (width, height, left, top)

    channels = 3
    frame_size = width * height * channels

    cmd = ('ffmpeg', '-i', input_filename,
           '-filter:v', crop,
           '-f', 'image2pipe', '-pix_fmt', 'rgb24',
           '-vcodec', 'rawvideo', tmp_file)
    if not os.path.exists(tmp_file):
        subprocess.check_call(cmd, stdin=subprocess.DEVNULL)
    size = os.stat(tmp_file).st_size
    nframes, extra = divmod(size, frame_size)
    assert extra == 0
    framedata = np.memmap(tmp_file, dtype=np.uint8, mode='r',
                          shape=(nframes, height, width, channels))
    framedata = framedata[f1:f2]
    nframes = len(framedata)

    digit_width = width // digits
    digitdata = framedata.reshape(
        -1, height, 3, digit_width, channels)
    digitdata = np.transpose(digitdata, (2, 0, 1, 3, 4))
    digitdata = digitdata.reshape((3, nframes, -1))
    diff = uint8absdiff(digitdata, axis=1).mean(axis=2)
    darkness = 255-np.max(digitdata, axis=(0, 2))
    darkness = darkness * diff.max() / darkness.max()
    plt.plot((f1 + np.arange(len(darkness))) / framerate, darkness)
    for i, digit in enumerate(diff):
        plt.plot((f1 + np.arange(len(digit))) / framerate, (3-i)*digit)
    plt.show()


if __name__ == '__main__':
    main()
