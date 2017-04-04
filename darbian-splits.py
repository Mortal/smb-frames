import argparse

from smb_timer import extract_frames, find_levels, crop_string
from signal import uint8absdiff, find_above


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-filename', '-i', required=True)
    parser.add_argument('--crop', '-c', required=True, type=crop_string)
    parser.add_argument('--crop-labels', '-l', required=True, type=crop_string)
    args = parser.parse_args()

    framerate, all_frames = extract_frames(args.input_filename, args.crop)
    nframes, height, width, channels = all_frames.shape

    for i, (f1, f2, extra) in enumerate(find_levels(framerate, all_frames)):
        print("Detected split at %s" % f2)

    framerate, all_splits = extract_frames(
        args.input_filename, args.crop_labels)
    change = uint8absdiff(all_splits.reshape(nframes, -1), axis=0) ** 2.0
    change = change.mean(axis=1)
    i, j = find_above(change, 250)
    print(i)


if __name__ == '__main__':
    main()
