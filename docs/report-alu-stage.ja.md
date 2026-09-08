# ALU 1 段 — ゼロベースからオペレータの world まで（レポート、2026-09-08）

> English: [report-alu-stage.md](report-alu-stage.md)

DIRECTOR 8（Fable 5.1 `0c3d10be`）。前半（DERIVE-2 → PLACE-1 → WORLD-1 → オペレータの world の full adder、REUSE-1、ALU-1、PLACE-ALU-1/2、T6 30/32）は DIRECTOR 7（`f9d66fa1`）の仕事で、本書はそれを引き継いで 32/32 → 合成世界 → オペレータの world → 給電器までを閉じた記録。非正典（`notes/**`）。時刻は UTC。

---

## 0. 一言で

**1 bit の ALU 1 段（ADD / SUB / AND / OR）を、Minecraft 1.20.6 の source から書いた規則表と代数だけから機械が導き、Bench（規則の写し）→ 合成 vanilla world → オペレータの world の 3 段で検算し、lever 5 本で 32 行全部を手で確かめられる状態にした。** 既存の redstone 回路も、オペレータの経験も、設計の前提には入れていない（§1 に何を渡し、何を渡さなかったかを書く）。

---

## 1. ゼロベースとは何か（渡した物 / 渡さなかった物）

| エージェント | 種類 | 渡した物 | 渡さなかった物 | 記録 |
|---|---|---|---|---|
| DERIVE-2（full adder の代数） | **blind** な Fable エージェント（文脈ゼロ） | DC の事実表 `docs/rules/facts-dc.md`（1.20.6-yarn source から DIRECTOR 7 が書いた comparator / container / wire / solid の規則。**回路の形は含まない**）+ 問い | オペレータの既存参照回路（本 export に含まない）、web、the development repository の他の file | `docs/algebra/derive2.md`、`derive2-blind-result.md`、`net_derive2.json`、`dc_eval.py`（当エージェント系の独立評価器）8/8 |
| PLACE-1（full adder の配置） | blind な Fable エージェント | 配置の事実表 `docs/rules/facts-geometry.md` + DERIVE-2 の網 | 同上 | `docs/placement/place1.md` Bench 8/8 |
| REUSE-1（全減算器） | blind な Fable エージェント | DERIVE-2 と **byte 一致**の規則表（sha256 e6001fed…）、問いだけ差し替え | 同上 | `docs/algebra/reuse1.md` 8/8 |
| ALU-1（ALU の代数） | Fable エージェント、**blind ではない** | 規則表 + この開発で導いた {0,3} 加算網（`given-adder03.json`）+ 減算網 + Astra の mux 案 | 既存回路、source（エージェントは未開封） | `docs/algebra/alu1.md`、`net_alu1.json`、`dc_eval_alu.py` 32/32 |
| PLACE-ALU-3（ALU の配置、本書） | Fable エージェント、blind ではない | 規則表 v2 `docs/rules/facts-dc-v2.md`、配置の事実表、VERT-1 の規則 `docs/rules/facts-vertical.md`、T6（30/32）、当エージェントの解析（§3） | オペレータの既存参照回路、web | `docs/placement/placealu3-result.md` 32/32 |
| RIG-1（給電器） | Fable エージェント | 上記 + WORLD-1/2 の給電器の形 | 同上 | `docs/placement/rig1.md` 32/32 |

ゼロベースの実体は **規則表が source 由来で回路の形を含まないこと**、**代数の最初の段が blind で出たこと**、**以後の段はこの開発で検証した物だけを再利用したこと**の 3 つ。B-??（オペレータの既存回路）は Bench の較正点であって、エージェントには渡していない（線 §8.4、`notes/2026-09-07-rebuild-line.md`）。

方針の出所: オペレータと Astra（第二 model の査読者、GPT-6）（2026-09-07 19:01Z）が定めた方針 — 既存回路の解法やオペレータの経験を設計の前提にしない、規則と実験で詰める、検証済み構成の再利用は可、未知の接続はオペレータに尋ねず小さく検証する（`docs/alu-place-handover.md` 冒頭）。

