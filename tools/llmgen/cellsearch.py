#!/usr/bin/env python3
"""tools/llmgen/cellsearch.py -- find a cell by searching block
edits against the machine, with no human redstone design in the loop.

SPIKE-1 (`notes/2026-09-06-spike1-cell-search-order.md`, OC-D92). The question
the operator put is whether a generated circuit can come from the RULES alone
-- 'past no redstone community' -- instead of from the idiom table, which is
human design written down. So the only thing this module is allowed to know is
`machine`: the vocabulary below is `machine.KNOWN` itself, and the fitness is
the machine's own answer on the spec's vectors. It imports `machine` and
nothing else from this package -- no `library` rows, no `netlist`, no `map`,
no `place`, and it never opens `data/workbench/idioms/`. That absence is the
experiment, so `test_llmgen.py` pins it by reading this file's imports.

WHAT A CANDIDATE IS. A box of `dims` cells with a floor of smooth stone one
layer below it (the floor is not part of the box and is never edited: without
it nothing at y=0 could be placed at all, since dust, gates and standing
torches all demand a solid below -- RedstoneWireBlock.canPlaceAt :224-231,
AbstractRedstoneGateBlock.canPlaceAt :49-51, AbstractTorchBlock.canPlaceAt
:44-45 -- and the input levers themselves are floor levers). Input levers and
the output lamp sit at fixed cells; every other cell of the box is the genome,
one vocabulary index each.

WHAT AN ACTION IS. One block edit: place, remove, or change the state of a
single cell. An edit whose RESULT is not placeable is REFUSED, not scored --
the search never sees an illegal cell as a bad cell. Placeability is the
vanilla `canPlaceAt` of each part, transcribed the way `machine` transcribes
its rules (the four citations above, plus WallTorchBlock.canPlaceAt :71-74 for
a wall torch's attachment and WallMountedBlock.canPlaceAt :32-38 for a lever),
with 'solid' meaning `machine.SOLID`.

WHAT A SCORE IS. Every vector of the truth table is run on a FRESH machine to
its rest state (`run_to_rest`) and the lamp read; fitness is
`hits - LAMBDA * parts` with LAMBDA small enough that a part can never buy a
hit. A candidate that has no rest state (an oscillator) or that the machine
has no rule for scores `UNSETTLED_FITNESS` and is counted. Fresh-per-vector is
a decision, not an inheritance: it makes the score the steady state of the
truth table with no history, so nothing is rewarded for remembering an earlier
vector, and it makes the score independent of the order the vectors are run.

SYMMETRY. R-3's canonical form (the D4 rotations and translations) does not
apply here: the fixed input and output cells nail the frame down. What
survives, when the box places its two inputs as mirror images across the x
plane and its output on that plane, is the mirror itself -- and for a spec
that is symmetric in its two inputs (XOR is) that mirror maps a candidate to a
different candidate with the same score. `Space.mirror` is that map when the
box admits it and `None` when it does not; the search dedups on
`min(genome, mirror(genome))`.

WHAT THIS CANNOT SEE (world 0, this lane ran no Minecraft). A cell found here
is verified against the machine, which is a transcription of the source and
was calibrated against the world on other artifacts -- it is NOT an
observation. A search optimises against its evaluator, so a cell that scores
4/4 here may be exploiting a rule the machine gets wrong. Every result of this
module is UNVERIFIED in world until a dynharness run says otherwise.
"""

import argparse
import itertools
import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import machine as M                                       # noqa: E402

#: The cost of one part, in hits. The order asks for 0 < LAMBDA < 1/parts_max
#: so a whole box of parts cannot outweigh one right answer; this lane takes
#: the tighter 0 < LAMBDA < 1/(2 * parts_max) (24 editable cells -> 0.0208) so
#: that `round(fitness)` is exactly the hit count, which is what `evolve`
#: ranks survival by.
LAMBDA = 0.01

#: What a candidate scores when the machine refuses it (no rule) or never
#: reaches a rest state (an oscillator). Below the worst legal score.
UNSETTLED_FITNESS = -1.0

#: gt allowed for a candidate to reach its rest state.
REST_LIMIT = 100

#: Every block whose `machine.weak` can be non-zero -- the parts that put
#: power into a neighbour on their own. A solid is not here: it emits only
#: what one of these strong-powers into it (`machine.emitted`).
EMITTERS = frozenset({M.DUST, M.TORCH, M.WALL_TORCH, M.LEVER, M.REPEATER,
                      M.COMPARATOR, M.REDSTONE_BLOCK})
