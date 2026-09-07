# PLACE-ALU-3 — 発注書（DIRECTOR 8 `0c3d10be`、2026-09-07T20:1xZ）

## 問い（1 つ）
T6（Bench 30/32、`T6_with_pins.json`）を出発点に、ALU 1 段の物理配置を **`alu_check2.py` で PASS 32/32 かつ lint L1/L2 が 0 件** にできるか。できたら block 一覧 JSON を返す。できなければ、最後に到達した配置と衝突の場所を返す。

## 停止条件
- 32/32 + lint L1/L2 = 0 が出た時（L3 は情報で、読み出し用の意図した接触なら可）。
- 40 分。**10 分ごとに `draft_<n>.json` をこの dir に保存**（途中で止まっても残るように）。

## 与件（読んでよい file はこれだけ + `tools/llmgen/capcell.py` / `machine.py`。オペレータの既存参照回路、web は読まない。開いた file を最後に列挙する）
- `T6_with_pins.json` — 出発点。`alu_check2.py T6_with_pins.json` → 30/32、lint L1 1 件（(8,2,7) の wire が comparator の上 = vanilla では置けない）。
- `alu_check2.py` — 32 行の判定 + lint。pin は JSON の `pins`（wire cell）で自由に動かせる / 増やせる（増やしたら報告欄に書く）。`reads` も同様。
- `../2026-09-08-placealu2/facts-dc-v2-given.md` — DC の規則（source 由来）。`../2026-09-07-place1/facts-geometry-given.md` — 配置の規則。`../2026-09-08-vert/README.md` — 縦の受け渡し + 斜め読みの規則（VERT-1）。
- `../2026-09-08-alu-place-handover.md` §2 §4 — T6 の意味（各 cell の役割）と、動かすと再発する干渉の一覧。
- `../2026-09-08-alu1/net_alu1.json` — 網（代数）。`node_values.txt` — 32 行の各 node の level（当席が評価器で出した）。

## T6 の各 gate（当席の読み、y=1 が主層、y=2 が r の cluster と P 橋）
back/front/side は facing = 入力側、front = pos − facing。
- 北半分（k→f の壁、変更不要）: kg (1,1,2) fW, c2 (2,1,3) fW, c2c (4,1,3) fW copy, c3p (6,1,3) fW, F (8,1,2) fW cmp（back K3 (7,1,2)、side w3p (8,1,3) と P rep (8,1,1)）、c1 (1,1,4) fS（back K9 (1,1,5)、side b (0,1,4)）、Qg2 (2,1,4) fS、c3 (3,1,4) fN（side a (4,1,4)、front S3 (3,1,5)）、xm (6,1,4) fS cmp（back S_x (6,1,5)）。P 行 z=0、P 注入 rep (1,1,1) (8,1,1)。
- 西の塊（Qg1 (2,1,6) fS = sub(K3q (2,1,7), [nP1 (1,1,6) fW ← RB (0,1,6) + P rep (1,1,7) fS ← P (1,1,8); WnRep (3,1,6) rep fE ← Wn solid (4,1,6)])、Wn 給電列 (4,1,9) rep fS → post (4,1,8) → rep (4,1,7) fS → (4,1,6)。P の第 2 入口 (0,1,8)→(1,1,8)→rep (2,1,8) fW → P solid (3,1,8) → torch (3,2,8) = nP。
- XOR の脚: x1 (7,1,5) fE = sub(a2 (8,1,5), [copy gate (7,1,6) fS ← W3 relay (7,1,7) ← W3b (8,1,7) fE = sub(K3 (9,1,7), [Wn (8,1,8)])]) → S_x (6,1,5)。x2 (6,1,6) fS = sub(W3 relay (6,1,7) ← W3a (6,1,8) fS = sub(K3 (6,1,9), [rep (7,1,8) fE ← Wn]), [side (5,1,6) = solid, side (7,1,6) = copy gate（向いていない → 0）]) → S_x。**落ちる 2 行の原因 = x2 の side に a が無い。**
- y=2 の r cluster: uplink wire (3,2,5)（S3 (3,1,5) の上、= c3）、c4 (2,2,5) fN cmp（K3 (2,2,4)）→ S4 (2,2,6) → wire (2,2,7) → c4c (3,2,7) fW → S4b (4,2,7) → w4b (5,2,7)；c5 (4,2,5) fN sub（K9 (4,2,4)）→ S5 (4,2,6)；c6 (5,2,6) fW = sub(S5, [w4b]) → S6 (6,2,6)；c7 (6,2,7) fN = sub(S6, [w4b, P rep (7,2,7) fE ← (8,2,7)(9,2,7) ← x=9 の P 線 ← 橋 (7,1,1) rep → K3F (7,1,2) → (7,2,2) → rep (7,2,3) → (7,2,4)(8,2,4)(9,2,4..7)]) → S7 (6,2,8)；c4g (5,2,8) fN = sub(w4b, [rep (4,2,8) fW ← torch nP]) → S4g (5,2,9)；r = wire (6,2,9) = max(S7, S4g)。蓋 solid (8,2,3) (8,2,5) (8,2,8)。

