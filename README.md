# Splits for zzz pc's D4 record

Download the video with `youtube-dl`:

```
youtube-dl https://www.twitch.tv/videos/132979603
```

Make sure you have ffmpeg installed and then run the Python 3 program
`smb-frames.py` with the following arguments:

* `-i SMB*v132979603.mp4` (filename of the downloaded video run)
* `-f 12.2` (the time point in the video where the run starts)
* `-t 36:34.2` (the time point where the run ends)
* `-c 42x14+374+37` (the rectangular region containing the game timer)
* `-d 0.05` (the number of seconds to add to each split)

The splits will be placed in `splits.json`.


# How long does darbian wait after darkness before splitting?

Download a video of darbian and locate a portion of the video that changes
whenever he splits, and locate the game timer.
Now run `darbian-splits.py` with the arguments:

* `-i "Lost Levels Warpless D-4 World Record attempts-v133288238.mp4"`
* `-l 54x132+2+322` (portion that changes on splits)
* `-c 84x28+1118+74` (game timer)

The first part of the output shows the detected level ends,
that is, the frames where `smb-frames.py` would make a split
if not given any `-d`.
The second part of the output shows when darbian actually made a split.
Divide the frame difference by the frame rate (60 FPS)
to the number of seconds to pass to `smb-frames.py -d`.


# Example output from smb-frames.py

```
rav@alcyone:~/work/smb-frames$ python smb-frames.py -i SMB*v132979603.mp4 -f 12.2 -t 36:34.2 -c 42x14+374+37 -d 0.05
66305 frames = 0:36:50.166667
Darkness at 0:00:06
Darkness at 0:00:10.266667
Darkness at 0:00:12.200000
Darkness at 0:00:46.766667
1-1 33.17 (from 0:00:13.600000 to 0:00:46.766667)
1-2 37.57 (from 0:00:53.366667 to 0:01:30.933333)
1-3 32.67 (from 0:01:32.266667 to 0:02:04.933333)
1-4 35.90 (from 0:02:06.300000 to 0:02:42.200000)
2-1 36.97 (from 0:02:43.533333 to 0:03:20.500000)
2-2 41.53 (from 0:03:21.900000 to 0:04:03.433333)
2-3 31.33 (from 0:04:04.800000 to 0:04:36.133333)
2-4 32.73 (from 0:04:37.466667 to 0:05:10.200000)
3-1 32.10 (from 0:05:11.566667 to 0:05:43.666667)
3-2 55.10 (from 0:05:49.800000 to 0:06:44.900000)
3-3 32.07 (from 0:06:46.266667 to 0:07:18.333333)
3-4 39.00 (from 0:07:19.700000 to 0:07:58.700000)
4-1 33.80 (from 0:08:00.066667 to 0:08:33.866667)
4-2 34.13 (from 0:08:35.266667 to 0:09:09.400000)
4-3 32.40 (from 0:09:10.733333 to 0:09:43.133333)
4-4 39.77 (from 0:09:44.500000 to 0:10:24.266667)
5-1 49.93 (from 0:10:25.700000 to 0:11:15.633333)
5-2 36.87 (from 0:11:22.200000 to 0:11:59.066667)
5-3 38.30 (from 0:12:00.366667 to 0:12:38.666667)
5-4 39.37 (from 0:12:40.066667 to 0:13:19.433333)
6-1 39.43 (from 0:13:20.800000 to 0:14:00.233333)
6-2 56.50 (from 0:14:06.366667 to 0:15:02.866667)
6-3 35.57 (from 0:15:04.233333 to 0:15:39.800000)
6-4 46.03 (from 0:15:41.133333 to 0:16:27.166667)
7-1 34.53 (from 0:16:28.566667 to 0:17:03.100000)
7-2 38.73 (from 0:17:04.466667 to 0:17:43.200000)
7-3 45.30 (from 0:17:44.600000 to 0:18:29.900000)
7-4 51.27 (from 0:18:31.300000 to 0:19:22.566667)
8-1 37.67 (from 0:19:23.900000 to 0:20:01.566667)
8-2 38.13 (from 0:20:02.900000 to 0:20:41.033333)
8-3 38.70 (from 0:20:42.466667 to 0:21:21.166667)
8-4 88.80 (from 0:21:22.633333 to 0:22:51.433333)
9-1 49.40 (from 0:22:52.666667 to 0:23:42.066667)
9-2 39.43 (from 0:23:43.433333 to 0:24:22.866667)
9-3 34.87 (from 0:24:24.200000 to 0:24:59.066667)
9-4 32.77 (from 0:25:00.400000 to 0:25:33.166667)
A-1 35.53 (from 0:25:34.533333 to 0:26:10.066667)
A-2 36.87 (from 0:26:16.666667 to 0:26:53.533333)
A-3 30.33 (from 0:26:54.866667 to 0:27:25.200000)
A-4 35.57 (from 0:27:26.566667 to 0:28:02.133333)
B-1 33.47 (from 0:28:03.466667 to 0:28:36.933333)
B-2 56.90 (from 0:28:43.066667 to 0:29:39.966667)
B-3 32.07 (from 0:29:41.300000 to 0:30:13.366667)
B-4 47.43 (from 0:30:14.733333 to 0:31:02.166667)
C-1 36.67 (from 0:31:03.500000 to 0:31:40.166667)
C-2 33.10 (from 0:31:41.533333 to 0:32:14.633333)
C-3 47.77 (from 0:32:16.033333 to 0:33:03.800000)
C-4 50.93 (from 0:33:05.166667 to 0:33:56.100000)
D-1 34.17 (from 0:33:57.433333 to 0:34:31.600000)
D-2 31.73 (from 0:34:32.933333 to 0:35:04.666667)
D-3 35.60 (from 0:35:06 to 0:35:41.600000)
D-4 67.07 (from 0:35:43.066667 to 0:36:50.133333)
```

