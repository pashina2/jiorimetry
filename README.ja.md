# Jiorimetry

> English: [README.md](README.md)

Minecraft 1.20.6 の redstone 回路を、人が既に知っている回路を書き写すのではなく、**game の
source から書き起こした規則表から導出する**実験的なツールチェーンです。出発点になる規則は DC の
信号強度演算 — comparator、container、dust の減衰、強給電された solid。結果は 3 つの面で読みます —
**Bench**（規則の写し）、**合成 vanilla world**（headless server）、そしてオペレータが実際に
遊んでいる **live world**。*Jiorimetry — 自織 (jiori, "self-weaving") + -metry.*

節: [1 思想](#1-思想) · [2 道具](#2-道具) · [3 事実](#3-事実) · [4 失敗](#4-失敗) ·
[5 使い方](#5-使い方) · [6 未証明](#6-未証明) · [7 版](#7-版) · [8 クレジット](#8-クレジット)

---

## 1. 思想

書き写した回路は、自分自身の説明を持ちません。部品や制約や要求が変わったときに導き直せず、次の
回路へ移せるものも残りません。だからここで抱えている対象は回路ではなく導出です — game が計算に
使っている規則を、source から人が読める表として書き起こし、それを当てはめて問いから配置済みの
成果物までを繋ぐ鎖。表には回路の形を入れない、というのが条件です。規則の中に形が書かれていれば、
それは答えを紛れ込ませたということであり、その下流はもう導出ではなく、既に知っている物の検算に
なります。

3 つの面は同じ成果物を読みますが、互いの複製ではありません。規則の写しは候補すべてに掛けられる
ほど安い代わりに、背後にある source の読みの正しさ以上には正しくなれません。合成世界は game の
code そのものを走らせますが、誰かが遊んでいる save ではありません。live world は、成果物が誰も
整えていない chunk と隣接物の中で実際に立たなければならない唯一の場所です。手前の面は失敗を安く
するために在り、どれも最後の面の代わりにはなりません — 安い面での読みは最後の面についての予測で
あって、代用ではない。

判定器 — layout が要求どおりに動くかを答える物 — は、world と速さだけが違い、それ以外は違わない
べきです。判定を安くするための近道はすべて計器側の便法であって、game の性質ではありません:
時間を持たない不動点、駆動せずに固定した入力、1 つだけの初期状態。ここに報告する価値のある失敗は
どれも規則の失敗ではなく便法の失敗で、いずれも world に訊くまで見えませんでした。だから便法は
「何も隠していない」と示せている間だけ残し、隠した瞬間に退けます。同じ理由で、要求は形を増やさず
一つに保ちます — 入力の系列と、そこから期待される出力の表。性質が増えるたびに新種の checker を
生やせば、計器は作れる回路の範囲より速く育ち、割に合わなくなります。

言語モデルによる導出は、実行のたびに払う費用であり危険です。機械的に逆引きできるものは逆引きす
べきで、順方向の規則を逆から読めば探索に要る候補手が出ます。そして成功した分解を、再利用してよい
条件と一緒に置いておけば、知識はモデルから機械へ移ります。モデルに残る取り分は分解であり、方向
としてはそれすら、導出済みの語彙の上の有限探索へ縮めていきます。作業の順序も同じ理屈から出ます:
要求を疑い、要らないものを消し、残りを単純にし、周回時間を縮め、それから自動化する — この順で。
消すべきだった物を自動化しないためです。

尺度は個々の道具ではなく鎖の全体です。ある工程は、問いから検証済みの読みまでの周回を縮めるとき
に作る価値があり、ある訂正は、次に導ける回路の範囲を広げるときに費用に見合います。

---

## 2. 道具

規則から配置済みの成果物までの 6 段。各段に、それを担う file を書きます。

1. **規則表。** 逆コンパイルした 1.20.6 の source を読み、行番号を引きながら DC の挙動を人が
   読める表にした物 — comparator、composter、torch、wire、および solidity の述語。回路の形は
   含みません。[`docs/rules/`](docs/rules)。
2. **代数。** エージェント（書かれた指示だけで動く model の 1 実行単位）に規則表と問いを渡すと、
   明示的な level 符号化を持つ comparator / torch / 定数 node の *網* が返ります — layout では
   ありません。網とは別に書いた評価器が検算します: `tools/checks/dc_eval.py`、`dc_eval_sub.py`、
   `dc_eval_alu.py`。記録は [`docs/algebra/`](docs/algebra)。
3. **配置。** その網に座標を与えます。幾何の規則表（隣接、dust の形状、斜めの読み、縦の受け渡し）
   の下で、エージェントが導いたものが [`docs/placement/`](docs/placement)、小さな問題については
   規則駆動の配置器 `tools/placer0/placer0.py` と判定器 `tools/placer0/placer0_check.py`。
4. **Bench。** `tools/llmgen/capcell.py` が DC 規則を再実装し（規則機械と部品表は
   `tools/llmgen/machine.py` と `library.py`）、block の一覧を cold と hot の 2 seed から不動点
   まで解き、整定を問うときは game tick で進めます。エージェントには見せない既存の参照回路に
   対して較正してあります。layout の checker `tools/checks/alu_check2.py`、
   `alu_check_slices.py`、`alu_check_contract.py` はいずれもこの 1 つの oracle に訊きます。
5. **合成世界。** `tools/world/feed.py` が layout と要求を受け取り、pin 固定の入力を置き換える
   物理的な給電器 cell を探索し、void の 1.20.6 world を作り（`tools/world/synthworld.py`、
   `worldgen.py`）、freeze/step しながら RCON で全行を駆動して（`tools/world/worldprobe.py`）、
   走行自身の出力から表を書きます。記録は [`docs/world/`](docs/world)。
6. **live world。** 同じ block 一覧を配置 program として書き出し
   （`tools/llmgen/cell_to_program.py`）、save に配置し、server を立てずに region file から
   `tools/world/regioncap.py` で読み戻します。

鎖の傍らに `tools/check_tables.py` が居ます。下の 2 つの表のどの行も、この repository の file を
引いていること、引いた文字列がその file にあることを検証します。file の一覧と必要な物は
[`tools/README.md`](tools/README.md)。

---

## 3. 事実

表は一つ、[`docs/facts.ja.md`](docs/facts.ja.md)（[English](docs/facts.md)）にあります。1 行は、
その数値をこの repository の file が示しているときにだけ存在します。各行は file と、その中の
文字列そのものと、ここで再現する command またはここでは走らない理由を持ちます。prose でしか
述べられていない読みは表に混ぜず表の下に並べ、`tools/check_tables.py` が引用を再検証します。

以下は、その表のうち world 2 面の行をそのまま写したものです。Bench の行と、file の裏付けが無い
主張は file の側にあります。

| 述語 | 面 | evidence | 再現方法 |
|---|---|---|---|
| ALU stage `v7` を実際の save に配置し、176 個中 176 個の block 配置が block 一覧と一致、container 6 個中 6 個が宣言どおりの中身だった。 | operator の world | `docs/world/live-alu-record.md` - `176/176 placements matched` | ここでは再現不可: save は配布していない。その回の無加工の region capture が `artifacts/world/capture.rest-20260907T2117Z.json`、`capture.add001-20260907T2125Z.json`、`capture.sub001-20260907T2126Z.json` |
| 静止状態で、配置した stage の comparator 23 個中 23 個が Bench の状態と一致した。 | operator の world | `docs/world/live-alu-record.md` - `23/23 comparators matched the Bench` | ここでは再現不可: 同じ save |
| region file から読んだ駆動 2 状態が Bench と一致し、いずれも comparator 24 個中 24 個一致。制御 lever ON で r = 3 / f = 0、OFF で r = 3 / f = 3。 | operator の world | `docs/world/live-alu-record.md` - `24/24 matched` | ここでは再現不可: 同じ save |
| 1-bit full adder が synthetic vanilla world で入力 8 通りすべて Bench を再現し、整定は 2〜10 game tick だった。 | synthetic world | `docs/world/world1-record.md` - `matches 8/8.` | ここでは再現不可: world 実行には 1.20.6 の server jar、Java 21 runtime、RCON 付き server directory が要り、いずれも配布していない（`tools/README.md`）。記録は `artifacts/world/world1.run.result.json` |
| adder の出力 2 点以外にも、8 vector にわたる comparator 状態の比較 112 件がすべて一致（不一致 0）。 | synthetic world | `docs/world/world1-record.md` - `112 read comparisons over the 8 recorded vectors, 0 unequal` | ここでは再現不可: 同じ理由 |
| ALU stage `v7` が synthetic vanilla world で 32 行すべて、r・f・畳んだ出力値のいずれについても Bench を再現した。 | synthetic world | `docs/world/world2-record.md` - `matches 32/32 for r, 32/32 for f` | ここでは再現不可: 同じ理由。記録は `artifacts/world/world2.run.result.json` |
| その回の読み取り点をすべて数えると 1024 点中 1024 点が一致し、うち comparator 状態比較 736 件は stage 自身の 23 個の comparator 上。 | synthetic world | `docs/world/world2-record.md` - `1024/1024 equal` | ここでは再現不可: 同じ理由 |
| 隣接する `alu_slice_v9` 2 枚が n=2 の 128 行すべてで Bench を再現し、読み取り点 14976 件で不一致 0。 | synthetic world | `docs/world/world4-record.md` - `14976` | ここでは再現不可: 同じ理由。記録は `artifacts/world/world4b1.run.result.json`、`world4b2`、`world4b3` |
| その回、128 行のうち 13 行は上限 40 game tick の中で 10 game tick の安定窓を閉じられず、丸めずに未整定として報告されている。 | synthetic world | `docs/world/world4-record.md` - `13 rows never closed a 10-gt window` | ここでは再現不可: 同じ理由 |
| synthetic world で駆動した placer の解 5 件のうち、14 行中 13 行は全読み取り点で一致し 1 行は一致せず、全体では 112 点中 105 点が一致。 | synthetic world | `docs/world/world4-record.md` - `105 of 112 equal` | ここでは再現不可: 同じ理由 |
| model を介さず world 側の道具に駆動させた ALU stage `v7` は world 32 行・失敗 0・読み取り点 1472 中 1472 一致。feeder cell は道具自身が探索したもの。 | synthetic world | `artifacts/world/feed1/out_v7/feed_v7.feed.md` - `0/1472` | ここでは再現不可: 同じ理由。job は `artifacts/world/feed1/job_v7.json` |
| 同じ道具で `v9` 2 枚は world 128 行・失敗 0・読み取り点 19328 中 19328 一致、未整定 13 行。 | synthetic world | `artifacts/world/feed1/out_world4/feed_world4.feed.md` - `0/19328` | ここでは再現不可: 同じ理由。job は `artifacts/world/feed1/job_world4.json` |
| 道具が一度も見たことのない pitch 14 の slice（第二 reviewer の探索が `v9` の内部を固定して見つけたもの）は world 128 行・失敗 0・読み取り点 20608 中 20608 一致。 | synthetic world | `artifacts/world/feed1/out_p14_final/feed_p14.feed.md` - `0/20608` | ここでは再現不可: 同じ理由。job は `artifacts/world/feed1/job_p14.json` |
| through-line 問題の loop 無し第三解は world 2 行・失敗 0・読み取り点 12 中 12 一致、最悪整定 8 game tick、68 block。 | synthetic world | `docs/world/p4-decay-trace.md` - `p4_throughline_v3` | ここでは再現不可: 同じ理由。出力は `artifacts/world/feed1/out_p4v3/` |
| 減衰する loop の game tick 毎 trace は、wire 1 hop あたり 1 level・1 周 4 game tick を示し、level 14 から 0 まで 56 tick。 | synthetic world | `docs/world/p4-decay-trace.md` - `14 rounds = 56 gt` | ここでは再現不可: 同じ理由。記録は `artifacts/world/feed1/out_p4trace/p4_trace.run.result.json` |
| 道具が駆動した world 実行 13 回の費用は RCON 呼び出し 3648392 回、実測 1483.3 秒、server が上がっている間の model token は 0。 | synthetic world | `docs/world/feed1-record.md` - `3648392` | ここでは再現不可: 同じ理由 |

---

## 4. 失敗

表は一つ、[`docs/failures.ja.md`](docs/failures.ja.md)（[English](docs/failures.md)）。形は同じ
で、この repository の file が示すときにだけ行になります。各行は、計器が何を信じて建てられて
いたか、そうでないと示した file、それによってこの repository で変わったもの、失敗の再現方法を
持ちます。evidence を export していない失敗は表の下に名前だけ挙げ、それ以上は主張しません。

先頭 4 行をそのまま写します。残りは file にあります。

| 信じていたこと | evidence | 変わったもの | 失敗の再現方法 |
|---|---|---|---|
| pin した入力 cell は level を保持するので、解が自分の入力を駆動することはあり得ず、pin は rule 複製への安全な問い方である。 | `docs/world/world4-record.md` - `the through-line is latched` | `tools/llmgen/capcell.py` で pin は床（pin 源と近傍の max）になった。修正後の判定器は以前通っていた解を却下し、その解は `artifacts/placer0/sol_p4_throughline.latched.json` として残されている。 | `cd tools/placer0 && python placer0_check.py ../../artifacts/placer0/problems.json p4_throughline ../../artifacts/placer0/sol_p4_throughline.latched.json`（BISTABLE と FAIL を印字） |
| rule 複製を cold start で 1 回反復すれば回路の DC 解が得られる。 | `docs/world/world4-record.md` - `in none of the other 13` | DC 解法は cold と hot の 2 seed から解き、2 解が食い違う cell を報告するようになった。挙動は `tools/llmgen/test_capcell.py` の unit test で固定。 | `cd tools/llmgen && python -m unittest test_capcell` |
| 解き直した through-line については判定器・placer・world が一致するはずで、実行前に書いた予測は 2/2 だった。 | `docs/world/feed1-record.md` - `FALSIFIED` | 対立の原因は DC ではなく時間だと辿られ、整定上限が Bench に入り（`set_floors`、`settle_after`）、placer の判定器は pin vector の順序対をすべて駆動し、contract checker に時間条項が入った。減衰する解は `artifacts/placer0/sol_p4_throughline.decay.json` として保存。 | `cd tools/placer0 && python placer0_check.py ../../artifacts/placer0/problems.json p4_throughline ../../artifacts/placer0/sol_p4_throughline.decay.json`（TIME と FAIL を印字） |
| 40 game tick の観測窓は整定を判定するのに十分で、窓の終わりで立っている値は latch である。 | `docs/world/p4-decay-trace.md` - `14 rounds = 56 gt` | 最後の変化が上限に接する regime は整定ではなく打ち切りとして記録される。整定は観測窓ではなく時間条項で縛る。 | recorded only: trace には server が要る。同じ判定の Bench 側は一つ上の行 |

### 記録

各回の記録は、書かれたときのまま置いてあります。

- [`docs/records/`](docs/records) — 記録の索引と、README にあった各回の文（回ごとの成果、由来の
  表、prose の失敗、実測費用、リポジトリ構成）。
- [`docs/world/world1-record.md`](docs/world/world1-record.md) — 合成世界の全加算器。
- [`docs/world/world2-record.md`](docs/world/world2-record.md) — 合成世界の ALU 1 段。
- [`docs/world/world4-record.md`](docs/world/world4-record.md) — 2 slice と配置器の解、そして latch。
- [`docs/world/feed1-record.md`](docs/world/feed1-record.md) — 実機段を 1 コマンドに。
- [`docs/world/p4-decay-trace.md`](docs/world/p4-decay-trace.md) — 減衰と latch を分けた tick 毎の trace。
- [`docs/world/live-alu-record.md`](docs/world/live-alu-record.md) — live world での配置と読み。
- [`docs/placement/slice1-result.md`](docs/placement/slice1-result.md) と [`slice-contract.ja.md`](docs/placement/slice-contract.ja.md) — slice 契約と、それで測った layout。
- [`docs/placement/placer0-result.md`](docs/placement/placer0-result.md) — 規則駆動の配置器の実証。
- [`docs/placement/xcheck-second-reviewer-slice-search.md`](docs/placement/xcheck-second-reviewer-slice-search.md) — 第二 reviewer の探索の cross-check。
- [`docs/report-alu-stage.ja.md`](docs/report-alu-stage.ja.md) — ALU 1 段の物語としての記録。

---

## 5. 使い方

Python 3.11 以上、標準ライブラリのみ。repository の root から実行します。Bench の経路に
インストールする package はありません。

```
git clone https://github.com/pashina2/jiorimetry.git && cd jiorimetry
```

git を使わない場合: [ZIP でまとめて download](https://github.com/pashina2/jiorimetry/archive/refs/heads/main.zip) して
展開し、展開先の directory で以下を実行してください。

| 道具 | command | 入力 / 出力 | 通ったときの出力 |
|---|---|---|---|
| Bench、全加算器の掃引 | `python tools/checks/bench_sweep.py artifacts/layouts/layout_place1.json` | layout の JSON。書き出し無し | 入力 vector 1 つにつき 1 行、最後に `ALL PASS` |
| Bench、ALU 1 段 | `python tools/checks/alu_check2.py artifacts/layouts/alu_stage_v7.json` | layout の JSON。隣に `LAYOUT.rows.json` を書く | 情報 lint の `LINT L3 …` の後に `PASS 32/32`。hard lint の `L1`（設置支持）と `L2`（斜めの dust の読み）は、綺麗なら何も出しません |
| Bench、slice の関数表 | `python tools/checks/alu_check_slices.py artifacts/layouts/alu_slice_v9.json 3` | layout の JSON と並べる枚数。書き出し無し | `n=3 PASS 512/512`（n=1 と n=2 は数秒、n=3 は数分） |
| Bench、slice 契約 | `python tools/checks/alu_check_contract.py artifacts/layouts/alu_slice_v9.json` | layout の JSON。書き出し無し | 条項 C1〜C7 の測定を 1 行ずつ、最後に FAIL 無しの `CONTRACT PASS`（数分） |
| Bench、記録された負の測定 | `python tools/checks/alu_check_slices.py artifacts/layouts/v7_as_slice.json 1` | 同上 | 落ちるのが正しい: `FAIL` の行と `n=1 PASS 20/32`。1 段は slice ではなく、それを言っているのがこの測定です |
| 代数の評価器（Bench とは独立） | `python tools/checks/dc_eval.py artifacts/layouts/net_derive2.json`、`dc_eval_sub.py artifacts/layouts/net_reuse1.json`、`dc_eval_alu.py artifacts/layouts/net_alu1.json` | 網の JSON。書き出し無し | 前 2 つは `ALL PASS`、ALU の網は `PASS 32/32` |
| 規則駆動の配置器 | `cd tools/placer0 && python placer0.py ../../artifacts/placer0/problems.json p2_copy_into_side` | 問題 file と問題名。配置を印字 | 見つけた配置と block 数。充足不能な問題では上限で `UNKNOWN` |
| 配置器の判定器 | `cd tools/placer0 && python placer0_check.py ../../artifacts/placer0/problems.json p4_throughline ../../artifacts/placer0/sol_p4_throughline.json` | 問題 file、問題名、解の JSON | `PASS`。棄却される解は理由（`BISTABLE` / `TIME`）と `FAIL` を印字 |
| 給電器 rig | `python tools/world/build_rig1.py` | script の隣に JSON を 2 つ書く | 行ごとに 1 行、最後に `PASS 32/32  (r,f identical to pinned alu_check2 rows: 32/32)` |
| layout の再生成 | `python tools/world/make_layout_world1.py && python tools/world/make_layout_world2.py` | script の隣に world の layout を書く | 出力無し。commit 済みの file と一致します — `git status --porcelain` と `cmp` で確認 |
| 実機段 | `python tools/world/feed.py JOB.json --out RUNDIR --run` | layout と要求を指す job の JSON。`RUNDIR` に world・probe の spec・走行結果・表を書く | 見つけた給電器 cell、続いて成果物ごとに 1 行: Bench 行数、world 行数、world の失敗、読み取り点、整定上限、block 数。本 repository が配布していない software が要ります — [`tools/README.md`](tools/README.md) |
| 表の checker | `python tools/check_tables.py` | 事実表・失敗表の 4 file を読む。書き出し無し | 行ごとに 1 行と `100 OK, 0 MISSING`、終了コード 0 |
| 単体試験、Bench | `cd tools/llmgen && python -m unittest test_capcell test_strength` | — | `Ran 37 tests`、`OK (skipped=3)`。skip 3 件は参照回路が要る試験で、その回路は本 export に含まれていません |
| 単体試験、実機段の道具 | `cd tools/world && python -m unittest test_feed` | — | `OK`。server は不要です |

古い印字 2 か所を訂正します。単体試験の行は 34 件と出していましたが、ここでの suite は 37 件
（skip 3、OK）で、増えたのは pin を床とする件と整定時間の件です。上の件数は実際に走らせて測り
ました。もう 1 つ、pin 版の rig の行は
`python tools/checks/alu_check2.py artifacts/layouts/rig1_full_bench.json` を `PASS 32/32` と
出していましたが、今日走らせると `PASS 12/32` です。pin が固定値ではなく床になったため、入力を
0 に pin しても、同じ layout が既に持っている物理的な給電器を上書きしなくなったからです。この
command は rig の計器ではありません。計器は上の `tools/world/build_rig1.py` で、lever の状態
だけで駆動し、いまも `PASS 32/32` を出します。

---

## 6. 未証明

ここの file が示していないもの。薄めた主張ではなく、不在です。

- **live world での slice。** `alu_slice_v9` と pitch 14 の slice は Bench と合成世界でしか
  読んでいません。live world に置いたのは ALU 1 段とその rig だけです。
- **live world での全加算器。** prose には出てきますが、その配置の表も capture も cell ごとの
  読みも、この repository にはありません。`docs/facts.ja.md` は file の裏付けが無い主張として
  挙げています。
- **多 bit の何か。** 多 bit の加算器も ALU も、どの world でも作っていません。
- **時間。** ここにある物はすべて DC の定常状態と、game tick で測った整定上限です。時間の
  モデルはなく、tick 順序の挙動 — 予約された tick による comparator の priming、pulse、tick の
  中の順序に依存するもの — を測る計器もありません。それらの規則は、この鎖が導出の出発点に
  している規則表に入っていません。
- **手組み回路に対する密度・速度の比較。** 測っていません。費用は絶対値でのみ報告します。
- **モデルの redstone 予備知識。** どちらとも主張しません。検査可能な主張はもっと狭く、規則表は
  source 由来で回路の形を含まない、代数の最初の段は project の文脈ゼロで出た、以後の段はこの
  開発の内側で検証した成果物だけを再利用した、というものです。
- **export していないと明記した失敗。** `docs/failures.ja.md` が表の下に挙げています: threshold
  gate を書き漏らした手書きの逆規則、27,103 block に達した netlist 方式の合成、配置器の欠陥 2 件を
  見つけたとされる断片探索、game が受け付けない minus 記号で打った座標表、棄却された rig と
  slice の draft。記録を export していないので、引けるのは記述だけです。
- **実測費用の表と人間側の費用**（最終段）。当時の session の counter から読んだ値で、計器の
  出力が背後にありません。[`docs/records/`](docs/records) に書かれたまま置いてあり、事実表の行に
  はしていません。

---

## 7. 版

版の印は `w<面>.r<回>` に、読み手が checkout している commit を付けたものです。`w` は事実表の行が
立っている最も強い面 — 0 が Bench、1 が合成世界、2 が live world。`r` は、独立の reviewer の指摘が
この repository の file で答えられた完了済みの回数で、
[`PUBLICATION_CHECKLIST.md`](PUBLICATION_CHECKLIST.md) §7 と `docs/` 以下の reviewer の記録から
数えます: 主要 4 文書の公開前の読み（checklist の §5・§6 と両 README で回答）、slice checker の
読み（`tools/checks/alu_check_contract.py`、`artifacts/layouts/alu_slice_v9.json`、改訂した
`docs/placement/slice-contract.md` で回答）、配置器の解を world で再生するよう求めた回
（`tools/llmgen/capcell.py`、`tools/placer0/`、`docs/world/world4-record.md` で回答）、実機段が
道具になった後の回（`tools/world/feed.py`、`artifacts/world/feed1/`、
`artifacts/layouts/reviewer_slice_p14_relocated.json`、
`docs/placement/xcheck-second-reviewer-slice-search.md`、`docs/world/p4-decay-trace.md` で回答）。
したがって現在の印は **`w2.r4`** に commit を付けたもの — `git rev-parse --short HEAD`。tag は
付けていません。

---

## 8. クレジット

- **pashina** — オペレータ。回路意味論の裁定、実 world での検証、Bench の較正に使った参照回路。[@pashina_2](https://x.com/pashina_2)
- 導出・配置・道具は、オペレータの指揮下で LLM のエージェント（Claude Fable 5.1 / Opus 5）が作成。
- **Astra** — 第二 model の reviewer（GPT-6、OpenAI）。発注の設計批評、導出した網の独立検算、mux の 2,990 例検算、配置と機械化提案を作り直させた批評。

MIT ライセンス — [LICENSE](LICENSE) を参照。

Mojang / Microsoft とは無関係です。Minecraft は Mojang Studios の商標です。game の code・jar・
world save・mod は、本リポジトリでは一切配布していません。
