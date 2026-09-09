# Jiorimetry

> English: [README.md](README.md)

Minecraft 1.20.6 の redstone 回路を、既知の回路を書き写すのではなく、game の source から
書き起こした規則表から導出するツールチェーンです。今の規則は DC の信号強度演算（comparator、
container、dust の減衰、強給電された solid）。結果は Bench（規則の写し）、合成 vanilla world
（headless server）、実際に遊んでいる world の 3 つで読みます。
*Jiorimetry — 自織 (jiori) + -metry。*

## なぜこう作るか

書き写した回路は、部品や要求が変わると作り直しになり、次に持ち越せるものが残りません。規則表
から導けば、変わった規則の分だけ導き直せます。表には回路の形を入れません。入れた時点で答えを
書いたことになるからです。判定は Bench で安く済ませますが、Bench は source を読んだ人の正しさ
を超えられないので、最後は world で読みます。

## 中身

規則から配置済みの成果物まで 6 段。

1. **規則表** — 逆コンパイルした 1.20.6 の source を行番号つきで表にしたもの。回路の形は含み
   ません。[`docs/rules/`](docs/rules)
2. **代数** — LLM の agent に規則表と問いを渡し、level 符号化つきの comparator / torch / 定数の
   網を返させます。網は別に書いた評価器で検算します: `tools/checks/dc_eval.py`、
   `dc_eval_sub.py`、`dc_eval_alu.py`。記録は [`docs/algebra/`](docs/algebra)
3. **配置** — 網に座標を与えます。agent が導いたものは [`docs/placement/`](docs/placement)、
   小さな問題は規則駆動の配置器 `tools/placer0/placer0.py` と判定器 `placer0_check.py`
4. **Bench** — `tools/llmgen/capcell.py` が DC 規則を再実装し（規則機械は `machine.py`、部品表
   は `library.py`）、block 一覧を cold / hot の 2 seed から不動点まで解き、整定を問うときは
   game tick で進めます。layout の checker `tools/checks/alu_check2.py`、`alu_check_slices.py`、
   `alu_check_contract.py` はすべてこれに訊きます
5. **合成 world** — `tools/world/feed.py` が layout と要求を受け取り、給電器 cell を探索し、
   void の 1.20.6 world を作り（`synthworld.py`、`worldgen.py`）、RCON で全行を駆動して
   （`worldprobe.py`）表を書きます。記録は [`docs/world/`](docs/world)
6. **実 world** — 同じ block 一覧を配置 program に書き出し（`tools/llmgen/cell_to_program.py`）、
   save に置き、region file から `tools/world/regioncap.py` で読み戻します

file の一覧と必要なものは [`tools/README.md`](tools/README.md)。

## 動かし方

Python 3.11 以上、標準ライブラリのみ。repository の root から実行します。

```
git clone https://github.com/pashina2/jiorimetry.git && cd jiorimetry
```

