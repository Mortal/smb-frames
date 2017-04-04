import os
import re
import json
import argparse
import datetime
import subprocess
import numpy as np

from signal import (
    find_above, find_peaks, uint8absdiff, uint8absdiffdist, running_min,
)


def timestamp(s):
    mo = re.match(r'^(?:(\d+):)?(\d+(?:\.\d+)?)$', s)
    if not mo:
        raise ValueError(s)
    return float(mo.group(1) or '0') * 60 + float(mo.group(2))


def crop_string(s):
    mo = re.match(r'^(\d+)x(\d+)\+(\d+)\+(\d+)$', s)
    if not mo:
        raise ValueError(s)
    return tuple(map(int, mo.group(1, 2, 3, 4)))


def get_framerate(f):
    ffmpeg_output = subprocess.check_output(
        ('ffprobe', f),
        stdin=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        universal_newlines=True)
    mo = re.search('(\d+) fps', ffmpeg_output)
    return int(mo.group(1))


digits = 3


def extract_frames(input_filename, crop):
    framerate = get_framerate(input_filename)
    width, height, left, top = crop
    crop = 'crop=%s:%s:%s:%s' % (width, height, left, top)

    base = os.path.splitext(os.path.basename(input_filename))[0]
    # youtube-dl appends "-v{id}" to Twitch.tv downloads,
    # so we can use this to make shorter filenames
    base = re.sub(r'.*-(v\d+)$', r'\1', base)
    tmp_file = '%s_%sx%s+%s+%s.dat' % (base, width, height, left, top)

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
    assert extra == 0, (size, frame_size, nframes, extra)
    print('%s frames = %s' %
          (nframes, datetime.timedelta(seconds=nframes / framerate)))
    return framerate, np.memmap(tmp_file, dtype=np.uint8, mode='r',
                                shape=(nframes, height, width, channels))


def find_levels(framerate, all_frames):
    light_i, light_j = find_above(all_frames.max(axis=(1, 2, 3)), 100)

    nframes, height, width, channels = all_frames.shape
    digit_width, extra = divmod(width, digits)
    assert extra == 0, 'Width of three digits must be div. by three'
    first = True
    level_start = None
    for f1, f2 in zip(light_i, light_j):
        framedata = all_frames[f1:f2]
        nframes = len(framedata)
        seconds = nframes/framerate
        # print("Section [%s:%s] of length %s" %
        #       (f1, f2, datetime.timedelta(seconds=seconds)))
        if first:
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
        if level_start is None:
            level_start = f1
            first = False
        if level_start is not None and np.any(change2 > 12):
            yield level_start, f2, (d12, change2, timer_peaks)
            level_start = None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plot', '-p', action='store_true')
    parser.add_argument('--from', '-f', dest='from_', type=timestamp)
    parser.add_argument('--to', '-t', type=timestamp)
    parser.add_argument('--input-filename', '-i', required=True)
    parser.add_argument('--crop', '-c', required=True, type=crop_string)
    parser.add_argument('--delay', '-d', default=0, type=float)
    args = parser.parse_args()

    if args.plot:
        import matplotlib.pyplot as plt

    framerate, all_frames = extract_frames(args.input_filename, args.crop)
    nframes, height, width, channels = all_frames.shape

    def level_name(i):
        world, part = divmod(i, 4)
        worlds = '123456789ABCD'
        return '%s-%s' % (worlds[world], part+1)

    split_at = [args.from_ * framerate]
    for i, (f1, f2, extra) in enumerate(find_levels(framerate, all_frames)):
        split_at.append(f2 + args.delay * framerate)
        f = f2 - f1
        print("%s %.2f (from %s to %s)" %
              (level_name(i),
               f/framerate,
               datetime.timedelta(seconds=f1 / framerate),
               datetime.timedelta(seconds=f2 / framerate)))

        if args.plot:
            d12, change2, timer_peaks = extra
            time = (f1 + np.arange(len(d12))) / framerate
            plt.plot(time, d12)
            plt.plot(time[:len(change2)], change2, 'k')
            plt.plot(time[timer_peaks], d12[timer_peaks], 'o')
            plt.show()
    split_at[-1] = args.to * framerate

    s0 = split_at[0]

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
            for i, (s1, s2) in enumerate(zip(split_at[:-1],
                                             split_at[1:]))
        ]
    }
    with open('splits.json', 'w') as fp:
        json.dump(obj, fp, indent=4)


def darbian_splits():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-filename', '-i', required=True)
    parser.add_argument('--crop', '-c', required=True, type=crop_string)
    parser.add_argument('--crop-labels', '-l', required=True, type=crop_string)
    args = parser.parse_args()

    framerate, all_frames = extract_frames(args.input_filename, args.crop)
    nframes, height, width, channels = all_frames.shape

    for i, (f1, f2, extra) in enumerate(find_levels(framerate, all_frames)):
        print("Detected split at %s" % f2)

    framerate, all_splits = extract_frames(args.input_filename, args.crop_labels)
    change = (
        uint8absdiff(all_splits.reshape(nframes, -1), axis=0) ** 2.0).mean(axis=1)
    i, j = find_above(change, 250)
    print(i)


if __name__ == '__main__':
    main()
