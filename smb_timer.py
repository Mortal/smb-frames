import re
import subprocess
import os
import datetime
import numpy as np
from signal import (
    uint8absdiff, uint8absdiffdist, running_min, find_peaks, find_above,
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


def stream_frames(input_filename, crop_data, buffer_seconds):
    framerate = get_framerate(input_filename)
    buffer_frames = int(buffer_seconds * framerate)

    def frame_blocks():
        width, height, left, top = crop_data
        crop_str = 'crop=%s:%s:%s:%s' % (width, height, left, top)

        channels = 3
        frame_size = width * height * channels
        buffer = np.zeros((buffer_frames, height, width, channels),
                          dtype=np.uint8)

        cmd = ('ffmpeg', '-loglevel', 'warning', '-nostats',
               '-i', input_filename,
               '-filter:v', crop_str,
               '-f', 'image2pipe', '-pix_fmt', 'rgb24',
               '-vcodec', 'rawvideo', '-')
        proc = subprocess.Popen(
            cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE)
        with proc:
            while proc.poll() is None:
                nbytes = proc.stdout.readinto(buffer)
                if nbytes == 0:
                    break
                nframes, extra = divmod(nbytes, frame_size)
                assert extra == 0, (nbytes, frame_size, nframes, extra)
                if nframes == buffer_frames:
                    yield buffer
                else:
                    yield buffer[:nframes]
            proc.stdout.close()
            if proc.wait() != 0:
                raise Exception(proc.returncode)

    return framerate, frame_blocks()


def stream_light_sections(frame_blocks, cutoff):
    FULL, START, INNER, END = object(), object(), object(), object()

    def iter_chunks():
        offset = 0
        for frame_block in frame_blocks:
            start, end = find_above(frame_block.max(axis=(1, 2, 3)), cutoff)
            for i, j in zip(start, end):
                if i == 0:
                    if j == len(frame_block) - 1:
                        yield INNER, offset + i, frame_block
                    else:
                        yield END, offset + i, frame_block[:j]
                elif j == len(frame_block) - 1:
                    yield START, offset + i, frame_block[i:]
                else:
                    yield FULL, offset + i, frame_block[i:j]
            offset += len(frame_block)

    chunks = iter_chunks()

    def iter_light_section(initial):
        yield initial
        for kind, offset, chunk in chunks:
            if kind is INNER:
                yield chunk
            elif kind is END:
                yield chunk
                return
            elif kind is FULL:
                raise ValueError('Unexpected FULL')
            elif kind is START:
                raise ValueError('Unexpected START')
            else:
                raise ValueError('Unexpected %r' % kind)

    for kind, offset, chunk in chunks:
        if kind in (FULL, END):
            yield offset, iter((chunk,))
        elif kind in (START, INNER):
            yield offset, iter_light_section(chunk)
        else:
            raise ValueError('Unexpected %r' % kind)


def iter_light_sections(frame_blocks, cutoff):
    buffer = None
    for offset, chunks in stream_light_sections(frame_blocks, cutoff):
        extra = []
        buffer_pos = 0
        for chunk in chunks:
            if buffer is None or buffer_pos >= len(buffer):
                extra.append(np.array(chunk))
            elif buffer_pos + len(chunk) > len(buffer):
                split = len(buffer) - buffer_pos
                buffer[buffer_pos:buffer_pos+split] = chunk[:split]
                extra.append(np.array(chunk[split:]))
            else:
                buffer[buffer_pos:buffer_pos+len(chunk)] = chunk
            buffer_pos += len(chunk)
        if extra:
            if buffer is None:
                buffer = np.concatenate(extra)
            else:
                buffer = np.concatenate([buffer] + extra)
        yield offset, buffer[:buffer_pos]


def parse_level(state, offset, framedata, framerate):
    nframes, height, width, channels = framedata.shape
    digit_width, extra = divmod(width, digits)
    assert not extra, 'width must be divisible by number of digits'

    f1 = offset
    f2 = f1 + nframes
    if state is None:
        first = True
        level_start = None
    else:
        first, level_start = state

    seconds = nframes/framerate
    # print("Section [%s:%s] of length %s" %
    #       (f1, f2, datetime.timedelta(seconds=seconds)))
    if first:
        print("Darkness at %s" %
              (datetime.timedelta(seconds=f2/framerate),))
    if seconds < 5:
        return (first, level_start), None

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
        return (first, level_start), None
    if level_start is None:
        level_start = f1
        first = False
    if level_start is not None and np.any(change2 > 12):
        result = level_start, f2, (d12, change2, timer_peaks)
        level_start = None
        return (first, level_start), result
    return (first, level_start), None


def levels_from_light_sections(framerate, light_sections):
    state = None
    for f1, framedata in light_sections:
        state, result = parse_level(state, f1, framedata, framerate)
        if result is not None:
            yield result


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
