# 事実表

> English: [facts.md](facts.md)

表は一つ。1 行 = **この repository の file が示している** 述語ひとつ。数値を述べた file がここに無いものは行にせず、
[file の裏付けが無い主張](#file-の裏付けが無い主張) に落とします（表に薄めて混ぜません）。

列:

* **述語** — 一文。数値は file がそう書いている場合のみ。
* **面** — 三つの oracle のどれで読んだか。operator の world（実際の save）、synthetic vanilla world
  （headless の 1.20.6 server）、Bench（`tools/llmgen/capcell.py` の rule 複製）。
* **evidence** — file、続いてその file の中で数値を担っている文字列そのもの。
* **再現方法** — この repository の中で走る command、または走らない理由。

行は面の強い順。`tools/check_tables.py` がこの file と `docs/failures.md` の evidence path と引用文字列を検証します。

| 述語 | 面 | evidence | 再現方法 |
|---|---|---|---|
| ALU stage `v7` を実際の save に配置し、176 個中 176 個の block 配置が block 一覧と一致、container 6 個中 6 個が宣言どおりの中身だった。 | operator の world | `docs/world/live-alu-record.md` - `176/176 placements matched` | ここでは再現不可: save は配布していない。その回の無加工の region capture が `artifacts/world/capture.rest-20260907T2117Z.json`、`capture.add001-20260907T2125Z.json`、`capture.sub001-20260907T2126Z.json` |
| 静止状態で、配置した stage の comparator 23 個中 23 個が Bench の状態と一致した。 | operator の world | `docs/world/live-alu-record.md` - `23/23 comparators matched the Bench` | ここでは再現不可: 同じ save |
| region file から読んだ駆動 2 状態が Bench と一致し、いずれも comparator 24 個中 24 個一致。制御 lever ON で r = 3 / f = 0、OFF で r = 3 / f = 3。 | operator の world | `docs/world/live-alu-record.md` - `24/24 matched` | ここでは再現不可: 同じ save |
| 1-bit full adder が synthetic vanilla world で入力 8 通りすべて Bench を再現し、整定は 2〜10 game tick だった。 | synthetic world | `docs/world/world1-record.md` - `matches 8/8.` | ここでは再現不可: world 実行には 1.20.6 の server jar、Java 21 runtime、RCON 付き server directory が要り、いずれも配布していない（`tools/README.md`）。記録は `artifacts/world/world1.run.result.json` |
| adder の出力 2 点以外にも、8 vector にわたる comparator 状態の比較 112 件がすべて一致（不一致 0）。 | synthetic world | `docs/world/world1-record.md` - `112 read comparisons over the 8 recorded vectors, 0 unequal` | ここでは再現不可: 同じ理由 |
| ALU stage `v7` が synthetic vanilla world で 32 行すべて、r・f・畳んだ出力値のいずれについても Bench を再現した。 | synthetic world | `docs/world/world2-record.md` - `matches 32/32 for r, 32/32 for f` | ここでは再現不可: 同じ理由。記録は `artifacts/world/world2.run.result.json` |
| その回の読み取り点をすべて数えると 1024 点中 1024 点が一致し、うち comparator 状態比較 736 件は stage 自身の 23 個の comparator 上。 | synthetic world | `docs/world/world2-record.md` - `1024/1024 equal` | ここでは再現不可: 同じ理由 |
| 隣接する `alu_slice_v9` 2 枚が n=2 の 128 行すべてで Bench を再現し、読み取り点 14976 件で不一致 0。 | synthetic world | `docs/world/world4-record.md` - `14976` | ここでは再現不可: 同じ理由。記録は `artifacts/world/world4b1.run.result.json`、`world4b2`、`world4b3` |
| その回、128 行のうち 13 行は上限 40 game tick の中で 10 game tick の安定窓を閉じられず、丸めずに未整定として報告されている。 | synthetic world | `docs/world/world4-record.md` - `13 rows never closed a 10-gt window` | ここでは再現不可: 同じ理由 |
| synthetic world で駆動した placer の解 5 件のうち、14 行中 13 行は全読み取り点で一致し 1 行は一致せず、全体では 112 点中 105 点が一致。 | synthetic world | `docs/world/world4-record.md` - `105 of 112 equal` | ここでは再現不可: 同じ理由 |
| model を介さず world 側の道具に駆動させた ALU stage `v7` は world 32 行・失敗 0・読み取り点 1472 中 1472 一致。feeder cell は道具自身が探索したもの。 | synthetic world | `artifacts/world/feed1/out_v7/feed_v7.feed.md` - `0/1472` | ここでは再現不可: 同じ理由。job は `artifacts/world/feed1/job_v7.json` |
| 同じ道具で `v9` 2 枚は world 128 行・失敗 0・読み取り点 19328 中 19328 一致、未整定 13 行。 | synthetic world | `artifacts/world/feed1/out_world4/feed_world4.feed.md` - `0/19328` | ここでは再現不可: 同じ理由。job は `artifacts/world/feed1/job_world4.json` |
| 道具が一度も見たことのない pitch 14 の slice（第二 reviewer の探索が `v9` の内部を固定して見つけたもの）は world 128 行・失敗 0・読み取り点 20608 中 20608 一致。 | synthetic world | `artifacts/world/feed1/out_p14_final/feed_p14.feed.md` - `0/20608` | ここでは再現不可: 同じ理由。job は `artifacts/world/feed1/job_p14.json` |
| through-line 問題の loop 無し第三解は world 2 行・失敗 0・読み取り点 12 中 12 一致、最悪整定 8 game tick、68 block。 | synthetic world | `docs/world/p4-decay-trace.md` - `p4_throughline_v3` | ここでは再現不可: 同じ理由。出力は `artifacts/world/feed1/out_p4v3/` |
| 減衰する loop の game tick 毎 trace は、wire 1 hop あたり 1 level・1 周 4 game tick を示し、level 14 から 0 まで 56 tick。 | synthetic world | `docs/world/p4-decay-trace.md` - `14 rounds = 56 gt` | ここでは再現不可: 同じ理由。記録は `artifacts/world/feed1/out_p4trace/p4_trace.run.result.json` |
| 道具が駆動した world 実行 13 回の費用は RCON 呼び出し 3648392 回、実測 1483.3 秒、server が上がっている間の model token は 0。 | synthetic world | `docs/world/feed1-record.md` - `3648392` | ここでは再現不可: 同じ理由 |
| ALU stage `v7` は Bench の 32 行すべてを通し、hard な lint 2 種は 0 件。 | Bench | `docs/placement/placealu3-result.md` - `PASS 32/32` | `python tools/checks/alu_check2.py artifacts/layouts/alu_stage_v7.json` |
| 1-bit full adder は Bench で入力 8 通りすべてを通す。 | Bench | `docs/placement/place1-bench-output.txt` - `ALL PASS` | `python tools/checks/bench_sweep.py artifacts/layouts/layout_place1.json` |
| bit slice `alu_slice_v9` は自身の pitch で並べたとき、n=1 / n=2 / n=3 のすべての入力と mode について n-bit ALU 関数を満たす。 | Bench | `docs/placement/slice1-result.md` - `n=3 PASS 512/512` | `python tools/checks/alu_check_slices.py artifacts/layouts/alu_slice_v9.json 3`（約 3 分。n=1 / n=2 は数秒） |
| `alu_slice_v9` は時間条項を含む slice contract の測定可能な条項すべてを通す。n=2 を往復駆動した 254 遷移、最悪整定 26 game tick、失敗 0。 | Bench | `docs/world/p4-decay-trace.md` - `worst settle 26 gt` | `python tools/checks/alu_check_contract.py artifacts/layouts/alu_slice_v9.json`（約 5 分） |
| 前身の `alu_slice_v8` は関数表を通す一方、through-line 条項では 512 行にわたり entry level の不一致 1024 件で落ちる。 | Bench | `docs/placement/slice1-result.md` - `C2 through-entry mismatches=1024` | `python tools/checks/alu_check_contract.py artifacts/layouts/alu_slice_v8.json` |
| slice contract に照らして読むと stage `v7` は n=1 で 32 中 20、n=2 で 128 中 38。 | Bench | `docs/placement/slice-contract.md` - `n=1 20/32, n=2 38/128` | `python tools/checks/alu_check_slices.py artifacts/layouts/v7_as_slice.json 1` |
| stage の記録された前身 layout は Bench で 32 中 30。 | Bench | `docs/alu-place-handover.md` - `PASS 30/32` | `python tools/checks/check_alu_stage.py artifacts/layouts/alu_stage_T6_30of32.json` |
| 93 block の feeder rig は pin を一切使わず lever の状態だけで 32 行すべてを駆動し、pin 付きの行を厳密に再現する。 | Bench | `docs/placement/rig1-result.md` - `PASS 32/32  (r,f identical to pinned alu_check2 rows: 32/32)` | `python tools/world/build_rig1.py`（script の隣に JSON を 2 つ書き出す。commit 済みの写しが `artifacts/layouts/rig1_full_bench.json`） |
| 導出した網は、網とは別に書かれた evaluator を通る。adder と subtractor は全行、ALU の網は 32 行。 | Bench | `docs/algebra/alu1-eval-output.txt` - `PASS 32/32` | `python tools/checks/dc_eval.py artifacts/layouts/net_derive2.json`、`python tools/checks/dc_eval_sub.py artifacts/layouts/net_reuse1.json`、`python tools/checks/dc_eval_alu.py artifacts/layouts/net_alu1.json` |
| rule 駆動の placer は充足可能な配置問題 5 問すべてを人手の座標なしで解き、うち 2 問では手で導いた形より小さい配置を見つけた。 | Bench | `docs/placement/placer0-result.md` - `PASS p5_max_merge blocks 9` | `cd tools/placer0 && python placer0_check.py ../../artifacts/placer0/problems.json p5_max_merge ../../artifacts/placer0/sol_p5_max_merge.json` |
| 6 問目は充足不能であり、その充足不能性は探索が失敗したことからではなく rule 複製から証明されている。 | Bench | `docs/placement/placer0-result.md` - `p3 is infeasible` | `cd tools/placer0 && python placer0.py ../../artifacts/placer0/problems.json p3_pkill_bridge -v`（600 秒の上限で UNKNOWN） |
| 時間条項を入れたあと、placer は through-line 問題を loop 無し 16 block・最悪整定 8 game tick で解き直した。 | Bench | `docs/world/p4-decay-trace.md` - `16 blocks, no loop` | `cd tools/placer0 && python placer0_check.py ../../artifacts/placer0/problems.json p4_throughline ../../artifacts/placer0/sol_p4_throughline.json` |
| 第二 reviewer の pitch 14 slice は、reviewer の判定器とは独立に書かれたここの計器で n=1 / n=2 の関数表を通る。 | Bench | `docs/placement/xcheck-second-reviewer-slice-search.md` - `== relocated p14 function` | `python tools/checks/alu_check_slices.py artifacts/layouts/reviewer_slice_p14_relocated.json 2` |
| Bench は修正した 2 つの挙動を unit test で固定している。pin は床であること、減衰する loop と真の latch を整定上限で区別すること。 | Bench | `tools/llmgen/test_capcell.py` - `FloorAndLatchTests` | `cd tools/llmgen && python -m unittest test_capcell test_strength` |
| world 側の道具は server を必要としない test を 14 件持つ。 | Bench | `docs/world/feed1-record.md` - `14 tests, no server` | `cd tools/world && python -m unittest test_feed` |
| world 用 layout 2 件は stage layout から専用 script で再生成でき、commit 済みの file を byte 単位で再現する。 | Bench | `tools/world/make_layout_world1.py` - `artifacts/layouts/layout_world1.json` | `python tools/world/make_layout_world1.py && python tools/world/make_layout_world2.py` のあと `git status --porcelain` と `cmp tools/world/layout_world2.json artifacts/layouts/layout_world2.json` |

## file の裏付けが無い主張

この repository の散文には書かれているが、読み取りを担う file がここに無いもの。行にはせず、畳まずに残します。

* **operator の world における 1-bit full adder の 8/8。** 言及は要約の一文だけで、その配置の表も capture も
  cell 単位の読みもこの repository には無い。adder の Bench 行と synthetic world 行はこれとは無関係に有効。
* **netlist 方式の合成が 27,103 block、comparator あたり dust 約 158 個に達したこと。** その方式の記録は export
  されておらず、数値は README の失敗一覧にしか無い。
* **第二 reviewer による mux の 2,990 例検算。** 結果は credit されているが、検算そのものはこの repository に無い。
* **費用表**（stage ごとの実時間と token、および合計）。裏付ける計器出力はここに無く、当時の session counter の値。
* **placer の欠陥 2 件を見つけたとされる pitch 11 の断片探索。** 費用表の 1 行としてしか現れず、記録も候補 layout も
  欠陥一覧も export されていない。
* **仕上げ段階の人手の費用**（配置 command、手作業の container 充填、client 再起動、lever 操作）。散文のみ。

README の再現節に印字されている 2 つの数は、印字後に計器が変わったため、現在のこの repository が出す値と一致しません。

* unit test の行は 34 件と書いてあるが、ここの suite は現在 37 件を走らせる（skip 3、OK）。増えた 3 件が pin を床と
  する場合と整定時間の場合。
* rig の行は pin 付きの stage checker が `artifacts/layouts/rig1_full_bench.json` で 32/32 を出すと書いてある。pin が
  保持値ではなく床になって以降、同じ checker はこの layout で 12/32 を出す。入力を 0 に pin しても、その layout が
  すでに持っている物理 feeder を上書きしなくなったため。rig 自身の計器は上の表にある lever 駆動の掃引で、こちらは
  今も 32/32 を通す。
