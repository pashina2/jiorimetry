#!/usr/bin/env python3
"""tools/llmgen/library.py -- the primitive library: every vanilla
redstone part as ONE ROW (faces it reads, faces it powers, the gt it
schedules, the state it carries), each cited to 1.20.6-yarn by file:line.

DESIGN: notes/2026-09-06-d1-llm-generator/DESIGN.md section 2. A part is a
state machine with three readable rules (read power / schedule a tick /
write state on that tick); the table below is those rules as data. Adding a
part is adding a row -- the netlist and the placer never branch on a part
name (PR-11), they ask the row.

Directions follow vanilla's convention as the rows are READ from the input
side: a face name here is measured FROM THE PART'S OWN CELL toward its
neighbour (the opposite sign of the `direction` argument that reaches
`getWeakRedstonePower`; see r4_netlist.py's sign paragraph).

The delays are the constants the sources hand `scheduleBlockTick`; a `lo`
without a `hi` is a source-readable lower bound whose upper end nobody has
measured (cell-decl provenance `source_lower_bound`). Nothing here is a
measurement.
"""

FACES = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0),
         "west": (-1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0)}
OPPOSITE = {"north": "south", "south": "north", "east": "west",
            "west": "east", "up": "down", "down": "up"}
HORIZONTAL = ("north", "east", "south", "west")

SRC = "minecraft-src 1.20.6-yarn "

#: Scheduled-tick constants, each the literal the cited line passes.
TORCH_GT = 2            # RedstoneTorchBlock.java:35 (SCHEDULED_TICK_DELAY), :98
REPEATER_GT_PER_DELAY = 2   # RepeaterBlock.java:53-55 (DELAY * 2)
COMPARATOR_GT = 2       # ComparatorBlock.java:53-54, :154
LAMP_OFF_GT = 4         # RedstoneLampBlock.java:48 (on is synchronous, :50)
OBSERVER_GT = 2         # ObserverBlock.java:60, :75
DISPENSER_GT = 4        # DispenserBlock.java:60, :128
DETECTOR_RAIL_GT = 20   # DetectorRailBlock.java:41, :117
BUTTON_STONE_GT = 20    # ButtonBlock.java:143 (pressTicks, stone 20 / wood 30)
PLATE_GT = 20           # AbstractPressurePlateBlock.java:48, :109
TARGET_GT = (8, 20)     # TargetBlock.java:34-35
HOPPER_COOLDOWN_GT = 8  # HopperBlockEntity transfer cooldown (setTransferCooldown(8))
PISTON_LO_GT = 2        # PistonBlock.java:173-214 block event; extension spans 2 gt (lower bound)
DUST_MAX_RUN = 15       # RedstoneWireBlock.java:251-275 (power decays by one per cell)

SMOOTH_STONE = "minecraft:smooth_stone"
DUST = "minecraft:redstone_wire"
REPEATER = "minecraft:repeater"
COMPARATOR = "minecraft:comparator"
TORCH = "minecraft:redstone_torch"
WALL_TORCH = "minecraft:redstone_wall_torch"
LEVER = "minecraft:lever"
BUTTON = "minecraft:stone_button"
PLATE = "minecraft:stone_pressure_plate"
REDSTONE_BLOCK = "minecraft:redstone_block"
LAMP = "minecraft:redstone_lamp"
PISTON = "minecraft:piston"
STICKY_PISTON = "minecraft:sticky_piston"
OBSERVER = "minecraft:observer"
POWERED_RAIL = "minecraft:powered_rail"
DETECTOR_RAIL = "minecraft:detector_rail"
HOPPER = "minecraft:hopper"
DROPPER = "minecraft:dropper"
DISPENSER = "minecraft:dispenser"
NOTE_BLOCK = "minecraft:note_block"
TARGET = "minecraft:target"
TRAPDOOR = "minecraft:oak_trapdoor"
DOOR = "minecraft:iron_door"