## 当席が確かめた事実（Bench / 幾何。使ってよい）
1. handover §3 の案（c6 を (4,2,7) 北向き）は不成立: (4,2,7) の gate は (4,1,7) が solid でないと置けないが、(4,1,7) は (4,1,6) を Wn で強給電する唯一の repeater（他の 3 面は WnRep / a wire / a3 で塞がる）。
2. x2 の side に a を置く唯一の cell は (5,1,6)。それは c6 (5,2,6) の支持でもある。∴ **c6（と S5 の読み手）が動く = y=2 の cluster の再配置が必須**。c6 が S5 (4,2,6) を back で読める cell は (5,2,6) / (3,2,6)（下が WnRep ✗）/ (4,2,7)（下が rep ✗）だけ。
3. (5,1,1) rep + (5,1,2) solid は死んだ橋の跡（消しても 30/32 不変）。消してよい。
4. 代数の同値（自由に選んでよい）: (a) x2 = sub(W3, [a]) = sub(K3, [Wn, a])（K3 を back、Wn と a を side に置く 1 gate で W3b と x2 を統合できる）。(b) xm = max(a, W3) − a·[Wn=0]: S_x = max(copy(a), copy(W3)) の solid、xm = sub(S_x, [as]) で as = sub(a, [Wn])。x1 / x2 が要らない代わりに as が要る。(c) P の kill は c7 でなく c5 か c6 の side でもよい（rep(P)=15 > 9）。(d) c4 の消費者は 3 つ（c6 side、c7 side、c4g back）。r_arith = c5 − 2·c4 = 3 iff c3 ∈ {0, 6}、r_logic = c4·[P=15]。
5. 干渉（handover §4 の再掲 + 追加）: 強給電 solid の 6 面は隣の wire に level を渡す（comparator / repeater が power した solid → wire は読む。**wire が power した solid → 別の wire は読まない**が comparator / repeater の back は読む）。y=2 の wire は水平隣が air なら真下の隣の wire を斜めに読む（塞ぐには y=2 側の隣を solid に）。comparator の side は wire / RB / 自分へ向いた gate だけ。repeater は back のみ（side は gate による lock）。torch は side から 0、back から 15。container は back からだけ。**RB は隣の wire に 15 を渡す。** wire を wire の隣に置くと −1（{0,3} の data には致命、Wn（≥3 で足りる）には可）。
6. tiling は今回の目標でない。x は 0..9 を推奨（必要なら 11 まで）、y は 0..2（y=3 が要るなら宣言）。z は 0..12。r の位置、P / Wn の導線、pin の位置は自由（変えたら報告）。k (0,1,2) と F (8,1,2) はそのまま。
7. Bench の癖: pin した wire は隣の強給電 solid を読まない（実機では読む）。∴ pin cell の隣に強給電 solid を置かない（置くなら、漏れが関数に効かない理由を書く）。

## 返すもの（`placealu3-result.md` + `alu_stage_v7.json`）
1. `alu_check2.py alu_stage_v7.json` の出力（PASS n/32、lint）。2. 変えた cell の一覧（消した / 足した / 向きを変えた）と各 gate の役割。3. pin と read の位置（変えた理由）。4. 開いた file の一覧、時間、自己申告 token。5. 32/32 に届かなければ: 最後の draft、衝突の場所、試して落ちた案。