DUST_NAME = M.DUST

#: Repeater delays and comparator modes, the blockstate values `machine` reads.
DELAYS = ("1", "2", "3", "4")
MODES = ("compare", "subtract")


def build_vocabulary():
    """Every block state the machine has a rule for, as the search's alphabet.

    Index 0 is air. The lever is left out on purpose and this is the only
    place the alphabet departs from `machine.KNOWN`: a lever is the operator's
    input device, and one the search placed would be a CONSTANT (nothing
    toggles it), which `minecraft:redstone_block` already provides at 15.
    Keeping it would triple the alphabet's per-cell size for nothing.
    """
    vocab = [None]
    for name in sorted(M.SOLID):
        #: a lamp is a solid the machine also lights, so it carries `lit`
        vocab.append((name, {"lit": "false"} if name == M.LAMP else {}))
    vocab.append((M.DUST, {"power": "0"}))
    vocab.append((M.TORCH, {"lit": "true"}))
    for facing in M.HORIZONTAL:
        vocab.append((M.WALL_TORCH, {"lit": "true", "facing": facing}))
    for facing in M.HORIZONTAL:
        for delay in DELAYS:
            vocab.append((M.REPEATER, {"facing": facing, "delay": delay,
                                       "locked": "false", "powered": "false"}))
    for facing in M.HORIZONTAL:
        for mode in MODES:
            vocab.append((M.COMPARATOR, {"facing": facing, "mode": mode,
                                         "powered": "false"}))
    return tuple(vocab)


VOCABULARY = build_vocabulary()

#: The mirror x -> -x acts on the horizontal facings by swapping east and west.
MIRROR_FACING = {"east": "west", "west": "east", "north": "north", "south": "south"}


def mirrored_state(index):
    """The vocabulary index of the same block state seen in the x mirror."""
    entry = VOCABULARY[index]
    if entry is None or "facing" not in entry[1]:
        return index
    name, props = entry
    want = dict(props)
    want["facing"] = MIRROR_FACING[props["facing"]]
    for i, other in enumerate(VOCABULARY):
        if other is not None and other[0] == name and other[1] == want:
            return i
    raise ValueError(f"no mirror for vocabulary index {index}")


MIRROR_STATE = tuple(mirrored_state(i) for i in range(len(VOCABULARY)))


# --------------------------------------------------------------------- specs
#: A spec is the truth table: a tuple of (input vector, wanted lamp state).
SPEC_XOR = (((False, False), False), ((False, True), True),
            ((True, False), True), ((True, True), False))
SPEC_NOT = (((False,), True), ((True,), False))
SPEC_BUFFER = (((False,), False), ((True,), True))
SPECS = {"xor": SPEC_XOR, "not": SPEC_NOT, "buffer": SPEC_BUFFER}