#: The library. One row per part. Keys:
#:   block      the vanilla id
#:   kind       source | sink | gate | wire | relay | mover | detector | declared
#:   reads      faces whose power the part READS ("attach", "back", "side",
#:              "all", "front_change", "quasi", or none)
#:   powers     faces the part POWERS and the class ("weak" = every reader,
#:              "strong" = the block there conducts on to dust)
#:   delay_gt   {"transition": gt} -- what scheduleBlockTick is handed;
#:              a tuple (lo, None) is a lower bound only
#:   state      blockstate properties with their rest defaults
#:   solid      True when the part is a full cube (isSolidBlock) -- what dust
#:              connection and strong relay depend on
#:   source     file:line list, all 1.20.6-yarn
#:   rule       the neighborUpdate / scheduledTick rule in one line
PARTS = {
    "dust": {
        "block": DUST, "kind": "wire", "solid": False,
        "reads": ("north", "east", "south", "west", "up_diag", "down_diag", "strong_from_solid"),
        "powers": {"connected_sides": "weak", "down": "strong_for_non_dust"},
        "delay_gt": {"update": 0},
        "state": {"north": "none", "east": "none", "south": "none",
                  "west": "none", "power": "0"},
        "source": [SRC + "RedstoneWireBlock.java:200-219",
                   SRC + "RedstoneWireBlock.java:251-275",
                   SRC + "RedstoneWireBlock.java:330-335",
                   SRC + "RedstoneWireBlock.java:343-362"],
        "rule": ("neighborUpdate -> update (synchronous, no tick); power = max("
                 "received with wiresGivePower=false, max(neighbour dust) - 1); "
                 "up-diagonal only when nothing solid sits above this cell"),
    },
    "repeater": {
        "block": REPEATER, "kind": "gate", "solid": False,
        "reads": ("back", "lock_sides"),
        "powers": {"front": "strong"},
        "delay_gt": {"rise": "delay*2", "fall": "delay*2"},
        "state": {"delay": "1", "facing": "north", "locked": "false",
                  "powered": "false"},
        "source": [SRC + "RepeaterBlock.java:53-55",
                   SRC + "AbstractRedstoneGateBlock.java:59-72",
                   SRC + "AbstractRedstoneGateBlock.java:92-120",
                   SRC + "AbstractRedstoneGateBlock.java:129-137",
                   SRC + "AbstractRedstoneGateBlock.java:180-184"],
        "rule": ("updatePowered: powered != hasPower && !isTicking -> schedule "
                 "DELAY*2; scheduledTick: powered&&!hasPower -> off; !powered -> "
                 "on (and re-schedule if input already gone); FACING points at "
                 "the input"),
    },
    "comparator": {
        "block": COMPARATOR, "kind": "gate", "solid": False,
        "reads": ("back", "side", "side", "container_strength"),
        "powers": {"front": "strong"},
        "delay_gt": {"rise": COMPARATOR_GT, "fall": COMPARATOR_GT},
        "state": {"facing": "north", "mode": "compare", "powered": "false"},
        "source": [SRC + "ComparatorBlock.java:53-54",
                   SRC + "ComparatorBlock.java:101-118",
                   SRC + "ComparatorBlock.java:154",
                   SRC + "ComparatorBlock.java:180",
                   SRC + "AbstractRedstoneGateBlock.java:140-147"],
        "rule": ("output = compare ? (back >= max(sides) ? back : 0) : "
                 "max(back - max(sides), 0); a container behind gives its "
                 "signal strength (hasComparatorOutput)"),
    },
    "torch": {
        "block": TORCH, "kind": "gate", "solid": False,
        "reads": ("attach",),
        "powers": {"all_but_attach": "weak", "up": "strong"},
        "delay_gt": {"rise": TORCH_GT, "fall": TORCH_GT, "burnout": 160},
        "state": {"lit": "true"},
        "source": [SRC + "RedstoneTorchBlock.java:35",
                   SRC + "RedstoneTorchBlock.java:64-72",
                   SRC + "RedstoneTorchBlock.java:76-99",
                   SRC + "RedstoneTorchBlock.java:103-106"],
        "rule": ("neighborUpdate: lit == shouldUnpower(attach) && !isTicking -> "
                 "schedule 2; scheduledTick: lit&&unpower -> off, !lit&&!unpower "
                 "-> on; the attach block is read with isEmittingRedstonePower"),
    },
    "wall_torch": {
        "block": WALL_TORCH, "kind": "gate", "solid": False,
        "reads": ("attach",),
        "powers": {"all_but_attach": "weak", "up": "strong"},
        "delay_gt": {"rise": TORCH_GT, "fall": TORCH_GT, "burnout": 160},
        "state": {"facing": "north", "lit": "true"},
        "source": [SRC + "WallRedstoneTorchBlock.java:82-101",
                   SRC + "RedstoneTorchBlock.java:35",
                   SRC + "RedstoneTorchBlock.java:96-99"],
        "rule": ("as torch; attach block = pos.offset(FACING.getOpposite()); "
                 "pays out to every receiver except direction == FACING"),
    },
    "lever": {
        "block": LEVER, "kind": "source", "solid": False,
        "reads": (),
        "powers": {"all": "weak", "attach": "strong"},
        "delay_gt": {"toggle": 0},
        "state": {"face": "floor", "facing": "north", "powered": "false"},
        "source": [SRC + "LeverBlock.java:152-168"],
        "rule": "player toggles POWERED; 15 on every face when powered",
    },
    "button": {
        "block": BUTTON, "kind": "source", "solid": False,
        "reads": (),
        "powers": {"all": "weak", "attach": "strong"},
        "delay_gt": {"release": BUTTON_STONE_GT},
        "state": {"face": "floor", "facing": "north", "powered": "false"},
        "source": [SRC + "ButtonBlock.java:143", SRC + "ButtonBlock.java:165-184",
                   SRC + "ButtonBlock.java:210"],
        "rule": "press -> powered, schedule pressTicks; scheduledTick -> unpowered",
    },
    "pressure_plate": {
        "block": PLATE, "kind": "detector", "solid": False,
        "reads": ("entity",),
        "powers": {"all": "weak", "down": "strong"},
        "delay_gt": {"release": PLATE_GT},
        "state": {"powered": "false"},
        "source": [SRC + "AbstractPressurePlateBlock.java:48",
                   SRC + "AbstractPressurePlateBlock.java:72-109",
                   SRC + "AbstractPressurePlateBlock.java:130-143"],
        "rule": "entity -> powered; re-checked every getTickRate() gt",
    },
    "redstone_block": {
        "block": REDSTONE_BLOCK, "kind": "source", "solid": True,
        "reads": (),
        "powers": {"all": "weak"},
        "delay_gt": {},
        "state": {},
        "source": [SRC + "RedstoneBlock.java:26-34"],
        "rule": "15 on every face, always; no strong power",
    },
    "lamp": {
        "block": LAMP, "kind": "sink", "solid": True,
        "reads": ("all",),
        "powers": {},
        "delay_gt": {"rise": 0, "fall": LAMP_OFF_GT},
        "state": {"lit": "false"},
        "source": [SRC + "RedstoneLampBlock.java:41-59"],
        "rule": ("neighborUpdate: lit != isReceivingRedstonePower -> lit ? "
                 "schedule 4 : set lit now; scheduledTick: lit && !receiving -> off"),
    },
    "piston": {
        "block": PISTON, "kind": "mover", "solid": False,
        "reads": ("all_but_front", "quasi"),
        "powers": {},
        "delay_gt": {"extend": (PISTON_LO_GT, None), "retract": (PISTON_LO_GT, None)},
        "state": {"extended": "false", "facing": "north"},
        "source": [SRC + "PistonBlock.java:111-118", SRC + "PistonBlock.java:134",
                   SRC + "PistonBlock.java:152-166", SRC + "PistonBlock.java:173-214"],
        "rule": ("shouldExtend: any face but the piston face emits, OR any face "
                 "around pos.up() emits (quasi); block event -> MOVING_PISTON; the "
                 "moved blocks change occupancy over time (DESIGN axis 5)"),
    },
    "sticky_piston": {
        "block": STICKY_PISTON, "kind": "mover", "solid": False,
        "reads": ("all_but_front", "quasi"),
        "powers": {},
        "delay_gt": {"extend": (PISTON_LO_GT, None), "retract": (PISTON_LO_GT, None)},
        "state": {"extended": "false", "facing": "north"},
        "source": [SRC + "PistonBlock.java:152-166", SRC + "PistonBlock.java:173-214",
                   SRC + "PistonBlock.java:316-318"],
        "rule": "as piston; pulls the block back on retract (0-tick drop when the pulse is shorter)",
    },
    "observer": {
        "block": OBSERVER, "kind": "detector", "solid": False,
        "reads": ("front_change",),
        "powers": {"back": "strong"},
        "delay_gt": {"rise": OBSERVER_GT, "fall": OBSERVER_GT},
        "state": {"facing": "north", "powered": "false"},
        "source": [SRC + "ObserverBlock.java:55-60", SRC + "ObserverBlock.java:75",
                   SRC + "ObserverBlock.java:87-102"],
        "rule": ("a state change of the block it faces -> schedule 2 -> powered "
                 "-> schedule 2 -> unpowered (a 2 gt pulse on its back)"),
    },
    "powered_rail": {
        "block": POWERED_RAIL, "kind": "wire", "solid": False,
        "reads": ("all", "rail_chain"),
        "powers": {"rail_chain": "rail"},
        "delay_gt": {"update": 0},
        "state": {"powered": "false", "shape": "north_south", "waterlogged": "false"},
        "source": [SRC + "PoweredRailBlock.java:112-131",
                   SRC + "PoweredRailBlock.java:135-146"],
        "rule": ("updateBlockState writes only when bl2 != bl (edge); power "
                 "propagates along up to 9 rails synchronously -- the instant-"
                 "circuit family (ADR-0036) is this row"),
    },
    "detector_rail": {
        "block": DETECTOR_RAIL, "kind": "detector", "solid": False,
        "reads": ("entity",),
        "powers": {"all": "weak", "down": "strong", "comparator": "container"},
        "delay_gt": {"release": DETECTOR_RAIL_GT},
        "state": {"powered": "false", "shape": "north_south", "waterlogged": "false"},
        "source": [SRC + "DetectorRailBlock.java:41", SRC + "DetectorRailBlock.java:69-82",
                   SRC + "DetectorRailBlock.java:117", SRC + "DetectorRailBlock.java:146-151"],
        "rule": "minecart -> powered, re-checked every 20 gt; comparator reads the cart",
    },
    "hopper": {
        "block": HOPPER, "kind": "sink", "solid": False,
        "reads": ("all",),
        "powers": {"comparator": "container"},
        "delay_gt": {"transfer": HOPPER_COOLDOWN_GT},
        "state": {"enabled": "true", "facing": "down"},
        "source": [SRC + "HopperBlock.java:154-160", SRC + "HopperBlock.java:178-183"],
        "rule": "powered -> enabled=false (stops); item moves every 8 gt (hopper clock)",
    },
    "dropper": {
        "block": DROPPER, "kind": "sink", "solid": True,
        "reads": ("all", "quasi"),
        "powers": {"comparator": "container"},
        "delay_gt": {"trigger": DISPENSER_GT},
        "state": {"facing": "north", "triggered": "false"},
        "source": [SRC + "DispenserBlock.java:60", SRC + "DispenserBlock.java:124-136",
                   SRC + "DispenserBlock.java:166-171"],
        "rule": "receiving(pos) || receiving(pos.up()) rising edge -> schedule 4 -> dispense",
    },
    "dispenser": {
        "block": DISPENSER, "kind": "sink", "solid": True,
        "reads": ("all", "quasi"),
        "powers": {"comparator": "container"},
        "delay_gt": {"trigger": DISPENSER_GT},
        "state": {"facing": "north", "triggered": "false"},
        "source": [SRC + "DispenserBlock.java:60", SRC + "DispenserBlock.java:124-136"],
        "rule": "as dropper",
    },
    "note_block": {
        "block": NOTE_BLOCK, "kind": "sink", "solid": True,
        "reads": ("all",),
        "powers": {},
        "delay_gt": {"play": 0},
        "state": {"instrument": "harp", "note": "0", "powered": "false"},
        "source": [SRC + "NoteBlock.java:83-89", SRC + "NoteBlock.java:134"],
        "rule": "powered flips with isReceivingRedstonePower; rising edge -> block event",
    },
    "target": {
        "block": TARGET, "kind": "detector", "solid": True,
        "reads": ("projectile",),
        "powers": {"all": "weak"},
        "delay_gt": {"arrow": TARGET_GT[0], "other": TARGET_GT[1]},
        "state": {"power": "0"},
        "source": [SRC + "TargetBlock.java:34-35", SRC + "TargetBlock.java:79-95"],
        "rule": "hit -> power by distance from centre, schedule 8 (arrow) / 20",
    },
    "solid": {
        "block": SMOOTH_STONE, "kind": "relay", "solid": True,
        "reads": ("strong_in", "weak_in"),
        "powers": {"all": "relay"},
        "delay_gt": {},
        "state": {},
        "source": [SRC + "RedstoneView.java:18-20", SRC + "RedstoneView.java:66-73"],
        "rule": ("getEmittedRedstonePower: max(own weak = 0, received STRONG); a "
                 "weakly powered block feeds torch/repeater/lamp/piston but no dust; "
                 "a dust reading it sees 0 from dust sources (wiresGivePower=false)"),
    },
    "trapdoor": {
        "block": TRAPDOOR, "kind": "declared", "solid": False,
        "reads": ("all",), "powers": {},
        "delay_gt": {"open": 0},
        "state": {"facing": "north", "half": "bottom", "open": "false",
                  "powered": "false", "waterlogged": "false"},
        "source": [SRC + "TrapdoorBlock.java:137-149"],
        "rule": "open follows isReceivingRedstonePower; declared only (state element)",
    },
    "door": {
        "block": DOOR, "kind": "declared", "solid": False,
        "reads": ("all", "other_half"), "powers": {},
        "delay_gt": {"open": 0},
        "state": {"facing": "north", "half": "lower", "hinge": "left",
                  "open": "false", "powered": "false"},
        "source": [SRC + "DoorBlock.java:231-239"],
        "rule": "open follows receiving(pos) || receiving(other half); declared only",
    },
}


