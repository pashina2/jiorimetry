#!/usr/bin/env python3
"""tools/llmgen/machine.py -- the library's rules, executable: a
block-level game-tick machine over a placed artifact.

DESIGN section 2 ('the same rules give three things'): the rest state the
program.json must spell (blockstate `power` / `lit` / `powered` are computed,
never typed), the gt-indexed prediction dynharness's trace is compared with,
and the dust connection state the placer writes. Every rule is one of the
1.20.6-yarn functions the library cites, transcribed by name:

    weak / strong        getWeakRedstonePower / getStrongRedstonePower
    emitted              RedstoneView.getEmittedRedstonePower (:66-73)
    received             RedstoneView.getReceivedRedstonePower (the 6-face max)
    dust_input           RedstoneWireBlock.getReceivedRedstonePower (:251-275)
    connection           RedstoneWireBlock.getRenderConnectionType (:200-219)
    placement_state      RedstoneWireBlock.getPlacementState line-extension rule
    torch / repeater / lamp  their neighborUpdate + scheduledTick pairs

Direction convention inside the power reads is vanilla's own: `d` is the
direction FROM THE RECEIVER TOWARD THE EMITTER (the argument that reaches
getWeakRedstonePower), so a reader standing below a dust asks with d="up".

Events inside one gt fire in TickPriority order (iteration 2 of the D-1
record) and, within one priority, in INSERTION order -- the order the ticks
were scheduled in, which is what the world does:

    tickOrder    minecraft-src 1.20.6-yarn world/World.java:128, :1042-1044
                 (`private long tickOrder;` / `return this.tickOrder++;`)
    subTickOrder minecraft-src 1.20.6-yarn world/tick/Tick.java:92-93
                 (createOrderedTick puts that counter in the OrderedTick)
    the order    minecraft-src 1.20.6-yarn world/tick/OrderedTick.java:24-30
                 (BASIC_COMPARATOR = priority, then subTickOrder), applied
                 while collecting (world/tick/WorldTickScheduler.java:169)
                 into the FIFO the ticks are then run from (:45, :183-185)

(LOOKUP-1, `notes/2026-09-06-cellsearch-zero-director.md` section 2;
The operator's own record of that circuit says the same.) Until
2026-09-06 this docstring and `step` claimed
the world ordered equal-priority events by a position hash and sorted by
position instead; that was wrong, and comparator priming -- a row of
comparators scheduled in one gt that resolves in the order it was booked --
cannot be reproduced by a position sort.

Containers (MACH-2): ComparatorBlock.getPower :102-120 reads a container
behind the comparator and REPLACES the redstone level with its
getComparatorOutput. The contents that value is computed from live in the
block entity, which no scan row carries (`notes/2026-09-06-state-holes-frame.md`
hole 1), so they are handed to the machine as a `block_entities` mapping whose
provenance is `declared`, never `measured`. A container the caller did not
declare is UNKNOWN, not empty: its comparator's output signal is None, and
reading that comparator raises instead of quietly answering 0.

Item transport (MACH-3): a hopper moves items, so a container's contents are no
longer only an INPUT to the comparator rule -- they are state the machine
advances. Three things arrive with it, each transcribed by function name:

    hopper_server_tick      HopperBlockEntity.serverTick :103-110
    hopper_insert_extract   HopperBlockEntity.insertAndExtract :112-131
    dropper_dispense        DropperBlock.dispense :52-84

and one thing that cannot be transcribed, said out loud rather than guessed:
the order block entities tick in. World.blockEntityTickers (world/World.java:103)
is a plain List appended in creation order (:478) and iterated in that order
(:489) -- no position sort, and no scan row carries it. So `be_tick_order` is
DECLARED, like the block-entity contents themselves, and a machine that was
handed no order uses the order the caller declared its block entities in. Two
different orders give two different gt for the same hopper column, which is a
fact about the world, not about this file.

Inside one game tick the world runs scheduled BLOCK ticks first, then entities,
then block entities (server/world/ServerWorld.java:327 / the entityList loop /
:385), and `step` does the same.

The in-flight tick queue (HOLES-2, hole 3 of the same frame) is the other
initial state a scan row cannot carry: a capture is the block states at one
instant and holds no future event, so a machine built from one starts at rest.
For a circuit captured mid-flight -- a primed comparator, a running clock --
the state IS the queue. `Machine(blocks, block_ticks=[...])` seeds it, in
`regioncap.decode_ticks`'s own row shape, and `block_tick_report` says whether
the queue was `declared` (the caller asserted it), `measured` (read out of the
world's chunk NBT) or `none` (never supplied -- not the same claim as an empty
measured queue). See `_load_ticks`.

What this machine does NOT model, said out loud: observers / pistons / rails
(rows in the library, no rule here yet -- an unknown block is refused, never
inert; the comparator rule arrived with D-2), torch burnout, chunk effects.
Entities are the deliberate omission inside the container branch too: the second
half of ComparatorBlock.getPower :110-117 also reads an item frame on the far
block, and an item frame is an entity (hole 2 of the same frame), so a
comparator aimed through a solid block at an item frame predicts the container
value or the wire level, never the frame's rotation. The one entity that IS
modelled is the item entity a dropper throws, and only in the minimal form the
storage frame asks for -- see ITEM_ENTITY_PROVENANCE, which says in one string
why its position is approximate and a gt read off it is not promotion-grade.
"""

import math as _math
import struct as _struct

from library import (FACES, OPPOSITE, HORIZONTAL, PARTS, DUST, REPEATER,
                     COMPARATOR, OBSERVER, TORCH, WALL_TORCH, LEVER, REDSTONE_BLOCK,
                     LAMP, SMOOTH_STONE, TORCH_GT, REPEATER_GT_PER_DELAY,
                     COMPARATOR_GT, LAMP_OFF_GT, HOPPER, DROPPER, DISPENSER,
                     DISPENSER_GT, HOPPER_COOLDOWN_GT)

#: Direction.rotateYClockwise, for a gate's two sides.
CLOCKWISE = {"north": "east", "east": "south", "south": "west", "west": "north"}


#: net/minecraft/world/tick/TickPriority: EXTREMELY_HIGH -3, VERY_HIGH -2,
#: HIGH -1, NORMAL 0 (lower fires first inside one game tick).
PRIORITY_VERY_HIGH, PRIORITY_HIGH, PRIORITY_NORMAL = -2, -1, 0


class MachineError(ValueError):
    """A block this machine has no rule for, or an inconsistent state."""


SOLID = {SMOOTH_STONE, LAMP, REDSTONE_BLOCK}
KNOWN = SOLID | {DUST, REPEATER, COMPARATOR, TORCH, WALL_TORCH, LEVER}
DUST_SIDES = {"north": "north", "south": "south", "east": "east", "west": "west"}


# ------------------------------------------------------------------ containers
#: Every block whose `hasComparatorOutput(state)` is true in 1.20.6-yarn, with
#: the rule its `getComparatorOutput` uses, transcribed by function name the
#: way the rest of this file is. Keys:
#:
#:   rule    which arithmetic getComparatorOutput runs
#:   solid   isSolidBlock, taken from GAP-7's
#:           `data/workbench/physics/solidity.json`; None means GAP-7 has no
#:           rule for that class and this machine REFUSES the block instead of
#:           guessing (test_llmgen pins every row against that file, so drift
#:           there fails the suite rather than a prediction)
#:   emits   emitsRedstonePower(); a block that emits has redstone behaviour
#:           this machine has no rule for, so it is refused as a block too
#:   source  file:line in minecraft-src 1.20.6-yarn
#:
#: Refusing a row is not the same as not knowing its arithmetic: every rule
#: here is transcribed and pinned, and `comparator_output` answers for any of
#: them. What `solid: None` / `emits: True` withholds is admission into the
#: BLOCK vocabulary, which needs a solidity rule and a redstone rule as well.
CONTAINER_RULE = {}

_SHULKER_COLORS = ("white", "orange", "magenta", "light_blue", "yellow", "lime",
                   "pink", "gray", "light_gray", "cyan", "purple", "blue",
                   "brown", "green", "red", "black")
_BULBS = ("copper_bulb", "exposed_copper_bulb", "weathered_copper_bulb",
          "oxidized_copper_bulb", "waxed_copper_bulb", "waxed_exposed_copper_bulb",
          "waxed_weathered_copper_bulb", "waxed_oxidized_copper_bulb")


def _container_row(ids, rule, solid, source, emits=False, **params):
    for block in ids:
        CONTAINER_RULE[block] = dict(rule=rule, solid=solid, source=source,
                                     emits=emits, **params)


# ScreenHandler.calculateComparatorOutput over a fixed slot count.
_container_row(["minecraft:barrel"], "inventory", True,
               "BarrelBlock.java:89-97", slots=27)
_container_row(["minecraft:chest", "minecraft:trapped_chest"], "inventory", None,
               "ChestBlock.java:353-361 (TrappedChestBlock.java:22 inherits it); a "
               "double chest is one DoubleInventory, so a pair is declared slots=54",
               slots=27)
_container_row(["minecraft:hopper"], "inventory", False,
               "HopperBlock.java:177-185", slots=5)
_container_row(["minecraft:dispenser", "minecraft:dropper"], "inventory", True,
               "DispenserBlock.java:165-173 (DropperBlock.java:28 inherits it)", slots=9)