# Example output from darbian-splits.py

```
rav@alcyone:~/work/smb-frames$ python darbian-splits.py -i *-v133288238.mp4 -c 84x28+1118+74 -l 54x132+2+322
Darkness at 0:00:11.916667
/usr/lib/python3.6/site-packages/numpy/core/fromnumeric.py:2889: RuntimeWarning: Mean of empty slice.
  out=out, **kwargs)
/usr/lib/python3.6/site-packages/numpy/core/_methods.py:80: RuntimeWarning: invalid value encountered in double_scalars
  ret = ret.dtype.type(ret / rcount)
Darkness at 0:00:29.600000
Darkness at 0:00:33.733333
Darkness at 0:01:02.133333
Darkness at 0:01:04.150000
Darkness at 0:01:07
Darkness at 0:01:08.833333
Darkness at 0:01:13.083333
Darkness at 0:01:15.066667
Darkness at 0:01:48.933333
2160 actual
3840 actual
6536 detected
9184 detected
11226 detected
13460 detected
13461 actual
15760 detected
15767 actual
18335 detected
18339 actual
20297 detected
20302 actual
22363 detected
22366 actual
24369 detected
24371 actual
27963 detected
27966 actual
29968 detected
29971 actual
32393 detected
32397 actual
34502 detected
34505 actual
36633 detected
36637 actual
38053 detected
38270 actual
40728 detected
43376 detected
45418 detected
47651 detected
47655 actual
50035 detected
50040 actual
51677 detected
52988 actual
53213 detected
54826 detected
59206 detected
61876 detected
63917 detected
66130 detected
66135 actual
68431 detected
68436 actual
71003 detected
71008 actual
72968 detected
72972 actual
73832 actual
76484 detected
79112 detected
81157 detected
83202 detected
83207 actual
85503 detected
85507 actual
88076 detected
88081 actual
90040 detected
90045 actual
92064 detected
92069 actual
92160 actual
94069 detected
94074 actual
96651 detected
97663 detected
97666 actual
99667 detected
99673 actual
102435 detected
102441 actual
104672 detected
104675 actual
106803 detected
106808 actual
108829 detected
108831 actual
111314 detected
111320 actual
114396 detected
114402 actual
117025 detected
117028 actual
119360 detected
119365 actual
121890 detected
121902 actual
124274 detected
124279 actual
128035 detected
128039 actual
130291 detected
130295 actual
133418 detected
133426 actual
135742 detected
135747 actual
138733 detected
138738 actual
141536 detected
141541 actual
144717 detected
144719 actual
146909 detected
146912 actual
147970 detected
149255 detected
149261 actual
151601 detected
151606 actual
155475 actual
157185 detected
157627 detected
160269 detected
160272 actual
162715 detected
162717 actual
164887 detected
164891 actual
166989 detected
166994 actual
167598 detected
168061 detected
169326 detected
172440 detected
172446 actual
175089 detected
175093 actual
176947 detected
176952 actual
179140 detected
179153 actual
180554 detected
180707 actual
...
```
