# JioΣetry

> English: [README.md](README.md)

*Jiorimetry — 自織 (jiori, "self-weaving") + -metry.*

Minecraft 1.20.6 の redstone 回路を、人が既に知っている回路を書き写すのではなく、**game の
source から書き起こした規則表から導出する**実験的なツールチェーンです。出発点になる規則は DC の
信号強度演算 — comparator、container、dust の減衰、強給電された solid。結果は 3 回検算します。
**Bench**（規則の写し）→ **合成 vanilla world** → オペレータが実際に遊んでいる world。

現在の成果物は 2 つです。

| 成果物 | Bench | 合成 vanilla world | オペレータの world |
|---|---|---|---|
| 1 bit 全加算器 | 8/8 | 8/8、全 read 一致 | 配置して読み戻し 8/8 |
| 1 bit ALU slice（ADD / SUB / AND / OR） | 32/32 | 32/32、read 1024/1024 | 配置、静止 comparator 23/23、lever 5 本 + lamp 2 個の給電器で駆動 |

---

## 1. 方法の実体

1. **規則表。** 逆コンパイルした 1.20.6 の source を読み、行番号を引きながら DC の挙動を人が読める
   表にした物 — `ComparatorBlock`、`ComposterBlock`、`RedstoneTorchBlock`、`RedstoneWireBlock`、
   および solidity の述語。この表は **回路の形を含みません**。[`docs/rules/`](docs/rules) にあります。
2. **代数。** モデルの席に規則表と問い（「この部品で全加算器を組め」）を渡すと、明示的な level
   符号化を持つ comparator / torch / 定数 node の *網* が返ります — layout ではありません。網とは
   別に書いた独立の評価器で検算します。[`docs/algebra/`](docs/algebra) を参照。
3. **配置。** 2 つ目の席に幾何の規則表（隣接、dust の形状、斜めの読み、縦の受け渡し）と網を渡し、
   座標を返させます。[`docs/placement/`](docs/placement) を参照。
4. **Bench。** `tools/llmgen/capcell.py` は DC 規則の再実装で、block の一覧を不動点まで解きます。
   席には決して見せない既存の参照回路に対して較正してあります。layout を通す費用はゼロ、1 秒。
5. **合成世界。** layout を、新しい void の 1.20.6 world の region file に、pin 固定の入力ではなく
   物理的な給電器つきで書き込み、headless server で tick させ、freeze/step しながら dust と
   comparator を 1 つ残らず RCON 越しに読み戻します。[`docs/world/`](docs/world) を参照。
6. **オペレータの world。** 同じ block 一覧を実際の save に配置し、region file から読み戻します。

Bench は安い oracle、合成世界は正直な oracle、そして数えるのはオペレータの world です。

---

## 2. 成果

### 1 bit 全加算器（PLACE-1 / WORLD-1）

level 符号化は {0, 5}。comparator 7 個。代数は **プロジェクトの文脈をゼロ** にした席が出しました
— 渡したのは DC の規則表と問いだけです。

- Bench: 8 入力 vector すべてで `ALL PASS` — [`docs/placement/place1-bench-output.txt`](docs/placement/place1-bench-output.txt)
- 合成世界: 8/8、全 read が Bench の予測と一致、settle 2–10 game tick —
  [`docs/world/world1-tables.md`](docs/world/world1-tables.md)、生データは
  [`artifacts/world/world1.run.result.json`](artifacts/world/world1.run.result.json)
- オペレータの world: 配置して読み戻し、8/8。

### 1 bit ALU slice（`alu_stage_v7`）

データ線は {0, 3}。制御線は 2 本: `P` ∈ {0, 15} が算術と論理を選び、`Wn` ∈ {0, 15} が ADD/AND と
SUB/OR を選びます。効いている恒等式は 3 つ:

- `r_SUB = r_ADD = parity(a, b, k)`
- `f = maj(a ⊕ W, b, k)` — carry と borrow を 1 本の線に
- `AND = carry(a, b, 0)`、`OR = carry(a, b, 1)` — 論理演算が carry 比較器 *そのもの*

