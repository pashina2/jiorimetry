# DERIVE-2 — 検算記録（DIRECTOR 7、13:30:13Z）

- エージェント: blind な Fable subagent（fable-architect）。与件 = `facts-given.md`（DC の事実表、回路の形なし）+ 問い（符号化 1 案、compare / subtract と定数だけの網、8 入力の検算、配置・tiling・最小性は不要）。禁止 = the development repository/** と web。エージェントが開いた file: facts.md、AbstractRedstoneGateBlock.java 128-149、RedstoneView.java 40-65（自己申告）。
- 実測: harness 559 s、**64.6k token**（エージェントの自己申告 25k）。途中保存あり（draft.md、上限内に完了）。
- エージェントの成果（verbatim）: `derive2-blind-result.md`。符号化 {0, 5}（bit = level ≥ 5）、comparator 7（subtract 6 / compare 1）、container 1（level 5 = 494 個）、redstone_block 2（共有なら 1）。網: U = 15 − a − b − cin（subtract 3 段）、cout = compare(K5, side U) = 5 iff U ≤ 5、T = 15 − U、sum = T − cout − cout。
- **当エージェントの独立検算**: `dc_eval.py`（エージェントとは別に当エージェントが事実表の出力規則から書いた評価器、自己試験で誤網が FAIL になることを確認済み）に `net_derive2.json` を通して **8/8 PASS**（a + b + cin = sum + 2·cout を復号後に判定）。container の level 5 = 494 個、493 個で 4 も当エージェントの式で一致。
- 未解決の接続（エージェントの列挙、当エージェントの読み添え）: (1) U の 2 側への fan-out（c4.side と c5.side）— wire 1 cell で無損失、2 cell なら U−1 になり sum が {1, 6} にずれる、(2) cout の 3 方向 fan-out（c6.side、c7.side、次段の cin）、(3) redstone_block の共有、(4) 入力 a / b / cin を level 5 で作る源（lever は 15）、(5) comparator 直列は同一直線・同一向き、(6) wire の max 合流は未使用。
- Astra の 4 分岐 → **分岐 1（一致、node と接続条件が具体的）**。次 = 未解決の接続を含む小範囲の物理化（配線・定数・支持を数える）→ Bench の DC 掃引。

- **第二モデルの査読者による独立検算（13:36:20Z、オペレータ経由）**: JSON の網を別の評価処理で 8 入力とも {0, 5} の full adder として確認（復号後だけでなく次段へ渡す level も揃う）。**指摘 1 件**: エージェントが出した補正案（減衰で 1 ずれたら定数 1 を引く）は成立しない — 入力 111 では U = 0 が減衰しても 0 のままなので、正しい sum = 5 からさらに 1 引くと 4 で誤答。元の 7 comparator 網は正しく、減衰の補正案だけが誤り。∴ PLACE-1 の与件: **U と cout の分岐は値を保って届ける**（wire 1 cell、または強給電された solid の隣の wire = 無損失。減衰の補正で逃げない）。ここで費用が膨らめば網へ戻る。

---

