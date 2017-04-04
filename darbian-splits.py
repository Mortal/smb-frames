#!/usr/bin/env python3
import argparse

from smb_timer import (
    crop_string, iter_light_sections, levels_from_light_sections,
    stream_frames,
)
from signal import uint8absdiff, find_above
import heapq


def actual_splits(input_filename, crop_labels, buffer_seconds):
    framerate, all_frames = stream_frames(
        input_filename, crop_labels, buffer_seconds)
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

    b = 5

    framerate, frame_blocks = stream_frames(args.input_filename, args.crop, b)
    light_sections = iter_light_sections(frame_blocks, 100)
    levels = levels_from_light_sections(framerate, light_sections)
    detected = ((f2, 'detected') for f1, f2, extra in levels)
    actual = ((f, 'actual')
              for f in actual_splits(args.input_filename, args.crop_labels, b))

    for x in heapq.merge(actual, detected):
        print(*x)


if __name__ == '__main__':
    main()