class Space:
    """The box, its fixed cells, and the alphabet its cells may hold."""

    def __init__(self, dims, inputs, output, alphabet=None):
        self.dims = tuple(dims)
        nx, ny, nz = self.dims
        self.cells = tuple(sorted((x, y, z) for x in range(nx)
                                  for y in range(ny) for z in range(nz)))
        self.inputs = tuple(inputs)
        self.output = tuple(output)
        fixed = set(self.inputs) | {self.output}
        for pos in fixed:
            if pos not in self.cells:
                raise ValueError(f"{pos} is outside {self.dims}")
        self.editable = tuple(p for p in self.cells if p not in fixed)
        self.alphabet = tuple(range(len(VOCABULARY))) if alphabet is None else tuple(alphabet)
        self.floor = {(x, -1, z): (M.SMOOTH_STONE, {})
                      for x in range(nx) for z in range(nz)}
        self._index = {pos: i for i, pos in enumerate(self.editable)}
        self.mirror = self._mirror_permutation()
        self.empty = tuple(0 for _ in self.editable)

    # -- the mirror ----------------------------------------------------
    def _mirror_permutation(self):
        """The cell permutation of x -> (nx-1) - x, when the box admits it:
        the box maps onto itself, the output cell is fixed, and the inputs are
        each other's images (so a spec symmetric in its inputs keeps its
        score). `None` when any of those fails."""
        nx = self.dims[0]

        def flip(pos):
            return (nx - 1 - pos[0], pos[1], pos[2])

        if flip(self.output) != self.output:
            return None
        if sorted(flip(p) for p in self.inputs) != sorted(self.inputs):
            return None
        if len(self.inputs) < 2:
            return None
        return tuple(self._index[flip(pos)] for pos in self.editable)

    def mirror_of(self, genome):
        """The same cell seen in the x mirror (the genome itself when the box
        does not admit the mirror)."""
        if self.mirror is None:
            return genome
        return tuple(MIRROR_STATE[genome[self.mirror[i]]]
                     for i in range(len(genome)))

    def canonical(self, genome):
        """`min(genome, its mirror image)` -- one name for a pair the score
        cannot tell apart."""
        return min(genome, self.mirror_of(genome))

    # -- candidates ----------------------------------------------------
    def parts(self, genome):
        return sum(1 for s in genome if s != 0)

    def blocks(self, genome, vector):
        """The machine's block dict for this candidate under one input
        vector: the floor, the levers, the lamp, and the genome."""
        out = dict(self.floor)
        for pos, on in zip(self.inputs, vector):
            out[pos] = (M.LEVER, {"face": "floor", "facing": "north",
                                  "powered": "true" if on else "false"})
        out[self.output] = (M.LAMP, {"lit": "false"})
        for pos, state in zip(self.editable, genome):
            if state:
                name, props = VOCABULARY[state]
                out[pos] = (name, dict(props))
        return out

    # -- reachability (the DC pre-filter) ------------------------------
    def reaches_output(self, genome):
        """Can ANY influence travel from a lever to the lamp in this cell?

        An OVER-approximation of the machine's own reads, so a False here is
        a proof: the lamp is dark on every vector, the candidate scores the
        vectors that want it dark, and the machine never has to run. The
        edges are one per read `machine` performs:

            emitter -> its 6 neighbours     weak/strong power (every part
                                            that has a non-zero `weak`)
            solid   -> its 6 neighbours     ONLY when the solid itself has an
                                            emitter neighbour -- `emitted` of
                                            a solid is `received_strong`, and
                                            a solid never strong-powers
                                            another solid, which is what stops
                                            the floor slab from shorting the
                                            whole box together
            dust    -> dust one step        `dust_input`'s j loop reads a dust
                      horizontally and      diagonally up or down over a
                      one step in y         neighbour (:240-248)

        Direction is ignored on purpose (a repeater feeds only its front, a
        wall torch not its support): dropping those makes the filter coarser,
        never wrong."""
        placed = dict(self.floor)
        for pos in self.inputs:
            placed[pos] = (M.LEVER, {"face": "floor", "facing": "north",
                                     "powered": "false"})
        placed[self.output] = (M.LAMP, {"lit": "false"})
        for pos, state in zip(self.editable, genome):
            if state:
                placed[pos] = VOCABULARY[state]

        def emitter(pos):
            entry = placed.get(pos)
            return entry is not None and entry[0] in EMITTERS

        seen = set(self.inputs)
        stack = list(self.inputs)
        while stack:
            pos = stack.pop()
            if pos == self.output:
                return True
            entry = placed.get(pos)
            if entry is None:
                continue
            name = entry[0]
            if name in EMITTERS:
                out = [M.add(pos, d) for d in M.FACES]
            elif name in M.SOLID and any(emitter(M.add(pos, d)) for d in M.FACES):
                out = [M.add(pos, d) for d in M.FACES]
            else:
                continue
            if name == DUST_NAME:
                for d in M.HORIZONTAL:
                    n = M.add(pos, d)
                    out.append(M.add(n, "up"))
                    out.append(M.add(n, "down"))
            for nxt in out:
                if nxt not in seen and nxt in placed:
                    seen.add(nxt)
                    stack.append(nxt)
        return self.output in seen

    # -- placeability --------------------------------------------------
    def legal(self, genome):
        """Vanilla `canPlaceAt` for every block of the candidate, with 'solid'
        = `machine.SOLID`. The levers and the lamp are checked too, so a box
        whose fixed cells cannot be placed is refused as a whole."""
        placed = dict(self.floor)
        for pos, on in zip(self.inputs, vector_of_falses(self.inputs)):
            placed[pos] = (M.LEVER, {"face": "floor", "facing": "north",
                                     "powered": "false"})
        placed[self.output] = (M.LAMP, {"lit": "false"})
        for pos, state in zip(self.editable, genome):
            if state:
                placed[pos] = VOCABULARY[state]

        def solid(pos):
            entry = placed.get(pos)
            return entry is not None and entry[0] in M.SOLID

        for pos, (name, props) in placed.items():
            if name in (M.DUST, M.REPEATER, M.COMPARATOR, M.TORCH):
                if not solid(M.add(pos, "down")):
                    return False
            elif name == M.WALL_TORCH:
                if not solid(M.add(pos, M.OPPOSITE[props["facing"]])):
                    return False
            elif name == M.LEVER:
                attach = {"floor": "down", "ceiling": "up"}.get(
                    props.get("face"), M.OPPOSITE.get(props.get("facing")))
                if not solid(M.add(pos, attach)):
                    return False
        return True


