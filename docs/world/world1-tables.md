# worldprobe -- world1 (run)

writer `worldprobe`, report_kind `bench_trace`, 2026-09-07T14:20:03Z. Units: gt.

run dir `<host-path><session-scratchpad> development repository--claude-worktrees-nervous-napier-e5d20c\<session-id>\scratchpad\world1-run`

## regimes

| regime | trigger | settle_gt | final_value | final_bits | first_stable_gt | last_change_gt | plateau | truncated |
|---|---|---|---|---|---|---|---|---|
| warm_a0b0c0 | none | 6 | 10 | `01011110000000` | 6 | 6 | false | false |
| warm_a0b0c1 | none | 10 | 6 | `01101110111010` | 10 | 10 | false | false |
| warm_a0b1c0 | none | 2 | 6 | `01101110111001` | 2 | 2 | false | false |
| warm_a0b1c1 | none | 8 | 9 | `10011111110011` | 8 | 8 | false | false |
| warm_a1b0c0 | none | 8 | 6 | `01101110111100` | 8 | 8 | false | false |
| warm_a1b0c1 | none | 8 | 9 | `10011111110110` | 8 | 8 | false | false |
| warm_a1b1c0 | none | 2 | 9 | `10011111110101` | 2 | 2 | false | false |
| warm_a1b1c1 | none | 10 | 5 | `10101101111111` | 10 | 10 | false | false |
| v_a0b0c0 | none | 8 | 10 | `01011110000000` | 8 | 8 | false | false |
| v_a0b0c1 | none | 10 | 6 | `01101110111010` | 10 | 10 | false | false |
| v_a0b1c0 | none | 2 | 6 | `01101110111001` | 2 | 2 | false | false |
| v_a0b1c1 | none | 8 | 9 | `10011111110011` | 8 | 8 | false | false |
| v_a1b0c0 | none | 8 | 6 | `01101110111100` | 8 | 8 | false | false |
| v_a1b0c1 | none | 8 | 9 | `10011111110110` | 8 | 8 | false | false |
| v_a1b1c0 | none | 2 | 9 | `10011111110101` | 2 | 2 | false | false |
| v_a1b1c1 | none | 10 | 5 | `10101101111111` | 10 | 10 | false | false |

### warm_a0b0c0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `01010000000000` | 10 |
| 2 | `01011000000000` | 10 |
| 4 | `01011100000000` | 10 |
| 6 | `01011110000000` | 10 |

### warm_a0b0c0 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| k5_slot7 | before | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |
| k5_slot7 | after | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |

### warm_a0b0c1 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `01011110000000` | 10 |
| 2 | `01011110000010` | 10 |
| 6 | `01011110100010` | 10 |
| 8 | `01011110110010` | 10 |
| 10 | `01101110111010` | 6 |

### warm_a0b0c1 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| k5_slot7 | before | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |
| k5_slot7 | after | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |

### warm_a0b1c0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `01101110111010` | 6 |
| 2 | `01101110111001` | 6 |

### warm_a0b1c0 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| k5_slot7 | before | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |
| k5_slot7 | after | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |

### warm_a0b1c1 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `01101110111001` | 6 |
| 2 | `01101110111011` | 6 |
| 6 | `10101111111011` | 5 |
| 8 | `10011111110011` | 9 |

### warm_a0b1c1 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| k5_slot7 | before | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |
| k5_slot7 | after | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |

### warm_a1b0c0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `10011111110011` | 9 |
| 2 | `10011111110100` | 9 |
| 6 | `01011110110100` | 10 |
| 8 | `01101110111100` | 6 |

### warm_a1b0c0 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| k5_slot7 | before | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |
| k5_slot7 | after | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |

### warm_a1b0c1 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `01101110111100` | 6 |
| 2 | `01101110111110` | 6 |
| 6 | `10101111111110` | 5 |
| 8 | `10011111110110` | 9 |

### warm_a1b0c1 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| k5_slot7 | before | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |
| k5_slot7 | after | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |

### warm_a1b1c0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `10011111110110` | 9 |
| 2 | `10011111110101` | 9 |

### warm_a1b1c0 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| k5_slot7 | before | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |
| k5_slot7 | after | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |

### warm_a1b1c1 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `10011111110101` | 9 |
| 2 | `10011111110111` | 9 |
| 4 | `10011101110111` | 9 |
| 10 | `10101101111111` | 5 |

### warm_a1b1c1 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| k5_slot7 | before | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |
| k5_slot7 | after | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |

### v_a0b0c0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `10101101111111` | 5 |
| 2 | `10101101111000` | 5 |
| 4 | `10101111111000` | 5 |
| 6 | `01101110011000` | 6 |
| 8 | `01011110000000` | 10 |

### v_a0b0c0 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| k5_slot7 | before | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |
| k5_slot7 | after | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |

### v_a0b0c1 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `01011110000000` | 10 |
| 2 | `01011110000010` | 10 |
| 6 | `01011110100010` | 10 |
| 8 | `01011110110010` | 10 |
| 10 | `01101110111010` | 6 |

### v_a0b0c1 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| k5_slot7 | before | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |
| k5_slot7 | after | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |

### v_a0b1c0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `01101110111010` | 6 |
| 2 | `01101110111001` | 6 |

### v_a0b1c0 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| k5_slot7 | before | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |
| k5_slot7 | after | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |

### v_a0b1c1 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `01101110111001` | 6 |
| 2 | `01101110111011` | 6 |
| 6 | `10101111111011` | 5 |
| 8 | `10011111110011` | 9 |

### v_a0b1c1 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| k5_slot7 | before | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |
| k5_slot7 | after | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |

### v_a1b0c0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `10011111110011` | 9 |
| 2 | `10011111110100` | 9 |
| 6 | `01011110110100` | 10 |
| 8 | `01101110111100` | 6 |

### v_a1b0c0 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| k5_slot7 | before | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |
| k5_slot7 | after | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |

### v_a1b0c1 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `01101110111100` | 6 |
| 2 | `01101110111110` | 6 |
| 6 | `10101111111110` | 5 |
| 8 | `10011111110110` | 9 |

### v_a1b0c1 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| k5_slot7 | before | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |
| k5_slot7 | after | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |

### v_a1b1c0 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `10011111110110` | 9 |
| 2 | `10011111110101` | 9 |

### v_a1b1c0 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| k5_slot7 | before | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |
| k5_slot7 | after | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |

### v_a1b1c1 -- changes

| gt | bits | value |
|---|---|---|
| 0 | `10011111110101` | 9 |
| 2 | `10011111110111` | 9 |
| 4 | `10011101110111` | 9 |
| 10 | `10101101111111` | 5 |

### v_a1b1c1 -- nbt (verbatim `data get block` replies)

| read | end | reply |
|---|---|---|
| k5_slot7 | before | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |
| k5_slot7 | after | `103, 65, 103 has the following block data: {count: 46, Slot: 7b, id: "minecraft:cobblestone"}` |

## rcon

| roundtrips | limit |
|---|---|
| 13996 | 60000 |