_container_row(["minecraft:furnace", "minecraft:blast_furnace", "minecraft:smoker"],
               "inventory", True, "AbstractFurnaceBlock.java:83-91", slots=3)
_container_row(["minecraft:shulker_box"]
               + ["minecraft:%s_shulker_box" % c for c in _SHULKER_COLORS],
               "inventory", None, "ShulkerBoxBlock.java:236-244", slots=27)
_container_row(["minecraft:brewing_stand"], "inventory", None,
               "BrewingStandBlock.java:99-107", slots=5)
_container_row(["minecraft:decorated_pot"], "inventory", None,
               "DecoratedPotBlock.java:246-254 over SingleStackInventory.java:28-51",
               slots=1)

# Blockstate-only rules: never unknown, because a scan row carries the state.
_container_row(["minecraft:cake"], "cake", None, "CakeBlock.java:129-137")
_container_row(["minecraft:candle_cake"], "const", None,
               "CandleCakeBlock.java:127-130 -> CakeBlock.java:44", value=14)
_container_row(["minecraft:cauldron"], "const", None,
               "AbstractCauldronBlock.java:89-92 declares it, and CauldronBlock does "
               "not override getComparatorOutput, so AbstractBlock.java:885-887 says 0",
               value=0)
_container_row(["minecraft:water_cauldron", "minecraft:powder_snow_cauldron"],
               "state_int", None, "LeveledCauldronBlock.java:104-107 (level 1..3)",
               prop="level")
_container_row(["minecraft:lava_cauldron"], "const", None,
               "LavaCauldronBlock.java:47-50", value=3)
_container_row(["minecraft:composter"], "state_int", None,
               "ComposterBlock.java:306-314 (level 0..8)", prop="level")
_container_row(["minecraft:beehive", "minecraft:bee_nest"], "state_int", True,
               "BeehiveBlock.java:86-94 (honey_level 0..5)", prop="honey_level")
_container_row(["minecraft:respawn_anchor"], "charges", True,
               "RespawnAnchorBlock.java:171-183")
_container_row(["minecraft:end_portal_frame"], "state_flag15", None,
               "EndPortalFrameBlock.java:67-78", prop="eye")
_container_row(["minecraft:%s" % b for b in _BULBS], "state_flag15", False,
               "BulbBlock.java:67-75", prop="lit")

# Block-entity rules with their own arithmetic.
_container_row(["minecraft:lectern"], "lectern", None,
               "LecternBlock.java:240-252 over LecternBlockEntity.java:178-181")
_container_row(["minecraft:jukebox"], "jukebox", True,
               "JukeboxBlock.java:100-114 over MusicDiscItem.java:70-72")
_container_row(["minecraft:chiseled_bookshelf"], "bookshelf", True,
               "ChiseledBookshelfBlock.java:224-240 over "
               "ChiseledBookshelfBlockEntity.java:36,147-148")
_container_row(["minecraft:crafter"], "crafter", True,
               "CrafterBlock.java:70-83 over CrafterBlockEntity.java:247-255")
_container_row(["minecraft:command_block", "minecraft:chain_command_block",
                "minecraft:repeating_command_block"], "command", True,
               "CommandBlock.java:141-153")
_container_row(["minecraft:detector_rail"], "detector_rail", False,
               "DetectorRailBlock.java:145-165 -- it reads a MINECART, an entity",
               emits=True)
_container_row(["minecraft:sculk_sensor", "minecraft:calibrated_sculk_sensor"],
               "sculk", None,
               "SculkSensorBlock.java:262-275 (CalibratedSculkSensorBlock.java:28 "
               "inherits it) over SculkSensorBlockEntity.java:81-83", emits=True)

#: Rules whose value cannot be read off the blockstate.
BLOCK_ENTITY_RULES = frozenset(("inventory", "lectern", "jukebox", "bookshelf",
                                "crafter", "command", "sculk", "detector_rail"))

#: Inventory.getMaxCountPerStack default -- Inventory.java:101-103.
DEFAULT_MAX_COUNT_PER_STACK = 99


def _f32(value):
    """Round a Python double to the nearest float: every step of
    ScreenHandler.calculateComparatorOutput happens in Java `float`."""
    return _struct.unpack("f", _struct.pack("f", value))[0]


def floor_f(value):
    """MathHelper.floor(float) :110-113 -- floor toward minus infinity."""
    i = int(value)
    return i - 1 if value < i else i


def lerp_positive(delta, start, end):
    """MathHelper.lerpPositive :665-668. With (0, 15) this is the classic
    `floor(delta * 14) + (1 if delta > 0 else 0)`."""
    i = end - start
    return start + floor_f(_f32(delta * _f32(float(i - 1)))) + (1 if delta > 0.0 else 0)


def inventory_output(items, slots, max_count_per_stack=DEFAULT_MAX_COUNT_PER_STACK):
    """ScreenHandler.calculateComparatorOutput(Inventory) :1024-1034.

    `items` is the declared contents: an iterable of {"count": n,
    "max_count": m}, m defaulting to a normal stack of 64. A slot the caller
    left out is empty, which is exactly what `ItemStack.isEmpty()` skips, so
    the same fill can be declared in any number of ways.
    """
    if slots is None or slots <= 0:
        raise MachineError("an inventory needs a positive slot count, not %r" % (slots,))
    f = 0.0
    n = 0
    for stack in items or ():
        count = int(stack.get("count", 0))
        if count == 0:
            continue
        n += 1
        if n > slots:
            raise MachineError("%d non-empty stacks declared for %d slots" % (n, slots))
        cap = min(int(max_count_per_stack), int(stack.get("max_count", 64)))
        f = _f32(f + _f32(float(count) / float(cap)))
    f = _f32(f / float(slots))
    return lerp_positive(f, 0, 15)


def comparator_output(name, props, block_entity=None):
    """getComparatorOutput(state, world, pos) for one container block.

    Returns the 0..15 signal, or None when the rule needs a block entity the
    caller did not declare -- the value is UNKNOWN, and the difference between
    unknown and empty is the whole of hole 1.
    """
    row = CONTAINER_RULE.get(name)
    if row is None:
        raise MachineError("%s has no comparator-output rule" % name)
    rule = row["rule"]
    if rule == "const":
        return row["value"]
    if rule == "state_int":
        return int(props[row["prop"]])
    if rule == "state_flag15":
        return 15 if props[row["prop"]] == "true" else 0
    if rule == "cake":
        return (7 - int(props["bites"])) * 2                # CakeBlock.java:134-136
    if rule == "charges":                                   # RespawnAnchorBlock.java:175-177
        return floor_f(_f32(_f32(float(int(props["charges"]) - 0) / 4.0) * 15.0))
    if rule == "lectern":
        if props.get("has_book") == "false":                # LecternBlock.java:246-250
            return 0
        if block_entity is None:
            return None
        pages = int(block_entity.get("page_count", 1))
        page = int(block_entity.get("page", 0))
        f = _f32(float(page) / _f32(float(pages) - 1.0)) if pages > 1 else 1.0
        return floor_f(_f32(f * 14.0)) + (1 if block_entity.get("has_book", True) else 0)
    if rule == "jukebox":
        if props.get("has_record") == "false":              # JukeboxBlock.java:106-112
            return 0
        if block_entity is None:
            return None
        return int(block_entity.get("disc_comparator_output", 0))
    if rule == "bookshelf":                                 # ChiseledBookshelfBlock.java:231-238
        if block_entity is None:
            return None
        return int(block_entity.get("last_interacted_slot", -1)) + 1
    if rule == "crafter":                                   # CrafterBlockEntity.java:247-255
        if block_entity is None:
            return None
        items = block_entity.get("items") or ()
        disabled = set(block_entity.get("disabled_slots") or ())
        filled = set(i for i, st in enumerate(items) if int(st.get("count", 0)) > 0)
        return len(filled | disabled)
    if rule == "command":                                   # CommandBlock.java:147-151
        if block_entity is None:
            return None
        return int(block_entity.get("success_count", 0))
    if rule == "sculk":
        if props.get("sculk_sensor_phase") != "active":     # SculkSensorBlock.java:269-273
            return 0
        if block_entity is None:
            return None
        return int(block_entity.get("frequency", 0))
    if rule == "detector_rail":
        if props.get("powered") == "false":                 # DetectorRailBlock.java:152-164
            return 0
        if block_entity is None:
            return None
        return int(block_entity.get("cart_output", 0))
    if rule == "inventory":
        if block_entity is None:
            return None
        return inventory_output(block_entity.get("items") or (),
                                int(block_entity.get("slots", row["slots"])),
                                int(block_entity.get("max_count_per_stack",
                                                     DEFAULT_MAX_COUNT_PER_STACK)))
    raise MachineError("no transcription for container rule %r" % rule)


# ------------------------------------------------------------- item transport
#: HopperBlockEntity.java:42-43 and :46. `transferCooldown` is -1 on
#: construction, but serverTick's `--` then setTransferCooldown(0) means an idle
#: hopper rests at 0 and retries every gt, so 0 is this machine's default.
HOPPER_SLOTS = 5                                    # HopperBlockEntity.java:43
DISPENSER_SLOTS = 9                                 # DispenserBlockEntity.java:23
DEFAULT_STACK_MAX = 64                              # ItemStack.getMaxCount default