def vector_of_falses(inputs):
    return tuple(False for _ in inputs)


def evaluate(space, spec, genome):
    """Run every vector on its own machine and count the hits.

    Returns `(hits, parts, trace)`; `hits` is `None` when the machine refused
    the candidate or it never came to rest."""
    parts = space.parts(genome)
    hits, trace = 0, []
    for vector, want in spec:
        try:
            m = M.Machine(space.blocks(genome, vector))
            gt = m.run_to_rest(limit=REST_LIMIT)
        except M.MachineError as exc:
            return None, parts, [{"vector": list(vector), "error": str(exc)}]
        lit = m.blocks[space.output][1]["lit"] == "true"
        trace.append({"vector": [bool(v) for v in vector], "lamp": lit,
                      "want": bool(want), "rest_gt": gt})
        hits += int(lit == bool(want))
    return hits, parts, trace


def fitness_of(hits, parts, sign=1):
    if hits is None:
        return UNSETTLED_FITNESS
    return sign * (hits - LAMBDA * parts)


class Scorer:
    """`evaluate` behind a memo on the canonical form, in front of the DC
    pre-filter. A cache hit and a pruned candidate both cost no machine run,
    so each is counted apart from the evaluations.

    THE PRE-FILTER SCORES, IT DOES NOT REFUSE (SPIKE-1b, a decision the order
    left to this agent). The order asks for candidates with no lever-to-lamp
    path to be 'rejected, 0 points certain, without running the machine'. Made
    a refusal -- an edit `mutate` retries, the way an unplaceable one is --
    it would stop the search dead: from the empty box EVERY first edit is
    unreachable, so a path could never be built one edit at a time, and the
    neutral drift SPIKE-1's D5 measured to be the only way out of the empty
    box would be gone. So an unreachable candidate keeps its place in the
    population and is SCORED, at exactly the score the machine would return:
    the lamp is dark on every vector, so it hits the vectors that want dark.

    The one gap, said out loud: an unreachable candidate that OSCILLATES
    would score those hits here where the machine would refuse it as having
    no rest state (UNSETTLED_FITNESS). SPIKE-1 measured 14-20 such cells per
    400,000 evaluations (0.005%), and only the unreachable share of that is
    affected; `test_llmgen.py` samples the box and pins that the two agree."""

    def __init__(self, space, spec, sign=1, prune=True):
        self.space, self.spec, self.sign = space, spec, sign
        self.prune = prune
        self.cache = {}
        self.evaluations = 0
        self.cache_hits = 0
        self.unsettled = 0
        self.pruned = 0
        #: hits an unreachable candidate scores: the vectors wanting dark
        self.dark_hits = sum(1 for _v, want in spec if not want)

    def __call__(self, genome):
        key = self.space.canonical(genome)
        got = self.cache.get(key)
        if got is not None:
            self.cache_hits += 1
            return got
        if self.prune and not self.space.reaches_output(genome):
            self.pruned += 1
            hits, parts = self.dark_hits, self.space.parts(genome)
        else:
            hits, parts, _trace = evaluate(self.space, self.spec, genome)
            self.evaluations += 1
            if hits is None:
                self.unsettled += 1
        got = (fitness_of(hits, parts, self.sign), hits, parts)
        self.cache[key] = got
        return got


def dump_rng_state(rng):
    """`random.Random.getstate()` as JSON: (version, 625 ints, gauss_next)."""
    version, internal, gauss = rng.getstate()
    return [version, list(internal), gauss]


def rebuild_rng_state(payload):
    return (payload[0], tuple(payload[1]), payload[2])