def block_string(block, props):
    """`minecraft:x[a=b,c=d]` with props sorted -- the program.json spelling."""
    if not props:
        return block
    return block + "[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]"


def part_of(block):
    """The library row whose `block` is `block`, or None."""
    for name, row in PARTS.items():
        if row["block"] == block:
            return name
    return None


def tile(part):
    """A minimal PLACEABLE occurrence of one part in the artifact frame:
    the part at y=2 with the support the source demands (a floor part
    stands on a solid; a wall torch hangs on one). Used by the test that
    pins 'every declared part can be placed and passes the program
    schema', DESIGN section 2."""
    row = PARTS[part]
    props = dict(row["state"])
    blocks = [[0, 1, 0, SMOOTH_STONE]]
    if part == "wall_torch":
        props["facing"] = "east"
        blocks.append([0, 2, 0, SMOOTH_STONE])
        blocks.append([1, 2, 0, block_string(row["block"], props)])
        return blocks
    if part == "door":
        upper = dict(props, half="upper")
        blocks.append([0, 2, 0, block_string(row["block"], props)])
        blocks.append([0, 3, 0, block_string(row["block"], upper)])
        return blocks
    blocks.append([0, 2, 0, block_string(row["block"], props)])
    return blocks

# ----------------------------------------------------------------- idioms
#: Material cost per part (DESIGN 8.2, the `material` profile): what the
#: part costs to craft in vanilla, so the comparator's quartz is a real
#: price the mapper can be asked to pay or avoid.
MATERIAL = {"torch": 1.0, "solid": 0.1, "repeater": 3.0, "comparator": 6.0,
            "dust": 0.2, "powered_rail": 2.0, "observer": 4.0, "sticky_piston": 5.0,
            "redstone_block": 9.0, "lamp": 1.0}

