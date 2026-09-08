# worldprobe -- p5_max_merge (run)

writer `worldprobe`, report_kind `bench_trace`, 2026-09-08T11:30:21Z. Units: gt.

run dir `<host-path><session-scratchpad>\w_w4\run_p5_max_merge`

## regimes

| regime | trigger | settle_gt | final_value | final_bits | first_stable_gt | last_change_gt | plateau | truncated |
|---|---|---|---|---|---|---|---|---|
| wake_on | none | 0 | 1 | `1000000000` | 0 | 0 | false | false |
| wake_off | none | 10 | 2 | `0111111111` | 10 | 10 | false | false |
| warm_W30a0 | none | 10 | 1 | `1000000000` | 10 | 10 | false | false |
| warm_W33a0 | none | 10 | 2 | `0101010111` | 10 | 10 | false | false |
| warm_W30a3 | none | 6 | 2 | `0110101011` | 6 | 6 | false | false |
| warm_W33a3 | none | 6 | 2 | `0111111111` | 6 | 6 | false | false |
| v_W30a0 | none | 10 | 1 | `1000000000` | 10 | 10 | false | false |
| v_W33a0 | none | 10 | 2 | `0101010111` | 10 | 10 | false | false |
| v_W30a3 | none | 6 | 2 | `0110101011` | 6 | 6 | false | false |
| v_W33a3 | none | 6 | 2 | `0111111111` | 6 | 6 | false | false |

### wake_on -- changes

| gt | bits | value |
|---|---|---|
| 0 | `1000000000` | 1 |

### wake_on -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 154 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 154 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### wake_off -- changes

| gt | bits | value |
|---|---|---|
| 0 | `1000000000` | 1 |
| 2 | `1011000000` | 1 |
| 4 | `1011110000` | 1 |
| 6 | `1011111100` | 1 |
| 8 | `1011111110` | 1 |
| 10 | `0111111111` | 2 |

### wake_off -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 154 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 154 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### warm_W30a0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `0111111111` | 2 |
| 2 | `0100111111` | 2 |
| 4 | `0100001111` | 2 |
| 6 | `0100000011` | 2 |
| 8 | `0100000001` | 2 |
| 10 | `1000000000` | 1 |

### warm_W30a0 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 154 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 154 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### warm_W33a0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `1000000000` | 1 |
| 2 | `1001000000` | 1 |
| 4 | `1001010000` | 1 |
| 6 | `1001010100` | 1 |
| 8 | `1001010110` | 1 |
| 10 | `0101010111` | 2 |

### warm_W33a0 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 154 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 154 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### warm_W30a3 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `0101010111` | 2 |
| 2 | `0110010111` | 2 |
| 4 | `0110100111` | 2 |
| 6 | `0110101011` | 2 |

### warm_W30a3 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 154 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 154 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### warm_W33a3 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `0110101011` | 2 |
| 2 | `0111101011` | 2 |
| 4 | `0111111011` | 2 |
| 6 | `0111111111` | 2 |

### warm_W33a3 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 154 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 154 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### v_W30a0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `0111111111` | 2 |
| 2 | `0100111111` | 2 |
| 4 | `0100001111` | 2 |
| 6 | `0100000011` | 2 |
| 8 | `0100000001` | 2 |
| 10 | `1000000000` | 1 |

### v_W30a0 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 154 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 154 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### v_W33a0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `1000000000` | 1 |
| 2 | `1001000000` | 1 |
| 4 | `1001010000` | 1 |
| 6 | `1001010100` | 1 |
| 8 | `1001010110` | 1 |
| 10 | `0101010111` | 2 |

### v_W33a0 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 154 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 154 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### v_W30a3 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `0101010111` | 2 |
| 2 | `0110010111` | 2 |
| 4 | `0110100111` | 2 |
| 6 | `0110101011` | 2 |

### v_W30a3 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 154 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 154 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

### v_W33a3 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `0110101011` | 2 |
| 2 | `0111101011` | 2 |
| 4 | `0111111011` | 2 |
| 6 | `0111111111` | 2 |

### v_W33a3 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| barrel_slot3 | before | `100, 65, 154 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |
| barrel_slot3 | after | `100, 65, 154 has the following block data: {count: 55, Slot: 3b, id: "minecraft:cobblestone"}` |

## rcon

| roundtrips | limit |
|---|---|
| 7457 | 600000 |

