# Placement rule sheet (DC, 1.20.6-yarn, written by DIRECTOR 7 from the source. Contains no circuit shapes)

> 日本語: [facts-geometry.ja.md](facts-geometry.ja.md)

## redstone_wire (`net/minecraft/block/RedstoneWireBlock.java`)
- Where it can be placed: where the block below satisfies `canRunOnTop` (:224-233, e.g. a solid whose top face is a full square). It cannot be placed in mid-air.
- The level it receives (`getReceivedRedstonePower` :251-275): i = the max emitted power from the blocks on the 6 surrounding faces (`world.getReceivedRedstonePower`; for anything but wire: the output of a gate / torch, redstone_block 15, and **a strongly powered solid emits the level it is receiving**). j = the max power of the neighbouring wires in the 4 horizontal directions, except that **if the neighbour is solid and the block above it is not solid, the wire above that neighbour is seen as well (climbing)**; and if the neighbour is not solid, **the wire below that neighbour is also seen (descending)**. Result = max(i, j − 1). Hence wire → wire is −1, while gate output / strongly powered solid → wire is lossless.
- A solid above breaks the climbing connection (:201, the bl in `getRenderConnectionType`).
- A wire weakly powers the solid it points at (connects to). A weakly powered solid does not power a wire, but a gate can read it at its back (only strong power; note that weak reads as 0 there: a gate's back uses the 2-argument `getEmittedRedstonePower`, which reads a solid's **strong** received power).

## Gate output (`AbstractRedstoneGateBlock.java`)
- `getWeakRedstonePower` :81-88 / `getStrongRedstonePower` :76-78: when powered and the queried direction is the output direction, the level (for a comparator the stored output, for a repeater 15). The output goes into the block at the front: if the front is solid it is **strongly powered** (level = the output), if it is wire it becomes that wire's power (lossless).
- What the back reads (facts-dc): the strong received power of a solid at the front, the power of a wire, a container, a gate output. **The side takes only wire / gate / redstone_block** (a solid's received power cannot be read).
- A gate needs a solid below it (placement condition).

## Relaying through a solid (conductor)
- comparator front → solid S (strongly powered, U) → the wire next to S (U, lossless) → the side of another comparator (U). Or a comparator that reads S directly at its back (U). One S can distribute to several wires / comparator backs (strong power belongs to the whole block, not to a single face).
- A strongly powered solid never powers another solid (strong stops after one step).

## Vertical
- Wire climbing / descending (the rule above): −1 each.
- Putting a wire above or below a strongly powered solid crosses vertically without loss (a wire on the solid's top face can be placed by `canRunOnTop`; below, a floor is needed under the solid to put the wire on).
- comparator / repeater are horizontal only (facing has 4 directions). A torch strongly powers the block above it (not used unless inversion is needed).

## Conditions for mounting on the test instrument (Bench)
- The inputs a / b / cin are placed as **wire cells**, and in a test their level is fixed at 0 or 5 (pinned). The outputs sum / cout are either a wire cell or the solid at a comparator's front (whose level the test reads).
- A container is a barrel, and its contents are declared as an item count (level 5 = 494 items, stack 64).
- The supporting solids (the floor) count towards the total (in a separate column).