#: The idiom table (DESIGN 8.1). One row = one cell the mapper may pick:
#:   fn         Boolean function of the ordered pins, as a python callable on
#:              truth-table signatures (ints over the leaf's 2^n rows) --
#:              the mapper matches by signature, never by name
#:   pins       ordered pin roles; a pin's `strength` is a condition the
#:              placer meets with a repeater (the comparator arithmetic is
#:              an equality of SIGNAL STRENGTHS, not of truth values)
#:   parts      parts per instance (k = fan-in), for the cost vector
#:   arc_gt     scheduled ticks on the cell itself (pin repeaters counted
#:              by the placer as edge repeaters, 2 gt each)
#:   stages     tick stages the cell adds on a path
#:   precondition  a predicate on the pin signatures the row REQUIRES
#:              (or_merge: the dust wired-OR is a max, so the two drivers
#:              must never be high together)
#:   source     1.20.6-yarn file:line, the rule the row rests on
IDIOMS = {
    "not": {
        "fn": lambda m, x: ~x & m, "arity": 1,
        "pins": [{"role": "attach", "strength": None}],
        "parts": lambda k, fabric="sparse": {"torch": 1, "solid": 1},
        "arc_gt": TORCH_GT, "stages": 1,
        "rows": 1, "cols": lambda k: 1,
        "source": [SRC + "RedstoneTorchBlock.java:76-99"],
        "rule": "torch on a block the input dust points into: lit == !input",
    },
    "nor": {
        "fn": lambda m, x, y: ~(x | y) & m, "arity": 2,
        "pins": [{"role": "attach", "strength": None}, {"role": "attach", "strength": None}],
        "parts": lambda k, fabric="sparse": {"torch": 1, "solid": 1,
                                             "repeater": (k if fabric == "sparse" else (0 if k <= 2 else k - 1))},
        "arc_gt": TORCH_GT, "stages": 1,
        "rows": 1, "cols": lambda k: k,
        "source": [SRC + "RedstoneTorchBlock.java:76-99", SRC + "RedstoneView.java:66-73",
                   SRC + "RedstoneWireBlock.java:343-362"],
        "rule": ("several dusts point into one solid B (strong from each, "
                 "RedstoneView:70), the torch on B reads the max: lit == !(x|y); "
                 "sparse fabric = every input through a diode onto an OR-dust, "
                 "dense fabric = the north face of B and a direct west run"),
    },
    "cmp_sub": {
        "fn": lambda m, x, y: x & ~y & m, "arity": 2,
        "pins": [{"role": "back", "strength": 15}, {"role": "side", "strength": 15}],
        "parts": lambda k, fabric="sparse": {"comparator": 1, "repeater": 2, "solid": 3},
        "arc_gt": COMPARATOR_GT, "stages": 1,
        "rows": 1, "cols": lambda k: 2,
        "source": [SRC + "ComparatorBlock.java:76-87", SRC + "ComparatorBlock.java:89-99",
                   SRC + "ComparatorBlock.java:147-177",
                   SRC + "AbstractRedstoneGateBlock.java:130-147", SRC + "RedstoneView.java:48-60"],
        "rule": ("subtract mode: output = back - max(sides) when back > sides, "
                 "else 0 (calculateOutputSignal); with both pins at strength 15 "
                 "this is x AND NOT y; two of them and a merge give |x - y| = XOR"),
    },
    "or_merge": {
        "fn": lambda m, x, y: (x | y) & m, "arity": 2,
        "precondition": lambda x, y: (x & y) == 0,
        "pins": [{"role": "diode", "strength": None}, {"role": "diode", "strength": None}],
        "parts": lambda k, fabric="sparse": {"repeater": k, "solid": k, "dust": 1},
        "arc_gt": 0, "stages": 0,
        "rows": 1, "cols": lambda k: k,
        "source": [SRC + "RedstoneWireBlock.java:251-275"],
        "rule": ("two diodes into one dust: the dust takes the max of its "
                 "sources, which is OR only when the drivers are exclusive"),
    },
    # comparator-only logic (SYN-2 rediscovery path, profile `strength` only:
    # `profiles` keeps them out of every other profile's search so the
    # D-1 / D-2 fixtures stay byte-identical)
    "cmp_inv": {
        "fn": lambda m, x: ~x & m, "arity": 1, "profiles": ("strength",),
        "pins": [{"role": "side", "strength": 15}],
        "parts": lambda k, fabric="sparse": {"comparator": 1, "redstone_block": 1, "repeater": 1, "solid": 2},
        "arc_gt": COMPARATOR_GT, "stages": 1,
        "rows": 1, "cols": lambda k: 2,
        "source": [SRC + "RedstoneBlock.java:26-34", SRC + "ComparatorBlock.java:74-87",
                   SRC + "AbstractRedstoneGateBlock.java:130-147"],
        "rule": ("subtract mode with a redstone block behind (15 on every face) and the "
                 "input on a side at strength 15: 15 - x = NOT x, an inversion with no torch"),
    },
    "dust_max": {
        "fn": lambda m, x, y: (x | y) & m, "arity": 2, "profiles": ("strength",),
        "pins": [{"role": "diode", "strength": None}, {"role": "diode", "strength": None}],
        "parts": lambda k, fabric="sparse": {"repeater": k, "solid": k, "dust": 1},
        "arc_gt": 0, "stages": 0,
        "rows": 1, "cols": lambda k: k,
        "source": [SRC + "RedstoneWireBlock.java:251-275"],
        "rule": ("two diodes into one dust: the dust takes the MAX of its sources "
                 "(getReceivedRedstonePower), which on 15/0 levels is OR with no "
                 "exclusivity condition -- or_merge's geometry, its precondition dropped"),
    },
    # wire idioms (chosen by the placer's cost, not by function)
    "rail_net": {
        "fn": None, "arity": 1, "wire": True,
        "pins": [{"role": "entry", "strength": None}],
        "parts": lambda n, fabric="sparse": {"repeater": 1, "powered_rail": n, "observer": 1, "solid": n + 2},
        "arc_gt": OBSERVER_GT, "stages": 1, "max_rails": 9,
        "rows": 1, "cols": lambda n: n,
        "source": [SRC + "PoweredRailBlock.java:113-132", SRC + "PoweredRailBlock.java:135-146",
                   SRC + "ObserverBlock.java:55-63", SRC + "ObserverBlock.java:96-102"],
        "rule": ("a repeater powers rail 0; isPoweredByOtherRails walks up to 8 "
                 "more rails synchronously (0 gt); the observer on the last rail "
                 "turns the POWERED edge into a 2 gt pulse on its back -- an EDGE "
                 "medium: a level consumer needs the piston T-flip-flop after it"),
    },
    "obs_pulse": {
        "fn": None, "arity": 1, "wire": True,
        "pins": [{"role": "front", "strength": None}],
        "parts": lambda n, fabric="sparse": {"observer": 1},
        "arc_gt": OBSERVER_GT, "stages": 1, "pulse_gt": OBSERVER_GT,
        "rows": 1, "cols": lambda n: 1,
        "source": [SRC + "ObserverBlock.java:55-63", SRC + "ObserverBlock.java:66-77"],
        "rule": "a state change of the faced block -> powered for 2 gt (scheduledTick :56-61)",
    },
    "piston_tff": {
        "fn": None, "arity": 1, "memory": True,
        "pins": [{"role": "toggle", "strength": None}],
        "parts": lambda n, fabric="sparse": {"sticky_piston": 1, "redstone_block": 1, "observer": 1, "solid": 2},
        "arc_gt": PISTON_LO_GT, "stages": 1,
        "rows": 1, "cols": lambda n: 3,
        "source": [SRC + "PistonBlock.java:132-150", SRC + "PistonBlock.java:152-166",
                   SRC + "PistonBlock.java:173-215"],
        "rule": ("declared only (DESIGN 8.1): a sticky piston moves a redstone "
                 "block between two read cells on each pulse; the moved occupancy "
                 "is the state; the router for moving occupancy is a later cut"),
    },
    "piston_rs": {
        "fn": None, "arity": 2, "memory": True,
        "pins": [{"role": "set", "strength": None}, {"role": "reset", "strength": None}],
        "parts": lambda n, fabric="sparse": {"sticky_piston": 2, "redstone_block": 1, "solid": 3},
        "arc_gt": PISTON_LO_GT, "stages": 1,
        "rows": 1, "cols": lambda n: 4,
        "source": [SRC + "PistonBlock.java:132-150", SRC + "PistonBlock.java:152-166"],
        "rule": "declared only: two pistons push one redstone block between a set cell and a reset cell",
    },
}