#: Containers this machine will MOVE items through. Every one of them is a
#: plain `Inventory` in 1.20.6-yarn. A furnace, blast furnace, smoker and
#: brewing stand are SidedInventory (their getAvailableSlots / canInsert /
#: canExtract decide which face reaches which slot), a shulker box is
#: SidedInventory too, a decorated pot is a SingleStackInventory and a crafter
#: has its own disabled-slot rule -- none of those side rules is transcribed
#: here, so transport REFUSES them instead of guessing. Their COMPARATOR output
#: is unaffected: `comparator_output` still answers for all of them.
TRANSPORT_INVENTORY = frozenset((
    "minecraft:barrel", "minecraft:chest", "minecraft:trapped_chest",
    HOPPER, DROPPER, DISPENSER,
))

#: ItemEntity.java:129-132 getGravity, and tick()'s drag / bounce :164-175.
ITEM_GRAVITY = 0.04
ITEM_DRAG = 0.98
ITEM_GROUND_BOUNCE = -0.5
#: AbstractBlock.Settings default slipperiness (Block.getSlipperiness), used by
#: ItemEntity.tick :167-169 for the on-ground horizontal drag.
DEFAULT_SLIPPERINESS = 0.6
#: EntityType.java:256 -- dimensions(0.25, 0.25) for an item.
ITEM_WIDTH = 0.25
ITEM_HEIGHT = 0.25
#: DispenserBlock.getOutputLocation :156-163 (facingOffset 0.7) and
#: ItemDispenserBehavior.spawnItem's y offsets.
DISPENSER_FACING_OFFSET = 0.7
ITEM_SPAWN_DROP_Y_AXIS = 0.125
ITEM_SPAWN_DROP_HORIZONTAL = 0.15625
#: Hopper.java INPUT_AREA_SHAPE = createCuboidShape(0, 11, 0, 16, 32, 16), in
#: block units and relative to the hopper's own block corner.
HOPPER_INPUT_AREA = (0.0, 11.0 / 16.0, 0.0, 1.0, 2.0, 1.0)

#: One string a result carries beside any number that came off an item entity.
#: ItemDispenserBehavior.spawnItem draws the ejection velocity from
#: Random.nextTriangular (util/math/random/Random.java:105-107), so the world
#: SAMPLES it: mode (offsetX*g, 0.2, offsetZ*g) with g = nextDouble()*0.1 + 0.2
#: in [0.2, 0.3). This machine carries the mode with g fixed at 0.25 and no
#: deviation, models no horizontal block collision and no stack merging, and
#: uses the caller's `entity_id` (default 0) in ItemEntity.tick's
#: `(age + getId()) % 4` move-skip -- the world's entity id is not knowable
#: from a scan. A gt read off an item entity is therefore APPROXIMATE and is
#: not evidence for a timing claim; a transfer between two containers is not.
ITEM_ENTITY_PROVENANCE = (
    "approximate: item-entity velocity is the mode of the world's triangular "
    "distribution (ItemDispenserBehavior.spawnItem), horizontal collision and "
    "stack merging are not modelled, and the move-skip uses a declared "
    "entity_id; container-to-container transfers are exact"
)


def make_stack(item_id, count=1, max_count=DEFAULT_STACK_MAX):
    """One ItemStack. `id` is the registry name; item components are NOT
    modelled, so `stacks_mergeable` compares ids alone (see its docstring)."""
    return {"id": str(item_id), "count": int(count), "max_count": int(max_count)}


def stack_is_empty(stack):
    """ItemStack.isEmpty()."""
    return stack is None or int(stack.get("count", 0)) <= 0


def stack_max(stack):
    return int(stack.get("max_count", DEFAULT_STACK_MAX))


def stacks_mergeable(first, second):
    """HopperBlockEntity.canMergeItems :390-392 over
    ItemStack.areItemsAndComponentsEqual.

    Item COMPONENTS (the 1.20.5+ replacement for item NBT) are not modelled:
    two stacks with the same registry id merge here even if the world would
    keep an enchanted one apart. A spec that needs that distinction must give
    the two stacks different ids.
    """
    return (int(first.get("count", 0)) <= stack_max(first)
            and first.get("id") == second.get("id"))


def normalise_slots(items, slots):
    """The declared `items` of a container, as a fixed-length slot list.

    `items` is what MACH-2 already accepted -- an iterable of
    {"id":, "count":, "max_count":} -- read positionally: entry i is slot i, a
    missing or zero-count entry is an empty slot. `items` may also be a mapping
    of slot index -> stack, which is what a `data get block ... Items` read
    looks like once its Slot bytes are used.
    """
    out = [None] * int(slots)
    if items is None:
        return out
    pairs = items.items() if isinstance(items, dict) else enumerate(items)
    for key, stack in pairs:
        i = int(key)
        if not 0 <= i < int(slots):
            raise MachineError("slot %d declared for a container with %d slots"
                               % (i, int(slots)))
        if stack_is_empty(stack):
            continue
        out[i] = make_stack(stack.get("id", "minecraft:stone"),
                            int(stack.get("count", 0)),
                            int(stack.get("max_count", DEFAULT_STACK_MAX)))
    return out


def boxes_intersect(a, b):
    """Box.intersects -- half-open on neither side, as the world has it."""
    return (a[0] < b[3] and a[3] > b[0]
            and a[1] < b[4] and a[4] > b[1]
            and a[2] < b[5] and a[5] > b[2])


def parse_pos(key):
    """A `block_entities` key: either "x,y,z" or an (x, y, z) tuple."""
    if isinstance(key, str):
        return tuple(int(t) for t in key.split(","))
    return tuple(int(t) for t in key)


def add(pos, d):
    v = FACES[d]
    return (pos[0] + v[0], pos[1] + v[1], pos[2] + v[2])


def is_solid(blocks, pos):
    entry = blocks.get(pos)
    if entry is None:
        return False
    if entry[0] in SOLID:
        return True
    row = CONTAINER_RULE.get(entry[0])
    return bool(row["solid"]) if row is not None else False


def connects_to(blocks, pos, d):
    """RedstoneWireBlock.connectsTo(state, direction) -- :372-381."""
    entry = blocks.get(pos)
    if entry is None:
        return False
    name, props = entry
    if name == DUST:
        return True
    if name == REPEATER:
        facing = props.get("facing")
        return d is not None and (facing == d or facing == OPPOSITE[d])
    if name == OBSERVER:                                   # :377-378
        return d == props.get("facing")
    return name in (TORCH, WALL_TORCH, LEVER, REDSTONE_BLOCK, COMPARATOR)   # emitsRedstonePower (:380)


def connection(blocks, pos, d):
    """getRenderConnectionType(world, pos, direction) -> none | side | up."""
    above_free = not is_solid(blocks, add(pos, "up"))
    n = add(pos, d)
    if above_free and is_solid(blocks, n) and blocks.get(add(n, "up"), (None,))[0] == DUST:
        return "up"          # smooth stone is side-solid-full-square
    if connects_to(blocks, n, d):
        return "side"
    if not is_solid(blocks, n) and blocks.get(add(n, "down"), (None,))[0] == DUST:
        return "side"
    return "none"


def placement_state(blocks, pos):
    """The four connection props the world settles a dust to (getPlacementState
    over getDefaultWireState, then the single-axis line extension)."""
    conn = {d: connection(blocks, pos, d) for d in HORIZONTAL}
    if all(v == "none" for v in conn.values()):
        return conn                                   # a dot
    ns_free = conn["north"] == "none" and conn["south"] == "none"
    ew_free = conn["east"] == "none" and conn["west"] == "none"
    out = dict(conn)
    if ns_free:
        for d in ("west", "east"):
            if conn[d] == "none":
                out[d] = "side"
    if ew_free:
        for d in ("north", "south"):
            if conn[d] == "none":
                out[d] = "side"
    return out


#: The blocks whose `scheduledTick` this machine transcribes -- and therefore
#: the only positions an initial tick queue may name. `_fire` has a branch for
#: exactly these; a pending tick anywhere else would be silently swallowed
#: (dirtied and dropped), which is the failure this tuple exists to refuse.
TICKABLE = (TORCH, WALL_TORCH, REPEATER, LAMP, COMPARATOR)

#: Where an initial tick queue came from. `declared` = the caller asserted it.
#: `measured` = it was read out of the world's own `block_ticks` (regioncap).
#: `none` = the queue was never supplied, which is NOT the same claim as an
#: empty measured queue and is kept distinguishable for that reason.
TICK_PROVENANCE = ("declared", "measured")


