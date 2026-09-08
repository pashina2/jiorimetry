# WORLD-2 — 発注書（DIRECTOR 8 `0c3d10be`、2026-09-07T20:3xZ）

## 問い（1 つ）
`artifacts/layouts/alu_stage_v7.json`（ALU 1 段、Bench 32/32）を、WORLD-1（`docs/world/world1-record.md`）と同じ手順で **合成 vanilla world（headless 1.20.6、worldprobe、freeze/step）** に置き、32 vector（ADD/SUB/AND/OR × a,b,k）の r と f が Bench と一致するか。一致数と、全 comparator（23）の powered の一致数を返す。

## 停止条件
- 32 vector の記録が取れ、表が書けた時（一致でも不一致でも）。不一致は不一致として記録する（世界も Bench も書き換えない）。
- 1.5 時間。

## 手順（WORLD-1 の写し。`record.md` §1〜§4 を先に読み、同じ 2 段構成 = 予測を先に書いてから走らせる）
1. **給電器の設計**（level 3 の data pin a×3 / b / k、level 0/15 の制御 pin P×2 / Wn）:
   - data: WORLD-1 の feeder と同形（compare gate、back = barrel **247 個 stack-64 = level 3**、side = lever 台の隣の wire、lever ON = bit 0 / OFF = bit 1）。gate の front = pin cell。pin: a (4,1,4) (8,1,5) (10,1,4)、b (0,1,4)、k (0,1,2)。
   - 制御: pin wire の隣に lever 台（solid、lever face=floor をその上）を置き、lever ON → 台が強給電 15 → wire = 15。P の pin は (0,1,0) と (0,1,8) の 2 cell（lever 2 本、常に同値で駆動）、Wn は (4,1,10)。
   - 給電器の cell は stage の block と衝突せず、stage の wire / gate の side に触れないこと（例: a2 (8,1,5) の feeder は (8,1,6) か (9,1,5) 側だが (9,1,5) は rep、(8,1,6) は air → (8,1,6) fN の gate、back (8,1,7) barrel ...のように各 pin で確かめる）。**Bench で先に検算**: `bench_sweep_feed.py`（world1）の要領で pin 無し・lever 状態で 32 行を解き、`alu_check2.py` の 32/32 と同じ r/f が出ることを確認してから世界を作る。
   - f の読み: F (8,1,2) は comparator なので、front (9,1,2) に wire を 1 つ足して power を読む（Bench で足しても 32/32 が崩れないことを先に確認。(9,1,3) の dummy comparator と隣接する）。または block entity の `OutputSignal` を nbt read。両方読めるなら両方。
2. **world**: `build_world1.py` を写して（block entity 付きで region を書く 4 行）、v7 + 給電器 + 支持床を void world に書く。オペレータの save、配置 front、`tools/**` には触れない。
3. **spec**: freeze、lever 駆動、step 1 gt、settle 10、max_gt 40、`limits.max_rcon` = 200000（64 regime）、rcon port は 25598、java_xmx 3G。**warm-up 32 regime（記録するが比較しない）→ 本番 32 regime**（WORLD-1 §4 の理由）。read: r (6,2,9) wire power=3 と power=0、f wire (9,1,2) power=3 / 0、全 23 comparator の powered（Bench の cmp_out>0 から期待値）、barrel 1 個の Items を nbt で読む。
4. **記録** `docs/world/world2-record.md`: §1 給電器、§2 Bench 予測（32 行）、§3 期待 final_value、§4 warm-up、（走行後）§5 走行、§6 表、§7 差異。結果 JSON / tables は worldprobe の出力を untouched で置く。

## 費用 / エージェント
Opus エージェント、上限 1.5 h、目安 150k token。host で全走は同時 1 本以下（他の重い process を起こさない）。