def mutate(space, rng, genome, max_edits=4, attempts=24):
    """`k` block edits, each one cell to a different state, each refused if
    the result cannot be placed. `None` when no legal edit was found."""
    k = 1
    while k < max_edits and rng.random() < 0.3:
        k += 1
    out = list(genome)
    made = 0
    for _ in range(k):
        for _try in range(attempts):
            i = rng.randrange(len(out))
            state = rng.choice(space.alphabet)
            if state == out[i]:
                continue
            was, out[i] = out[i], state
            if space.legal(tuple(out)):
                made += 1
                break
            out[i] = was
    if not made:
        return None
    return tuple(out)


def evolve(space, spec, seed, budget, mu=8, lam=32, sign=1,
           sample_every=2000, checkpoint=None, checkpoint_every=0, resume=None,
           stall_limit=200, max_seconds=0, live=None, live_every=0):
    """mu+lambda with neutral drift. Stops on a perfect score or the budget.

    SURVIVAL IS RANKED BY `round(fitness)`, WHICH IS THE HIT COUNT: LAMBDA is
    small enough (LAMBDA * parts < 1/2 for any box this searches) that the
    part cost never crosses a hit boundary, so rounding recovers the hits and
    the fraction only orders the elite -- one slot, the best fitness, always
    survives -- and picks the answer at the end. This is not decoration. Rank
    survivors by the raw fitness instead and the search cannot start: the
    empty cell already answers the two XOR vectors that want the lamp dark, so
    it scores 2.0, while every one-part neighbour scores 1.99 and is thrown
    away. Measured on this box before the fix: 5,000 evaluations, 13,718 of
    them repeats of cells already seen, best still the empty cell. The part
    cost has to be a tie-break inside a hit level, not a wall between them.

    A run can be cut into chunks: `resume` picks up a payload this function
    wrote, restoring the population and the random state, so the trajectory is
    the one an unbroken run would have taken. The counters are not identical
    across a cut -- the memo starts empty again, so a candidate the earlier
    chunk had cached is re-run and counts as an evaluation. `evaluations` is
    therefore an upper bound on the machine runs a chunked run made, and the
    exact count of an unbroken one."""
    rng = random.Random(seed)
    score = Scorer(space, spec, sign)
    want = len(spec)
    started = time.time()

    if resume:
        rng.setstate(rebuild_rng_state(resume["rng_state"]))
        population = [(score(tuple(g)), tuple(g)) for g in resume["population"]]
        score.evaluations = resume["evaluations"]
        score.pruned = resume.get("pruned", 0)
        rejected = resume["rejected_edits"]
        curve = list(resume["curve"])
        chunks = resume.get("chunks", 1) + 1
    else:
        population = [(score(space.empty), space.empty) for _ in range(mu)]
        rejected = 0
        curve = [{"evaluations": score.evaluations, "fitness": population[0][0][0],
                  "hits": population[0][0][1], "parts": population[0][0][2]}]
        chunks = 1
    best = max(population, key=lambda t: t[0][0])
    next_sample = score.evaluations + sample_every
    next_checkpoint = score.evaluations + checkpoint_every
    next_live = score.evaluations + live_every

    dropped_frames = [0]

    def frame(current):
        """Write one live frame. `best` is read from the enclosing scope at
        every call, so a frame carries the best of THIS moment rather than the
        one that stood when the run started. A frame that could not be swapped
        in is COUNTED, not raised -- see `write_json_atomic`."""
        if not write_json_atomic(live, live_record(space, spec, seed,
                                                   score.evaluations, best,
                                                   current)):
            dropped_frames[0] += 1

    #: FRAME 0, before the first child. A display started next to the search
    #: has to have something to draw; making it wait `live_every` evaluations
    #: would leave the operator looking at nothing for a whole generation, and
    #: the state at evaluation 0 -- the empty box, `mu` copies of it -- is a
    #: fact about the run rather than a placeholder.
    if live and live_every:
        frame(best)

    def result(reason):
        return {
            "seed": seed, "budget": budget, "stopped": reason, "chunks": chunks,
            "evaluations": score.evaluations, "cache_hits": score.cache_hits,
            "rejected_edits": rejected, "unsettled": score.unsettled,
            "pruned": score.pruned,
            "mu": mu, "lambda_offspring": lam, "lambda_cost": LAMBDA,
            "fitness_sign": sign, "elapsed_s": round(time.time() - started, 3),
            "space": describe(space), "spec": [[list(v), bool(w)] for v, w in spec],
            "best": best_record(space, spec, best[1], best[0]),
            "population": [list(g) for _s, g in population],
            "rng_state": dump_rng_state(rng),
            "curve": curve,
        }

    #: `max_seconds` cuts the chunk on the clock instead of on a count.
    #: A caller that must return inside a fixed wall-clock window cannot pick
    #: an evaluation count that fills it -- the rate moves with how reachable
    #: the population has become -- and a chunk killed from outside loses
    #: everything since its last checkpoint. Stopping on time makes every
    #: chunk end with a written payload the next one resumes from exactly.
    stalled, ran_out = 0, False
    while score.evaluations < budget and best[0][1] != want:
        if max_seconds and time.time() - started >= max_seconds:
            ran_out = True
            break
        was = (score.evaluations, score.pruned)
        children = []
        for _ in range(lam):
            parent = population[rng.randrange(len(population))][1]
            child = mutate(space, rng, parent)
            if child is None:
                rejected += 1
                continue
            children.append((score(child), child))
            if live and live_every and score.evaluations >= next_live:
                next_live = score.evaluations + live_every
                frame(children[-1])
            if score.evaluations >= budget:
                break
        pool = population + children
        rng.shuffle(pool)
        pool.sort(key=lambda t: round(t[0][0]), reverse=True)
        elite = max(range(len(pool)), key=lambda i: pool[i][0][0])
        population = [pool[elite]] + [p for i, p in enumerate(pool)
                                      if i != elite][:mu - 1]
        if population[0][0][0] > best[0][0]:
            best = population[0]
            curve.append({"evaluations": score.evaluations, "fitness": best[0][0],
                          "hits": best[0][1], "parts": best[0][2]})
        if score.evaluations >= next_sample:
            next_sample = score.evaluations + sample_every
            curve.append({"evaluations": score.evaluations, "fitness": best[0][0],
                          "hits": best[0][1], "parts": best[0][2]})
        if checkpoint and checkpoint_every and score.evaluations >= next_checkpoint:
            next_checkpoint = score.evaluations + checkpoint_every
            write_json(checkpoint, result("checkpoint"))
        if best[0][1] == want:
            break
        #: a box small enough to be walked out entirely stops answering with
        #: new cells -- every child is already in the memo -- and the budget
        #: would never be spent. Stop instead of spinning.
        stalled = stalled + 1 if (score.evaluations, score.pruned) == was else 0
        if stalled >= stall_limit:
            break
    curve.append({"evaluations": score.evaluations, "fitness": best[0][0],
                  "hits": best[0][1], "parts": best[0][2]})
    #: THE LAST FRAME. Without it the file on disk is whatever the loop
    #: happened to write before it stopped, and a display left running would
    #: stand on a candidate from before the answer instead of on the answer.
    if live and live_every:
        frame(best)
    #: SAID OUT LOUD, and not put in the payload: the checkpoint's shape is
    #: what `--resume` and the committed SPIKE-1 files depend on, so a number
    #: about the display goes to stdout instead of into the result.
    if dropped_frames[0]:
        print("live: " + str(dropped_frames[0]) + " frame(s) dropped (the "
              "file stayed open past " + str(LIVE_REPLACE_TRIES) + " tries)",
              file=sys.stderr)
    if best[0][1] == want:
        return result("solved")
    if ran_out:
        return result("time")
    return result("exhausted" if stalled >= stall_limit else "budget")