git を使わない場合は [ZIP](https://github.com/pashina2/jiorimetry/archive/refs/heads/main.zip) を
展開して、その directory で実行してください。

| やること | command | 通ったときの出力 |
|---|---|---|
| Bench、全加算器の掃引 | `python tools/checks/bench_sweep.py artifacts/layouts/layout_place1.json` | vector ごとに 1 行、最後に `ALL PASS` |
| Bench、ALU 1 段 | `python tools/checks/alu_check2.py artifacts/layouts/alu_stage_v7.json` | `LINT L3 …` の後に `PASS 32/32`。隣に `LAYOUT.rows.json` を書きます |
| Bench、slice を n 枚並べた関数表 | `python tools/checks/alu_check_slices.py artifacts/layouts/alu_slice_v9.json 3` | `n=3 PASS 512/512`（n=3 は数分） |
| Bench、slice 契約 | `python tools/checks/alu_check_contract.py artifacts/layouts/alu_slice_v9.json` | C1〜C7 を 1 行ずつ、最後に `CONTRACT PASS`（数分） |
| Bench、落ちる例 | `python tools/checks/alu_check_slices.py artifacts/layouts/v7_as_slice.json 1` | `FAIL` の行と `n=1 PASS 20/32`。1 段は slice ではありません |
| 代数の評価器 | `python tools/checks/dc_eval.py artifacts/layouts/net_derive2.json`、`dc_eval_sub.py artifacts/layouts/net_reuse1.json`、`dc_eval_alu.py artifacts/layouts/net_alu1.json` | 前 2 つは `ALL PASS`、ALU は `PASS 32/32` |
| 配置器 | `cd tools/placer0 && python placer0.py ../../artifacts/placer0/problems.json p2_copy_into_side` | 見つけた配置と block 数。解けない問題は上限で `UNKNOWN` |
| 配置器の判定器 | `cd tools/placer0 && python placer0_check.py ../../artifacts/placer0/problems.json p4_throughline ../../artifacts/placer0/sol_p4_throughline.json` | `PASS`。棄却は理由（`BISTABLE` / `TIME`）と `FAIL` |
| 給電器 rig | `python tools/world/build_rig1.py` | 最後に `PASS 32/32  (r,f identical to pinned alu_check2 rows: 32/32)`。script の隣に JSON を 2 つ書きます |
| layout の再生成 | `python tools/world/make_layout_world1.py && python tools/world/make_layout_world2.py` | 出力なし。commit 済みの file と一致します |
| 合成 world | `python tools/world/feed.py JOB.json --out RUNDIR --run` | 給電器 cell、続いて成果物ごとに 1 行（Bench 行数、world 行数、失敗、読み取り点、整定上限、block 数）。1.20.6 の server jar と Java 21 が別途要ります（[`tools/README.md`](tools/README.md)） |
| 表の checker | `python tools/check_tables.py` | 行ごとに 1 行と `100 OK, 0 MISSING` |
| 単体試験 | `cd tools/llmgen && python -m unittest test_capcell test_strength` | `Ran 37 tests`、`OK (skipped=3)`。skip は参照回路が要る 3 件 |
| 単体試験、world の道具 | `cd tools/world && python -m unittest test_feed` | `OK`。server 不要 |

`python tools/checks/alu_check2.py artifacts/layouts/rig1_full_bench.json` は今は `PASS 12/32` を
出します。pin が固定値ではなく床（pin と近傍の max）になったので、pin を 0 にしても layout 内の
給電器を上書きしなくなったためです。rig を測るのは上の `build_rig1.py` です。

## できたもの

数値はすべて [`docs/facts.ja.md`](docs/facts.ja.md)（[English](docs/facts.md)）の行から写して
います。表の各行は、それを示す file とその中の文字列を引いていて、`tools/check_tables.py` が
毎回検証します。file のない主張は表に入れず、表の下に別に並べています。

実際に遊んでいる world:

- ALU 1 段 `v7` を save に置き、176 block 中 176 が一覧と一致、container 6 個中 6 個が宣言どおり。
  静止状態で comparator 23 個中 23 個が Bench と一致。lever を切り替えた 2 状態も 24 個中 24 個
  一致（[`docs/world/live-alu-record.md`](docs/world/live-alu-record.md)、無加工の capture は
  `artifacts/world/`）。

合成 vanilla world（server と Java は配布していないので、記録と走行結果の JSON で追えます）:

- 1-bit 全加算器: 8 入力すべて Bench と一致、整定 2〜10 tick、comparator 比較 112 件で不一致 0
  （[`docs/world/world1-record.md`](docs/world/world1-record.md)）。
- ALU 1 段 `v7`: 32 行すべて一致、読み取り点 1024 中 1024（[`docs/world/world2-record.md`](docs/world/world2-record.md)）。
  道具だけで駆動し直した回は 1472 中 1472、model の token は 0（`artifacts/world/feed1/out_v7/`）。
- slice `alu_slice_v9` を 2 枚: 128 行すべて一致、読み取り点 14976 で不一致 0。うち 13 行は
  40 tick の上限内で 10 tick の安定窓を閉じられず、未整定として記録
  （[`docs/world/world4-record.md`](docs/world/world4-record.md)）。道具だけの回は 19328 中 19328
  （`artifacts/world/feed1/out_world4/`）。
- 第二 reviewer が見つけた pitch 14 の slice（道具は初見）: 128 行すべて一致、20608 中 20608
  （`artifacts/world/feed1/out_p14_final/`）。
- 配置器の解 5 件: 14 行中 13 行が一致、1 行が不一致（112 点中 105）。不一致の 1 行が下の
  「壊れたこと」の最初の項目です。
- through-line 問題の loop なしの解: 2 行とも一致、整定 8 tick、68 block
  （[`docs/world/p4-decay-trace.md`](docs/world/p4-decay-trace.md)）。
- 道具が駆動した world 実行 13 回の費用: RCON 呼び出し 3648392 回、1483.3 秒、model token 0
  （[`docs/world/feed1-record.md`](docs/world/feed1-record.md)）。

Bench だけの行（v9 の n=1/2/3 で 32/128/512、契約 C1〜C7、代数の評価器など）は表にあります。

## 壊れたこと

すべて [`docs/failures.ja.md`](docs/failures.ja.md)（[English](docs/failures.md)）にあり、各行に
示した file、変えたもの、再現 command がついています。主なもの:

- **pin した入力は安全だと思っていた。** 解が自分の入力を強く駆動して pin を越え、world では
  latch した。Bench の pin は床（pin と近傍の max）になり、以前通っていた解は却下されるように
  なった（`artifacts/placer0/sol_p4_throughline.latched.json`）。
- **cold start の 1 回の反復で DC 解が出ると思っていた。** 双安定な回路を見落とした。cold と hot
  の 2 seed から解き、食い違う cell を報告するようになった。
- **解き直した解は world でも通ると予測して 2/2 と書いた。** 外れた。原因は DC ではなく時間で、
  Bench に整定の上限（`set_floors`、`settle_after`）が入り、判定器は pin vector の順序対を全部
  駆動するようになった（`sol_p4_throughline.decay.json`）。
- **40 tick の窓で立っている値は latch だと思っていた。** 実際は 1 hop 1 level、1 周 4 tick で
  56 tick かけて減衰していた。上限に接した変化は整定ではなく打ち切りとして記録するようになった。
- **1 段の ALU を slice と呼んでいた。** 並べると落ちる（`v7_as_slice.json` で `20/32`）。slice の
  条件は契約 checker C1〜C7 に書き、pitch 12 の `alu_slice_v9` が通った。
- **pitch 11 は 6 回探索してすべて同じ境界で落ちた。** 記録は
  [`docs/placement/xcheck-second-reviewer-slice-search.md`](docs/placement/xcheck-second-reviewer-slice-search.md)。

各回の文はそのまま [`docs/records/`](docs/records) に置いてあります。

## ないもの

- slice（`v9`、pitch 14）を実際の world に置いた記録。Bench と合成 world だけです。
- 実 world での全加算器の配置記録（文には出てきますが、表も capture もありません）。
- 多 bit の加算器や ALU。
- 時間の規則。comparator の priming（予約 tick の順序）、pulse、tick 内の順序は規則表に入って
  おらず、計器もありません。今あるのは DC の定常状態と、tick で測った整定の上限だけです。
- 手組み回路との密度や速度の比較。
- export していない失敗の記録（手書き逆規則の閾値 gate 漏れ、27,103 block の netlist、断片探索
  の欠陥 2 件、minus 記号の座標表、却下した draft）。名前だけ `docs/failures.ja.md` の下にあります。
- 費用の表と人間側の費用の裏付け。session の counter から読んだ値で、計器の出力がありません。

## 版

版の印は `w<面>.r<回>` に commit を付けたものです。`w` は「できたもの」の行が立っている最も
強い面で、0 が Bench、1 が合成 world、2 が実 world。`r` は、独立の reviewer の指摘にこの
repository の file で答え終えた回数です（[`PUBLICATION_CHECKLIST.md`](PUBLICATION_CHECKLIST.md)
§7 と `docs/` の reviewer 記録から数えます）。今は **`w2.r4`** + `git rev-parse --short HEAD`。
tag は付けていません。

## クレジットとライセンス

- **pashina** — オペレータ。回路意味論の裁定、実 world での検証、Bench の較正に使った参照回路。[@pashina_2](https://x.com/pashina_2)
- 導出・配置・道具は、オペレータの指揮下で LLM の agent（Claude Fable 5.1 / Opus 5）が作成。
- **Astra** — 第二 model の reviewer（GPT-6、OpenAI）。発注の設計批評、導出した網の独立検算、mux の 2,990 例検算、配置と機械化提案を作り直させた批評。

MIT ライセンス — [LICENSE](LICENSE)。

Mojang / Microsoft とは無関係です。Minecraft は Mojang Studios の商標です。game の code・jar・
world save・mod は配布していません。
