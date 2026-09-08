# PLACE-ALU-1 — 記録（DIRECTOR 7、2026-09-08 18:01:13Z）

- エージェント: Fable、35 分上限、与件 = 規則表 2 つ + ALU-1 の網 + PLACE-1 の配置例。**収束せず**（interface は決定、block 一覧は未完、packing 2 回とも中継 solid の 6 面隣接で破綻）。実測 25 分、87k token（自己申告 45k）。
- source でエージェントが見つけた事実 2 つ（当エージェントが検算）: (1) **torch は comparator の side から 0 と読まれる**（`RedstoneTorchBlock.getStrongRedstonePower` :103-108 は DOWN 以外 0、side は strong を読む）→ ALU-1 の nP（torch）は 1 層では成立せず、`sub(back = redstone_block 15, side = P)` に置換（真理値表同一、+1 comparator +1 redstone_block −torch）。**当エージェントの規則表の誤り**（side は gate / torch の strong power を読める、と書いていた）。(2) 提案の `sub(W15, K12)` は side が container を読めないので不成立 → W を反転極性の 15 線（Wn）で運び、`sub(K3, [Wn])` で局所変換（極性の合意が要る）。
- interface（決定）: k = F(i−1) の front の wire cell、f = F の front、P は z=0 の行を repeater 1 個で復元しつつ通す（spur で 14）、Wn は別の行、pitch は x 方向（PX ≈ 9〜10、未確定）。
- 破綻の型: 強給電 solid の中継は 6 面すべての隣接 wire に level を渡すので、S2 の隣に nP 線や k 線を置けない。次のエージェントへの処方（エージェントの言葉）: **中継の近傍を先に描き、gate は後から詰める。c2 の fan-out は copy comparator（+1）を予算に入れる。**
- 予測 count（未検証）: comparator 16、barrel 2、redstone_block 1、repeater 2（P / Wn の復元）、中継 ~6、wire ~16、支持 ~1/部品 → ~50 + 支持、箱 PX × 2 × 10。
- 原文: `placealu1-result.md`。
