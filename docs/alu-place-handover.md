# 引き継ぎ: ALU 1 段の物理配置（Bench 30/32）— DIRECTOR 7 `f9d66fa1`、2026-09-07T19:26Z

オペレータと第二モデルの査読者の判断により、文脈長の上限に達する前に状態を保存した。会話の要約ではなく **次の実行に必要な状態** だけを書く。方針（2026-09-08）: **既存回路の解法やオペレータの経験を設計の前提にしない。規則（`docs/rules/facts-dc-v2.md`、`docs/rules/facts-geometry.md`）と実験で詰める。この開発で検証した構成は再利用してよい。未知の接続はオペレータに尋ねず小さく検証する。**

## 1. 最後に検証した配置（上書き禁止）

- `artifacts/layouts/alu_stage_T6_30of32.json` — 182 block（comparator 22、repeater 14、wire 37、barrel 7、redstone_block 1、torch 1、smooth_stone 100）、箱 x 0..9 / y 0..2 / z 0..11。
- 実行: `cd notes/2026-09-08-placealu2 && python check_alu_stage.py alu_stage_T6_30of32.json` → `PASS 30/32`（当席が 2026-09-07T19:26Z に再現）。pin と read は script の docstring。Bench = `tools/llmgen/capcell.py` の `Bench`（loader `bench_sweep.py` 同梱、状態文字列を自前で解く、barrel は stack 64 で宣言）。
- 網の意味（ALU-1、`docs/algebra/alu1.md`）: データ {0,3}、P ∈ {0,15}（0 = 算術、15 = 論理）、Wn ∈ {0,15}（**反転極性**: 15 = ADD/AND、0 = SUB/OR、局所で W3 = sub(K3, [Wn]) = 3 iff Wn = 0）。r = wire (6,2,9)、f = F (8,1,2) の出力。

## 2. 落ちる 2 行と原因（特定済み）

| op | a b k | 期待 r f | 実測 r f | 原因 |
|---|---|---|---|---|
| SUB | 1 0 1 | 0 0 | 0 3 | x2 = sub(W3, [a]) の side に **a が入っていない**（x2 = W3 のまま）→ S_x = 3 → xm = 3 → c3p = 3 → F = 3 |
| SUB | 1 1 0 | 0 0 | 0 3 | 同上 |

x2 は (6,1,6) facing south（front = S_x (6,1,5)、back = 中継 (6,1,7) = W3）。side は (5,1,6) = **c6 (5,2,6) の支持 solid**、(7,1,6) = **x1 へ W3 を渡す copy gate**（facing south、x2 からは 0 に見える）。∴ a を入れる cell が無い。

## 3. 次に試す変更（未実施）

Wn の給電 repeater (4,1,7)（facing south、back (4,1,8) = Wn post）を東側へ移し、(4,1,7) を支持 solid にして **c6 を (4,2,7) facing north** に置く（back = S5 (4,2,6) ✓）。すると c6 の west side (3,2,7) = c4 の copy gate c4c（facing west、出力は東 = c6 へ）を**直接**読めるので S4b (4,2,7) と w4b (5,2,7) が不要になり、(5,1,6) の支持義務が消え、x2 の side (5,1,6) に a（第 3 の入力 cell、wire）を置ける。ただし c7 (6,2,7) の side は w4b (5,2,7) で c4 を読んでいたので、c7 用の c4 を別の中継（例: c4c の front を別の solid にして c7 側へ）で供給し直す。**動かす部品を共有している c4 / c6 / c7 なので、修正後は 32 行全部（r と f）を再確認する**（Astra）。

## 4. 干渉を直した箇所（動かすと再発する制約）

- 中継 solid（強給電）の 6 面すべてが隣の wire に level を渡す。S6 (6,2,6) の隣に P 線を通して 5 が漏れた → P 線は x=9 経由に。
- **y=2 の wire は、水平隣が air のとき真下（y=1）の wire を斜めに読む（−1）**（VERT-1、`docs/rules/facts-vertical.md`）。塞いだ蓋: (8,2,3)（w3p の上）、(8,2,5)（a2 (8,1,5) の上）、(8,2,8)（Wn (8,1,8) の上）。y=2 の線を動かす時は真下の隣の y=1 wire を全部確認する。
- repeater / comparator の facing = **入力側**（back = pos + facing、front = pos − facing）。P の repeater (7,2,3) を逆向きに置いた失点あり。
- comparator の side は wire / redstone_block / **自分へ向いた gate** だけを読む（torch・container・solid の受電は 0）。torch は back からは 15 と読める（(3,2,8) の torch = nP、その取り付け block (3,1,8) を P で強給電）。
- cc3（c3 の copy）の side cell に Wn を置いていた席の誤り → (4,1,6) を強給電 solid の柱に（WnRep の back は solid の強受電を読める）。
- 縦の受け渡し（comparator front → 強給電 solid → 真上の wire → y=2 の gate）は Bench で無損失（5 値）。**実機は未確認**。

## 5. 段階の記録（再現用）

`south_step1.json`（北半分 + c3 の uplink (3,2,5) + c4 (2,2,5) / c5 (4,2,5) at y=2、32 行で c4 / c5 正） → T2b（c6 / c7 / P 線、32 行で c7 正） → T4（c4g + solid 2 個で合流する r、torch の nP kill、32 行で r 正） → T6（f の経路: x1 (7,1,5) fE、x2 (6,1,6) fS、W3 生成 2 個 (6,1,8) fS / (8,1,7) fE、Wn の行 z=10..11、30/32）。中間 JSON は当席の scratchpad にあり、消える。T6 だけ notes に保存。

## 6. その後

- 32/32 が出たら: (a) 合成世界（worldprobe、`docs/world/world1-record.md` の手順）で 32 行、(b) aiwb の raw program（barrel は別置き、bow 8 本 = level 3 なら **6 本**: 6/27 → floor(3.11)+1 = 4 ✗ → level 3 は **5 本**（5/27 = 0.185 → floor(2.59) + 1 = 3 ✓）、level 9 は 15 本（15/27 = 0.556 → floor(7.78) + 1 = 8 ✗ → 16 本: 0.593 → 8+1 = 9 ✓）を /data merge、torch は raw に入る）→ オペレータの `/aiwb place`。
- 2 段の接合（f(i) → k(i+1)、P / Wn の通し）は Astra (c) のとおり 1 段の後に。
- 保留中の盤の act: gateproof 常駐の起こし直し（オペレータの in-world 作業終了の合図で CONDUCTOR 6 へ）、着地 carry（今日の記録 = `notes/2026-09-08-*`、未着地）、厄払い #4〜#8（オペレータが止めた地点）。
