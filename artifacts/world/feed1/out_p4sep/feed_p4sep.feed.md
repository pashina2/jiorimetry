# feed.py -- feed_p4sep

Readings copied from `worldprobe` result files; nothing retyped.

## artifacts

| artifact | kind | Bench | world rows | world FAIL | read points | mismatch | settle gt | blocks | rcon |
|---|---|---|---|---|---|---|---|---|---|
| p4_throughline_sep | placer0 | 2/2 | 2 | 1 | 14 | 7/14 | 0..0 (0 unsettled) | 70 | 3519 |

first counterexample, p4_throughline_sep: `{"regime": "v_T0", "read": "O_0", "cell": [107, 65, 101], "expected": true, "got": false, "other_reads": ["O_15", "c0_1_2", "c1_1_2", "d2_2_1", "d4_3_1"]}`

## runs

| spec | wall s | rcon | returncode |
|---|---|---|---|
| p4_throughline_sep | 67.1 | 3519 | 0 |