class Machine:
    def __init__(self, blocks, block_entities=None, be_tick_order=None,
                 block_ticks=None, block_ticks_provenance="declared"):
        #: {pos: {...}} -- the DECLARED initial block-entity state (MACH-2).
        #: No scan row carries it, so its provenance is `declared`: the caller
        #: asserted it, the world was not asked. `block_entity_report` hands
        #: that back so a result can say so.
        self.block_entities = {}
        for key, value in (block_entities or {}).items():
            self.block_entities[parse_pos(key)] = dict(value)
        self.blocks = {}
        for pos, (name, props) in blocks.items():
            if name in CONTAINER_RULE:
                row = CONTAINER_RULE[name]
                if row["solid"] is None:
                    raise MachineError(
                        f"no solidity rule for {name} at {pos}: GAP-7's "
                        f"data/workbench/physics/solidity.json has none for its class, "
                        f"and this machine refuses a block rather than guess whether "
                        f"dust connects over it (its comparator output IS transcribed: "
                        f"machine.comparator_output)")
                if row["emits"]:
                    raise MachineError(
                        f"{name} at {pos} emits redstone power ({row['source']}) and "
                        f"this machine has no rule for that; its comparator output IS "
                        f"transcribed (machine.comparator_output)")
            elif name not in KNOWN:
                raise MachineError(f"no rule for {name} at {pos}")
            self.blocks[pos] = (name, dict(props))
        for pos in self.block_entities:
            if pos not in self.blocks:
                raise MachineError(f"a block entity was declared at {pos}, where there "
                                   f"is no block")
            if self.blocks[pos][0] not in CONTAINER_RULE:
                raise MachineError(f"a block entity was declared at {pos}, which is a "
                                   f"{self.blocks[pos][0]} and has no comparator output")
        self.gt = 0
        #: pos -> (gt the scheduled tick fires, TickPriority, subTickOrder)
        self.pending = {}
        #: World.tickOrder -- the counter Tick.createOrderedTick reads; it only
        #: ever increases, so it orders equal-priority events by booking time
        self.tick_order = 0
        #: HOLE 3 (MACH-3 / HOLES-2): the in-flight queue this machine starts
        #: from. Without it every prediction begins at rest, which is wrong for
        #: any capture taken while the circuit was mid-flight -- comparator
        #: priming and a clock's phase ARE the queue and nothing else.
        self.block_ticks_provenance = "none"
        self.initial_ticks = []
        if block_ticks is not None:
            self._load_ticks(block_ticks, block_ticks_provenance)
        self.wires_give = True
        #: ComparatorBlockEntity.outputSignal -- block-entity state the
        #: blockstate does not carry; 0 on placement, written by update() :165
        self.cmp_out = {pos: 0 for pos, (name, _p) in self.blocks.items() if name == COMPARATOR}
        for pos, (name, props) in self.blocks.items():
            if name == DUST:
                props.update(placement_state(self.blocks, pos))
                props.setdefault("power", "0")
        # index by class (D-2): the synchronous settle walks a worklist of
        # dust cells instead of every block, which is what made a 3400-block
        # adder predictable in seconds; the fixpoint is the same (pinned by
        # the D-1 half adder prediction fixture, byte for byte)
        self._dust = [pos for pos, (name, _p) in self.blocks.items() if name == DUST]
        self._lamps = [pos for pos, (name, _p) in self.blocks.items() if name == LAMP]
        self._parts = [pos for pos, (name, _p) in self.blocks.items()
                       if name in TICKABLE]
        self._near = {}
        self._dirty = set(self._dust)
        self._init_transport(be_tick_order)
        # A comparator reading a container nobody declared is UNDEFINED from
        # the first settle, not 0: mark it before anything can read it.
        for pos, (name, _props) in self.blocks.items():
            if name == COMPARATOR and self.back_container_undeclared(pos):
                self.cmp_out[pos] = None

    def _load_ticks(self, block_ticks, provenance):
        """Seed `pending` from a tick queue -- hole 3 of the state-holes frame.

        The row shape is `regioncap.decode_ticks`'s, so a queue read out of a
        save's chunk NBT can be handed over untouched:

            {"pos": [x, y, z], "id": "minecraft:repeater", "delay": 2,
             "priority": 0}                 (`nbt` and anything else ignored)

        `type` is accepted as a spelling of `id` and `sub_tick_order` /
        `subTickOrder` of the booking counter. `delay` is RELATIVE, exactly as
        vanilla stores it (`Tick.t` is "triggerTick - currentTick" on save), so
        delay 1 fires on the first `step()`.

        Two refusals rather than a quiet answer. A position this machine has no
        `scheduledTick` rule for is rejected: `_fire` has no branch for it, so
        the tick would be dropped and the caller would read the resulting rest
        state as a prediction. And a declared `id` that disagrees with the
        block actually at that position is rejected, because the disagreement
        means the queue and the blocks came from different worlds."""
        if provenance not in TICK_PROVENANCE:
            raise MachineError(
                "block_ticks provenance must be one of %s, not %r -- a queue "
                "the caller asserted and a queue read out of the world are "
                "different claims" % ("/".join(TICK_PROVENANCE), provenance))
        self.block_ticks_provenance = provenance
        for index, row in enumerate(block_ticks):
            if "pos" not in row:
                raise MachineError(f"scheduled tick {index} has no pos: {row!r}")
            pos = parse_pos(row["pos"])
            if pos not in self.blocks:
                raise MachineError(f"a scheduled tick was given at {pos}, where "
                                   f"there is no block")
            name = self.blocks[pos][0]
            if name not in TICKABLE:
                raise MachineError(
                    f"a scheduled tick was given at {pos}, which is a {name}: "
                    f"this machine transcribes scheduledTick for "
                    f"{'/'.join(TICKABLE)} only, and would drop the tick")
            declared_id = row.get("id", row.get("type"))
            if declared_id is not None and declared_id != name:
                raise MachineError(
                    f"the tick queue says {declared_id} at {pos} but the blocks "
                    f"say {name}: the queue and the blocks are not the same "
                    f"world")
            if pos in self.pending:
                raise MachineError(f"two scheduled ticks were given at {pos}; "
                                   f"ChunkTickScheduler holds one per (pos, type)")
            delay = int(row.get("delay", row.get("t", 0)))
            if delay < 0:
                raise MachineError(f"scheduled tick at {pos} has delay {delay}; "
                                   f"a queue holds the future, not the past")
            priority = int(row.get("priority", row.get("p", PRIORITY_NORMAL)))
            sub = row.get("sub_tick_order", row.get("subTickOrder"))
            sub = index if sub is None else int(sub)
            self.pending[pos] = (self.gt + delay, priority, sub)
            self.initial_ticks.append({"pos": "%d,%d,%d" % pos, "block": name,
                                       "delay": delay, "priority": priority,
                                       "sub_tick_order": sub})
        if self.pending:
            self.tick_order = max(sub for _w, _p, sub in
                                  self.pending.values()) + 1

    def block_tick_report(self):
        """What a result should carry about hole 3 (frame section 1).

        `provenance` is `none` when no queue was supplied at all -- which is a
        different statement from a `measured` queue that came back empty, and
        the difference is the whole point of recording it. Every capture this
        repo holds today is the second case (REGION-1 read `block_ticks` = 0
        for B-??, B-03 and B-04), and a reader cannot tell the two apart from
        an empty list alone."""
        return {
            "provenance": self.block_ticks_provenance,
            "initial": list(self.initial_ticks),
            "pending_now": [{"pos": "%d,%d,%d" % pos, "fires_at_gt": when,
                             "priority": prio, "sub_tick_order": sub}
                            for pos, (when, prio, sub)
                            in sorted(self.pending.items())],
            "gt": self.gt,
        }

    def _dust_near(self, pos):
        """Dust cells whose input can depend on the state at `pos`: within
        Chebyshev distance 2 (a torch reaches a dust through the block above
        it; a repeater through the block in front)."""
        if pos not in self._near:
            x, y, z = pos
            self._near[pos] = [p for p in self._dust
                               if abs(p[0] - x) <= 2 and abs(p[1] - y) <= 2 and abs(p[2] - z) <= 2]
        return self._near[pos]

    # ------------------------------------------------------------ reads
    def _name(self, pos):
        return self.blocks.get(pos, (None, None))[0]

    def weak(self, e, d):
        entry = self.blocks.get(e)
        if entry is None:
            return 0
        name, props = entry
        if name == DUST:
            if not self.wires_give or d == "down":
                return 0
            power = int(props["power"])
            if power == 0:
                return 0
            if d == "up" or props.get(OPPOSITE[d]) in ("side", "up"):
                return power
            return 0
        if name == TORCH:
            return 15 if props["lit"] == "true" and d != "up" else 0
        if name == WALL_TORCH:
            return 15 if props["lit"] == "true" and d != props["facing"] else 0
        if name == LEVER:
            return 15 if props["powered"] == "true" else 0
        if name == REPEATER:
            return 15 if props["powered"] == "true" and props["facing"] == d else 0
        if name == COMPARATOR:
            # AbstractRedstoneGateBlock.getWeakRedstonePower: powered && facing
            # == direction -> getOutputLevel = the block entity's signal
            if props["facing"] != d:
                return 0
            signal = self.cmp_out.get(e, 0)
            if signal is None:
                # Hole 1, refused rather than defaulted: the container feeding
                # this comparator was never declared, so neither its output
                # signal nor its POWERED is known, and a dust `power` has no
                # blockstate for "unknown". Declare the block entity.
                raise MachineError(
                    "the comparator at %r has an undefined output signal: it reads a "
                    "container whose block entity was not declared. Pass it in "
                    "block_entities (see Machine.block_entity_report)." % (e,))
            return signal if props["powered"] == "true" else 0
        if name == REDSTONE_BLOCK:
            return 15
        return 0

    def strong(self, e, d):
        name = self._name(e)
        if name == DUST:
            return self.weak(e, d) if self.wires_give else 0
        if name in (TORCH, WALL_TORCH):
            return self.weak(e, d) if d == "down" else 0
        if name == LEVER:
            props = self.blocks[e][1]
            attach = {"floor": "up", "ceiling": "down"}.get(props.get("face"), props.get("facing"))
            return 15 if props["powered"] == "true" and d == attach else 0
        if name in (REPEATER, COMPARATOR):
            return self.weak(e, d)
        return 0

    def received_strong(self, pos):
        return max(self.strong(add(pos, d), d) for d in FACES)

    def emitted(self, e, d):
        value = self.weak(e, d)
        if is_solid(self.blocks, e):
            value = max(value, self.received_strong(e))
        return value

    def received(self, pos):
        return max(self.emitted(add(pos, d), d) for d in FACES)

    def dust_input(self, pos):
        self.wires_give = False
        i = self.received(pos)
        self.wires_give = True
        j = 0
        if i < 15:
            for d in HORIZONTAL:
                n = add(pos, d)
                j = max(j, self._dust_power(n))
                if is_solid(self.blocks, n) and not is_solid(self.blocks, add(pos, "up")):
                    j = max(j, self._dust_power(add(n, "up")))
                    continue
                if is_solid(self.blocks, n):
                    continue
                j = max(j, self._dust_power(add(n, "down")))
        return max(i, j - 1)

    def _dust_power(self, pos):
        entry = self.blocks.get(pos)
        return int(entry[1]["power"]) if entry and entry[0] == DUST else 0

    # ------------------------------------------------------------ parts
    def torch_should_unpower(self, pos):
        name, props = self.blocks[pos]
        if name == TORCH:
            return self.emitted(add(pos, "down"), "down") > 0
        d = OPPOSITE[props["facing"]]
        return self.emitted(add(pos, d), d) > 0

    def repeater_has_power(self, pos):
        facing = self.blocks[pos][1]["facing"]
        return self.emitted(add(pos, facing), facing) > 0

    def lamp_receiving(self, pos):
        return self.received(pos) > 0

    # comparator -- ComparatorBlock + AbstractRedstoneGateBlock, by function name
    def _gate_level(self, back, facing):
        """AbstractRedstoneGateBlock.getPower :130-139 -- the redstone level
        behind a gate, before ComparatorBlock's override looks at containers."""
        i = self.emitted(back, facing)
        if i >= 15:
            return i
        entry = self.blocks.get(back)
        return max(i, int(entry[1]["power"]) if entry and entry[0] == DUST else 0)

    def container_output(self, pos):
        """getComparatorOutput at `pos`, or None when its block entity was not
        declared. A block with no comparator output raises.

        The contents this reads are the LIVE ones once item transport has moved
        anything (MACH-3): `self.inv` is the slot list a hopper writes, and
        `self.block_entities` keeps the caller's declaration as it was handed
        in. Reading the declaration here would make a comparator blind to every
        transfer, which is the whole point of MACH-3.
        """
        name, props = self.blocks[pos]
        block_entity = self.block_entities.get(pos)
        if pos in self.inv:
            block_entity = dict(block_entity or {})
            block_entity["items"] = [dict(s) for s in self.inv[pos]
                                     if not stack_is_empty(s)]
        return comparator_output(name, props, block_entity)

    def back_container_undeclared(self, pos):
        """Would `gate_back` at this comparator have to read a container whose
        block entity nobody declared?

        Conservative on the read-through branch: that branch only fires while
        the wire level is below 15, which is state, and this is asked before
        the first settle -- so a solid back with an undeclared container behind
        it counts as undeclared. Refusing early beats answering 0 late.
        """
        if self._name(pos) != COMPARATOR:
            return False
        facing = self.blocks[pos][1]["facing"]
        back = add(pos, facing)
        if self._name(back) in CONTAINER_RULE:
            return self.container_output(back) is None
        if not is_solid(self.blocks, back):
            return False
        far = add(back, facing)
        if self._name(far) in CONTAINER_RULE:
            return self.container_output(far) is None
        return False

    def gate_back(self, pos):
        """ComparatorBlock.getPower :102-120 over AbstractRedstoneGateBlock's
        :130-139.

        A container behind the comparator REPLACES the redstone level -- there
        is no max, so a full wire behind a chest with one item reads 1. When
        the block behind has no comparator output, is solid and the level is
        under 15, the read steps one further in the same direction (:110-117);
        the item frame the same branch also looks for is an entity and is not
        modelled. A repeater has no such override, so this only fires for a
        comparator. Returns None when the container is undeclared.
        """
        facing = self.blocks[pos][1]["facing"]
        back = add(pos, facing)
        i = self._gate_level(back, facing)
        if self._name(pos) != COMPARATOR:
            return i
        if self._name(back) in CONTAINER_RULE:
            return self.container_output(back)
        if i < 15 and is_solid(self.blocks, back):
            far = add(back, facing)
            if self._name(far) in CONTAINER_RULE:
                return self.container_output(far)
        return i

    def _emitted_side(self, e, d):
        """RedstoneView.getEmittedRedstonePower(pos, direction, onlyFromGate=false)
        :45-60: a redstone block is 15, a dust is its POWER, any other emitter
        is its STRONG power in that direction, everything else 0 (a solid
        beside a comparator feeds the side nothing)."""
        entry = self.blocks.get(e)
        if entry is None:
            return 0
        name, props = entry
        if name == REDSTONE_BLOCK:
            return 15
        if name == DUST:
            return int(props["power"])
        if name in (REPEATER, COMPARATOR, TORCH, WALL_TORCH, LEVER):
            return self.strong(e, d)
        return 0

    def gate_sides(self, pos):
        """AbstractRedstoneGateBlock.getMaxInputLevelSides :141-147."""
        facing = self.blocks[pos][1]["facing"]
        d2, d3 = CLOCKWISE[facing], CLOCKWISE[CLOCKWISE[CLOCKWISE[facing]]]
        return max(self._emitted_side(add(pos, d2), d2), self._emitted_side(add(pos, d3), d3))

    def cmp_output(self, pos):
        """ComparatorBlock.calculateOutputSignal :74-87: 0 when the back is 0
        or a side exceeds it; back - side in subtract mode; back in compare.
        None when the back is an undeclared container."""
        i = self.gate_back(pos)
        if i is None:
            return None
        if i == 0:
            return 0
        j = self.gate_sides(pos)
        if j > i:
            return 0
        return i - j if self.blocks[pos][1]["mode"] == "subtract" else i

    def cmp_has_power(self, pos):
        """ComparatorBlock.hasPower :89-100. None when the back is an
        undeclared container."""
        i = self.gate_back(pos)
        if i is None:
            return None
        if i == 0:
            return False
        j = self.gate_sides(pos)
        if i > j:
            return True
        return i == j and self.blocks[pos][1]["mode"] == "compare"

    def cmp_target_not_aligned(self, pos):
        """AbstractRedstoneGateBlock.isTargetNotAligned :199-203: the block in
        front is a gate facing another way."""
        facing = self.blocks[pos][1]["facing"]
        front = self.blocks.get(add(pos, OPPOSITE[facing]))
        return front is not None and front[0] in (REPEATER, COMPARATOR) and front[1]["facing"] != OPPOSITE[facing]

    # ------------------------------------------------------- item transport
    def _init_transport(self, be_tick_order):
        """Slot lists, hopper cooldowns and the DECLARED block-entity tick
        order. See the module docstring for why the order is declared."""
        #: pos -> slot list (entries are a stack dict or None). Only containers
        #: whose contents were declared appear; an undeclared one is UNKNOWN.
        self.inv = {}
        #: pos -> HopperBlockEntity.transferCooldown
        self.hopper_cd = {}
        #: pos -> HopperBlockEntity.lastTickTime, the gt of its last serverTick
        self.hopper_last_tick = {}
        self.item_entities = []
        #: the gt of the last transfer/dispense, or None while nothing has moved
        self.last_transfer_gt = None
        self._hoppers = [p for p, (n, _q) in self.blocks.items() if n == HOPPER]
        self._droppers = [p for p, (n, _q) in self.blocks.items()
                          if n in (DROPPER, DISPENSER)]
        for pos, (name, props) in self.blocks.items():
            if name == HOPPER:
                props.setdefault("facing", "down")      # HopperBlock.java:68
                props.setdefault("enabled", "true")
            elif name in (DROPPER, DISPENSER):
                props.setdefault("facing", "north")     # DispenserBlock.java:76
                props.setdefault("triggered", "false")
        for pos, be in self.block_entities.items():
            name = self.blocks[pos][0]
            row = CONTAINER_RULE[name]
            if row["rule"] != "inventory":
                continue
            slots = int(be.get("slots", row["slots"]))
            self.inv[pos] = normalise_slots(be.get("items"), slots)
            if name == HOPPER:
                self.hopper_cd[pos] = int(be.get("transfer_cooldown", 0))
                self.hopper_last_tick[pos] = int(be.get("last_tick_time", -1))
        for pos in self._hoppers:
            self.hopper_cd.setdefault(pos, 0)
            self.hopper_last_tick.setdefault(pos, -1)
        declared = [p for p in self.block_entities if p in set(self._hoppers)]
        rest = sorted(set(self._hoppers) - set(declared))
        self.be_order = declared + rest
        if be_tick_order is not None:
            order = [parse_pos(p) for p in be_tick_order]
            if sorted(order) != sorted(self._hoppers):
                raise MachineError(
                    "be_tick_order must be a permutation of the %d hopper(s) in "
                    "this machine (%r), got %r"
                    % (len(self._hoppers), sorted(self._hoppers), order))
            self.be_order = order

    def _transport_inventory(self, pos):
        """HopperBlockEntity.getInventoryAt :351-353 -- the slot list of the
        container at `pos`, or None when there is no container there.

        Raises for a container this machine has no transport rule for
        (TRANSPORT_INVENTORY says which, and why), and for one whose contents
        were never declared: unknown is not empty (hole 1).
        """
        name = self._name(pos)
        if name is None or name not in CONTAINER_RULE:
            return None
        if name not in TRANSPORT_INVENTORY:
            raise MachineError(
                "no item-transport rule for %s at %r: its inventory is sided or "
                "special in 1.20.6-yarn and this machine refuses to guess which "
                "face reaches which slot (machine.TRANSPORT_INVENTORY says which "
                "containers it will move items through). Its COMPARATOR output "
                "is unaffected: machine.comparator_output still answers for it."
                % (name, pos))
        if pos not in self.inv:
            raise MachineError(
                "the %s at %r would take part in an item transfer, but its block "
                "entity was not declared: its contents are UNKNOWN, not empty. "
                "Pass it in block_entities (an empty container is declared with "
                "items: [])." % (name, pos))
        return self.inv[pos]

    def _inv_is_empty(self, slots):
        """Inventory.isEmpty()."""
        return all(stack_is_empty(s) for s in slots)

    def _hopper_is_full(self, pos):
        """HopperBlockEntity.isFull :133-139 -- every slot at its max count."""
        for stack in self.inv[pos]:
            if stack_is_empty(stack) or int(stack["count"]) != stack_max(stack):
                return False
        return True

    def _is_inventory_full(self, pos):
        """HopperBlockEntity.isInventoryFull :192-200. An empty slot has count 0
        and is therefore never `>= getMaxCount()`, so it makes the answer False.
        """
        for stack in self.inv[pos]:
            if stack_is_empty(stack) or int(stack["count"]) < stack_max(stack):
                return False
        return True

    def _hopper_disabled(self, pos):
        """HopperBlockEntity.isDisabled :422-424."""
        return self.hopper_cd.get(pos, 0) > HOPPER_COOLDOWN_GT

    def _transfer_slot(self, from_pos, to_pos, stack, slot):
        """HopperBlockEntity.transfer(from, to, stack, slot, side) :300-333.

        `canInsert` (:284-290) is Inventory.isValid, true for every container in
        TRANSPORT_INVENTORY, and none of them is a SidedInventory, so the side
        argument the world passes has no effect and is not carried here.
        Returns what is left of `stack` (None when all of it moved).
        """
        to_slots = self.inv[to_pos]
        target = to_slots[slot]
        was_empty = self._inv_is_empty(to_slots)
        moved = False
        if stack_is_empty(target):
            to_slots[slot] = stack
            stack = None
            moved = True
        elif stacks_mergeable(target, stack):
            room = stack_max(stack) - int(target["count"])
            j = min(int(stack["count"]), room)
            stack["count"] -= j
            target["count"] += j
            moved = j > 0
            if stack_is_empty(stack):
                stack = None
        if moved:
            if (was_empty and self._name(to_pos) == HOPPER
                    and not self._hopper_disabled(to_pos)):
                j = 0
                if from_pos is not None and self._name(from_pos) == HOPPER:
                    if (self.hopper_last_tick.get(to_pos, -1)
                            >= self.hopper_last_tick.get(from_pos, -1)):
                        j = 1
                self.hopper_cd[to_pos] = HOPPER_COOLDOWN_GT - j
            self.last_transfer_gt = self.gt
        return stack

    def _transfer(self, from_pos, to_pos, stack):
        """HopperBlockEntity.transfer(from, to, stack, side) :260-282 for a
        non-sided inventory: slots 0..size-1 until the stack is spent."""
        for slot in range(len(self.inv[to_pos])):
            if stack_is_empty(stack):
                return stack
            stack = self._transfer_slot(from_pos, to_pos, stack, slot)
        return stack

    def _take_one(self, slots, i):
        """`inventory.removeStack(i, 1)` for a slot known to be non-empty."""
        stack = slots[i]
        return make_stack(stack["id"], 1, stack_max(stack))

    def _spend_one(self, slots, i):
        stack = slots[i]
        stack["count"] -= 1
        if stack_is_empty(stack):
            slots[i] = None

    def hopper_insert(self, pos):
        """HopperBlockEntity.insert :141-164 -- one item into the block the
        hopper faces."""
        facing = self.blocks[pos][1]["facing"]
        target = add(pos, facing)
        if self._transport_inventory(target) is None:
            return False
        if self._is_inventory_full(target):
            return False
        slots = self.inv[pos]
        for i, stack in enumerate(slots):
            if stack_is_empty(stack):
                continue
            left = self._transfer(pos, target, self._take_one(slots, i))
            if stack_is_empty(left):
                self._spend_one(slots, i)
                return True
        return False

    def _extract_slot(self, hopper_pos, from_pos, slot):
        """HopperBlockEntity.extract(hopper, inventory, slot, side) :225-240.
        `canExtract` (:292-298) is Inventory.canTransferTo, true by default and
        not overridden by any container in TRANSPORT_INVENTORY."""
        slots = self.inv[from_pos]
        if stack_is_empty(slots[slot]):
            return False
        left = self._transfer(from_pos, hopper_pos, self._take_one(slots, slot))
        if stack_is_empty(left):
            self._spend_one(slots, slot)
            return True
        return False

    def _extract_entity(self, hopper_pos, ent):
        """HopperBlockEntity.extract(inventory, itemEntity) :242-254."""
        left = self._transfer(None, hopper_pos, dict(ent["stack"]))
        if stack_is_empty(left):
            self.item_entities.remove(ent)
            return True
        ent["stack"] = left
        return False

    def hopper_input_box(self, pos):
        """Hopper.INPUT_AREA_SHAPE offset to the hopper's block, the way
        getInputItemEntities :345-348 offsets it."""
        a = HOPPER_INPUT_AREA
        return (pos[0] + a[0], pos[1] + a[1], pos[2] + a[2],
                pos[0] + a[3], pos[1] + a[4], pos[2] + a[5])

    def _entity_box(self, ent):
        x, y, z = ent["pos"]
        half = ITEM_WIDTH / 2.0
        return (x - half, y, z - half, x + half, y + ITEM_HEIGHT, z + half)

    def hopper_extract(self, pos):
        """HopperBlockEntity.extract(world, hopper) :202-223 -- the inventory
        ABOVE first, item entities only when nothing blocks from above.

        `blockState.isFullCube` is read here as this machine's `is_solid`, which
        comes from GAP-7's solidity table; the two predicates agree for every
        block in the BLOCK vocabulary but are not the same function, and a block
        in BlockTags.DOES_NOT_BLOCK_HOPPERS is not modelled at all.
        """
        above = add(pos, "up")
        source = self._transport_inventory(above)
        if source is not None:
            for slot in range(len(source)):
                if self._extract_slot(pos, above, slot):
                    return True
            return False
        if is_solid(self.blocks, above):
            return False
        box = self.hopper_input_box(pos)
        for ent in list(self.item_entities):
            if not boxes_intersect(self._entity_box(ent), box):
                continue
            if self._extract_entity(pos, ent):
                return True
        return False

    def hopper_insert_and_extract(self, pos):
        """HopperBlockEntity.insertAndExtract :112-131."""
        if self.hopper_cd.get(pos, 0) > 0:
            return False
        if self.blocks[pos][1].get("enabled") != "true":
            return False
        slots = self._transport_inventory(pos)
        moved = False
        if not self._inv_is_empty(slots):
            moved = self.hopper_insert(pos)
        if not self._hopper_is_full(pos):
            # Java's `bl |= supplier.getAsBoolean()` always evaluates the right
            # side,
            # so the extract runs even when the insert already moved something.
            extracted = self.hopper_extract(pos)
            moved = moved or extracted
        if moved:
            self.hopper_cd[pos] = HOPPER_COOLDOWN_GT
            return True
        return False

    def hopper_server_tick(self, pos):
        """HopperBlockEntity.serverTick :103-110."""
        self.hopper_cd[pos] = self.hopper_cd.get(pos, 0) - 1
        self.hopper_last_tick[pos] = self.gt
        if self.hopper_cd[pos] <= 0:
            self.hopper_cd[pos] = 0
            return self.hopper_insert_and_extract(pos)
        return False

    def dispenser_receiving(self, pos):
        """DispenserBlock.neighborUpdate :125 -- the block ITSELF or the block
        one above it. A hopper's rule (HopperBlock.updateEnabled :158-164) reads
        only its own position; the two are different on purpose."""
        return self.received(pos) > 0 or self.received(add(pos, "up")) > 0

    def spawn_item(self, pos, facing, stack):
        """ItemDispenserBehavior.spawnItem over DispenserBlock.getOutputLocation
        :156-163, with the MODE of the world's random velocity. Read
        ITEM_ENTITY_PROVENANCE before using a gt that came off this."""
        v = FACES[facing]
        x = pos[0] + 0.5 + DISPENSER_FACING_OFFSET * v[0]
        y = pos[1] + 0.5 + DISPENSER_FACING_OFFSET * v[1]
        z = pos[2] + 0.5 + DISPENSER_FACING_OFFSET * v[2]
        y -= ITEM_SPAWN_DROP_Y_AXIS if v[1] else ITEM_SPAWN_DROP_HORIZONTAL
        g = 0.25                     # mode of nextDouble() * 0.1 + 0.2
        ent = {"pos": [x, y, z], "vel": [v[0] * g, 0.2, v[2] * g],
               "stack": stack, "age": 0, "on_ground": False, "entity_id": 0,
               "spawned_gt": self.gt, "provenance": ITEM_ENTITY_PROVENANCE}
        self.item_entities.append(ent)
        return ent

    def dispense(self, pos):
        """DropperBlock.dispense :52-84 (DispenserBlock.dispense :96-114 for the
        dispenser half, which is out of scope -- storage frame section 6).

        Returns "insert", "spawn" or None (nothing to dispense).
        """
        name, props = self.blocks[pos]
        slots = self._transport_inventory(pos)
        filled = [i for i, s in enumerate(slots) if not stack_is_empty(s)]
        if not filled:
            return None                   # chooseNonEmptySlot returns -1, :63
        if len(filled) > 1:
            raise MachineError(
                "the %s at %r has %d non-empty slots, and "
                "DispenserBlockEntity.chooseNonEmptySlot :39-48 picks one of "
                "them UNIFORMLY AT RANDOM. This machine refuses to pick rather "
                "than present a random choice as a prediction: declare exactly "
                "one non-empty slot, or model the choice outside."
                % (name, pos, len(filled)))
        i = filled[0]
        if name == DISPENSER:
            raise MachineError(
                "the dispenser at %r holds an item, and its behaviour is decided "
                "by DispenserBehavior (a per-item table: bucket, bone meal, TNT, "
                "...) which the storage frame section 6 puts out of scope. A "
                "DROPPER at the same place is transcribed." % (pos,))
        facing = props["facing"]
        target = add(pos, facing)
        to_slots = self._transport_inventory(target)
        if to_slots is not None:
            left = self._transfer(pos, target, self._take_one(slots, i))
            if stack_is_empty(left):
                self._spend_one(slots, i)
                self.last_transfer_gt = self.gt
                return "insert"
            return None                   # :77-81, the stack is written back whole
        self.spawn_item(pos, facing, self._take_one(slots, i))
        self._spend_one(slots, i)
        self.last_transfer_gt = self.gt
        return "spawn"

    def tick_item_entities(self):
        """The entity half of one game tick (ServerWorld.tick's entityList
        loop, which runs after the scheduled block ticks and before the block
        entities)."""
        for ent in list(self.item_entities):
            self._item_entity_tick(ent)

    def _item_entity_tick(self, ent):
        """ItemEntity.tick :134-194, minus water and lava buoyancy, minus
        tryMerge and minus the 6000 gt despawn (storage frame section 6)."""
        vel = ent["vel"]
        vel[1] -= ITEM_GRAVITY                                  # applyGravity
        skip = (ent["on_ground"]
                and (vel[0] * vel[0] + vel[2] * vel[2]) <= 1.0e-5
                and (ent["age"] + int(ent.get("entity_id", 0))) % 4 != 0)
        if not skip:
            self._move_item(ent)
            f = ITEM_DRAG
            if ent["on_ground"]:
                f = DEFAULT_SLIPPERINESS * ITEM_DRAG
            vel[0] *= f
            vel[1] *= ITEM_DRAG
            vel[2] *= f
            if ent["on_ground"] and vel[1] < 0.0:
                vel[1] *= ITEM_GROUND_BOUNCE
        ent["age"] += 1

    def _move_item(self, ent):
        """Entity.move(SELF, velocity) reduced to the vertical axis: the item
        stops on the first solid block it would enter going down. Horizontal
        collision is NOT modelled (ITEM_ENTITY_PROVENANCE)."""
        pos, vel = ent["pos"], ent["vel"]
        pos[0] += vel[0]
        pos[2] += vel[2]
        target = pos[1] + vel[1]
        ent["on_ground"] = False
        if vel[1] < 0.0:
            bx, bz = _math.floor(pos[0]), _math.floor(pos[2])
            for cy in range(_math.floor(target), _math.floor(pos[1]) + 1):
                if not is_solid(self.blocks, (bx, cy, bz)):
                    continue
                top = float(cy + 1)
                if target < top <= pos[1] + 1.0e-9:
                    target = top
                    vel[1] = 0.0
                    ent["on_ground"] = True
                    break
        pos[1] = target

    def tick_block_entities(self):
        """World.tickBlockEntities :481-495 over the DECLARED order."""
        for pos in self.be_order:
            self.hopper_server_tick(pos)

    def total_items(self):
        """Every item this machine holds, {id: count}, for the `no_item_lost`
        invariant. Undeclared containers are not counted and cannot be: their
        contents are unknown."""
        total = {}
        for slots in self.inv.values():
            for stack in slots:
                if stack_is_empty(stack):
                    continue
                total[stack["id"]] = total.get(stack["id"], 0) + int(stack["count"])
        for ent in self.item_entities:
            stack = ent["stack"]
            total[stack["id"]] = total.get(stack["id"], 0) + int(stack["count"])
        return total

    def inventory_snapshot(self):
        """{"x,y,z": [stack or None, ...]} -- the live slot lists."""
        return {"%d,%d,%d" % pos: [None if stack_is_empty(s) else dict(s)
                                   for s in slots]
                for pos, slots in sorted(self.inv.items())}

    def inventory_is_full(self, pos):
        """Public `_is_inventory_full`: the container is in the state where a
        further insert is refused. This is what `no_overflow` means."""
        return self._is_inventory_full(parse_pos(pos))

    def container_counts(self, pos):
        """{id: count} in one declared container."""
        out = {}
        for stack in self.inv[parse_pos(pos)]:
            if stack_is_empty(stack):
                continue
            out[stack["id"]] = out.get(stack["id"], 0) + int(stack["count"])
        return out

    def transport_report(self):
        """What a storage result should carry about the item path (MACH-3)."""
        return {
            "be_tick_order": ["%d,%d,%d" % p for p in self.be_order],
            "be_tick_order_provenance": "declared",
            "hopper_cooldown_gt": HOPPER_COOLDOWN_GT,
            "hoppers": {"%d,%d,%d" % p: {"cooldown": self.hopper_cd[p],
                                         "last_tick_gt": self.hopper_last_tick[p],
                                         "enabled": self.blocks[p][1]["enabled"]}
                        for p in sorted(self._hoppers)},
            "item_entities": [{"pos": [round(c, 6) for c in e["pos"]],
                               "stack": dict(e["stack"]),
                               "age": e["age"],
                               "on_ground": e["on_ground"]}
                              for e in self.item_entities],
            "item_entity_provenance": (ITEM_ENTITY_PROVENANCE
                                       if self.item_entities else "none spawned"),
            "totals": self.total_items(),
        }

    # ------------------------------------------------------------ dynamics
    def schedule(self, pos, when, priority):
        """Book a scheduled tick, stamping it with the world's tick order.

        World.getTickOrder returns `this.tickOrder++`; Tick.createOrderedTick
        stores it as OrderedTick.subTickOrder. A position already in `pending`
        is never re-stamped here -- the callers check first, the way
        ChunkTickScheduler refuses a duplicate (pos, type)."""
        self.pending[pos] = (when, priority, self.tick_order)
        self.tick_order += 1

    def due_order(self):
        """The positions whose scheduled tick fires this gt, in the order the
        world runs them: OrderedTick.BASIC_COMPARATOR = (priority, then
        subTickOrder). Position is not part of the key."""
        due = [(prio, sub, pos) for pos, (when, prio, sub) in self.pending.items()
               if when <= self.gt]
        due.sort(key=lambda t: (t[0], t[1]))       # (priority, subTickOrder)
        return [pos for _prio, _sub, pos in due]

    def _settle_sync(self):
        """Dust to its fixpoint and lamps on -- the part of a neighbour update
        that happens inside the same call, with no tick. Worklist: a dust
        whose power changes re-queues the dust cells near it (its own
        `update` notifies neighbours, RedstoneWireBlock.java:330-335)."""
        work = self._dirty
        self._dirty = set()
        n = 0
        while work:
            pos = work.pop()
            n += 1
            if n > 2000000:
                raise MachineError("dust did not settle")
            props = self.blocks[pos][1]
            new = str(self.dust_input(pos))
            if new != props["power"]:
                props["power"] = new
                work.update(self._dust_near(pos))
        for pos in self._lamps:
            props = self.blocks[pos][1]
            if props["lit"] == "false" and self.lamp_receiving(pos):
                props["lit"] = "true"
        # HopperBlock.updateEnabled :158-164 -- synchronous, no scheduled tick,
        # and it reads the hopper's OWN position only.
        for pos in self._hoppers:
            props = self.blocks[pos][1]
            enabled = "false" if self.received(pos) > 0 else "true"
            if props["enabled"] != enabled:
                props["enabled"] = enabled

    def settle(self):
        """Synchronous part of a neighbour update, then every tick-scheduling
        part checks its rule and books its tick."""
        self._settle_sync()
        # DispenserBlock.neighborUpdate :123-133: the RISING edge sets TRIGGERED
        # and books the tick 4 gt out; the falling edge only clears TRIGGERED.
        # TRIGGERED itself is what stops a second booking, so this needs no
        # `pos in self.pending` guard.
        for pos in self._droppers:
            props = self.blocks[pos][1]
            powered = self.dispenser_receiving(pos)
            triggered = props["triggered"] == "true"
            if powered and not triggered:
                props["triggered"] = "true"
                self.schedule(pos, self.gt + DISPENSER_GT, PRIORITY_NORMAL)
            elif not powered and triggered:
                props["triggered"] = "false"
        for pos in self._parts:
            name, props = self.blocks[pos]
            if pos in self.pending:
                continue
            if name in (TORCH, WALL_TORCH):
                if (props["lit"] == "true") == self.torch_should_unpower(pos):
                    self.schedule(pos, self.gt + TORCH_GT, PRIORITY_NORMAL)
            elif name == REPEATER:
                if (props["powered"] == "true") != self.repeater_has_power(pos):
                    # AbstractRedstoneGateBlock.updatePowered :110-118: HIGH,
                    # or VERY_HIGH when the gate is currently powered
                    prio = PRIORITY_VERY_HIGH if props["powered"] == "true" else PRIORITY_HIGH
                    self.schedule(pos, self.gt + REPEATER_GT_PER_DELAY * int(props["delay"]), prio)
            elif name == LAMP:
                if props["lit"] == "true" and not self.lamp_receiving(pos):
                    self.schedule(pos, self.gt + LAMP_OFF_GT, PRIORITY_NORMAL)
            elif name == COMPARATOR:
                # ComparatorBlock.updatePowered :147-156: not ticking, and either
                # the signal to store changed or POWERED disagrees with hasPower
                i = self.cmp_output(pos)
                if i is None:
                    # Undeclared container behind it: it cannot know that
                    # anything changed, so it books nothing and stays undefined.
                    self.cmp_out[pos] = None
                    continue
                if i != self.cmp_out[pos] or (props["powered"] == "true") != self.cmp_has_power(pos):
                    prio = PRIORITY_HIGH if self.cmp_target_not_aligned(pos) else PRIORITY_NORMAL
                    self.schedule(pos, self.gt + COMPARATOR_GT, prio)

    def _fire(self, pos):
        name, props = self.blocks[pos]
        self._dirty.update(self._dust_near(pos))
        if name in (DROPPER, DISPENSER):
            self.dispense(pos)                  # DispenserBlock.scheduledTick :135-138
        elif name in (TORCH, WALL_TORCH):
            unpower = self.torch_should_unpower(pos)
            if props["lit"] == "true" and unpower:
                props["lit"] = "false"
            elif props["lit"] == "false" and not unpower:
                props["lit"] = "true"
        elif name == REPEATER:
            has = self.repeater_has_power(pos)
            if props["powered"] == "true" and not has:
                props["powered"] = "false"
            elif props["powered"] == "false":
                props["powered"] = "true"
                if not has:     # scheduledTick :70 re-schedules at VERY_HIGH
                    self.schedule(pos, self.gt + REPEATER_GT_PER_DELAY * int(props["delay"]),
                                  PRIORITY_VERY_HIGH)
        elif name == LAMP:
            if props["lit"] == "true" and not self.lamp_receiving(pos):
                props["lit"] = "false"
        elif name == COMPARATOR:
            # ComparatorBlock.update :158-177: store the signal, then set POWERED
            # from hasPower when the signal changed (or always in compare mode)
            i = self.cmp_output(pos)
            j = self.cmp_out[pos]
            self.cmp_out[pos] = i
            if i is None:
                return
            if j != i or props["mode"] == "compare":
                has = self.cmp_has_power(pos)
                if props["powered"] == "true" and not has:
                    props["powered"] = "false"
                elif props["powered"] == "false" and has:
                    props["powered"] = "true"

    def step(self):
        """Advance one game tick: fire what is due IN TICK-PRIORITY ORDER,
        re-settling the synchronous part (dust, lamps-on) after every event
        so a later event reads the world the earlier one left -- which is
        what scheduledTick's own re-read of the input does. Learned from
        the world (D-1 record, iteration 2): with events fired as a set the
        model predicted a 4 gt sum glitch on vector 11 that the world does
        not show, because the carry's diode repeater (HIGH) ticks before the
        sum torch (NORMAL) in the same gt. Within one priority the order is
        the order the ticks were booked (OrderedTick.subTickOrder), see
        `due_order` and the module docstring."""
        self.gt += 1
        due = self.due_order()
        for pos in due:
            del self.pending[pos]
        for pos in due:
            self._fire(pos)
            self._settle_sync()
        # ServerWorld.tick: scheduled block ticks (:327) run first, then the
        # entityList loop, then tickBlockEntities (:385). MACH-3 keeps that
        # order; without a container in the artifact both calls are no-ops and
        # the DC fixpoint is byte-identical to what MACH-2 predicted.
        self.tick_item_entities()
        self.tick_block_entities()
        self.settle()

    def set_slot(self, pos, slot, stack):
        """The machine's `item replace block <pos> container.<slot> with ...`.

        This is the stimulus of a storage spec: it writes the block entity, not
        a block state, exactly as the world's command does, and it does NOT
        touch the transfer cooldown (the world's command does not either).
        """
        pos = parse_pos(pos)
        slots = self._transport_inventory(pos)
        if slots is None:
            raise MachineError("%r is %s, not a container this machine moves "
                               "items through" % (pos, self._name(pos)))
        if not 0 <= int(slot) < len(slots):
            raise MachineError("slot %r is outside the %d slots at %r"
                               % (slot, len(slots), pos))
        slots[int(slot)] = None if stack_is_empty(stack) else make_stack(
            stack["id"], int(stack.get("count", 1)),
            int(stack.get("max_count", DEFAULT_STACK_MAX)))
        self.settle()
        return slots[int(slot)]

    def give(self, pos, stack):
        """`set_slot` into the first empty slot (DispenserBlockEntity's
        addToFirstFreeSlot :50-57 shape)."""
        pos = parse_pos(pos)
        slots = self._transport_inventory(pos)
        for i, held in enumerate(slots):
            if stack_is_empty(held):
                return self.set_slot(pos, i, stack)
        raise MachineError("every slot of the %s at %r is occupied"
                           % (self._name(pos), pos))

    def set_lever(self, pos, powered):
        name, props = self.blocks[pos]
        if name != LEVER:
            raise MachineError(f"{pos} is {name}, not a lever")
        props["powered"] = "true" if powered else "false"
        self._dirty.update(self._dust_near(pos))
        self.settle()

    def at_rest(self):
        """No scheduled tick outstanding AND nothing is still moving items.

        A hopper is not a scheduled tick, so `pending` alone would call a
        machine "at rest" while an item is still on its way down a column.
        With no container in the artifact `last_transfer_gt` stays None and
        there are no item entities, so this is exactly `not self.pending` and
        the DC fixpoint is unchanged.
        """
        if self.pending or self.item_entities:
            return False
        if self.last_transfer_gt is None:
            return True
        return self.gt - self.last_transfer_gt > HOPPER_COOLDOWN_GT

    def run_to_rest(self, limit=400):
        self.settle()
        for _ in range(limit):
            if self.at_rest():
                return self.gt
            self.step()
        raise MachineError(f"no rest state within {limit} gt (an oscillator?)")

    def run_gt(self, n, observer=None):
        """Advance `n` gt unconditionally, calling `observer(self)` after each
        one. A storage spec is evaluated over a gt SERIES, not a fixpoint
        (storage frame section 3-2), so this is its driver."""
        self.settle()
        for _ in range(int(n)):
            self.step()
            if observer is not None:
                observer(self)
        return self.gt

    def snapshot(self):
        return {pos: (name, dict(props)) for pos, (name, props) in self.blocks.items()}

    def signal_snapshot(self):
        """The comparators' stored output signals (block-entity state).
        A None is a comparator whose container was never declared."""
        return dict(self.cmp_out)

    def container_positions(self):
        """Positions of the blocks in this machine that have a comparator
        output, in scan order."""
        return sorted(p for p, (n, _q) in self.blocks.items() if n in CONTAINER_RULE)

    def undeclared_containers(self):
        """Containers whose rule needs a block entity and got none. Every one
        of these makes some comparator's output undefined."""
        return sorted(p for p in self.container_positions() if self.container_output(p) is None)

    def block_entity_report(self):
        """What a result should carry about hole 1 (frame section 1).

        `provenance` is `declared` for every one of these: the caller asserted
        the contents, no scan measured them. When SCAN-NBT lands it becomes
        `measured` and this report is where that shows.
        """
        declared = {}
        for pos in self.container_positions():
            if pos not in self.block_entities:
                continue
            name = self.blocks[pos][0]
            declared["%d,%d,%d" % pos] = {
                "block": name,
                "provenance": "declared",
                "rule": CONTAINER_RULE[name]["rule"],
                "source_ref": "minecraft-src 1.20.6-yarn " + CONTAINER_RULE[name]["source"],
                "comparator_output": self.container_output(pos),
            }
        return {
            "provenance": "declared",
            "declared": declared,
            "undeclared": ["%d,%d,%d" % p for p in self.undeclared_containers()],
            "state_only": ["%d,%d,%d" % p for p in self.container_positions()
                           if p not in self.block_entities
                           and CONTAINER_RULE[self.blocks[p][0]]["rule"]
                           not in BLOCK_ENTITY_RULES],
        }

    def observe(self, positions):
        """{pos: value} of the swept property, dynharness-style: lit for
        torches and lamps, powered for repeaters and levers, power for dust."""
        out = {}
        for pos in positions:
            name, props = self.blocks[pos]
            key = {TORCH: "lit", WALL_TORCH: "lit", LAMP: "lit", REPEATER: "powered",
                   COMPARATOR: "powered", LEVER: "powered", DUST: "power",
                   HOPPER: "enabled", DROPPER: "triggered",
                   DISPENSER: "triggered"}[name]
            out[pos] = props[key]
        return out