#: Level arithmetic (SYN-2): the comparator's rules on LEVELS 0..15, as
#: DECLARED rows -- `sfn` is the level function, `fn` is None so no search
#: uses them. No placer carries a level net yet: a dust loses one per cell
#: (RedstoneWireBlock :251-275) and every fabric pin restores 15 through a
#: repeater, so a level net is a geometry constraint the fabric does not
#: have. B-??'s carry-cancel table (`fixtures/b_final_bit_slice.cell.json`)
#: is what these rows are checked against (test_strength.py).
LEVEL_IDIOMS = {
    "cmp_cmp_s": {
        "fn": None, "sfn": lambda x, y: x if x >= y else 0, "arity": 2, "level": True,
        "pins": [{"role": "back", "strength": None}, {"role": "side", "strength": None}],
        "parts": lambda k, fabric="sparse": {"comparator": 1, "solid": 1},
        "arc_gt": COMPARATOR_GT, "stages": 1, "rows": 1, "cols": lambda k: 1,
        "source": [SRC + "ComparatorBlock.java:74-87"],
        "rule": "compare mode: back when back >= max(sides), else 0 (calculateOutputSignal)",
    },
    "cmp_sub_s": {
        "fn": None, "sfn": lambda x, y: max(x - y, 0), "arity": 2, "level": True,
        "pins": [{"role": "back", "strength": None}, {"role": "side", "strength": None}],
        "parts": lambda k, fabric="sparse": {"comparator": 1, "solid": 1},
        "arc_gt": COMPARATOR_GT, "stages": 1, "rows": 1, "cols": lambda k: 1,
        "source": [SRC + "ComparatorBlock.java:74-87"],
        "rule": "subtract mode: max(back - max(sides), 0) (calculateOutputSignal)",
    },
    "const_s": {
        "fn": None, "sfn": lambda k: int(k), "arity": 0, "level": True,
        "pins": [],
        "parts": lambda k, fabric="sparse": {"comparator": 1, "barrel": 1},
        "arc_gt": COMPARATOR_GT, "stages": 1, "rows": 1, "cols": lambda k: 2,
        "source": [SRC + "ComparatorBlock.java:102-120", SRC + "BarrelBlock.java:89-97",
                   SRC + "ScreenHandler.java:1024-1034"],
        "rule": ("a container behind a compare-mode comparator replaces the level with its "
                 "comparator output: a barrel with n single-item stacks gives "
                 "machine.inventory_output(n of count 1 / max 1, 27 slots) = 3 for 4, 14 for 26, 2 for 2"),
    },
    "attenuate_s": {
        "fn": None, "sfn": lambda x, d: max(x - int(d), 0), "arity": 2, "level": True,
        "pins": [{"role": "entry", "strength": None}, {"role": "cells", "strength": None}],
        "parts": lambda k, fabric="sparse": {"dust": k, "solid": k},
        "arc_gt": 0, "stages": 0, "rows": 1, "cols": lambda k: k,
        "source": [SRC + "RedstoneWireBlock.java:251-275"],
        "rule": "a run of d dust cells lowers the level by d (one per cell, never below 0)",
    },
    "dust_max_s": {
        "fn": None, "sfn": lambda x, y: max(x, y), "arity": 2, "level": True,
        "pins": [{"role": "source", "strength": None}, {"role": "source", "strength": None}],
        "parts": lambda k, fabric="sparse": {"dust": 1, "solid": 1},
        "arc_gt": 0, "stages": 0, "rows": 1, "cols": lambda k: 1,
        "source": [SRC + "RedstoneWireBlock.java:251-275"],
        "rule": "one dust fed by two levels carries their max (getReceivedRedstonePower)",
    },
}
IDIOMS.update(LEVEL_IDIOMS)