176 block: comparator 23、repeater 14、dust 35、container 6（level 3 の定数 4 個、level 9 が 2 個）、
redstone_block 1、torch 1、smooth_stone 96。箱は 11 × 3 × 12。

- Bench: `PASS 32/32`、`r` と `f` は正確に {0, 3} に落ちる —
  [`artifacts/rows/alu_stage_v7.json.rows.json`](artifacts/rows/alu_stage_v7.json.rows.json)
- 合成世界: **32/32 行、cell ごとの read 1024/1024 が一致**、settle 2–14 gt —
  [`docs/world/world2-record.md`](docs/world/world2-record.md)、生データは
  [`artifacts/world/world2.run.result.json`](artifacts/world/world2.run.result.json)
- オペレータの world: 176/176 block を配置、静止 comparator 23/23 が一致、駆動状態 3 つを
  region file から読み出し — [`docs/world/live-alu-record.md`](docs/world/live-alu-record.md)
- 93 block の給電器 rig（lever 5 本、composter の定数 4 個、lamp 2 個）で 32 行すべてを手で
  操作できます — [`docs/placement/rig1-result.md`](docs/placement/rig1-result.md)

---

### 追記（2026-09-08、同日後半）: 突き合わせられる bit slice

上の 1 段 v7 は動く 1 段ですが bit slice ではありませんでした。入力 `a` に 3 cell（うち 1 つは
pitch の外）が要り、`P` の第 2 入口と `Wn` の行が through-line になっておらず、東端が閉じて
いませんでした。オペレータは、bit slice の突き合わせと pitch 整合を、2 段目に進む前に満たす必要が
あると裁定しました。そこで slice 契約（`docs/placement/slice-contract.md`）と、layout をその pitch で
n 個並べて n bit の ALU 関数を全入力・全 mode について解く checker（`tools/checks/alu_check_slices.py`）を
書きました。結果 `artifacts/layouts/alu_slice_v8.json`（pitch 12、箱 12x4x14、292 block:
comparator 50、repeater 15、wire 55、barrel 7）: n=1 32/32、n=2 128/128、n=3 512/512、並べた
layout の配置 lint 0。詳細と境界 cell の一覧は `docs/placement/slice1-result.md`、2 slice の層別図は
`artifacts/images/alu_slice_v8_x2_layers.png`。未実施: 2 slice の合成世界での走行と、オペレータの
world での走行。


## 3. **主張しない** こと

- **まだ bit slice ではありません。** オペレータは、bit slice の作業 — 隣接する slice の突き合わせと
  pitch 整合 — が未達であると評価し、2 段目を試みる前にそれを満たさなければならないと裁定
  しました。`v7` は 1 段としては動きますが、slice ではありません。正式な slice 契約（+x 方向の
  pitch ≤ 12、各 slice の内側で through-line を 15 に戻すこと、carry の受け渡しが正確に 0/3、
  port は南面か上面のみ、並べたときの閉包）は
  [`docs/placement/slice-contract.md`](docs/placement/slice-contract.md) に書いてあり、`v7` を
  その契約で読むと **20/32** です — 下の再現手順を参照。
- **8 bit の何かはありません。** 多 bit の加算器も ALU も作っていません。
- **時間の主張はありません。** ここにある物はすべて DC / 定常状態です。settle 時間は観測として
  報告しているだけで、モデルではありません。
- 手組みの回路に対する **密度比較・速度比較はしません**。費用は絶対値でのみ報告します。
- **モデルに redstone の予備知識が無かったとは主張しません。** 主張はもっと狭く、検査可能です —
  規則表は source 由来で回路の形を含まない、代数の最初の段は blind で出た、以後の段はこの開発の
  内側で検証した成果物だけを再利用した。§4 を参照。

---

## 4. 由来（各席に何を渡したか）

