# WORLD-4 — 発注書（DIRECTOR 8 `0c3d10be`、2026-09-08T09:4xZ）

Astra（第二 model の reviewer）の PLACER-0 批評（2026-09-08）: 探索器と判定器が同じ規則の穴を共有しているのが最大の不足。次の最小実験 = 既存の成功解を使い捨て実機 world で再生する差分試験。当席は同意し、slice v9 の 2 段突き合わせ（WORLD-3 として保留していた分）を同じ便に載せる。

## 問い（1 つ）
WORLD-2（`docs/world/`）と同じ手順の **合成 vanilla world（headless 1.20.6、worldprobe、freeze/step、warm-up regime → 本番 regime）** で、
- (A) PLACER-0 の成功解 5 個（`artifacts/placer0/sol_p1_sub2side.json`、`sol_p2_copy_into_side.json`、`sol_p4_throughline.json`、`sol_p5_max_merge.json`、`sol_p6_vertical_cap.json`。問題は `problems.json`。p3 は充足不能なので対象外）を、問題の fixed cell + 解答 cell + 給電器で置き、**pin の全組合せ**（p1: a∈{0,3}×Wn∈{0,15} = 4、p2: 2、p4: 2、p5: 4、p6: d∈{0,3}、N=15 固定 = 2）について output wire の power が `expect`（`placer0_check.py -v` の expect 列）と一致するか。
- (B) `artifacts/layouts/alu_slice_v9.json` を `alu_check_slices.tiled(lay,2)` で 2 slice 並べ（584 cell、pitch 12）、**n=2 の 128 行**（ADD/SUB/AND/OR × A∈0..3 × B∈0..3 × k∈{0,1}）について r0 (6,3,9)、r1 (18,3,9)、f（comparator (23,2,2) の front (24,2,2) に wire を 1 個足して power を読む。Bench で足しても 128/128 が崩れないことを先に確認）が Bench と一致するか。加えて **through-line の slice 1 入口** (12,2,0) と (12,3,12) の power（期待 = pin と同値、15/0）、**中間 carry** (12,2,2) の power（期待 = `alu_check_contract.expected_carry` の 0/3）、全 comparator の powered（Bench の cmp_out>0）も読む。
返すのは、artifact ごとの Bench PASS / world FAIL 件数、期待との不一致率、整定 tick 数、配置 block 数（Astra の指定 4 項目）。

## 停止条件
- (A) 5 個 × 全組合せ と (B) 128 行の記録が取れ、表が書けた時（一致でも不一致でも）。不一致は不一致として記録し、**最初の反例を cell 単位で書く**（どの gate / wire が Bench と違う level か）。world も Bench も規則表も書き換えない。
- 2.5 時間。(A) が先、(B) が後。(A) で server が立たない等の環境障害なら (B) を試みず、障害を記録して止まる。

## 手順（WORLD-2 の写し。`docs/world/world2-record.md` §1〜§4 と `build_world2.py`、`bench_sweep_feed2.py`、`make_layout_world2.py`、`world2.spec.json` を先に読む。同じ 2 段構成 = 予測を先に書いてから走らせる）
1. **給電器**: data pin（level 0/3）= compare gate + back barrel 247 個 stack-64 + side の lever wire（lever ON = bit 0、OFF = bit 1、WORLD-2 §1 の宣言）。control pin（0/15、p1 の Wn、p4 の T、p6 の N、v9 の P と Wn）= pin wire の隣に solid 台 + `face=floor` lever（ON = 15）。p6 の N は常に 15（lever ON 固定）。給電器の cell は artifact の cell と衝突せず、artifact の wire / gate の side に触れないこと。v9 の b1 = (12,3,6) は上面 port なので、給電 gate を (11,3,6) facing=west（支持 solid (11,2,6) を足す）か別の形で置く。**Bench で先に検算**: `bench_sweep_feed2.py` の要領で pin 無し・lever 状態で全行を解き、(A) は `placer0_check.py` の expect と、(B) は `alu_check_slices.py alu_slice_v9.json 2` の 128/128 と同じ値が出ることを確認してから world を書く。
2. **world**: 1 つの void world に 6 個の artifact を z 方向に 10 cell 以上離して置く（各 artifact の原点を記録）。`build_world2.py` を写し（block entity 付きで region を書く 4 行）、支持床を足す。saves/cpu、aiwb、`tools/**` には触れない。
3. **spec**: freeze、lever 駆動、step 1 gt、settle 10、max_gt 40、rcon port 25598、java_xmx 3G。**warm-up regime（記録するが比較しない）→ 本番 regime**。(A) は artifact ごとに warm 全組合せ → v 全組合せ。(B) は warm 128 → v 128。read の数が多いので、`limits.max_rcon` は 1 regime の rcon 数を実測してから決める（上限 600000）。
4. **記録** `docs/world/record.md`: §1 給電器（artifact ごとの表）、§2 Bench 予測（(A) 14 行、(B) 128 行 + through/carry の期待）、§3 期待 final_value、§4 warm-up の理由、（走行後）§5 走行、§6 表（Astra の 4 項目を artifact ごとに）、§7 差異と最初の反例。結果 JSON / tables は worldprobe の出力を untouched で置く（`world4.run.result.json`、`world4.run.tables.md`）。build script、layout JSON、spec も同じ directory に。

## 費用 / 席
Opus 席、上限 2.5 h、目安 300k token。host で全走は同時 1 本以下（他の重い process を起こさない）。web なし、`notes/bench/**` 禁止、world / aiwb / tools / git に触れない。
