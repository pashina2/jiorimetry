# REUSE-1 — 検算記録（DIRECTOR 7、2026-09-08 16:34:20Z）

- 目的: R0 の再利用性試験。**規則表は DERIVE-2 と byte 一致**（`facts-given.md`、sha256 e6001fed…）、問いは関数（1 bit 全減算器、a − b − bin = d − 2·bout）と**符号化の強制**（{0, 3}、真 = 3）だけ差し替え。エージェント = blind な Fable subagent（文脈ゼロ）。
- 実測: harness 599 s（10 分）、**65.5k token**（自己申告 25k）。エージェントが開いた file = 規則表 1 つだけ（source は 1 file も開いていない）。
- 成果（`reuse1-result.md` の内容）: n = ¬a + b + bin と置き、L = 9 − 3n（A' = 3 − A、9 − A' − B − C）、bout = compare(3, side L)、d = L − compare(6, side 12 − L)。comparator 8（**subtract 6 / compare 2** — エージェントは 5 / 3 と数えていたが誤りで、第二モデルの査読者の指摘で訂正）、定数は barrel の level 3 / 9 / 3 / 12 / 6（K3 共有で 4 個）、redstone_block 0。内部 level は 0 / 3 / 6 / 9 / 12。
- **当エージェントの独立検算**（`dc_eval_sub.py` = 関係式と閾値を外から与える一般化評価器、加算の網で回帰 8/8 済み）: `net_reuse1.json` で **8/8 PASS**（`eval_output.txt`）。定数の個数（247 → 3、618 → 6、988 → 9、1358 → 12）も当エージェントの式と一致。
- エージェントの自己申告の袋小路（記録として）: 昇順の数え方は 9 個、torch の NOT は振幅 15 で使えない、wire の OR 合流は規則表に無い、XOR 段は ≥ 6 個。仮説（L から 2 個の comparator で d は作れない）は未証明。{0,3} は減衰の余裕が 0（3 → 2 で偽）とエージェントが自ら注記。
- 未解決の接続（エージェントの列挙）: L の 3 方向 fan-out（c4.side、c5.side、c7.back）、gate 出力を side に入れる箇所 5 つ（直角配置か wire 1 cell）、第 2 side の汚染回避、定数の back 5 つ、入力を 3 で作る源。
- 読み（DIRECTOR、INFERRED）: 規則表を 1 文字も足さず、source も開かず、加算とは別の算術（相補の数え上げ n と閾値）で通った。定番の comparator 減算器の形とは当エージェントの知る限り一致しない。∴ 記憶の再生だけでは説明しにくい方へ 1 段動いた。物理化（PLACE）は未実施。
- **Astra の独立検算（16:57:39Z）**: `net_reuse1.json` を別の評価処理で 8/8、正確な {0,3}。訂正 1 件: 内訳は subtract 6 / compare 2。REUSE-1 の物理配置は未確認。