| 段 | 席 | 渡した物 | 渡さなかった物 |
|---|---|---|---|
| DERIVE-2（加算器の代数） | blind、文脈ゼロ | DC の規則表 + 問い | 参照回路、web、他のあらゆる file |
| PLACE-1（加算器の配置） | blind | 幾何の規則表 + DERIVE-2 の網 | 同上 |
| REUSE-1（全減算器） | blind | **byte 一致** の規則表（sha256 `e6001fed…`）、問いだけ差し替え | 同上 |
| ALU-1（ALU の代数） | blind ではない | 規則表 + 上で導いた {0,3} の加算網・減算網 + 第二モデルの査読者による mux の示唆 | 参照回路、source は開けていない |
| PLACE-ALU-3（ALU の配置） | blind ではない | 規則表 v2 + 30/32 で落ちていた前身 + この session の解析 | 参照回路、web |
| RIG-1（給電器） | blind ではない | 上記 + 合成世界の給電器の形 | 同上 |

オペレータ自身の既存の参照回路は、**Bench の較正にのみ** 使いました。設計を出した席には一度も
見せていません。

---

## 5. 再現

Python 3.11 以上、標準ライブラリのみ。Bench の経路にインストールする package はありません。

```
git clone <this repo> && cd jiorimetry
```

### Bench — ALU slice、32 行

```
$ python tools/checks/alu_check2.py artifacts/layouts/alu_stage_v7.json
LINT L3 wire touches strongly-powered relay (5, 2, 7) relay (4, 2, 7) driven by (3, 2, 7)
LINT L3 wire touches strongly-powered relay (8, 1, 3) relay (7, 1, 3) driven by (6, 1, 3)
LINT L3 wire touches strongly-powered relay (8, 1, 3) relay (8, 1, 4) driven by (9, 1, 4)
LINT L3 wire touches strongly-powered relay (6, 2, 9) relay (5, 2, 9) driven by (5, 2, 8)
LINT L3 wire touches strongly-powered relay (6, 2, 9) relay (6, 2, 8) driven by (6, 2, 7)
LINT L3 wire touches strongly-powered relay (2, 2, 7) relay (2, 2, 6) driven by (2, 2, 5)
LINT L3 wire touches strongly-powered relay (8, 1, 5) relay (8, 1, 4) driven by (9, 1, 4)
LINT L3 wire touches strongly-powered relay (5, 2, 2) relay (5, 1, 2) driven by (5, 1, 1)
LINT L3 wire touches strongly-powered relay (3, 2, 5) relay (3, 1, 5) driven by (3, 1, 4)
PASS 32/32
```

`L1`（vanilla の設置支持）と `L2`（斜めの dust の読み）は hard lint で、0 です。`L3` は情報です。

### Bench — 全加算器、8 行

```
$ python tools/checks/bench_sweep.py artifacts/layouts/layout_place1.json
(0, 0, 0, 'sum', 0, 'cout', 0, 'dec', 0, 0, 'rounds', 3, True, True)
(0, 0, 1, 'sum', 5, 'cout', 0, 'dec', 1, 0, 'rounds', 4, True, True)
(0, 1, 0, 'sum', 5, 'cout', 0, 'dec', 1, 0, 'rounds', 4, True, True)
(0, 1, 1, 'sum', 0, 'cout', 5, 'dec', 0, 1, 'rounds', 3, True, True)
(1, 0, 0, 'sum', 5, 'cout', 0, 'dec', 1, 0, 'rounds', 4, True, True)
(1, 0, 1, 'sum', 0, 'cout', 5, 'dec', 0, 1, 'rounds', 3, True, True)
(1, 1, 0, 'sum', 0, 'cout', 5, 'dec', 0, 1, 'rounds', 3, True, True)
(1, 1, 1, 'sum', 5, 'cout', 5, 'dec', 1, 1, 'rounds', 3, True, True)
ALL PASS
```

### 記録された負の測定 — `v7` を slice として読む

