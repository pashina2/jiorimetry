# DC 信号強度演算の事実表（DERIVE-2 の与件、2026-09-07T13:18Z、DIRECTOR 7 が 1.20.6-yarn から読んで書いた。回路の形は含まない）

単位: level 0..15（整数）。DC = 静止状態のみ。遅延・tick・priming は扱わない。

## comparator（`net/minecraft/block/ComparatorBlock.java`、`AbstractRedstoneGateBlock.java`）
- 向き: `FACING` = gate から**入力側**へ向く方向。back = pos + FACING、front（出力）= pos − FACING、side = pos ± FACING を水平に 90° 回した 2 方向。
- back の値 i（`AbstractRedstoneGateBlock.getPower` :130-139 + `ComparatorBlock.getPower` :102-120）: back の block が
  - redstone_block → 15、redstone_wire → その power、gate / torch など emitsRedstonePower な block → その strong power（`RedstoneView.getEmittedRedstonePower` :45-62）、
  - solid（導体）→ その block が受けている strong power（2 引数版 getEmittedRedstonePower: solid なら max(i, receivedStrong)）、
  - container（`hasComparatorOutput`）→ その comparator 出力（下の式）。back が solid で i < 15 なら、**その 1 つ先**の block が container ならその値、item frame も同様。
- side の値 j（`getMaxInputLevelSides` :141-147）: 2 側の max。読める源 = redstone_block 15、wire の power、gate / torch の strong power。**solid の受電は side からは読めない**（3 引数版に solid の節が無い）。
- 出力（`calculateOutputSignal` :74-87）: i == 0 → 0。j > i → 0。subtract → i − j。compare → i。
- 出力は front の block へ: front が solid なら strong power（level = 出力）、wire なら power。front の先の comparator はそれを back で読める。

## container の level（`ScreenHandler.calculateComparatorOutput` :1023-1033、`MathHelper.lerpPositive` :665-668）
- f = ( Σ_slot count / maxCount(item) ) / slots。level = floor(f × 14) + (f > 0 ? 1 : 0)。空 → 0、満杯 → 15。
- barrel は 27 slot。stack 上限 64 の item なら、level k（1 ≤ k ≤ 14）に要る item 数 n は f = n / (64·27) が (k−1)/14 ≤ f < k/14 を満たす n。例: n = 1 → 1、n = 124 → 2、n = 247 → 3、… 15 は満杯 1728。
- comparator の back に置けば定数源。値は容易に変えられる（可変値の源にもなる）。

## その他の部品（DC）
- redstone_block: 15 の定数（back でも side でも 15）。
- repeater（`RepeaterBlock`）: back > 0 なら出力 15、else 0（正規化）。side は gate のみ（lock）。
- torch: 取り付け先の block が受電していなければ 15、していれば 0（反転）。上の block を strong power する。
- redstone_wire: 隣の wire から −1 で伝播、gate / torch / redstone_block / strong-powered solid から直接 level を受ける。back / side のどちらからも読める。減衰は距離で引き算になるが、**subtract の side に定数を当てれば 1 block で引ける**ので、距離を使わなくてよい。
- 導体（solid）: `AbstractBlock.Settings.solidBlockPredicate` = full cube（既定、:1179）かつ `solidBlock(Blocks::never)` で外されていない（glass 全種、observer、redstone_block、leaves、ice、glowstone、sea_lantern、beacon、moving piston、tnt、scaffolding、powder_snow、copper_grate、copper_bulb、dripstone、chorus_flower、bamboo は非導体）。wool、smooth_stone は導体。

## 使ってよい部品
comparator（compare / subtract）、container（barrel）、redstone_block、redstone_wire、solid（導体）、repeater、torch。lever は入力。lamp は出力の観測に使ってよい。