def exhaustive(space, spec, sign=1):
    """Every placeable candidate in the box, scored. Only for boxes small
    enough that `len(alphabet) ** len(editable)` is walkable."""
    score = Scorer(space, spec, sign)
    best = None
    legal = 0
    for genome in itertools.product(space.alphabet, repeat=len(space.editable)):
        if not space.legal(genome):
            continue
        legal += 1
        got = score(genome)
        if best is None or got[0] > best[0][0]:
            best = (got, genome)
    return {
        "space": describe(space), "spec": [[list(v), bool(w)] for v, w in spec],
        "candidates": len(space.alphabet) ** len(space.editable),
        "placeable": legal, "evaluations": score.evaluations,
        "cache_hits": score.cache_hits, "unsettled": score.unsettled,
        "pruned": score.pruned,
        "fitness_sign": sign,
        "best": best_record(space, spec, best[1], best[0]),
    }


def describe(space):
    return {"dims": list(space.dims), "inputs": [list(p) for p in space.inputs],
            "output": list(space.output), "editable_cells": len(space.editable),
            "alphabet": len(space.alphabet), "mirror": space.mirror is not None}


def genome_blocks(space, genome):
    """One candidate's block table. PURE, and NO MACHINE RUN -- which is why
    it is its own function rather than an expression inside `best_record`:
    that function runs the whole spec to attach a trace, and the live writer
    below must not pay four machine runs per frame to draw a set of cells it
    already holds. Lifted verbatim, so a checkpoint's `best.blocks` is byte
    for byte what it was."""
    return [{"pos": list(pos), "block": VOCABULARY[state][0],
             "state": dict(VOCABULARY[state][1])}
            for pos, state in sorted(zip(space.editable, genome))
            if state]


