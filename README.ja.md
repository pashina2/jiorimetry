# Jiorimetry

> English: [README.md](README.md)

Minecraft 1.20.6 の redstone 回路を、既知の回路の書き写しではなく、game の source から書き起こした
規則表から導出するためのツールチェーンです。現在扱う規則は DC の信号強度演算 — comparator、
container、dust の減衰、強給電された solid — に限られます。導出した layout は、規則の写しである
Bench、headless server で立てた合成 vanilla world、そしてオペレータが実際に遊んでいる world の三つで
読み、最後の一つだけを結果として数えます。
*Jiorimetry — 自織 (jiori) + -metry。*

## 方針

書き写した回路は自分の根拠を持たないので、部品や要求が一つ変わるたびに作り直しになり、次の回路へ
持ち越せる知識も残りません。規則表から導出しておけば、変わった規則の分だけ導き直せばよく、導出の
過程そのものが次の探索の材料になります。そのため規則表には回路の形を一切入れません。形を書いた
時点で答えを先に与えたことになり、以降の工程は導出ではなく既知の回路の確認に変わるからです。

Bench は規則の再実装であり、候補の全数に掛けられるほど安価ですが、その正しさは source を読んだ人の
読みの正しさを超えません。合成 world は game の code そのものを走らせますが、誰かが遊んでいる save
ではありません。安価な段はいずれも失敗を安く済ませるためにあり、最後の段の予測にはなっても代わりに
はならない — これがこの repository で数値を扱うときの前提です。

判定器は world と速さだけが違うべきで、判定を安くするための近道は game の性質ではなく計器の都合
です。実際、ここで報告している失敗はすべて規則の誤りではなく近道の穴でした。時間を持たない不動点、
駆動せずに固定した入力、一つだけの初期状態。近道は何も隠していないと示せる間だけ残し、隠した
時点で外します。

## 構成

規則から配置済みの成果物まで 6 段で繋がっています。

1. **規則表** — 逆コンパイルした 1.20.6 の source を、行番号を引きながら人が読める表にしたもの。
   comparator、composter、torch、wire、solidity の述語。回路の形は含まない。
   [`docs/rules/`](docs/rules)
2. **代数** — LLM の agent に規則表と問いを渡し、level 符号化を明示した comparator / torch / 定数
   node の網を返させる段。網は layout ではなく、網とは独立に書いた評価器 `tools/checks/dc_eval.py`、
   `dc_eval_sub.py`、`dc_eval_alu.py` で検算する。記録は [`docs/algebra/`](docs/algebra)
3. **配置** — 網に座標を与える段。agent が幾何の規則表（隣接、dust の形状、斜めの読み、縦の
   受け渡し）の下で導いた layout は [`docs/placement/`](docs/placement)、小さな問題は規則駆動の配置器
   `tools/placer0/placer0.py` と判定器 `placer0_check.py` が扱う
4. **Bench** — `tools/llmgen/capcell.py` が DC 規則を再実装し（規則機械は `machine.py`、部品表は
   `library.py`）、block の一覧を cold と hot の二つの seed から不動点まで解く。整定を問うときは
   game tick で進める。agent には見せない参照回路に対して較正済み。layout の checker
   `tools/checks/alu_check2.py`、`alu_check_slices.py`、`alu_check_contract.py` はすべてこの Bench に
   訊く
5. **合成 world** — `tools/world/feed.py` が layout と要求を受け取り、pin の代わりになる物理的な給電器
   cell を探索し、void の 1.20.6 world を生成して（`synthworld.py`、`worldgen.py`）、freeze / step
   しながら全行を RCON で駆動し（`worldprobe.py`）、走行の出力から表を書く。記録は
   [`docs/world/`](docs/world)
6. **実 world** — 同じ block 一覧を配置 program として書き出し（`tools/llmgen/cell_to_program.py`）、
   save に置き、server を立てずに region file から `tools/world/regioncap.py` で読み戻す

file の一覧と実行に必要なものは [`tools/README.md`](tools/README.md) にあります。

## 実行

Python 3.11 以上、標準ライブラリのみで動きます。repository の root から実行してください。

```
git clone https://github.com/pashina2/jiorimetry.git && cd jiorimetry
```

