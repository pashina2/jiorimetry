# RIG-1 — lever 5 本 + lamp 2 個の給電器（DIRECTOR 8、2026-09-07T21:41–22:18Z）

- 発注書は `scratchpad` に書いた（worktree への書き込みが権限で落ちたため）。内容: stage の standing cell と重ならない、block entity なし（composter[level=3]）、lever 1 本 = 信号 1 つ、r/f に lamp。
- Fable 席 15.5 分、実測 192k token: `rig1.program.json`（93 block）、Bench 32/32（lever 状態だけから）、lint L1/L2 0。床 2 cell（(7,0,6) (8,0,7)）を先に air にする必要あり。
- オペレータの world: `/setblock` 2 行 + `/aiwb place alu_stage_v7_rig1 6001 131 -4114`。region 22:18Z: rig 93/93 cell、SUB 1−0−0（lever a OFF, b ON, k ON）→ r 3 点灯 / f 0 消灯、stage comparator 23/23 一致（`capture.sub100-20260907T2218Z.json`）。
- 置いた直後は block update が無く給電器と lamp が寝ている → lever を 1 回ずつ倒して起こす（WORLD-1/2 の warm-up と同じ理由）。
