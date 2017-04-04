'''
Some 1D signal processing utilities.
'''
import numpy as np


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


def uint8distance(x1, x2, axis):
    return np.minimum(x1-x2, x2-x1)


def diffdist(x, axis, d):
    a = tuple(slice(0, -d) if i == axis else slice(None)
              for i in range(x.ndim))
    b = tuple(slice(d, None) if i == axis else slice(None)
              for i in range(x.ndim))
    return x[b] - x[a]


def uint8absdiffdist(x, axis, d):
    return np.minimum(diffdist(x, axis, d),
                      diffdist(255-x, axis, d))


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
