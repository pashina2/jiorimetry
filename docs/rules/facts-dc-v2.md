# DC signal-strength rule sheet v2 (incorporates the two source checks from PLACE-ALU-1, 2026-09-07T18:01Z. Original = the given for DERIVE-2, 2026-09-07T13:18Z, read out of 1.20.6-yarn and written by DIRECTOR 7. Contains no circuit shapes)

> 日本語: [facts-dc-v2.ja.md](facts-dc-v2.ja.md)

Unit: level 0..15 (integer). DC = steady state only. Delay, ticks and priming are out of scope.

## comparator (`net/minecraft/block/ComparatorBlock.java`, `AbstractRedstoneGateBlock.java`)
- Orientation: `FACING` = the direction from the gate towards its **input side**. back = pos + FACING, front (output) = pos − FACING, side = the two directions obtained by rotating pos ± FACING 90° horizontally.
- The back value i (`AbstractRedstoneGateBlock.getPower` :130-139 + `ComparatorBlock.getPower` :102-120): if the block at the back is
  - redstone_block → 15; redstone_wire → its power; a block that emitsRedstonePower such as a gate / torch → its strong power (`RedstoneView.getEmittedRedstonePower` :45-62);
  - solid (conductor) → the strong power that block is receiving (the 2-argument getEmittedRedstonePower: for a solid, max(i, receivedStrong));
  - a container (`hasComparatorOutput`) → its comparator output (formula below). If the back is solid and i < 15, then **the block one further on**, if it is a container, gives its value; the same holds for an item frame.
- The side value j (`getMaxInputLevelSides` :141-147): the max of the two sides. Readable sources = redstone_block 15, the power of a wire, **the output of a gate (only while that gate's facing points at the reader, `AbstractRedstoneGateBlock.getWeakRedstonePower` :81-88)**. **A solid's received power cannot be read from the side** (the 3-argument version has no clause for solids). **A torch also reads 0 from the side** (the side reads strong power, and `RedstoneTorchBlock.getStrongRedstonePower` :103-108 is 0 in every direction but DOWN). **A container cannot be read from the side either** (the only thing that reads a container's value is `ComparatorBlock.getPower` at the back).
- Output (`calculateOutputSignal` :74-87): i == 0 → 0. j > i → 0. subtract → i − j. compare → i.
- The output goes into the block at the front: if the front is solid it is strong power (level = the output), if it is wire it becomes that wire's power. A comparator beyond the front can read it at its back.

## The level of a container (`ScreenHandler.calculateComparatorOutput` :1023-1033, `MathHelper.lerpPositive` :665-668)
- f = ( Σ_slot count / maxCount(item) ) / slots. level = floor(f × 14) + (f > 0 ? 1 : 0). Empty → 0, full → 15.
- A barrel has 27 slots. For an item with a stack limit of 64, the item count n needed for level k (1 ≤ k ≤ 14) is the n whose f = n / (64·27) satisfies (k−1)/14 ≤ f < k/14. Examples: n = 1 → 1, n = 124 → 2, n = 247 → 3, … 15 is a full 1728.
- Placed at a comparator's back it is a constant source. Its value is easy to change (so it can also be a source of a variable value).

## The other parts (DC)
- redstone_block: the constant 15 (15 from the back and from the side alike).
- repeater (`RepeaterBlock`): if back > 0 the output is 15, else 0 (normalisation). Only gates act on the side (lock).
- torch: 15 if the block it is attached to is not receiving power, 0 if it is (inversion). It strong-powers the block above it. **From a comparator's back it reads as weak 15** (the 2-argument `RedstoneView.getEmittedRedstonePower` :66-73 reads weak, and a torch's weak is 15 in every direction but UP :64-69), but **from the side it is 0** (see the side clause above).
- redstone_wire: propagates from a neighbouring wire at −1, and takes the level directly from a gate / torch / redstone_block / strongly-powered solid. Readable from both the back and the side. Attenuation makes subtraction a matter of distance, but **putting a constant on a subtract's side subtracts in one block**, so distance need not be used.
- Conductor (solid): `AbstractBlock.Settings.solidBlockPredicate` = full cube (the default, :1179) and not removed by `solidBlock(Blocks::never)` (all kinds of glass, observer, redstone_block, leaves, ice, glowstone, sea_lantern, beacon, moving piston, tnt, scaffolding, powder_snow, copper_grate, copper_bulb, dripstone, chorus_flower and bamboo are non-conductors). Wool and smooth_stone are conductors.

## The parts that may be used
comparator (compare / subtract), container (barrel), redstone_block, redstone_wire, solid (conductor), repeater, torch. A lever is an input. A lamp may be used to observe an output.
