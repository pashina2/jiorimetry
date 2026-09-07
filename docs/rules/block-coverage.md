# 規則化した block の一覧（DC 層、1.20.6、2026-09-08 時点）

「規則化」= 1.20.6-yarn の逆コンパイル source を読み、挙動を自分の言葉で事実表（`docs/rules/`）に書き、Bench（`tools/llmgen/capcell.py` + `machine.py`）が同じ規則で解き、合成世界と実世界で一致を確認した物。code は含まない。時間（tick / priming）の層は対象外。

| block | 規則化した性質（DC） | 出所（事実表 → source の位置） | Bench | 実機 | 使った所 |
|---|---|---|---|---|---|
| **comparator** | facing = 入力側、back = pos+facing、front = pos−facing、side = 水平 ±90°。back は wire の power / gate の出力 / solid の強受電 / redstone_block 15 / container の level（solid 越し 1 段も）。side は wire・redstone_block・自分へ向いた gate だけ（solid の受電・torch・container は 0）。出力: i==0 → 0、j>i → 0、subtract → i−j、compare → i。front が solid なら強給電（level = 出力）、wire なら power | facts-dc-v2 → `ComparatorBlock.getPower` 102-120、`calculateOutputSignal` 74-87、`AbstractRedstoneGateBlock.getPower` 130-139、`getMaxInputLevelSides` 141-147、`getWeakRedstonePower` 81-88 | ○ | ○（full adder 8/8、ALU 32/32、23 個の出力を region で一致） | 全部 |
| **repeater** | back > 0 → 出力 15、else 0（正規化）。side は gate による lock のみ。back は solid の強受電 / wire / 向いた gate を読む | facts-dc-v2「その他の部品」、facts-geometry | ○ | ○ | P / Wn の注入と through-line、Wn 給電列 |
| **redstone_wire** | 隣の wire から −1、gate 出力 / 強給電 solid / redstone_block から無損失。水平隣が solid でその上が非 solid なら「隣の上の wire」を読む（登り）、隣が非 solid なら「隣の下の wire」を読む（降り、VERT-1）。上に solid があると登りは切れる。wire は向く solid を弱給電（gate の back からは強のみ読める）。設置は下が full square の block | facts-geometry → `RedstoneWireBlock.getReceivedRedstonePower` 251-275、`canRunOnTop` 224-233、`getRenderConnectionType` 201；VERT-1 | ○ | ○（斜め読みは Bench で発見、実機では回避配置） | 全部 |
| **導体 solid（smooth_stone 等）** | 述語 = full cube かつ `solidBlock(never)` で外されていない。強給電（gate の front / repeater / torch の上）は 6 面すべての隣の wire と gate の back に level を渡す。solid → solid には伝わらない | facts-dc-v2 → `AbstractBlock.Settings.solidBlockPredicate` 1179、never 指定 24 種；facts-geometry「solid の中継」 | ○ | ○（relay 中継、縦の受け渡し） | relay、支持、蓋 |
| **非導体（glass、observer、redstone_block、leaves、ice、glowstone、sea_lantern、beacon、moving piston、tnt、scaffolding、powder_snow、copper_grate、copper_bulb、dripstone、chorus_flower、bamboo）** | `solidBlock(never)` の 24 種 = 受電を中継しない | facts-dc-v2 | ○（一覧として） | — | 未使用（分離材の候補） |
| **redstone_block** | back / side のどちらからも 15。隣の wire にも 15 | facts-dc-v2 | ○ | ○ | nP1 の back |
| **redstone_torch** | 取り付け先が受電していなければ 15、していれば 0。上の block を強給電。comparator の back からは weak 15 として読める、side からは 0 | facts-dc-v2 → `RedstoneTorchBlock.getStrongRedstonePower` 103-108、`RedstoneView.getEmittedRedstonePower` 66-73 | ○ | ○ | nP（P の反転） |
| **container（barrel）** | level = floor(f×14) + [f>0]、f = Σ(count/maxCount)/slots。barrel 27 slot、stack 64: 247 個 → 3、988 個 → 9、494 個 → 5、満杯 1728 → 15。bow（stack 1）: 5 本 → 3、16 本 → 9。comparator の back からだけ読める（side は 0）。block entity | facts-dc-v2 → `ScreenHandler.calculateComparatorOutput` 1023-1033、`MathHelper.lerpPositive` 665-668 | ○（個数で宣言） | ○（bow の本数で実測: 15 本 = 8、16 本 = 9） | 定数 K3 / K9 / K5 |
| **composter** | `getComparatorOutput` = blockstate の level（0..8）。block entity ではない（program に載る）。full cube ではない（上に置けない、導体でない） | 追加確認 → `ComposterBlock` 50-57、307-313；`ComparatorBlock` 103-109 | ×（Bench では barrel 247 に置換して検算） | ○（RIG-1 の定数 4 個、SUB 1−0−0 一致） | 給電器の level 3 |
| **lever** | ON → 取り付け block を強給電 15（隣の wire が 15 を読む）。comparator の side からは直接読めない（wire を挟む） | facts-geometry「試験の器」、WORLD-1 record §1 | ○（状態で宣言） | ○（給電器） | 給電器の側線 |
| **redstone_lamp** | 隣接から受電で点灯。full cube の導体（強給電 solid として振る舞う） | RIG-1 | ○（solid として宣言） | ○（r / f の表示） | 出力の表示 |

## 事実表に書いてあるが、まだ使っていない / Bench 未検証の性質
- wire の 2 方向分岐で値を保つ条件（強給電 solid の隣に置く、wire→wire を作らない）は使用済み。dust の max 合流（複数の gate から 1 つの wire）は r で使用済み（solid 経由）。
- container の「solid 越し」読み（back が solid で i<15 の時、その先の container を読む）は事実表にあるが配置では未使用。
- item frame の comparator 読みは事実表に記載のみ。

## 対象外（時間の層、別の事実表が要る）
observer、piston、hopper の搬送、note block、target、rail、sculk sensor、pressure plate、button（machine.py には hopper / lever / lamp / trapdoor / rail の部分実装があるが、DC の事実表としては書いていない）。comparator の tick 予約（priming）も対象外。
