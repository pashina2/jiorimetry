# PLACE-1 — 検算記録（DIRECTOR 7、13:54:05Z）

- 席: blind な Fable subagent。与件 = DC の事実表 + 配置の事実表（`facts-geometry-given.md`、当席が source から書いた）+ DERIVE-2 の網、制約 = 分岐は無損失。禁止 = the development repository/** と web。席が開いた file: 与件 4 + source 4 file（AbstractRedstoneGateBlock 70-154、ComparatorBlock 70-124、RedstoneWireBlock 251-276 / 342-363、RedstoneBlock grep）。
- 実測: harness 881 s（14.7 分）、**102k token**（自己申告 35k）。途中保存あり。
- 成果（verbatim）: `place1-blind-result.md`。1 層（y=1）+ 支持（y=0）、箱 7 × 2 × 5。comparator 7 / barrel 1（494 個）/ redstone_block 2 / wire 6 / 中継 solid 4 / 支持 13 = **33 block**（sum の読み出し wire + 支持を足すと 35）。U は中継 solid S_U から 2 本の独立 wire へ無損失、cout は 1 wire cell が c6 / c7 両方の side に接する形（c7 を 90° 回して中継）。wire → wire の −1 hop は 0。
- **当席の Bench 掃引**（`bench_sweep.py` = 当席が capcell.Bench の上に書いた loader、自己試験 2 本済み。`layout_place1.json` = 席の表を当席が JSON にしたもの、sum は読み出し wire (3,1,4)、cout は wire (5,1,3)、入力は wire を 0 / 5 に pin）: **8/8 PASS**、sum / cout の level は正確に {0, 5}（`bench_sweep_output.txt`）。DC の fixpoint は 3〜4 round で収束。
- 未解決（席の列挙）: tiling の pitch（cout の 4 方向目が取れない、y を 1 段ずらす案は未検証）、harness の pin 方式（当席は状態書き）、barrel の slot 配分（合計で決まるので無関係）。
- 世界では未検証（Bench のみ）。次の候補 = WORLD-1（合成世界、headless、worldprobe で 8 vector）→ その後 tiling の loop。
- **the second-model reviewer の再検算（14:04:37Z、オペレータ経由、同じ Bench）**: 保存された 35 block 配置 = 全 8 入力で正確な {0,5}、合格。入力 wire の pin を外し、入力用 comparator と定数源を足した模型 44 block も 8/8 合格（メモリ上、実機ではない）。残る大きな問題 = 実機動作と段間接続（cout の次段への受け渡しが未解決、速度も未評価）。the second-model reviewer の判断: 次は 1 段の実機確認に進む価値がある。
