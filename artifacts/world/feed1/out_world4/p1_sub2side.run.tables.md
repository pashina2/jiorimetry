# worldprobe -- p1_sub2side (run)

writer `worldprobe`, report_kind `bench_trace`, 2026-09-08T11:26:47Z. Units: gt.

run dir `<host-path><session-scratchpad>\w_w4\run_p1_sub2side`

## regimes

| regime | trigger | settle_gt | final_value | final_bits | first_stable_gt | last_change_gt | plateau | truncated |
|---|---|---|---|---|---|---|---|---|
| wake_on | none | 4 | 1 | `10000011` | 4 | 4 | false | false |
| wake_off | none | 4 | 1 | `10100100` | 4 | 4 | false | false |
| warm_Wn0a0 | none | 8 | 2 | `01011000` | 8 | 8 | false | false |
| warm_Wn15a0 | none | 8 | 1 | `10000011` | 8 | 8 | false | false |
| warm_Wn0a3 | none | 4 | 1 | `10100100` | 4 | 4 | false | false |
| warm_Wn15a3 | none | 4 | 1 | `10100111` | 4 | 4 | false | false |
| v_Wn0a0 | none | 8 | 2 | `01011000` | 8 | 8 | false | false |
| v_Wn15a0 | none | 8 | 1 | `10000011` | 8 | 8 | false | false |
| v_Wn0a3 | none | 4 | 1 | `10100100` | 4 | 4 | false | false |
| v_Wn15a3 | none | 4 | 1 | `10100111` | 4 | 4 | false | false |

### wake_on -- changes

| gt | bits | value |
|---|---|---|
| 0 | `10000000` | 1 |
| 2 | `10000001` | 1 |
| 4 | `10000011` | 1 |

### wake_on -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 100 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 100 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### wake_off -- changes

| gt | bits | value |
|---|---|---|
| 0 | `10000011` | 1 |
| 2 | `10100010` | 1 |
| 4 | `10100100` | 1 |

### wake_off -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 100 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 100 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### warm_Wn0a0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `10100100` | 1 |
| 2 | `10000100` | 1 |
| 4 | `10000000` | 1 |
| 6 | `10010000` | 1 |
| 8 | `01011000` | 2 |

### warm_Wn0a0 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 100 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 100 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### warm_Wn15a0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `01011000` | 2 |
| 2 | `01011001` | 2 |
| 4 | `01011011` | 2 |
| 6 | `01001011` | 2 |
| 8 | `10000011` | 1 |

### warm_Wn15a0 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 100 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 100 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### warm_Wn0a3 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `10000011` | 1 |
| 2 | `10100010` | 1 |
| 4 | `10100100` | 1 |

### warm_Wn0a3 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 100 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 100 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### warm_Wn15a3 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `10100100` | 1 |
| 2 | `10100101` | 1 |
| 4 | `10100111` | 1 |

### warm_Wn15a3 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 100 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 100 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### v_Wn0a0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `10100111` | 1 |
| 2 | `10000110` | 1 |
| 4 | `10000000` | 1 |
| 6 | `10010000` | 1 |
| 8 | `01011000` | 2 |

### v_Wn0a0 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 100 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 100 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### v_Wn15a0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `01011000` | 2 |
| 2 | `01011001` | 2 |
| 4 | `01011011` | 2 |
| 6 | `01001011` | 2 |
| 8 | `10000011` | 1 |

### v_Wn15a0 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 100 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 100 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### v_Wn0a3 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `10000011` | 1 |
| 2 | `10100010` | 1 |
| 4 | `10100100` | 1 |

### v_Wn0a3 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 100 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 100 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### v_Wn15a3 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `10100100` | 1 |
| 2 | `10100101` | 1 |
| 4 | `10100111` | 1 |

### v_Wn15a3 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 100 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 100 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

## rcon

| roundtrips | limit |
|---|---|
| 6723 | 600000 |