def best_record(space, spec, genome, scored):
    hits, parts, trace = evaluate(space, spec, genome)
    return {
        "fitness": scored[0], "hits": hits, "parts": parts,
        "genome": list(genome),
        "blocks": genome_blocks(space, genome),
        "trace": trace,
        "world_status": "UNVERIFIED in world (no Minecraft ran in this lane)",
    }


def write_json(path, payload):
    Path(path).write_bytes((json.dumps(payload, indent=2, sort_keys=False) + "\n")
                           .encode("utf-8"))


#: How many times a frame's swap is attempted, and the pause between tries.
#: 20 x 20 ms is 0.4 s of patience against a reader that holds the file for a
#: few milliseconds once a second -- generous enough that a frame is dropped
#: only when something is holding it open far longer than a poll, and short
#: enough that the search is never the thing waiting.
LIVE_REPLACE_TRIES = 20
LIVE_REPLACE_PAUSE = 0.02


def write_json_atomic(path, payload):
    """`write_json`, except a reader can never see half of it: the bytes go to
    a sibling temporary and `Path.replace` (`os.replace`'s own semantics)
    swaps it in.

    A SECOND WRITER RATHER THAN A CHANGE TO `write_json`: the checkpoint's
    bytes are what `--resume` and the committed SPIKE-1 files depend on, and a
    checkpoint has no reader while it is being written. The live file does --
    a display polls it once a second while the search rewrites it -- so the
    atomicity belongs to the new surface and not to the old one.

    THE TEMPORARY DOES NOT END IN `.json`. `display_search --checkpoint-dir`
    globs `*.json`, so a temporary carrying that suffix would be read as a
    checkpoint for exactly as long as it existed, which is the failure this
    function exists to prevent.

    THE SWAP RETRIES, AND A FRAME IS DROPPED RATHER THAN RAISED. MEASURED in
    this lane, on Windows, with a reader thread polling the file the way a
    display does: `os.replace` raises `PermissionError` (WinError 5) when the
    destination is open in another process. The destination of a live frame is
    open in another process BY DESIGN, once a second, because that is what
    watching it means -- so on that platform the swap is not a single act but
    one that has to wait its turn. `LIVE_REPLACE_TRIES` of them, and if the
    file is still held, THIS FRAME IS LOST AND THE SEARCH GOES ON: the live
    file is something the run is watched through, and a run that died because
    somebody was looking at it would be a worse failure than a missing frame.
    Returns whether the frame landed.
    """
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes((json.dumps(payload, indent=2, sort_keys=False) + "\n")
                    .encode("utf-8"))
    for attempt in range(LIVE_REPLACE_TRIES):
        try:
            tmp.replace(path)
            return True
        except OSError:
            if attempt + 1 < LIVE_REPLACE_TRIES:
                time.sleep(LIVE_REPLACE_PAUSE)
    try:
        tmp.unlink()
    except OSError:
        pass
    return False


def live_record(space, spec, seed, evaluations, best, current, ts=None):
    """ONE FRAME OF THE ANIMATION: the candidate being evaluated now
    (`current`) and the best so far (`best`), each as a block table.

    NO MACHINE RUN AND NO TRACE. Every number here is already in hand when the
    scorer returns, so a frame costs a JSON dump and nothing else -- and
    `hits` / `parts` are the ones the search actually scored with rather than
    a re-evaluation that could disagree with them.

    `space` and `spec` ride along so that THIS FILE IS ALREADY A CHECKPOINT to
    the display's existing adapter: `space.dims` and `best` are precisely what
    `display_search.read_checkpoint` requires. The animation therefore needs
    no second contract, only two more optional fields.

    `ts` is the frame's own clock, in seconds. It is what a reader gates on: a
    file whose `ts` has not moved carries the same frame, and drawing it again
    would rebuild a client's buffers for nothing. The WRITER stamps it rather
    than the reader taking the file's mtime, because mtime granularity is a
    fact about a filesystem and two frames must stay distinguishable on any.
    """
    def side(scored, genome):
        return {"fitness": scored[0], "hits": scored[1], "parts": scored[2],
                "blocks": genome_blocks(space, genome)}

    return {
        "seed": seed,
        "evaluations": evaluations,
        "space": describe(space),
        "spec": [[list(v), bool(w)] for v, w in spec],
        "best": side(best[0], best[1]),
        "current": side(current[0], current[1]),
        "ts": time.time() if ts is None else float(ts),
    }


