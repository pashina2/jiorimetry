# worldprobe -- p2_copy_into_side (run)

writer `worldprobe`, report_kind `bench_trace`, 2026-09-08T11:28:04Z. Units: gt.

run dir `<host-path><session-scratchpad>\w_w4\run_p2_copy_into_side`

## regimes

| regime | trigger | settle_gt | final_value | final_bits | first_stable_gt | last_change_gt | plateau | truncated |
|---|---|---|---|---|---|---|---|---|
| wake_on | none | 0 | 1 | `1000000` | 0 | 0 | false | false |
| wake_off | none | 8 | 1 | `1010111` | 8 | 8 | false | false |
| warm_a0 | none | 10 | 2 | `0101000` | 10 | 10 | false | false |
| warm_a3 | none | 10 | 1 | `1010111` | 10 | 10 | false | false |
| v_a0 | none | 10 | 2 | `0101000` | 10 | 10 | false | false |
| v_a3 | none | 10 | 1 | `1010111` | 10 | 10 | false | false |

### wake_on -- changes

| gt | bits | value |
|---|---|---|
| 0 | `1000000` | 1 |

### wake_on -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 118 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 118 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### wake_off -- changes

| gt | bits | value |
|---|---|---|
| 0 | `1000000` | 1 |
| 2 | `1010000` | 1 |
| 4 | `1010100` | 1 |
| 6 | `1010110` | 1 |
| 8 | `1010111` | 1 |

### wake_off -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 118 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 118 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### warm_a0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `1010111` | 1 |
| 2 | `1000111` | 1 |
| 4 | `1000011` | 1 |
| 6 | `1000001` | 1 |
| 8 | `1000000` | 1 |
| 10 | `0101000` | 2 |

### warm_a0 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 118 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 118 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### warm_a3 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `0101000` | 2 |
| 2 | `0111000` | 2 |
| 4 | `0111100` | 2 |
| 6 | `0111110` | 2 |
| 8 | `0111111` | 2 |
| 10 | `1010111` | 1 |

### warm_a3 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 118 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 118 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### v_a0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `1010111` | 1 |
| 2 | `1000111` | 1 |
| 4 | `1000011` | 1 |
| 6 | `1000001` | 1 |
| 8 | `1000000` | 1 |
| 10 | `0101000` | 2 |

### v_a0 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 118 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 118 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### v_a3 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `0101000` | 2 |
| 2 | `0111000` | 2 |
| 4 | `0111100` | 2 |
| 6 | `0111110` | 2 |
| 8 | `0111111` | 2 |
| 10 | `1010111` | 1 |

### v_a3 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 118 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 118 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

## rcon

| roundtrips | limit |
|---|---|
| 3901 | 600000 |