#: Attribution of every idiom row, in the vocabulary of
#: `notes/2026-09-06-metrics-frame.md` section 2 (OC-D102): `engine` (a
#: transcription of the 1.20.6 source), `community technique: <name>`,
#: `operator design: <bench>`, `machine-discovered: <record>`. `source`
#: stays the yarn file:line list (test_llmgen pins its shape), so the
#: attribution has its own key. A row whose behaviour was CALIBRATED on a
#: bench names it in `calibrated_on`.
ORIGIN = {
    "not": "engine", "nor": "engine", "cmp_sub": "engine", "or_merge": "engine",
    "cmp_inv": "engine", "dust_max": "engine",
    "rail_net": "community technique: instant wire (powered-rail chain, ADR-0036 family)",
    "obs_pulse": "engine",
    "piston_tff": "community technique: piston T flip-flop",
    "piston_rs": "community technique: piston RS latch",
    "cmp_cmp_s": "engine", "cmp_sub_s": "engine", "const_s": "engine",
    "attenuate_s": "engine", "dust_max_s": "engine",
}
ORIGIN_VOCABULARY = ("engine", "community technique: ", "operator design: ", "machine-discovered: ")
for _name in LEVEL_IDIOMS:
    IDIOMS[_name]["calibrated_on"] = "operator design: B-?? (the reference bit-slice circuit; its record is not part of the public export)"
