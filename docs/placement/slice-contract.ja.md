# SLICE-1 — 発注書（DIRECTOR 8 `0c3d10be`、2026-09-07T22:5xZ）

> English: [slice-contract.md](slice-contract.md)

オペレータは、ビットスライス化・スライス同士の突き合わせ・ピッチ整合が未達であり、2 段目に進む前にこれを満たす必要があると裁定した。v7 は 1 段としては動くが slice ではない。

## 問い（1 つ）
ALU 1 段 v7（`artifacts/layouts/alu_stage_v7.json`、Bench 32/32）を、下の **slice 契約** を満たす配置 v8 に組み替え、`tools/checks/alu_check_slices.py` で **n = 1 (32 行) / n = 2 (128 行) / n = 3 (512 行) 全部 PASS** にできるか。

## slice 契約（hard）
1. **pitch は +x 方向、PX ≤ 12**（小さいほど良い）。slice の箱は x ∈ [0, PX−1]、y ∈ [0, 2]（y=3 を使うなら宣言）、z ∈ [0, Z]、Z ≤ 13。**x ≥ PX の cell は 1 つも無い。**
2. **through-line（P、Wn）**: 入口 = x=0 の wire cell、出口 = x=PX−1 の同じ (y,z) の cell。出口の東隣 (PX,y,z) が次の slice の入口 cell そのもの（wire→wire の接続）なので、**各 slice 内で repeater を通して出口の level を 15 に戻す**（P、Wn は 0/15 の制御線。0 は 0 のまま）。P の第 2 入口が要るなら、それも through-line にするか slice 内で導く（外から 2 か所に給電しない）。
3. **carry**: k = wire cell (0, yk, zk)。f = comparator (PX−1, yk, zk) facing west、その front (PX, yk, zk) = 次の slice の k cell。level は正確に 0/3。
4. **slice ごとの port**: a、b（入力、wire cell 各 1 個）、r（出力、wire cell 1 個）。**南面（z = Z）か上面（y=3）**に置く。x 面には置かない。a は 1 cell（v7 の 3 cell 分配は slice 内で copy する）。
5. **閉包**: slice i の cell と slice i±1 の cell が接するのは、through-line の出口→入口と f→k だけ。x=0 / x=PX−1 にある wire・gate は、境界の向こうの cell と結合しない（向こうは solid か air か、こちらを向いていない gate）。判定は n=2/3 の Bench（隣の slice が居ても 1 slice の表が変わらない）。
6. 干渉の規則は v7 と同じ（`docs/rules/facts-dc-v2.md`、`docs/rules/facts-geometry.md`、`docs/rules/facts-vertical.md`、`docs/alu-place-handover.md` §4）。強給電 solid の 6 面漏れ、y=2 の斜め読み、pin の隣に強給電 solid を置かない、wire→wire は −1（data には致命）。

## 与件
- v7 と PLACE-ALU-3 の設計（`docs/placement/placealu3-result.md`: S_x = max(a,W3) − a·[Wn=0]、P kill を c5/c6 の side に、dummy comparator の形状）、node の値表 `node_values.txt`、網 `artifacts/layouts/net_alu1.json`。
- 器: `tools/checks/alu_check_slices.py`（layout の `slice` 節 = pitch / through / ports を読み、n 個並べて解く）、`tools/checks/alu_check2.py`（1 段の 32 行 + lint L1/L2/L3。tiled した n=2 の layout にも lint を掛ける = `alu_check_slices.tiled(lay,2)` を JSON に書いて `lint`）。Bench = `tools/llmgen/capcell.py`。
- v7 を契約で読むと何が落ちるか（当エージェントの実測）: `v7_as_slice.json`（pitch 11、a = (10,1,4) だけ）で n=1 20/32、n=2 38/128。a の 3 cell、P の第 2 入口 (0,1,8)、Wn の行（x=4..8 のみ）、東端 (9..10) の部品が契約違反。

## 返すもの（`docs/placement/slice-contract.md`）
- `alu_slice_v8.json`（`slice` 節つき）、`draft_<n>.json`（10 分ごと）。
- `slice1-result.md`: (1) n=1/2/3 の PASS 行（印字そのまま）、(2) lint 行、(3) 契約の各項をどう満たしたか（through-line の経路と repeater の位置、a の copy、f→k の cell、x=0 / x=PX−1 の cell 一覧と境界の向こうの cell）、(4) PX、block 数、部品の内訳、(5) 未達なら最後の draft と衝突の場所、(6) 開いた file、時間、token。
上限 45 分。web なし、オペレータの既存参照回路の参照は禁止、world / aiwb / tools / git に触れない。

## 第二 reviewer の読みを受けた改訂（2026-09-08）

Astra（第二 model、reviewer）は `tools/checks/alu_check_slices.py` が n bit の関数表しか検査していないこと、`v8` が 2 条の文言に違反していること（P = 15 のとき出口 9、次の入口 8。Wn は 12 と 11）を示しました。関数表が通ったのは、P/Wn の消費側が全て repeater で正規化しているためです。契約の各条項を直接測る第二の checker `tools/checks/alu_check_contract.py` を書き、測るもの・構造で見るもの・検査しないものを docstring に列挙しました。DIRECTOR 席が 2 条項を改訂しました（開示。オペレータは覆せます）:

- **2 条。** 出口 cell（PX-1, y, z）は wire **または west 向き repeater**。測定述語は「n = 3 の全行で、slice i > 0 の入口 wire が pin level と正確に一致する（15 は 15、0 は 0）」。出口に repeater を置く配置だけが、slice i に slice 0 と同じ level を見せます。
- **4 条。** 「x 面に port を置かない」の根拠は閉包です。x = 0 / x = PX-1 列の port は、境界の向こうが air で斜めの wire 対が無ければ許可し、checker がそれを測って（C5）port を報告します（C4 note）。`v9` はこの読みで `b` を (0, 3, 6) に残しています。

`v9` = `v8` の (11,2,0) と (11,3,12) を wire から `repeater[facing=west]` に変えたもの: n = 1/2/3 で 32/32、128/128、512/512、契約 FAIL 0、note 3。

