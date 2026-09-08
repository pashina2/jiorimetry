# ALU-1 — 検算記録（DIRECTOR 7、2026-09-08 17:27:55Z）

- エージェント: Fable subagent、**blind ではない**（与件 = 規則表（不変、`facts-given.md`）+ {0,3} 加算網（`given-adder03.json`）+ 減算網 + 第二モデルの査読者が示した 5 subtract の mux 案）。縛りなし: 規則表の DC 部品（comparator / torch / repeater / dust の max / 定数）を何でも、費用は block 見積で。符号化はエージェントが選ぶ。オペレータは部品の制約を外して進めるよう裁定した。
- 実測: harness 1,359 s（22.7 分）、**69.5k token**（自己申告 45k）。エージェントが開いた file = 与件 4 つだけ（source も the development repository も未開封）。
- 成果（verbatim `alu1-result.md`）: データ {0,3}、制御 2 線 P ∈ {0,15}（算術 / 論理）と W ∈ {0,3}（ADD/AND = 0、SUB/OR = 3）。恒等式 3 つ: (i) r_SUB = r_ADD = parity(a,b,k)、(ii) f = maj(a ⊕ W, b, k)（carry と borrow を 1 本に）、(iii) AND = carry(a,b,0)、OR = carry(a,b,1)（論理は carry 比較器そのもの）。**comparator 14 + barrel 2（level 9 / 3、各 2 面から読む）+ torch 1、block 見積 ≈ 32**（支持除く）。算術 9 比較器 ≈ 16 block、制御 5 比較器 + torch ≈ 12 block。
- 新規に導いたもの（エージェントの開示）: level XOR（相互 subtract 2 つを 1 つの comparator の 2 side で max 合流）、kp の mux を c2 の 2 side で、論理演算 = carry 比較器、出力脚の gating（P を c7 / F の空き side に載せて殺す）、torch の Pbar。減算網と 5 node の mux は使わなかった。
- **当エージェントの独立検算**（`dc_eval_alu.py` = 混合部品の評価器、加算網で回帰 8/8 済み）: `net_alu1.json` で **32/32 PASS、r と f は全行で正確に {0,3}**（`eval_output.txt`）。
- 未解決（エージェントの列挙）: 余裕 0 の fan-out cell（a、W、c4 がそれぞれ 4 隣接）、2 side の comparator 4 つ（c2 / c7 / c3p / F）、P と Pbar の減衰の許容（P は 9 まで、Pbar は 3 まで）、W を lever から作る変換（+2 block）、r の dust cell を直読み。
- Astra の (c) に従い、配置は入出力の接合箇所（k 入力、f 出力、制御線の通し）から始め、2 段で桁と制御切替を確かめる。