for _name, _row in IDIOMS.items():
    _row.setdefault("origin", ORIGIN[_name])


def level_eval(expr):
    """Evaluate a level expression: an int, or (row name, *sub-expressions)
    over the `sfn` rows. The declared rows' only executable form."""
    if isinstance(expr, int):
        return expr
    name, args = expr[0], expr[1:]
    row = IDIOMS[name]
    if row.get("sfn") is None:
        raise KeyError("%s has no level function" % name)
    return row["sfn"](*[level_eval(a) for a in args])


def idiom_tile(name):
    """A minimal placeable occurrence of a wire / memory idiom (schema pin
    for the declared-only rows). Logic idioms are placed by place.py."""
    s = SMOOTH_STONE
    rail = block_string(POWERED_RAIL, {"powered": "false", "shape": "east_west", "waterlogged": "false"})
    if name == "rail_net":
        return [[x, 1, 0, s] for x in range(0, 4)] + [
            [0, 2, 0, block_string(REPEATER, {"delay": "1", "facing": "west", "locked": "false", "powered": "false"})],
            [1, 2, 0, rail], [2, 2, 0, rail],
            [3, 2, 0, block_string(OBSERVER, {"facing": "west", "powered": "false"})]]
    if name == "obs_pulse":
        return [[0, 1, 0, s], [0, 2, 0, block_string(OBSERVER, {"facing": "west", "powered": "false"})]]
    if name == "piston_tff":
        return [[x, 1, 0, s] for x in range(0, 3)] + [
            [0, 2, 0, block_string(STICKY_PISTON, {"extended": "false", "facing": "east"})],
            [1, 2, 0, REDSTONE_BLOCK],
            [2, 2, 0, block_string(OBSERVER, {"facing": "west", "powered": "false"})]]
    if name == "piston_rs":
        return [[x, 1, 0, s] for x in range(0, 4)] + [
            [0, 2, 0, block_string(STICKY_PISTON, {"extended": "false", "facing": "east"})],
            [1, 2, 0, REDSTONE_BLOCK],
            [3, 2, 0, block_string(STICKY_PISTON, {"extended": "false", "facing": "west"})]]
    raise KeyError(name)
