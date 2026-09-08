# worldprobe -- p4_throughline (run)

writer `worldprobe`, report_kind `bench_trace`, 2026-09-08T11:29:13Z. Units: gt.

run dir `<host-path><session-scratchpad>\w_w4\run_p4_throughline`

## regimes

| regime | trigger | settle_gt | final_value | final_bits | first_stable_gt | last_change_gt | plateau | truncated |
|---|---|---|---|---|---|---|---|---|
| wake_on | none | 10 | 2 | `0111111` | 10 | 10 | false | false |
| wake_off | none | 0 | 2 | `0111111` | 0 | 0 | false | false |
| warm_T0 | none | 0 | 1 | `1000000` | 0 | 22 | true | false |
| warm_T15 | none | 10 | 2 | `0111111` | 10 | 10 | false | false |
| v_T0 | none | 0 | 2 | `0111111` | 0 | 0 | false | false |
| v_T15 | none | 0 | 2 | `0111111` | 0 | 0 | false | false |

### wake_on -- changes

| gt | bits | value |
|---|---|---|
| 0 | `1000000` | 1 |
| 2 | `1010000` | 1 |
| 4 | `1011000` | 1 |
| 6 | `1011100` | 1 |
| 8 | `1011110` | 1 |
| 10 | `0111111` | 2 |

### wake_off -- changes

| gt | bits | value |
|---|---|---|
| 0 | `0111111` | 2 |

### warm_T0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `0111111` | 2 |
| 16 | `0110111` | 2 |
| 18 | `0100011` | 2 |
| 20 | `0100001` | 2 |
| 22 | `1000000` | 1 |

### warm_T15 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `1000000` | 1 |
| 2 | `1010000` | 1 |
| 4 | `1011000` | 1 |
| 6 | `1011100` | 1 |
| 8 | `1011110` | 1 |
| 10 | `0111111` | 2 |

### v_T0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `0111111` | 2 |

### v_T15 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `0111111` | 2 |

## rcon

| roundtrips | limit |
|---|---|
| 3834 | 600000 |

