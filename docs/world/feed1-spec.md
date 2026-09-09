# FEED-1 — 実機段から LLM を外す道具の仕様（DIRECTOR 8 `0c3d10be`、2026-09-08）

オペレータの方向（2026-09-08、要旨）: LLM の占有範囲を減らし、最終的に導出をアルゴリズム化する。実機段（WORLD-1/2/4）は毎回 Opus 席が給電器・world・spec・表を手で書いており（WORLD-2 187k、WORLD-4 296k）、内容は layout と pin から機械的に決まる。ここを一回払いで道具にする。

## 問い（1 つ）
`layout JSON`（`blocks`、`barrels`、`pins` {name: {cell, levels}} または slice 節、`reads`）を入力に、**給電器の合成 → fed layout の Bench 検算 → void world の生成 → worldprobe spec → 走行 → artifact ごとの表** を 1 コマンドで無人実行し、WORLD-2（v7、32 行）と WORLD-4（PLACER-0 の 5 解 + v9×2 の 128 行）の結果を人手なしで再現できるか。

## 入出力
- 入力: layout JSON（複数可、1 world に z 方向 ≥ 10 cell 間隔で並べる）、行の生成規則（`pins` の全組合せ、または ALU の mode 表）、期待値の出所（`placer0_check` の expect 式、または `alu_check_slices` の関数表）。
- 出力（1 directory）: `fed_layout.json`（給電器込み。Bench で期待値と一致した証拠 = 行ごとの一致表）、`world/`（region + block entity）、`run.spec.json`、worldprobe の `run.result.json` / `run.tables.md`（untouched）、`table.md`（artifact ごと: Bench PASS、world 行、world FAIL、read 点数、不一致率、整定 gt、block 数 = Astra の 4 項目 + read 点数）、最初の反例（cell 単位）。
- 触らないもの: 規則表、Bench、対象 layout、<operator-save>、aiwb、tools/ の既存 file（新 file は `tools/world/feed.py` として追加）。

## 給電器の合成（探索、座標は人が書かない）
- data pin（level 3）: compare gate + back barrel 247 + side の lever wire（lever ON = bit 0）。gate の front = pin cell。gate / barrel / side wire / lever 台の 4〜7 cell を pin の周囲（layout の box の外側を優先、box 内の air も可）から探索し、**(1) layout の cell と衝突しない、(2) layout の wire / gate の side・back に触れない（L3 相当）、(3) 支持がある（L1）、(4) fed layout を Bench で全行解いて期待値と一致し、`dc_solve_both` の diff が空** を満たす最初の候補を採る。候補が無ければその pin を報告して止まる（層を跨ぐ落とし = WORLD-2 の a1/a2 の形も候補に含める）。
- control pin（0/15）: pin wire の隣の solid 台 + `face=floor` lever。同じ 4 条件。
- 出力 comparator（f など）: front に wire を 1 個足して power を読む。足しても Bench の表が崩れないことを (4) で確認。

## world と spec
- WORLD-2 の `build_world2.py` の region 書き（block entity 込みの 4 行）を関数化。void、bbox は全 artifact + 給電器 + 余白 2。
- spec: freeze、lever 駆動、step 1 gt、settle 10、max_gt 40、rcon 25598、xmx 3G。**artifact ごとに wake 2 regime + warm 全行 + v 全行**（WORLD-4 の所見: 他の artifact の sweep 中に保持されているだけでは温まらない）。`max_rcon` は 1 regime の rcon 数を実測して決め、上限 600,000 を超える時は run を分割（WORLD-4 の 3 分割と同じ規則: index mod n で全 mode を跨ぐ）。
- read: 出力 wire の level（期待値 2 値）、全 comparator の powered（Bench の cmp_out>0）、slice なら through-line 入口と中間 carry。

## 受理（stop condition = 答えられる述語）
1. `feed.py artifacts/layouts/alu_stage_v7.json` が無人で WORLD-2 の 32/32（r・f）と comparator 23 の一致を再現する。
2. `feed.py` で WORLD-4 の 6 artifact を無人で回し、(A) 13/14 + p4 T=0 の反例（cell 単位で同じ 3 cell）、(B) 128/128 を再現する。**ただし Bench 側は floors + `dc_solve_both` 導入後なので、p4 の旧解は Bench の段で BISTABLE として落ちる（world に行く前に止まる）ことが正**。新解（comparator 版）は world でも一致するはず = 予測を先に書く。
3. 上の 2 件の wall time と rcon 数を表にする。

## 費用 / 席
Opus 席、上限 3 h、目安 250k（一回払い）。以後の実機段は LLM 0（`feed.py` の実行と表の転記のみ）。web なし、`<reference-circuit-records>/**` 禁止、git に触れない（着地は DIRECTOR）。