#: The boxes this lane searched. `xor3` is the order's 3x3x3 with two levers
#: on the north floor corners and the lamp on the mirror plane; the two small
#: ones exist so a full enumeration can say what the best possible score is.
SPACES = {
    "xor3": lambda: Space((3, 3, 3), [(0, 0, 0), (2, 0, 0)], (1, 0, 2)),
    "tiny2": lambda: Space((2, 2, 1), [(0, 0, 0)], (1, 1, 0)),
    "line3": lambda: Space((3, 2, 1), [(0, 0, 0)], (2, 0, 0),
                           alphabet=small_alphabet()),
    #: SPIKE-1b. `xor7` is the box `cellref` MEASURED to hold both hand-built
    #: reference XORs (the comparator form at 14 parts and the torch form at
    #: 20), so a search that fails in it failed to FIND an answer that is
    #: there -- which is the distinction SPIKE-1 could not draw in 3x3x3.
    #: `xor5` is the smaller box only the comparator form fits.
    "xor5": lambda: Space((5, 1, 5), [(0, 0, 2), (4, 0, 2)], (2, 0, 2)),
    "xor7": lambda: Space((7, 1, 5), [(0, 0, 2), (6, 0, 2)], (3, 0, 2)),
}


def small_alphabet():
    """air, smooth stone, dust, standing torch -- the four states a 3x2x1 box
    can be walked exhaustively over."""
    keep = [0]
    for i, entry in enumerate(VOCABULARY):
        if entry is not None and entry[0] in (M.SMOOTH_STONE, M.DUST, M.TORCH):
            keep.append(i)
    return tuple(keep)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--space", default="xor3", choices=sorted(SPACES))
    ap.add_argument("--spec", default="xor", choices=sorted(SPECS))
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--budget", type=int, default=1000000)
    ap.add_argument("--mu", type=int, default=8)
    ap.add_argument("--offspring", type=int, default=32)
    ap.add_argument("--sign", type=int, default=1, choices=(1, -1),
                    help="-1 inverts the fitness (the negative control)")
    ap.add_argument("--exhaustive", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--checkpoint-every", type=int, default=0)
    ap.add_argument("--resume", help="a payload an earlier chunk wrote")
    ap.add_argument("--max-seconds", type=float, default=0,
                    help="end the chunk on the clock, with a resumable payload")
    ap.add_argument("--live",
                    help="a file rewritten atomically every --live-every "
                         "evaluations, for a display to poll")
    ap.add_argument("--live-every", type=int, default=0,
                    help="evaluations between live frames; 0 (default) is off")
    args = ap.parse_args(argv)

    space = SPACES[args.space]()
    spec = SPECS[args.spec]
    if args.exhaustive:
        payload = exhaustive(space, spec, sign=args.sign)
    else:
        resume = None
        if args.resume:
            resume = json.loads(Path(args.resume).read_text(encoding="utf-8"))
        payload = evolve(space, spec, args.seed, args.budget, mu=args.mu,
                         lam=args.offspring, sign=args.sign,
                         checkpoint=args.out,
                         checkpoint_every=args.checkpoint_every, resume=resume,
                         max_seconds=args.max_seconds,
                         live=args.live, live_every=args.live_every)
    if args.out:
        write_json(args.out, payload)
    summary = {k: payload[k] for k in ("evaluations", "cache_hits", "unsettled", "pruned")
               if k in payload}
    summary["hits"] = payload["best"]["hits"]
    summary["parts"] = payload["best"]["parts"]
    summary["fitness"] = payload["best"]["fitness"]
    if "stopped" in payload:
        summary["stopped"] = payload["stopped"]
        summary["elapsed_s"] = payload["elapsed_s"]
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="backslashreplace")
    raise SystemExit(main())
