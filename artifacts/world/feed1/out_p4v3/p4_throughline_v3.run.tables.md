# worldprobe -- p4_throughline_v3 (run)

writer `worldprobe`, report_kind `bench_trace`, 2026-09-08T13:00:23Z. Units: gt.

run dir `<host-path><session-scratchpad>\feed1_runs\out_p4v3\run_p4_throughline_v3`

## regimes

| regime | trigger | settle_gt | final_value | final_bits | first_stable_gt | last_change_gt | plateau | truncated |
|---|---|---|---|---|---|---|---|---|
| wake_on | none | 6 | 2 | `010111` | 6 | 6 | false | false |
| wake_off | none | 8 | 1 | `101000` | 8 | 8 | false | false |
| warm_T0 | none | 0 | 1 | `101000` | 0 | 0 | false | false |
| warm_T15 | none | 8 | 2 | `010111` | 8 | 8 | false | false |
| v_T0 | none | 8 | 1 | `101000` | 8 | 8 | false | false |
| v_T15 | none | 8 | 2 | `010111` | 8 | 8 | false | false |

### wake_on -- changes

| gt | bits | value |
|---|---|---|
| 0 | `100000` | 1 |
| 2 | `100100` | 1 |
| 4 | `100110` | 1 |
| 6 | `010111` | 2 |

### wake_off -- changes

| gt | bits | value |
|---|---|---|
| 0 | `010111` | 2 |
| 2 | `011111` | 2 |
| 4 | `011011` | 2 |
| 6 | `011001` | 2 |
| 8 | `101000` | 1 |

### warm_T0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `101000` | 1 |

### warm_T15 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `101000` | 1 |
| 2 | `100000` | 1 |
| 4 | `100100` | 1 |
| 6 | `100110` | 1 |
| 8 | `010111` | 2 |

### v_T0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `010111` | 2 |
| 2 | `011111` | 2 |
| 4 | `011011` | 2 |
| 6 | `011001` | 2 |
| 8 | `101000` | 1 |

### v_T15 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `101000` | 1 |
| 2 | `100000` | 1 |
| 4 | `100100` | 1 |
| 6 | `100110` | 1 |
| 8 | `010111` | 2 |

## rcon

| roundtrips | limit |
|---|---|
| 3261 | 600000 |

