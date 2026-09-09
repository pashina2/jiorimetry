# 失敗表

> English: [failures.md](failures.md)

形は [`facts.ja.md`](facts.ja.md) と同じ。1 行は、この repository の file が示すときにだけ存在します。
evidence が export されていない失敗は表の下に候補として名前だけ挙げ、それ以上は主張しません。

列:

* **信じていたこと** — 計器がその上に建てられていた前提。
* **evidence** — そうでないと示した file、続いてその file 中の文字列そのもの。
* **変わったもの** — それによって変わったこの repository の file または規則。
* **失敗の再現方法** — この repository の中で走る command、または `recorded only`。

| 信じていたこと | evidence | 変わったもの | 失敗の再現方法 |
|---|---|---|---|
| pin した入力 cell は level を保持するので、解が自分の入力を駆動することはあり得ず、pin は rule 複製への安全な問い方である。 | `docs/world/world4-record.md` - `the through-line is latched` | `tools/llmgen/capcell.py` で pin は床（pin 源と近傍の max）になった。修正後の判定器は以前通っていた解を却下し、その解は `artifacts/placer0/sol_p4_throughline.latched.json` として残されている。 | `cd tools/placer0 && python placer0_check.py ../../artifacts/placer0/problems.json p4_throughline ../../artifacts/placer0/sol_p4_throughline.latched.json`（BISTABLE と FAIL を印字） |
| rule 複製を cold start で 1 回反復すれば回路の DC 解が得られる。 | `docs/world/world4-record.md` - `in none of the other 13` | DC 解法は cold と hot の 2 seed から解き、2 解が食い違う cell を報告するようになった。挙動は `tools/llmgen/test_capcell.py` の unit test で固定。 | `cd tools/llmgen && python -m unittest test_capcell` |
| 解き直した through-line については判定器・placer・world が一致するはずで、実行前に書いた予測は 2/2 だった。 | `docs/world/feed1-record.md` - `FALSIFIED` | 対立の原因は DC ではなく時間だと辿られ、整定上限が Bench に入り（`set_floors`、`settle_after`）、placer の判定器は pin vector の順序対をすべて駆動し、contract checker に時間条項が入った。減衰する解は `artifacts/placer0/sol_p4_throughline.decay.json` として保存。 | `cd tools/placer0 && python placer0_check.py ../../artifacts/placer0/problems.json p4_throughline ../../artifacts/placer0/sol_p4_throughline.decay.json`（TIME と FAIL を印字） |
| 40 game tick の観測窓は整定を判定するのに十分で、窓の終わりで立っている値は latch である。 | `docs/world/p4-decay-trace.md` - `14 rounds = 56 gt` | 最後の変化が上限に接する regime は整定ではなく打ち切りとして記録される。整定は観測窓ではなく時間条項で縛る。 | recorded only: trace には server が要る。同じ判定の Bench 側は一つ上の行 |
| stage `v7` は bit slice なので、その隣に第 2 段を置ける。 | `docs/placement/slice-contract.md` - `n=1 20/32, n=2 38/128` | slice contract を明文化し、並べて解く checker を用意した。`v7` は段として据え置き、slice として `v8`、続いて `v9` を作った。 | `python tools/checks/alu_check_slices.py artifacts/layouts/v7_as_slice.json 1` |
| n=1 / n=2 / n=3 の関数表を通れば slice contract を満たしている。 | `docs/placement/slice1-result.md` - `C2 through-entry mismatches=1024` | 第二 reviewer の読みで、checker は関数表しか測っていないと分かった。各条項を直接測る第二の checker を用意し、docstring に測らない述語を明記。出口 2 本を repeater に置き換えて `v9` とし、2 条項を修正して `docs/placement/slice-contract.md` に記録した。 | `python tools/checks/alu_check_contract.py artifacts/layouts/alu_slice_v8.json` |
| 新しい条項 checker は収束と最終出力を検査し、side lock を全 slice で見て、座標の重複を受け付けない。 | `docs/placement/xcheck-second-reviewer-slice-search.md` - `named three holes` | 3 つの穴は `tools/checks/alu_check_contract.py` で塞がれ、出力は非収束行と最終出力の不一致も報告するようになった。`v9` は依然として通る。 | `python tools/checks/alu_check_contract.py artifacts/layouts/alu_slice_v9.json`（約 5 分） |
| 同じ内部から pitch 12 より小さい slice を組める。 | `docs/placement/xcheck-second-reviewer-slice-search.md` - `FAIL C5 boundary pair (10,2,4)` | pitch 12 を維持。候補は 1 行も解く前に境界対で構造的に落ち、測定条項でも落ちる。 | recorded only: 候補 layout はこの repository に無く、その cross-check だけがある |
| warm-up を 1 度通せば world に立っている artifact はすべて温まる。 | `docs/world/world4-record.md` - `3 of 14` | 各 chunk の前に wake regime を置き、artifact は自分の掃引中にだけ読むようにした。container を背にした comparator は非通電で load され、近傍が動くまで誤った読みのままになる。 | recorded only: server が要る |
| 1 回の実行が使う server 呼び出しの見積もりには上限までの余裕があった。 | `docs/world/feed1-record.md` - `0.7% low` | 見積もりを 5% 増しで取るようにし、最大の job は 4 分割になった。 | recorded only: server が要る |
| 何も測らずに終わった実行の結果 file も他と一緒に表にできる。 | `docs/world/feed1-record.md` - `KeyError: regimes` | 表の生成は空の結果 file を許容するようになり、resume flag が既に建てた world を再利用して完了済み spec を飛ばす。 | recorded only: server が要る |
| 入力 pin の西 3 cell を埋めれば feeder 探索は拒否し、world を建てない。 | `docs/world/feed1-record.md` - `FAILED-AS-WRITTEN` | 予測は薄めずに失敗として答えられた。探索は pin の下を通して 32/32 に達した。拒否の経路を試すため、全接近路を塞ぐ第二の variant を追加し、test でも覆っている。 | recorded only: 拒否の報告は `artifacts/world/feed1/out_v7walled/` と `artifacts/world/feed1/out_v7blocked/` |
| 前身 layout の失敗 2 行は配置の問題であり、座標を動かせば直る。 | `docs/placement/placealu3-result.md` - `two algebra swaps` | 幾何的な修正はすべて既に使われている support cell と衝突した。代わりに代数を書き換え、それが layout の 1 列と不可能な cell をまとめて消した。 | `python tools/checks/check_alu_stage.py artifacts/layouts/alu_stage_T6_30of32.json`（出発点だった 32 中 30） |
| Bench で全行を通した rig はそのまま置ける。 | `docs/placement/rig1-result.md` - `32/32 but 14 L2 diagonal links` | hard な lint 2 種は注記ではなく却下である。第 1 draft は全行を通したが却下、第 2 draft は repeater の背面 cell が空気で 32 中 20、第 3 draft が rig になった。world 建設 3 回分が無料で回避された。 | `python tools/world/build_rig1.py`（採用された draft。却下された draft はこの repository に無い） |
| 充填済みと報告された container は充填されており、level 9 の定数は手で入れやすい。 | `docs/world/live-alu-record.md` - `twice in a row a feeder barrel was reported as filled while it was still empty` | 読みは region file から取り、読むたびに更新時刻を確認するようにした。level 9 の container 2 つは 1 個足りず、駆動状態を読む前に修正された。 | recorded only: 実際の save |
| 探索器と判定器が同じ rule 複製を共有していても配置を受理するのに十分である。 | `docs/world/world4-record.md` - `This is the blind spot Astra named` | それ以上大きいものを作る前に、5 つの解を world で再生した。それがこの表の最初の行の latch を捕まえた。 | recorded only: server が要る。Bench 側は `cd tools/placer0 && python placer0_check.py ../../artifacts/placer0/problems.json p1_sub2side ../../artifacts/placer0/sol_p1_sub2side.json` |
| 配置問題 6 問はすべて充足可能で、解けない問題があれば探索の弱さである。 | `docs/placement/placer0-result.md` - `p3 is infeasible` | 充足不能性は rule 複製から証明された。出力 cell は固定 comparator の front であり、その side cell は禁止 cell の上に立たずには給電できない。誤っていたのは探索ではなく問題のほう。 | `cd tools/placer0 && python placer0.py ../../artifacts/placer0/problems.json p3_pkill_bridge -v` |
| 探索 heuristic の手調整 2 箇所は無害な安全弁である。 | `docs/placement/placer0-result.md` - `getting them` | 誤ると 5 block の解があるところで 10 block の配置を返した。両方の調整は測定結果の隣に明記されている。 | `cd tools/placer0 && python placer0.py ../../artifacts/placer0/problems.json p2_copy_into_side`（5 block の配置を返す） |

## evidence がこの repository に無い候補

名前を挙げるだけで、主張はしません。行にするには記録の export が要ります。

* **手書きの逆規則が閾値 gate を取りこぼしていたこと。** 修正前の規則集の記録はこの repository に無く、代数の記録 2 件は
  閾値を設計上の注記としてしか触れていない。
* **27,103 block に達した netlist 方式の合成。** 失敗そのものは README の散文にあるが、layout も測定も方式の記録も
  export されていない。
* **placer の欠陥 2 件を見つけたとされる pitch 11 の断片探索。** 費用表が名を挙げるのみ。ここにある pitch 11 の evidence は
  第二 reviewer の候補への cross-check（上の行）であって、欠陥のほうではない。
* **game が受け付けない minus 記号で打たれた座標表。** 散文のみ。
* **rig と slice の draft そのもの。** 結果の記録は却下された各 draft とその点数を述べているが、draft の layout は export
  されていないので、引用できるのは記述だけ。