これは **落ちるのが正しい** 測定です。slice の主張を正直に保つための計測です。

```
$ python tools/checks/alu_check_slices.py artifacts/layouts/v7_as_slice.json 1
FAIL OR A 1 B 0 k 0 r [0] f 0 conv True
FAIL OR A 1 B 0 k 1 r [0] f 0 conv True
n=1 PASS 20/32
```

（落ちるのは 12 行で、上に出ているのはその最後の 2 行です。同じ layout は `n=2` では 38/128。）

### 代数の評価器（Bench とは独立）

```
$ python tools/checks/dc_eval.py     artifacts/layouts/net_derive2.json   # ALL PASS
$ python tools/checks/dc_eval_sub.py artifacts/layouts/net_reuse1.json    # ALL PASS
$ python tools/checks/dc_eval_alu.py artifacts/layouts/net_alu1.json      # PASS 32/32
```

### 30/32 の前身と、給電器

```
$ python tools/checks/check_alu_stage.py artifacts/layouts/alu_stage_T6_30of32.json
FAIL SUB (1, 0, 1) r 0 f 3 conv True
FAIL SUB (1, 1, 0) r 0 f 3 conv True
PASS 30/32

$ python tools/checks/alu_check2.py artifacts/layouts/rig1_full_bench.json
PASS 32/32
```

給電器の掃引は回路を **lever の状態だけ** で駆動し — pin 固定の入力を使わずに — pin 版の行を
そのまま再現します。

### 単体試験

Bench とその強度モデルは単体試験を持っており、一緒に写してあります。

```
$ cd tools/llmgen && python -m unittest test_capcell test_strength
.......s....s............s........
----------------------------------------------------------------------
Ran 34 tests in 16.768s

OK (skipped=3)
```

（skip 3 件は fixture 依存の試験で、その fixture は本 export に含まれていません。）

### layout の再生成

`tools/world/make_layout_world1.py` と `make_layout_world2.py` は、段の layout から
`artifacts/layouts/layout_world1.json` と `layout_world2.json` を再生成します。どちらも commit 済みの
file を byte 単位で再現します。

### world の段（利用者が用意する software が要る）

`tools/world/` は実際の server を駆動します。完全性のために同梱していますが、そのままでは
動きません。用意する物（Minecraft 1.20.6 の server jar、Java 21 runtime、RCON を有効にした server
ディレクトリ）は [`tools/README.md`](tools/README.md) を参照してください。jar・save・mod は
一切配布していません。

---

## 6. 報告に値する失敗

- **netlist 方式の合成、27,103 block。** 初期の方式は EDA の pipeline をそのまま借り、算術を gate の
  netlist に切ってから placer に渡しました。placer は net の上で信号強度を運べず、comparator 1 個
  あたり dust 約 158 個を費やし、素朴な baseline より大きい 27,103 block の成果物を作りました。
  修正は「切るのをやめること」— 代数と配置を信号強度のまま一緒に導き、boolean の netlist には
  決して落とさない。
- **T6 が 30/32 で止まり、座標ではなく代数を変えて解けた。** SUB の 2 行が落ちたのは、`x2`
  comparator の side に入力 `a` が合法的に届く cell が無かったためです。幾何的な修正はどれも、
  既に使われている支持 cell と衝突しました。解は代数のその部分を書き換えること —
  `S_x = max(a, W3)`、`as = sub(a, [Wn])`、`xm = sub(S_x, [as])` — と、`P` kill を 1 個の
  comparator の side から共有 side へ移すことでした。これで layout から 1 列がまるごと消え、
  配置不能だった cell も一緒に消えました。
  [`docs/placement/placealu3-result.md`](docs/placement/placealu3-result.md) を参照。
- **給電器の draft は world ではなく Bench で捕まりました。** `draft_1` は 32/32 でしたが斜めの dust
  接続を 14 本持っており L2 制約で棄却、`draft_2` は repeater の背面 cell が air で 20/32。さらに
  給電の cell を 1 つ air のまま残したのは、その真上が強給電された段の relay だからで、これは
  合成世界で学んだ規則を、オペレータの save に block が 1 つも届く前に適用したものです。world
  build 3 回分を費用ゼロで回避しました。
