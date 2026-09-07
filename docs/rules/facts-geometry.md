# 配置の事実表（DC、1.20.6-yarn、DIRECTOR 7 が source から書いた。回路の形は含まない）

## redstone_wire（`net/minecraft/block/RedstoneWireBlock.java`）
- 置ける場所: 下の block が `canRunOnTop`（:224-233、上面が full square の solid など）。空中には置けない。
- 受ける level（`getReceivedRedstonePower` :251-275）: i = 周囲 6 面の block からの emitted power の max（`world.getReceivedRedstonePower`、wire 以外: gate / torch の出力、redstone_block 15、**強給電された solid はその受電 level を出す**）。j = 水平 4 方向の隣の wire の power の max、ただし **隣が solid で、その上が solid でなければ、隣の上の wire も見る（登り）**；隣が solid でなければ **隣の下の wire も見る（降り）**。結果 = max(i, j − 1)。∴ wire → wire は −1、gate 出力 / 強給電 solid → wire は無損失。
- 上に solid があると登りの接続は切れる（:201、`getRenderConnectionType` の bl）。
- wire は自分が向く（接続する）solid を弱給電する。弱給電された solid は wire を給電しないが、gate の back からは読める（強給電のみ、弱は 0 と読む点に注意: gate の back は `getEmittedRedstonePower` の 2 引数版で solid の **強** 受電を読む）。

## gate の出力（`AbstractRedstoneGateBlock.java`）
- `getWeakRedstonePower` :81-88 / `getStrongRedstonePower` :76-78: powered で、問われた方向が出力方向なら level（comparator は stored output、repeater は 15）。出力は front の block へ: front が solid なら **強給電**（level = 出力）、wire なら wire の power になる（無損失）。
- back の読み（facts-dc）: front の solid の強受電、wire の power、container、gate 出力。**side は wire / gate / redstone_block だけ**（solid の受電は読めない）。
- gate は下に solid が要る（設置条件）。

## solid（導体）の中継
- comparator の front → solid S（強給電 U）→ S の隣の wire（U、無損失）→ 別の comparator の side（U）。または S を back で直に読む comparator（U）。1 つの S から複数の wire / comparator の back へ配れる（強給電は面ごとではなく block 全体）。
- 強給電された solid が別の solid を給電することはない（強は 1 段で止まる）。

## 縦
- wire の登り / 降り（上の規則）: −1 ずつ。
- 強給電された solid の上 / 下に wire を置けば無損失で縦に渡る（solid の上面の wire は canRunOnTop で置ける；下は solid の下に wire を置く床が要る）。
- comparator / repeater は水平のみ（facing は 4 方向）。torch は上の block を強給電する（反転が要らなければ使わない）。

## 試験の器（Bench）に載せる条件
- 入力 a / b / cin は **wire の cell** として置き、試験では level を 0 か 5 に固定する（pinned）。出力 sum / cout は wire の cell か comparator の front の solid（試験で level を読む）。
- container は barrel、中身は個数で宣言（level 5 = 494 個、stack 64）。
- 支持の solid（床）は数に含める（別欄）。
