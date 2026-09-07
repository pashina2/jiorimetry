# PLACE-ALU-2 — 記録（DIRECTOR 7、2026-09-08 18:51:33Z）

- 席: Fable、40 分上限、the second-model reviewer の条件（中継近傍を先に、幅制約なし、copy 自由、網の共有を解いてよい、未完なら衝突と試した修正を残す）。**harness の turn 上限（12）で 28 分時点に停止**（続行の手段が無い）。実測 179k token（自己申告 70k）。
- **鍵の発見（席の §0）**: k → f のデータ経路は 1 層では段の全幅を横切る壁（k, kg, c2, S2, c2c, S2b, c3p, S3p, F）になり、P（北の行）は南半分（c4..c7、c4g、r、x1/x2、Wn）へ 1 層では届かない。これが前 2 回の崩壊の共通原因。**決めた修正 = y=2 の P 橋**（強給電した solid の上の repeater 連鎖で壁を越え、solid の下の wire へ無損失で降ろす。gate は水平しか読まないので solid の上の repeater は漏れない）。さらに (A) P の注入は spur wire でなく **consumer の side へ向いた repeater**（15 か 0）で、(B) Qg を 2 段に分割（Qg1 = sub(K3, [nP1 gate, WnRep repeater])、Qg2 = sub(back = S_L) が c2 へ向く）。
- **収束した部分**: 北半分（k → f の経路、c1 / c2 / c3、Qg2、P 注入）、PX = 9。block 一覧は §2、per-comparator は §3。
- **未完**: 南半分（c4..c7、c4g、r、XOR の x1 / x2、Wn の行）。残った衝突（§7）: 橋の降り口が cc3 の front や S3b の隣と衝突、S3b の空き面が 1 つで w3 が橋の柱と衝突（推奨 = 橋を列 7 へ）、a に空き面が無い（copy comparator ca が要るが出力 cell が衝突）。§9 の addendum（橋を列 7 へ動かした 2 回目、部分、全体未検証）。
- 原文: `placealu2-partial.md`（17 KB、§0〜§9）。与件の規則表 v2: `facts-dc-v2-given.md`。
