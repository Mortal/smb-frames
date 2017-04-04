#!/usr/bin/env python3
import argparse

from smb_timer import crop_string, stream_frames, find_levels_streaming
from signal import uint8absdiff, find_above
import heapq


def iter_actual_splits(input_filename, crop_labels, input_buffer_seconds=5):
    framerate, all_frames = stream_frames(
        input_filename, crop_labels, input_buffer_seconds)
    offset = 0
    for frames in all_frames:
        nframes = len(frames)
        change = uint8absdiff(frames.reshape(nframes, -1), axis=0) ** 2.0
        change = change.mean(axis=1)
        i, j = find_above(change, 250)
        yield from i + offset
        offset += nframes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-filename', '-i', required=True)
    parser.add_argument('--crop', '-c', required=True, type=crop_string)
    parser.add_argument('--crop-labels', '-l', required=True, type=crop_string)
    args = parser.parse_args()

    framerate, levels = find_levels_streaming(args.input_filename, args.crop)
    detected = ((f2, 'detected') for f1, f2, extra in levels)
    actual_splits = iter_actual_splits(args.input_filename, args.crop_labels)
    actual = ((f, 'actual') for f in actual_splits)

    for x in heapq.merge(actual, detected):
        print(*x)


if __name__ == '__main__':
    main()
