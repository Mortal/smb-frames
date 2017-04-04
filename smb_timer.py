import re
import subprocess
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
    '''
    Iterator over cropped video stream.

    - input_filename: path to video file (passed to ffmpeg)
    - crop_data: tuple of (width, height, left, top) indicating crop
    - buffer_seconds: how many seconds worth of frames to return at a time

    Returns the framerate and an iterator over frame spans.
    '''

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
    '''
    Given iterator over frame spans, iterate over "light sections" of video.

    A light section is a consecutive portion of the video where the brightest
    pixel is brighter than the given threshold.

    Yields pairs (offset, iterator), where the iterator yields frame spans
    in a particular light section.
    '''

    FULL, START, INNER, END = object(), object(), object(), object()

    def iter_chunks():
        offset = 0
        started = False
        for frame_block in frame_blocks:
            start, end = find_above(frame_block.max(axis=(1, 2, 3)), cutoff)
            for i, j in zip(start, end):
                at_start = i == 0
                at_end = j == len(frame_block) - 1
                if at_start and started:
                    yield INNER, offset + i, frame_block[:j+1]
                    if not at_end:
                        yield END, None, None
                        started = False
                else:
                    if started:
                        yield END, None, None
                    if at_end:
                        yield START, offset + i, frame_block[i:]
                        started = True
                    else:
                        yield FULL, offset + i, frame_block[i:j+1]
            offset += len(frame_block)

    chunks = iter_chunks()

    def iter_light_section(initial):
        yield initial
        for kind, offset, chunk in chunks:
            if kind is INNER:
                yield chunk
            elif kind is END:
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
    '''
    Given iterator over light section frame span iterators,
    yield entire light sections concatenated into a single buffer.
    '''

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


def levels_from_light_sections(framerate, light_sections):
    '''
    Given iterator over light sections, compute the times at which levels
    start and stop.
    '''

    first = True
    level_start = None
    for f1, framedata in light_sections:
        # Off-by-one for backwards compatibility with published splits
        framedata = framedata[:-1]

        nframes, height, width, channels = framedata.shape
        f2 = f1 + nframes
        digit_width, extra = divmod(width, digits)
        assert not extra, 'width must be divisible by number of digits'

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
            # The timer wasn't running in this light section
            assert level_start is None
            continue
        if level_start is None:
            level_start = f1
            first = False
        if level_start is not None and np.any(change2 > 12):
            yield level_start, f2, (d12, change2, timer_peaks)
            level_start = None


def find_levels_streaming(input_filename, crop, input_buffer_seconds=5):
    '''
    Given specification of cropped video, compute times when levels start and
    stop.

    - input_filename: path to video file
    - crop_data: tuple of (width, height, left, top) indicating where the SMB
      level timer is
    '''
    framerate, frame_blocks = stream_frames(
        input_filename, crop, input_buffer_seconds)
    light_sections = iter_light_sections(frame_blocks, 100)
    levels = levels_from_light_sections(framerate, light_sections)
    return framerate, levels