git を使わない場合は [ZIP](https://github.com/pashina2/jiorimetry/archive/refs/heads/main.zip) を展開し、
その directory で実行します。

| 対象 | command | 通過時の出力 |
|---|---|---|
| Bench、全加算器の掃引 | `python tools/checks/bench_sweep.py artifacts/layouts/layout_place1.json` | vector ごとに 1 行、最後に `ALL PASS` |
| Bench、ALU 1 段 | `python tools/checks/alu_check2.py artifacts/layouts/alu_stage_v7.json` | `LINT L3 …` に続いて `PASS 32/32`。隣に `LAYOUT.rows.json` を書く |
| Bench、slice を n 枚並べた関数表 | `python tools/checks/alu_check_slices.py artifacts/layouts/alu_slice_v9.json 3` | `n=3 PASS 512/512`（n=3 は数分） |
| Bench、slice 契約 | `python tools/checks/alu_check_contract.py artifacts/layouts/alu_slice_v9.json` | C1〜C7 の測定を 1 行ずつ、最後に `CONTRACT PASS`（数分） |
| Bench、落ちる例 | `python tools/checks/alu_check_slices.py artifacts/layouts/v7_as_slice.json 1` | `FAIL` の行と `n=1 PASS 20/32`。1 段の ALU は slice ではない、という測定 |
| 代数の評価器 | `python tools/checks/dc_eval.py artifacts/layouts/net_derive2.json`、`dc_eval_sub.py artifacts/layouts/net_reuse1.json`、`dc_eval_alu.py artifacts/layouts/net_alu1.json` | 前二つは `ALL PASS`、ALU の網は `PASS 32/32` |
| 配置器 | `cd tools/placer0 && python placer0.py ../../artifacts/placer0/problems.json p2_copy_into_side` | 見つけた配置と block 数。解けない問題は上限で `UNKNOWN` |
| 配置器の判定器 | `cd tools/placer0 && python placer0_check.py ../../artifacts/placer0/problems.json p4_throughline ../../artifacts/placer0/sol_p4_throughline.json` | `PASS`。棄却時は理由（`BISTABLE` / `TIME`）と `FAIL` |
| 給電器 rig | `python tools/world/build_rig1.py` | 最後に `PASS 32/32  (r,f identical to pinned alu_check2 rows: 32/32)`。script の隣に JSON を 2 つ書く |
| layout の再生成 | `python tools/world/make_layout_world1.py && python tools/world/make_layout_world2.py` | 出力なし。commit 済みの file と byte 一致 |
| 合成 world | `python tools/world/feed.py JOB.json --out RUNDIR --run` | 給電器 cell、続いて成果物ごとに 1 行（Bench 行数、world 行数、失敗、読み取り点、整定上限、block 数）。1.20.6 の server jar と Java 21 は配布していない（[`tools/README.md`](tools/README.md)） |
| 表の checker | `python tools/check_tables.py` | 行ごとに 1 行、最後に `100 OK, 0 MISSING` |
| 単体試験 | `cd tools/llmgen && python -m unittest test_capcell test_strength` | `Ran 37 tests`、`OK (skipped=3)`。skip の 3 件は参照回路が必要で、その回路は export していない |
| 単体試験、world の道具 | `cd tools/world && python -m unittest test_feed` | `OK`。server 不要 |

なお `python tools/checks/alu_check2.py artifacts/layouts/rig1_full_bench.json` は現在 `PASS 12/32` を
出します。pin が固定値から床（pin と近傍の max）に変わったため、入力を 0 に pin しても layout 内の
給電器を上書きしなくなったのが理由で、rig の計器は上の `build_rig1.py` です。

## 結果

以下の数値はすべて [`docs/facts.ja.md`](docs/facts.ja.md)（[English](docs/facts.md)）の行から写した
ものです。表の各行は、その数値を示す file と file 中の文字列を引いており、`tools/check_tables.py` が
引用の存在を検証します。file の裏付けがない主張は表に入れず、表の下に別に並べています。

**実 world** — ALU 1 段 `v7` を save に配置し、176 block 中 176 が一覧と一致、container 6 個中 6 個が
宣言どおりの中身でした。静止状態で comparator 23 個中 23 個が Bench と一致し、lever を切り替えた
2 状態でも 24 個中 24 個が一致しています（[`docs/world/live-alu-record.md`](docs/world/live-alu-record.md)、
無加工の capture は `artifacts/world/`）。

**合成 world** — server と Java は配布していないので、記録と走行結果の JSON で追う形になります。

- 1-bit 全加算器: 8 入力すべてで Bench と一致、整定 2〜10 tick、comparator の比較 112 件で不一致 0
  （[`docs/world/world1-record.md`](docs/world/world1-record.md)）。
- ALU 1 段 `v7`: 32 行すべて一致、読み取り点 1024 中 1024（[`docs/world/world2-record.md`](docs/world/world2-record.md)）。
  道具だけで駆動し直した回は 1472 中 1472、その間の model token は 0（`artifacts/world/feed1/out_v7/`）。
- slice `alu_slice_v9` を 2 枚: 128 行すべて一致、読み取り点 14976 で不一致 0。うち 13 行は上限
  40 tick の中で 10 tick の安定窓を閉じられず、未整定として記録されています
  （[`docs/world/world4-record.md`](docs/world/world4-record.md)）。道具だけの回は 19328 中 19328
  （`artifacts/world/feed1/out_world4/`）。
- 第二 reviewer が見つけた pitch 14 の slice（道具にとっては初見）: 128 行すべて一致、20608 中 20608
  （`artifacts/world/feed1/out_p14_final/`）。
- 配置器の解 5 件: 14 行中 13 行が一致、1 行が不一致（112 点中 105）。不一致の 1 行が次節の最初の
  項目です。
- through-line 問題の loop なしの解: 2 行とも一致、整定 8 tick、68 block
  （[`docs/world/p4-decay-trace.md`](docs/world/p4-decay-trace.md)）。
- 道具が駆動した world 実行 13 回の費用: RCON 呼び出し 3648392 回、1483.3 秒、model token 0
  （[`docs/world/feed1-record.md`](docs/world/feed1-record.md)）。

Bench だけの行（v9 の n=1/2/3 で 32/128/512、契約 C1〜C7、代数の評価器など）は表の側にあります。

## 失敗

失敗はすべて [`docs/failures.ja.md`](docs/failures.ja.md)（[English](docs/failures.md)）に、示した file、
それによって変わったもの、再現 command とともに載せています。主なものを挙げます。

- **pin した入力は安全だと考えていた。** 解が自分の入力を強く駆動して pin を越え、world では latch
  しました。Bench の pin は床（pin と近傍の max）になり、それまで通っていた解は却下されるように
  なっています（`artifacts/placer0/sol_p4_throughline.latched.json`）。
- **cold start からの一回の反復で DC 解が得られると考えていた。** 双安定な回路を見落としました。
  現在は cold と hot の 2 seed から解き、食い違う cell を報告します。
- **解き直した解は world でも通ると予測し、2/2 と書いてから走らせた。** 外れました。原因は DC では
  なく時間で、Bench に整定の上限（`set_floors`、`settle_after`）が入り、判定器は pin vector の順序対を
  すべて駆動するようになりました（`sol_p4_throughline.decay.json`）。
- **40 tick の窓の終わりで立っている値は latch だと読んだ。** 実際には 1 hop あたり 1 level、1 周
  4 tick で 56 tick かけて減衰していました。上限に接した変化は整定ではなく打ち切りとして記録します。
- **1 段の ALU を slice と呼んでいた。** 並べると落ちます（`v7_as_slice.json` で `20/32`）。slice の
  条件を契約 checker C1〜C7 に書き、pitch 12 の `alu_slice_v9` がそれを通っています。
- **pitch 11 は 6 回探索してすべて同じ境界で落ちた。** 記録は
  [`docs/placement/xcheck-second-reviewer-slice-search.md`](docs/placement/xcheck-second-reviewer-slice-search.md)。

各回の記録は書かれた当時のまま [`docs/records/`](docs/records) に置いてあります。

## 未達

file が示していないものを、薄めた主張ではなく不在として挙げます。

- slice（`v9`、pitch 14）を実 world に置いた記録。Bench と合成 world だけです。
- 実 world での全加算器の配置記録。文には出てきますが、表も capture もありません。
- 多 bit の加算器や ALU。
- 時間の規則。comparator の priming（予約 tick の順序）、pulse、tick 内の順序は規則表に入っておらず、
  計器もありません。今あるのは DC の定常状態と、tick で測った整定の上限だけです。
- 手組み回路との密度や速度の比較。費用は絶対値でしか報告していません。
- export していない失敗の記録。手書き逆規則の閾値 gate 漏れ、27,103 block に達した netlist 方式、
  断片探索が見つけたとされる配置器の欠陥 2 件、game が受け付けない minus 記号で打った座標表、
  却下した draft。名前だけ `docs/failures.ja.md` の表の下にあります。
- 費用の表と人間側の費用の裏付け。session の counter から読んだ値で、計器の出力が背後にありません。

## 版

版の印は `w<面>.r<回>` に commit を付けたものです。`w` は「結果」の行が立っている最も強い面で、
0 が Bench、1 が合成 world、2 が実 world。`r` は、独立の reviewer の指摘にこの repository の file で
答え終えた回数で、[`PUBLICATION_CHECKLIST.md`](PUBLICATION_CHECKLIST.md) §7 と `docs/` 以下の
reviewer 記録から数えます。現在は **`w2.r4`** + `git rev-parse --short HEAD`。tag は付けていません。

## クレジットとライセンス

- **pashina** — オペレータ。回路意味論の裁定、実 world での検証、Bench の較正に使った参照回路。[@pashina_2](https://x.com/pashina_2)
- 導出・配置・道具は、オペレータの指揮下で LLM の agent（Claude Fable 5.1 / Opus 5）が作成。
- **Astra** — 第二 model の reviewer（GPT-6、OpenAI）。発注の設計批評、導出した網の独立検算、mux の 2,990 例検算、配置と機械化提案を作り直させた批評。

MIT ライセンス — [LICENSE](LICENSE)。

Mojang / Microsoft とは無関係です。Minecraft は Mojang Studios の商標です。game の code・jar・world
save・mod は配布していません。
