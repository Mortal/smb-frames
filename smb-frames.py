import os
import re
import json
import argparse
import datetime
import subprocess
import numpy as np
import scipy.signal


def find_above(xs, cutoff):
    # From github.com/TK-IT/regnskab regnskab/images/extract.py
    above = xs > cutoff
    above_pad = np.r_[False, above, False]
    is_start = above_pad[1:-1] & ~above_pad[0:-2]
    is_end = above_pad[1:-1] & ~above_pad[2:]
    start = is_start.nonzero()[0]
    end = is_end.nonzero()[0]
    assert len(start) == len(end)
    return start, end


def find_peaks(xs, cutoff, skip_start=True, skip_end=True):
    # From github.com/TK-IT/regnskab regnskab/images/extract.py
    xs = np.asarray(xs).ravel()
    n = len(xs)
    peaks = []
    start, end = find_above(xs, cutoff)
    for i, j in zip(start, end):
        peaks.append(i + np.argmax(xs[i:j+1]))
    peaks = np.array(peaks, dtype=np.intp)
    m = np.median(np.diff(peaks))
    if skip_start:
        peaks = peaks[peaks > m/2]
    if skip_end:
        peaks = peaks[peaks < n - m/2]
    return peaks


def uint8absdiff(x, axis):
    return np.minimum(np.diff(x, axis=axis),
                      np.diff(255-x, axis=axis))


def diffdist(x, axis, d):
    a = tuple(slice(0, -d) if i == axis else slice(None)
              for i in range(x.ndim))
    b = tuple(slice(d, None) if i == axis else slice(None)
              for i in range(x.ndim))
    return x[b] - x[a]


def uint8absdiffdist(x, axis, d):
    return np.minimum(diffdist(x, axis, d),
                      diffdist(255-x, axis, d))


def timestamp(s):
    mo = re.match(r'^(?:(\d+):)?(\d+(?:\.\d+)?)$', s)
    if not mo:
        raise ValueError(s)
    return float(mo.group(1) or '0') * 60 + float(mo.group(2))


def running_op(xs, r, op):
    n, = xs.shape
    d = 2*r+1
    y = [xs[i:n-d+i+1] for i in range(d)]
    output = np.zeros_like(xs)
    target = output[r:n-r]
    target[:] = y[0]
    for z in y[1:]:
        op(target, z, target)
    output[:r] = [xs[:r+1+i].min() for i in range(r)]
    output[n-r:] = [xs[n-r-i:].min() for i in range(r)]
    return output


def running_min(xs, r):
    '''
    >>> xs = np.array([0, 1, 1, 1, 0])
    >>> print(running_min(xs, 1))
    [0 0 1 0 0]
    >>> xs = np.array([1, 1, 0, 1, 1])
    >>> print(running_min(xs, 1))
    [1 0 0 0 1]
    '''
    return running_op(xs, r, np.minimum)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plot', '-p', action='store_true')
    parser.add_argument('from_', type=timestamp)
    parser.add_argument('to', type=timestamp)
    args = parser.parse_args()

    if args.plot:
        import matplotlib.pyplot as plt

    framerate = 30

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
    print('%s frames = %s' %
          (nframes, datetime.timedelta(seconds=nframes / framerate)))
    all_frames = np.memmap(tmp_file, dtype=np.uint8, mode='r',
                           shape=(nframes, height, width, channels))
    light_i, light_j = find_above(all_frames.max(axis=(1, 2, 3)), 100)

    level_start = []
    level_stop = []

    def print_level(n, s, f):
        world, part = divmod(n, 4)
        print("Level %s-%s %s on frame %s (%s)" %
              (world+1, part+1, s, f,
               datetime.timedelta(seconds=f/framerate)))

    def print_start():
        # print_level(len(level_start)-1, 'started', level_start[-1])
        pass

    def level_name(i):
        world, part = divmod(i, 4)
        worlds = '123456789ABCD'
        return '%s-%s' % (worlds[world], part+1)

    def print_stop():
        # print_level(len(level_stop)-1, 'ended', level_stop[-1])
        f = level_stop[-1] - level_start[-1]
        print("%s %.2f (from %s to %s)" %
              (level_name(len(level_stop)-1),
               f/framerate,
               datetime.timedelta(seconds=level_start[-1] / framerate),
               datetime.timedelta(seconds=level_stop[-1] / framerate)))

    for f1, f2 in zip(light_i, light_j):
        framedata = all_frames[f1:f2]
        nframes = len(framedata)
        seconds = nframes/framerate
        # print("Section [%s:%s] of length %s" %
        #       (f1, f2, datetime.timedelta(seconds=seconds)))
        if len(level_start) == 0:
            print("Darkness at %s" %
                  (datetime.timedelta(seconds=f2/framerate),))
        if seconds < 5:
            continue

        digitdata = np.asarray([
            framedata[:, :, i:i+digit_width, :].reshape(nframes, -1)
            for i in range(0, width, digit_width)])
        # time = np.arange(f1, f2) / framerate

        change = uint8absdiff(digitdata, axis=1).mean(axis=2)

        # Find periods where the timer changes rapidly
        # indicating the end of the level.
        change2 = uint8absdiffdist(digitdata[2], axis=0, d=3).mean(axis=1)
        change2 = running_min(change2, 8)
        digit_diff = uint8absdiff(digitdata, axis=0).mean(axis=2)
        digit_diff = np.maximum(digit_diff[:, :-1], digit_diff[:, 1:])

        d2 = np.maximum(0, change[2] - change[1])
        d1 = np.maximum(0, change[1] - change[0])
        d12 = np.maximum(d1, d2)
        timer_peaks = find_peaks(d12, 7.5)
        # print('One time unit is %s frames' % np.median(np.diff(timer_peaks)))
        if len(timer_peaks) <= 1:
            continue
        if len(level_start) == len(level_stop):
            level_start.append(f1)
            print_start()
        if len(level_start) == len(level_stop) + 1 and np.any(change2 > 12):
            level_stop.append(f2)
            print_stop()

        if args.plot:
            time = (f1 + np.arange(change.shape[1])) / framerate
            plt.plot(time, d12)
            plt.plot(time[:len(change2)], change2, 'k')
            plt.plot(time[timer_peaks], d12[timer_peaks], 'o')
            plt.show()

    level_stop_augmented = (
        [args.from_ * framerate] +
        level_stop[:-1] +
        [args.to * framerate])
    s0 = level_stop_augmented[0]

    # "Urn format", to be imported by
    # https://github.com/LiveSplit/LiveSplit/blob/master/LiveSplit/LiveSplit.Core/Model/RunFactories/UrnRunFactory.cs
    obj = {
        'title': '',
        'attempt_count': 1,
        'start_delay': '0:0:00',
        'splits': [
            {
                'title': level_name(i),
                'time': str(datetime.timedelta(seconds=(s2 - s0)/framerate)),
                'best_time':
                str(datetime.timedelta(seconds=(s2 - s0)/framerate)),
                'best_segment':
                str(datetime.timedelta(seconds=(s2 - s1)/framerate)),
            }
            for i, (s1, s2) in enumerate(zip(level_stop_augmented[:-1],
                                             level_stop_augmented[1:]))
        ]
    }
    with open('splits.json', 'w') as fp:
        json.dump(obj, fp, indent=4)


if __name__ == '__main__':
    main()