- **notes に記録された運用上の失点** — container を詰めたと報告したが実際は詰まっていなかった
  （2 回）、座標の表を hyphen-minus ではなく U+2212 で打ち、game に拒否された、など。

---

## 7. 実測の費用

**最終段のみ**（2026-09-08: 32/32 → 合成世界 → オペレータの world → 給電器 rig）の席時間と token。
それ以前の段は同じ基準で計測していません。

| 便 | 席の class | 実時間 | token |
|---|---|---|---|
| PLACE-ALU-3（32/32 の layout） | Fable | 12 分 | 145k |
| WORLD-2（合成世界の走行） | Opus | 21 分 | 187k |
| in-world の marker 調査 | Sonnet | 3.4 分 | 108k |
| in-world の marker 修正 | Opus | 35 分 | 111k |
| RIG-1（空振り 1 回 + 本番） | Fable | 9 + 15.5 分 | 75k + 192k |
| **合計** | | **席時間 約 1.6 時間** | **約 820k** |

同じ段における人間側の費用: 配置 command 3 回、container の手詰め 6 個、client の再起動 2 回、
lever の操作。

---

## 8. リポジトリの構成

```
docs/rules/        source 由来の規則表（DC、DC v2、幾何、縦の受け渡し）
docs/algebra/      導出された網と、その独立評価器
docs/placement/    layout の導出、30/32 の前身、給電器、slice 契約
docs/world/        合成世界・実 world の記録と cell ごとの表
docs/report-alu-stage.md   ALU 1 段の物語としての記録
artifacts/layouts/ block 一覧と node の網（JSON）
artifacts/programs/ 配置 program
artifacts/rows/    行ごとの真理値表と node 値の表
artifacts/world/   worldprobe の spec と結果（無改変）、region の capture
artifacts/images/  層別図と網の図
tools/llmgen/      Bench（capcell）と、その土台の規則機械
tools/checks/      上で使った掃引・checker・評価器
tools/world/       合成世界の生成、RCON probe、region の capture
```

**言語の規約。** 二言語の文書は 1 つの規約に従います: 英語の原本が `name.md`、日本語が
`name.ja.md`、そして各々が冒頭で相手にリンクします。この規約に載っているのは、この README、
4 枚の規則表（`docs/rules/`）、slice 契約、block の網羅表、ALU 1 段のレポート、実 world の記録、
`tools/README.md` です。席が生成した結果 note と world の表 — `docs/algebra/*-result.md`、
`docs/placement/*-result.md`、`docs/placement/placealu2-partial.md`、`docs/world/world*-record.md`、
`world*-tables.md`、`PUBLICATION_CHECKLIST.md` — は英語の原本であり、翻訳は付きません。残りの
短い発注 note（`docs/algebra/` と `docs/placement/` の問い、`docs/alu-place-handover.md`）は、
書かれた当時の日本語の作業記録そのままで、対になる英語版はありません。引用と非公開の材料は
削ってありますが、数値・座標・file 参照・表は、対になる 2 つの file の間でも、元の記録との間でも
変えていません。

---

## 9. クレジット

- **pashina** — オペレータ。回路意味論の裁定、実 world での検証、Bench の較正に使った参照回路。
- 導出・配置・道具は、オペレータの指揮下で LLM の席（Claude Fable 5.1 / Opus 5）が作成。
- **Astra** — 第二 model の reviewer（発注の設計批評、導出した網の独立検算、mux の 2,990 例検算、配置と機械化提案を作り直させた批評）。

MIT ライセンス — [LICENSE](LICENSE) を参照。

Mojang / Microsoft とは無関係です。Minecraft は Mojang Studios の商標です。game の code・jar・
world save・mod は、本リポジトリでは一切配布していません。
