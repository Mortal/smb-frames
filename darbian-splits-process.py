#!/usr/bin/env python3
import re
from collections import Counter


def main():
    actual = []
    detected = []

    with open('README.md') as fp:
        for line in fp:
            mo = re.match(r'^(\d+) (detected|actual)$', line.strip())
            if not mo:
                continue
            if mo.group(2) == 'actual':
                actual.append(int(mo.group(1)))
            else:
                detected.append(int(mo.group(1)))

    def dist(i, j):
        return abs(detected[i] - actual[j])

    i = 0
    j = 0
    diff = Counter()
    while i < len(detected):
        # Advance j to closest in 'actual'
        while j+1 < len(actual) and dist(i, j+1) < dist(i, j):
            j += 1
        d = actual[j] - detected[i]
        try:
            diff[d] += 1
        except KeyError:
            diff[d] = 1
        i += 1
    print('\n'.join('%3d frames: %s time%s' % (k, v, '' if v == 1 else 's')
                    for k, v in sorted(diff.items())
                    if -100 < k < 100))
    e = sorted(diff.elements())
    print('Median: %s frames' % e[len(e)//2])


if __name__ == '__main__':
    main()
