# feed.py -- feed_world4

Readings copied from `worldprobe` result files; nothing retyped.

## artifacts

| artifact | kind | Bench | world rows | world FAIL | read points | mismatch | settle gt | blocks | rcon |
|---|---|---|---|---|---|---|---|---|---|
| p1_sub2side | placer0 | 4/4 | 4 | 0 | 32 | 0/32 | 4..8 (0 unsettled) | 54 | 6723 |
| p2_copy_into_side | placer0 | 2/2 | 2 | 0 | 14 | 0/14 | 10..10 (0 unsettled) | 62 | 3901 |
| p4_throughline | placer0 | 2/2 | 2 | 1 | 14 | 7/14 | 0..0 (0 unsettled) | 69 | 3834 |
| p5_max_merge | placer0 | 4/4 | 4 | 0 | 40 | 0/40 | 6..10 (0 unsettled) | 55 | 7457 |
| p6_vertical_cap | placer0 | 2/2 | 2 | 0 | 12 | 0/12 | 8..8 (0 unsettled) | 45 | 3645 |
| slice_v9_n2 | alu_slice_n2 | 128/128 | 128 | 0 | 19328 | 0/19328 | 4..28 (13 unsettled) | 625 | 1681200 |

first counterexample, p4_throughline: `{"regime": "v_T0", "read": "O_0", "cell": [107, 65, 139], "expected": true, "got": false, "other_reads": ["O_15", "c0_1_2", "c1_1_2", "d2_2_1", "d4_3_1"]}`

## runs

| spec | wall s | rcon | returncode |
|---|---|---|---|
| p1_sub2side | reused | 6723 | 0 |
| p2_copy_into_side | reused | 3901 | 0 |
| p4_throughline | reused | 3834 | 0 |
| p5_max_merge | reused | 7457 | 0 |
| p6_vertical_cap | reused | 3645 | 0 |
| slice_v9_n2_1 | 263.6 | 564655 | 0 |
| slice_v9_n2_2 | 246.0 | 564649 | 0 |
| slice_v9_n2_3 | reused | 551896 | 0 |

