#!/usr/bin/env python3
import json
import argparse
import datetime
import numpy as np

from smb_timer import timestamp, crop_string, extract_frames, find_levels


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


if __name__ == '__main__':
    main()