---

## 2. 代数（ALU-1、`docs/algebra/alu1-result.md`）

- データ a / b / k / r / f ∈ {0, 3}（bit = level ≥ 3）。制御 2 線: **P ∈ {0, 15}**（0 = 算術、15 = 論理）、**W ∈ {0, 3}**（ADD/AND = 0、SUB/OR = 3）。物理では W の代わりに **Wn ∈ {0,15}**（15 = ADD/AND）を配り、局所で W3 = sub(K3, [Wn]) に変換する（PLACE-ALU-1 の source 検証: torch は side から 0、side は container を読めない）。
- 恒等式 3 つ: (i) r_SUB = r_ADD = parity(a, b, k)、(ii) f = maj(a ⊕ W, b, k)（carry と borrow を 1 本に）、(iii) AND = carry(a, b, 0)、OR = carry(a, b, 1)（論理演算 = carry 比較器そのもの）。
- 網（comparator 16 + torch 1 + 定数 K3 / K9）:

| node | 式 | 意味 |
|---|---|---|
| kg | sub(k, [P]) | k、論理では 0 |
| Qg | sub(W, [nP]) | W、算術では 0（論理で k の代わりに W を入れる） |
| c1 / c2 / c3 | sub(K9,[b]) / sub(c1,[kg,Qg]) / sub(c2,[a]) | 9 − 3·(a + b + k') |
| c4 | cmp(K3, [c3]) | carry（= 論理結果） |
| c5 / c6 / c7 | sub(K9,[c3]) / sub(c5,[c4]) / sub(c6,[c4,P]) | r_arith = 3·[c3 ∈ {0,6}] |
| c4g / r | sub(c4,[nP]) / max(c7, c4g) | 論理 r / 合流 |
| x1 / x2 / c3p / F | sub(a,[W]) / sub(W,[a]) / sub(c2,[x1,x2]) / cmp(K3,[c3p,P]) | a ⊕ W を経た carry/borrow |

32 行の node 値: `artifacts/rows/node_values.txt`。当エージェントの独立評価器 `dc_eval_alu.py` で 32/32。

---

## 3. 配置（v7、`artifacts/layouts/alu_stage_v7.json`）

- **176 block**: comparator 23 / repeater 14 / wire 35 / barrel 6（K3 ×4 = 247 個 = level 3、K9 ×2 = 988 個 = level 9）/ redstone_block 1 / torch 1 / smooth_stone 96（支持床 y=0 を含む）。箱 x 0..10、y 0..2、z 0..11。層別図 `alu_stage_v7_layers.png`（rig 込みは `artifacts/images/alu_v7_rig1_layers.png`）。
- pin（wire cell）: a = (4,1,4) (8,1,5) (10,1,4)、b = (0,1,4)、k = (0,1,2)、P = (0,1,0) (0,1,8)、Wn = (4,1,10)。読み: r = wire (6,2,9)、f = comparator F (8,1,2) の出力（front (9,1,2)）。
- 構造: y=1 が主層（k → f の壁 z=2..3、西の Qg1 塊、XOR の脚 x=6..10）、y=2 が r の cluster（c4〜c7、c4g、nP torch）と P の注入橋。縦の受け渡しは comparator → 強給電 solid → 真上の wire（VERT-1、Bench で無損失を確認、実機で成立）。
- **T6（30/32）から v7（32/32）への設計変更**（PLACE-ALU-3、`placealu3-result.md`）: 落ちる 2 行 = SUB で a=1 の時 f=3（x2 の side に a が無い）。a を入れられる cell (5,1,6) は r cluster の c6 の支持で、handover §3 の案（c6 を (4,2,7) へ）は支持 (4,1,7) が Wn の給電 repeater なので不成立（当エージェントの解析、`notes/2026-09-08-director-8-registrations.md`）。解いたのは代数の側:
  1. **S_x = max(a, W3)、xm = sub(S_x, [as])、as = sub(a, [Wn])**（x1 / x2 を copy 化、copy gate と W3b と K3 1 個を撤去、as 1 個を追加）。
  2. **P の kill を c7 の side から c5 / c6 の共有 side (5,2,5) へ**（15 > 9）。x=9 の P 線・橋・蓋 3 個が消え、配置不能だった (8,2,7)（comparator の上の wire）も消えた。
  3. dummy comparator (9,1,3): w3p (8,1,3) の wire 形状を N+E にして南の relay に漏らさない（Bench の形状規則、実機で成立）。
- lint（`alu_check2.py`）: L1 支持（vanilla の設置条件）、L2 斜め読み（VERT-1）、L3 強給電 relay に触れる wire（情報）。v7 = L1/L2 0。

---

## 4. 検算の 3 段

| 段 | 器 | 結果 | 一次記録 |
|---|---|---|---|
| Bench | `tools/llmgen/capcell.py` の `Bench`（規則の写し、B-?? で較正）、pin 固定 | **32/32**、r/f は正確に {0,3} | `artifacts/rows/alu_stage_v7.json.rows.json` |
| 合成世界（WORLD-2） | headless vanilla 1.20.6、void world、lever 給電（compare gate + barrel 247 + side wire、lever ON = bit 0）、worldprobe で freeze/step、warm-up 32 + 本番 32 regime | **r/f 32/32、全 read 1024/1024**（comparator 23 + 給電器の powered 込み）、settle 2..14 gt、rcon 103,169 | `artifacts/world/world2.run.result.json`（計測値は無改変、実行 metadata は redact 済み — `PUBLICATION_CHECKLIST.md` §3）、`record.md`（予測を先に書いた 2 段構成） |
| オペレータの world（LIVE-ALU） | `/aiwb place alu_stage_v7_nobarrel 6005 133 -4113` + barrel 6 個（bow 5 / 16 本）、region file の読み（regioncap） | 配置 176/176、静止 comparator **23/23**、ADD 0+0+1 → r 3 / f 0、SUB 0−0−1 → r 3 / f 3、**24/24** | `docs/world/live-alu-record.md`、capture 3 本 |
| 給電器（RIG-1） | lever 5 本、composter[level=3] ×4（block entity なし）、lamp 2、93 block、`/aiwb place alu_stage_v7_rig1 6001 131 -4114` | Bench 32/32（lever 状態だけから）、world で SUB 1−0−0 → r 3 点灯 / f 0 消灯、comparator 23/23 | `docs/placement/rig1.md`、`rig1-result.md`、capture |

Bench が隠して world で見えた 3 点（全部 world で確認済み）: dummy comparator の wire 形状、pin の隣の強給電 relay（as ≤ a、as ≤ 3 で値は不変）、置いた直後の block update 不在（warm-up が要る = WORLD-1/2 の機構と同じ）。

---

## 5. 操作の手引き（オペレータの world）

origin (6005,133,−4113)、y=133 床 / 134 主層 / 135 cluster。

| lever（y=135） | 座標 | ON | OFF |
|---|---|---|---|
| a | 6017 135 -4108 | a = 0 | a = 1 |
| b | 6003 135 -4108 | b = 0 | b = 1 |
| k | 6003 135 -4112 | k = 0 | k = 1 |
| P | 6001 135 -4109 | 論理（AND/OR） | 算術（ADD/SUB） |
| Wn | 6009 135 -4102 | ADD / AND | SUB / OR |

lamp: r = 6011 135 -4103、f = 6014 134 -4111（点灯 = 1）。mark 10 個（IN a×3 / b / k / P×2 / Wn、OUT r / f）は積み上がる（`flows.py` の `_mark_put` を union に、2026-09-08 の裁定 A）。期待表 32 行は `docs/placement/rig1-result.md` §4。

例: 全 OFF = SUB 1−1−1 → r 点灯・f 点灯。Wn ON = ADD 1+1+1 = 3 → 同じ。さらに k ON（k=0）= 1+1 = 2 → r 消灯・f 点灯。

---

## 6. 費用（実測、harness の token）

| 段 | エージェント | 時間 | token |
|---|---|---|---|
| PLACE-ALU-3 | Fable | 12 分 | 145k |
| WORLD-2 | Opus | 21 分 | 187k |
| mark 調査 | Sonnet | 3.4 分 | 108k |
| mark 修正 | Opus | 35 分 | 111k |
| RIG-1（空振り + 本番） | Fable | 9 + 15.5 分 | 75k + 192k |
| 合計 | | ≈ 1.6 h のエージェント時間 | ≈ 820k |

オペレータの act: 配置 3 回、barrel の手詰め 6 個、restart 2 回、lever。当エージェントの失点: in-game に無い旗 `--no-backup-gate` の案内、256 字を超える `/data merge` 行、表の座標に U+2212 を使い `Expected integer` を招いた（記憶に登録）、発注書の書き込みが権限で落ちて Fable エージェント 1 本が空振り。

---

## 7. 主張の範囲と、しないこと

- **主張**: 1 bit ALU 1 段（`v7`。1 段であって tiling できる slice ではない。slice `v8`・`v9` は後の結果で README と `docs/placement/slice1-result.md` に記録）が、規則表と代数から機械が導いた配置（Bench 32/32）→ 合成世界 32/32 → オペレータの world（静止 23/23 + 動作 3 状態）で一致し、lever で操作できる。full adder（8/8 三系）に続く 2 個目。
- **しない**: 8 段、tiling（a3 pin が x=10 に出ているので pitch ≥ 11 か折り返し）、速度、既存参照回路との密度比較（費用は絶対値で報告する方針）、および仕様変更に対する無改修性（R0 の 3 条件）。
- 32 行全部をオペレータの world で回した記録はまだ無い（給電は lever なので、オペレータが回すか、rig を写しの world に置いて worldprobe で自動掃引する = ブラッシュアップ D）。

---

## 8. ブラッシュアップ候補

- **A** a の pin 3 cell → 1 cell（配置の再検討、tiling の前提）
- **B** barrel を composter に（K3 4 個は可。K9 2 個は composter の上限 8 なので、定数 8 で組み直す代数の変更が要る）
- **C** 入力側にも lamp（lever の向きでなく level で見える）
- **D** rig 込みで 32 行を自動掃引（写しの world + worldprobe）
- **E** 2 段目の接合（f(i) → k(i+1)、P / Wn の通し）— オペレータの go 待ち

---

## 9. 参照

- 線（方針と履歴）: `notes/2026-09-07-rebuild-line.md`（§8.2 OC-D110 = 基礎は信号強度演算、§8.4 B-?? の位置、§8.5 1 周目）
- 引き継ぎ: `docs/alu-place-handover.md`（§2 落ちる 2 行、§4 干渉の規則）
- 規則表: `docs/rules/facts-dc.md`、`docs/rules/facts-dc-v2.md`、`docs/rules/facts-geometry.md`、`docs/rules/facts-vertical.md`
- 代数: `docs/algebra/derive2.md`、`docs/algebra/reuse1.md`、`docs/algebra/alu1.md`
- 配置: `docs/placement/placealu2.md`（T6、partial）、`docs/placement/placealu3-result.md`（v7、checker、program、層別図）
- 世界: `docs/world/world1-record.md`、`docs/world/world2-record.md`、`docs/world/live-alu-record.md`、`docs/placement/rig1.md`
- 登録（時系列）: `notes/2026-09-07-director-7-registrations.md`、`notes/2026-09-08-director-8-registrations.md`
- 器: `tools/llmgen/capcell.py`（Bench）、`tools/world/worldprobe.py`（写しの world の観測）、`tools/world/regioncap.py`（region file の読み）、`tools/workbench/bridge/flows.py`（aiwb の flow、mark の修正 `3ef098ad`）
