# VERT-1 — 縦の受け渡しの micro 試験（Bench のみ、DIRECTOR 7、2026-09-08 19:01:51Z）

> English: [facts-vertical.md](facts-vertical.md)

方針（Astra、オペレータ同意）: 未知の接続はオペレータに尋ねず小さく検証する。Bench（規則の写し、B-?? で較正）と実機の確認は分けて記録する。**本試験は Bench のみ、実機は未確認。**

形: pinned wire L → comparator cA（compare、back = wire）→ front の solid S（強給電 = L）→ **S の真上の wire** → y=2 の comparator cB。

| 試験 | 読み手 | 結果（L = 0 / 3 / 5 / 9 / 15） |
|---|---|---|
| T1 | cB の back = 上の wire | 上の wire = L、cB の出力 = L（無損失、5 値とも） |
| T2 | cB の side = 上の wire、back = redstone_block（subtract） | 15 − L（0 → 15、3 → 12、5 → 10、9 → 6）= 正確 |
| T3 | **干渉**: y=1 で S の隣 (2,1,1) に P の wire（15）を置く | 上の wire が **14** を読む（y=2 の wire は、水平隣が air の時その下の wire を読む = 斜め下の接続、−1） |

∴ 規則として使えるもの（Bench）: (1) comparator → 強給電 solid → 真上の wire は無損失で、back でも side でも読める。(2) **y=2 の wire の水平隣 4 cell が air なら、その真下（y=1）に wire を置いてはいけない**（斜め下の接続で漏れる）。置くなら y=2 側の隣を solid で塞ぐ（solid の上の wire は読まれない: 隣が solid の時は隣の上の wire を見るので、隣 (2,2,1) を solid にすれば (2,3,1) を見て air）。逆に言えば、y=2 の制御線と y=1 のデータ線は**同じ列に重ねるか、solid で仕切る**。
