# PLACER-0 — 小さな配置探索器の実証（DIRECTOR 8、2026-09-08）

- 問い: LLM が毎回座標を考え直している部分を、規則からの探索プログラムに置き換えられるか（Astra の修正を入れた受理条件: 端子と禁止 cell を変えた 5 つ以上の小問題を、人の候補座標なしで解く。成功率・時間・block 数を測る）。
- 問題 6 つ（`problems.json`、当席が v7 / RIG-1 / v8 の断片の**機能**から切り出し、答えの配置は席に渡していない）、判定器 `placer0_check.py`（Bench を oracle に、pin の全組合せで出力 wire の level を照合 + lint）。空解は 6 問とも FAIL、当席の手解が p2 で PASS = 器の較正。
- 探索器 `placer0.py`（Opus 席、751 行、座標リテラル 0）: 「(部分配置, 未解決の要求)」上の IDA*、展開は DC 規則の逆向き書き換え、heuristic = pin から (cell, level) への緩和 Dijkstra（最低 block 数）。
- 結果（当席が judge で再実行）: p1 8 block / 9.9 s、p2 5 / 0.1 s、p4 17 / 0.9 s、p5 9 / 5.8 s、p6 6 / 0.5 s = **5/5 PASS**。p3 は **当席の出題ミスで充足不能**（side の 2 cell の真下が両方 forbidden で発信体が置けない）— 席が不能の証明を書いた。
- 席が自力で見つけた形: 固定の壁 solid を repeater の front にして越える（p2）、壁の上面を強給電して屋根 y=3 を渡る（p4）、2 つの copy gate の front を同じ solid に向けて max（p5、v7 の S_x と同型を再発見）、二重反転で y=2 に wire を置かず斜め読みを回避（p6）。
- 開示: 判定器の穴 1 つ（solution の barrels が problem の barrels を上書きできる）は次版で塞ぐ。手で入れた規則 = gate 幾何、comparator/repeater の算術と逆、side/back の可読性、wire の max、強給電 6 面、支持、barrel の式、L2 の修復書き換え。人が要った所 = 要求分解の枠組み、heuristic の定数 2 つ、解法 lib 無し（ortools / z3 が無い）。
- 費用: Opus 50 分（計算 25 分）、実測 232k token。
