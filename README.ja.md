# 日本語

> English: [README.md](README.md)

## これは何か

Minecraft 1.20.6 の **redstone 回路を、source から書き起こした規則表と代数だけから導出する**
実験的なツールチェーンです。人が知っている回路を書き写すのではありません。出発点は DC の
信号強度演算（comparator、container、dust の減衰、強給電された solid）です。

検算は 3 段です。**Bench**（規則の写し、費用ゼロ）→ **合成 vanilla world**（headless server、
RCON で freeze/step、全 cell を読み戻す）→ **オペレータの world**（実際に遊んでいる save）。

## 現在の成果

| 成果物 | Bench | 合成世界 | オペレータの world |
|---|---|---|---|
| 1 bit 全加算器 | 8/8 | 8/8、全 read 一致 | 配置して読み戻し 8/8 |
| 1 bit ALU slice（ADD / SUB / AND / OR） | 32/32 | 32/32、read 1024/1024 | 176/176 配置、静止 comparator 23/23、lever 5 本 + lamp 2 個の給電器で操作可 |

ALU は 176 block（comparator 23、repeater 14、dust 35、container 6、redstone_block 1、
torch 1、smooth_stone 96）。箱は 11 × 3 × 12。データ線は {0, 3}、制御線は `P`（0 = 算術 /
15 = 論理）と `Wn`（15 = ADD/AND / 0 = SUB/OR）。

鍵になった恒等式は 3 つです。`r_SUB = r_ADD = parity(a, b, k)`、`f = maj(a ⊕ W, b, k)`
（carry と borrow を 1 本の線に載せる）、`AND = carry(a, b, 0)` と `OR = carry(a, b, 1)`
（論理演算が carry 比較器そのものになる）。

### 追記（2026-09-08、同日後半）: 突き合わせられる bit slice

上の 1 段 v7 は動く 1 段だが bit slice ではなかった: 入力 a に 3 cell（うち 1 つは pitch の外）が要り、P の第 2 入口と Wn の行が through-line になっておらず、東端が閉じていなかった。オペレータは「bit slice の突き合わせと pitch 整合を満たすまで 2 段目に進まない」と裁定した。そこで slice 契約（`docs/placement/slice-contract.md`）と、layout を pitch で n 個並べて n bit ALU として全入力・全 mode を解く checker（`tools/checks/alu_check_slices.py`）を書いた。結果 `artifacts/layouts/alu_slice_v8.json`（pitch 12、箱 12×4×14、292 block: comparator 50 / repeater 15 / wire 55 / barrel 7）: n=1 32/32、n=2 128/128、n=3 512/512、並べた配置の設置 lint 0。境界 cell の一覧は `docs/placement/slice1-result.md`、2 slice の層別図は `artifacts/images/alu_slice_v8_x2_layers.png`。未実施: 2 slice の合成世界とオペレータの world での検証。


## 主張しないこと

- **まだ bit slice ではありません。** オペレータは、ビットスライス化・隣接段との突き合わせ・
  ピッチ整合が未達であり、2 段目に進む前にこれを満たす必要があると裁定しました。`v7` は
  1 段としては動きますが slice ではありません。slice 契約は
  [`docs/placement/slice-contract.md`](docs/placement/slice-contract.md) にあり、`v7` を
  その契約で読むと **20/32** です（再現手順は §5）。
- 8 bit の加算器も ALU もありません。
- 速度・遅延の主張はありません。すべて DC（定常状態）です。settle 時間は観測値として
  報告しているだけで、モデルではありません。
- 既存の手組み回路との密度比較・速度比較はしません。費用は絶対値でのみ報告します。
- 「モデルが redstone を知らない」とは主張しません。主張はもっと狭く、検証可能なものです
  — 規則表は source 由来で回路の形を含まない、代数の最初の段は文脈ゼロの席から出た、
  以後の段はこの開発で検証した物だけを再利用した、の 3 点です。

## 再現

Python 3.11 以上、標準ライブラリのみ。Bench の経路に追加パッケージは要りません。
印字は §5（英語側）にそのまま貼ってあります。

```
python tools/checks/alu_check2.py       artifacts/layouts/alu_stage_v7.json     # PASS 32/32
python tools/checks/bench_sweep.py      artifacts/layouts/layout_place1.json    # ALL PASS
python tools/checks/alu_check_slices.py artifacts/layouts/v7_as_slice.json 1    # n=1 PASS 20/32
```

3 つ目は **失敗するのが正しい** 測定です。

world 段（`tools/world/`）は実サーバを駆動します。1.20.6 の server jar と Java 21 は
利用者が用意してください（[`tools/README.md`](tools/README.md)）。jar・save・mod は
一切同梱していません。

## 失敗の記録

- **netlist 方式で 27,103 block。** 算術を gate の netlist に切ってから placer に渡した結果、
  placer が信号強度を net の上で運べず、comparator 1 個あたり dust 約 158 個を費やしました。
  修正は「切らないこと」— 代数と配置を信号強度のまま一緒に導く。
- **T6 が 30/32 で止まり、座標ではなく代数を変えて解けた。** SUB の 2 行が落ちたのは、`a` を
  入れられる cell が `x2` の side に無かったためです。幾何的な回避は全部、既に使われている
  支持 cell と衝突しました。`S_x = max(a, W3)` 系への書き換えと `P` kill の移動で、配置不能
  だった cell ごと 1 列が消えました。
- **給電器の draft は world ではなく Bench で落ちました。** `draft_1` は 32/32 でしたが斜めの
  dust 接続が 14 本あり L2 制約で棄却、`draft_2` は repeater の背面が air で 20/32。さらに
  給電 cell を 1 つ air のまま残したのは、その真上が強給電された段の relay だからで、これは
  合成世界で学んだ規則を save に触れる前に適用したものです。world build 3 回分を費用ゼロで
  避けました。

## 費用（実測）

最終段（2026-09-08）のみ: 席時間 合計 **約 1.6 時間**、token **約 82 万**。内訳は §7 の表。
人間側の作業は、配置コマンド 3 回、container の手詰め 6 個、client 再起動 2 回、lever 操作。

## クレジット

- **pashina** — オペレータ。回路意味論の裁定、実 world での検証、Bench 較正に使った参照回路。
- 導出・配置・道具は LLM の席（Claude Fable 5.1 / Opus 5）が、オペレータの指揮下で作成。
- 設計案 1 件と誤りの指摘 2 件は、独立した第二モデルの査読者によるものです。

MIT ライセンス。Mojang / Microsoft とは無関係です。
