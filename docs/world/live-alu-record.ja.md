# LIVE-ALU — ALU 1 段 v7 がオペレータの worldで動いた記録（DIRECTOR 8 `0c3d10be`、2026-09-07T21:1x–21:27Z）

> English: [live-alu-record.md](live-alu-record.md)

D4.1 の観測（オペレータの world、regioncap = region file の読み、untouched の capture 3 本を同梱）。promotion-grade ではない（`notes/**`）。

## 配置
- program `alu_stage_v7_nobarrel`（170 block、`artifacts/programs/alu_stage_v7_nobarrel.program.json` を host の programs dir に置いた）を **オペレータが** `/aiwb place alu_stage_v7_nobarrel 6005 133 -4113` で配置（worldsnap snapshot 20:56Z の後。最初は backup_stale で拒否された）。
- barrel 6 個は block entity のためオペレータが手で置き、bow を入れた（level 3 = 5 本 ×4、level 9 = 16 本 ×2）。最初の読み（21:13Z）で level 9 の 2 個が 15 本（level 8）と分かり、1 本ずつ追加で修正。
- 21:17Z の capture: 配置 176/176 一致、barrel 6/6 正、**comparator 23/23 が Bench の静止状態（SUB 0,0,0）と一致**。

## 実演（k = 1 だけ給電、Wn を lever で切替）
給電器: comparator (6004,134,-4111) facing west、back = barrel (6003,134,-4111) bow 5 本 → k pin (6005,134,-4111) = 3。Wn: solid (6009,134,-4102) + lever (6009,135,-4102)。

| 状態 | k | Wn | r (6011,135,-4104) | f (6013,134,-4111) | Bench | comparator |
|---|---|---|---|---|---|---|
| lever ON = ADD 0+0+1 | 3 | 15 | **3** | **0** | r 3 f 0 | 24/24 一致 |
| lever OFF = SUB 0−0−1 | 3 | 0 | **3** | **3**（borrow） | r 3 f 3 | 24/24 一致 |

捕まえた失点: 給電 barrel が空のまま「詰めた」という報告が 2 回続いた（本文で言い換え）（別の barrel に入れていた）。region の barrel 中身は chunk 保存時にしか更新されないが、今回は autosave が十分速かった（各読みで mtime が 1 分以内）。

## 主張の範囲
1 bit ALU slice（ADD/SUB/AND/OR、データ {0,3}）が、規則表と代数から機械が導いた配置（PLACE-ALU-3、Bench 32/32）→ 合成世界 32/32 → オペレータの world で静止 1 状態 + 動作 2 状態が Bench と一致した。32 行全部を world で回してはいない（給電器 8 点を置く act はオペレータの手なので、今日は 3 状態）。8 段・速度・tiling は未着手。
