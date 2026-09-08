# tools/

> English: [README.md](README.md)

ここにある物はすべて標準ライブラリのみの Python 3.11 以上です。リポジトリのルートから実行して
ください。`sys.path` の行は各 file からの相対で解決するので、インストールも `PYTHONPATH` も
不要です。

```
tools/llmgen/   Bench と規則の機械
tools/checks/   掃引・checker・評価器   （外部依存なし）
tools/world/    合成世界の生成 + 実 world の観測（利用者が用意する software が要る）
```

## tools/llmgen — Bench

| file | 何であるか |
|---|---|
| `machine.py` | DC の規則モデル: 各部品が何を読み、何を出し、dust がどう減衰し、gate がどの面を見て、何を solid と数えるか。1.20.6 の source から書いた。 |
| `library.py` | `machine.py` が索く部品表。import は無い。 |
| `capcell.py` | `Bench` — block の一覧を読み込み、DC の不動点まで解き、任意の cell を読み戻す。`tools/checks/` の checker はすべてこの oracle を呼ぶ。 |
| `cellref.py`、`cellsearch.py`、`gen.py`、`netlist.py`、`place.py`、`map.py` | 機械の周りの探索・生成の層。`cell_to_world.py` が import するので同梱している。 |
| `cell_to_world.py`、`cell_to_program.py`、`litematic_writer.py` | cell を world への配置、または配置 program に翻訳する。 |
| `test_capcell.py`、`test_strength.py` | 単体試験: `cd tools/llmgen && python -m unittest test_capcell test_strength` |

Bench は正しいと仮定した物ではなく **較正** した物です。既存の参照回路に対して走らせ、cell ごとの
読みを実世界の読みと突き合わせました。その回路は本 export には含まれていません。

## tools/checks — server の要らない物すべて

| file | 使い方 |
|---|---|
| `bench_sweep.py LAYOUT` | 全加算器の掃引、8 vector。`ALL PASS` / `FAIL`。 |
| `alu_check2.py LAYOUT [-v]` | ALU 1 段: 32 行 + 配置 lint `L1`（vanilla の設置条件）、`L2`（斜めの dust の読み）、`L3`（情報）。layout の隣に `LAYOUT.rows.json` を書く。 |
| `alu_check_slices.py LAYOUT [n] [-v]` | 宣言された pitch に沿って layout を `n` 個並べ、`n` bit の ADD/SUB/AND/OR を検査する。`n = 1, 2, 3` が全部通って初めて slice と言える。 |
| `check_alu_stage.py LAYOUT` | 古く単純な方の ALU 1 段の検査（30/32 の前身に使った）。 |
| `dc_eval.py NET`、`dc_eval_sub.py NET`、`dc_eval_alu.py NET` | layout ではなく *網* を、代数から直接評価する。一致に意味を持たせるため、Bench とは独立に書いてある。 |
| `bench_sweep_feed.py`、`bench_sweep_feed2.py` | 同じ掃引を、pin 固定の入力ではなく物理的な給電器と lever の状態で駆動する版 — 合成世界との比較を同条件にしているのはこれ。 |

## tools/world — このリポジトリが同梱しない software が要る

これらは実際の Minecraft server を駆動します。**利用者が用意する物:**

1. **Minecraft 1.20.6 の server jar。** ここでは配布していません。`eula.txt` に同意した自分の
   server ディレクトリに置いてください。
2. `PATH` の通った **Java 21 runtime**。
3. その server の `server.properties` で **RCON を有効化**し、password を server ディレクトリの
   `rcon-password.txt` に置くこと。
4. build script はそのディレクトリを `--template` として取ります。既定はリポジトリ相対の
   `runtime/carpet-work` ですが、これは **本リポジトリには含まれていません** — 自分のを指して
   ください。

| file | 何をするか |
|---|---|
| `worldgen.py`、`_deps/tplgen.py`、`_deps/litematic_to_nbt.py` | region file と `level.dat` を直接書く。任意の block 一覧を新しい world に入れられる唯一の writer。 |
| `synthworld.py` | 上をまとめて「block 一覧を入れると遊べる void world が出る」形にする。 |
| `worldprobe.py` | server を headless で走らせ、tick loop を凍結し、step し、名前のついた cell をすべて RCON 越しに読み戻す。`artifacts/world/` の `*.run.result.json` はこれが作る。 |
| `regioncap.py` | server を走らせずに `.mca` region file から blockstate を直接読む。オペレータ自身の world に触れずに観測するのに使う。 |
| `build_world1.py`、`build_world2.py` | 全加算器と ALU の合成世界を作る。 |
| `make_layout_world1.py`、`make_layout_world2.py` | 段の layout から world の layout（段 + 給電器）を導く。server は不要で、commit 済みの JSON を byte 単位で再現する。 |
| `build_rig1.py` | lever 5 本の給電器 rig を作り、Bench で掃引する。server は不要。 |

`rcon.py` は最小限の RCON client（標準ライブラリの socket のみ）。

## 宙に浮いた参照について

`tools/llmgen/` の docstring は `notes/2026-09-06-…` のような path を引いています。これらは非公開の
開発リポジトリへの由来の指し先で、ここでは解決できません。規則の出所を記録している物なので、
削らずそのまま残してあります。

host の絶対 path、user 名、session 識別子は、記録された run の metadata の中も含めて、全体を通じて
`<host-path>`、`<user>`、`<session-id>`、`<dev-repo>` に置き換えてあります。`artifacts/world/*.json`
の実測 block データには手を入れていません。
