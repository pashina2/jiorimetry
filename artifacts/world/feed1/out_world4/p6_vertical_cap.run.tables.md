# worldprobe -- p6_vertical_cap (run)

writer `worldprobe`, report_kind `bench_trace`, 2026-09-08T11:31:43Z. Units: gt.

run dir `<host-path><session-scratchpad>\w_w4\run_p6_vertical_cap`

## regimes

| regime | trigger | settle_gt | final_value | final_bits | first_stable_gt | last_change_gt | plateau | truncated |
|---|---|---|---|---|---|---|---|---|
| wake_on | none | 4 | 1 | `100101` | 4 | 4 | false | false |
| wake_off | none | 8 | 2 | `011010` | 8 | 8 | false | false |
| warm_N15d0 | none | 8 | 1 | `100101` | 8 | 8 | false | false |
| warm_N15d3 | none | 8 | 2 | `011010` | 8 | 8 | false | false |
| v_N15d0 | none | 8 | 1 | `100101` | 8 | 8 | false | false |
| v_N15d3 | none | 8 | 2 | `011010` | 8 | 8 | false | false |

### wake_on -- changes

| gt | bits | value |
|---|---|---|
| 0 | `100000` | 1 |
| 2 | `100100` | 1 |
| 4 | `100101` | 1 |

### wake_on -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `102, 65, 173 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `102, 65, 173 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### wake_off -- changes

| gt | bits | value |
|---|---|---|
| 0 | `100101` | 1 |
| 2 | `101101` | 1 |
| 4 | `101001` | 1 |
| 6 | `101000` | 1 |
| 8 | `011010` | 2 |

### wake_off -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `102, 65, 173 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `102, 65, 173 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### warm_N15d0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `011010` | 2 |
| 2 | `010010` | 2 |
| 4 | `010110` | 2 |
| 6 | `010111` | 2 |
| 8 | `100101` | 1 |

### warm_N15d0 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `102, 65, 173 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `102, 65, 173 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### warm_N15d3 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `100101` | 1 |
| 2 | `101101` | 1 |
| 4 | `101001` | 1 |
| 6 | `101000` | 1 |
| 8 | `011010` | 2 |

### warm_N15d3 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `102, 65, 173 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `102, 65, 173 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### v_N15d0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `011010` | 2 |
| 2 | `010010` | 2 |
| 4 | `010110` | 2 |
| 6 | `010111` | 2 |
| 8 | `100101` | 1 |

### v_N15d0 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `102, 65, 173 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `102, 65, 173 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### v_N15d3 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `100101` | 1 |
| 2 | `101101` | 1 |
| 4 | `101001` | 1 |
| 6 | `101000` | 1 |
| 8 | `011010` | 2 |

### v_N15d3 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `102, 65, 173 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `102, 65, 173 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

## rcon

| roundtrips | limit |
|---|---|
| 3645 | 600000 |

