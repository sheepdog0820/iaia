# ファイル操作コマンドのOS監査指摘

2026-09-08、固定候補 `tableno-formal-release:10d21e42`（ID `sha256:dec00ade1cc08142732ee124b9082d2c19e88003cac4a40339d3efc302e69cf2`）の残るLOW 6件を確認した。

## 実測と実行経路

ネットワークなし・読み取り専用・終了時削除のコンテナでパッケージを確認。coreutils 9.7-3、diffutils 1:3.10-4、tar 1.35+dfsg-3.1。Pythonのshutil.whichによる再検査は終了0で、tar/chown/chgrp/sort/uniq/unexpand/diff3がすべて `/usr/bin` に存在した。

初回のシェル検査ではcommand -vがtarだけを返したため、それ以外を未搭載とはせず再検査した。`/proc/sys/fs/protected_symlinks` はPermission deniedで読み取れず、カーネルの対策値は未確認。権限を上げた再検査や設定変更は行っていない。

Dockerfile/dockerのシェルを対象コマンド名で検索した結果、DockerfileのCOPY --chownとビルド時chownだけが一致した。chown -Rはあるが-Lを併用せず、通常のentrypointにも対象コマンドの呼び出しはない。別途記録した主要Pythonの外部コマンド検索にも一致はなかったが、依存・保守操作の全経路がないことの証明ではない。

## 項目別評価

| CVE | 公式情報と残る条件 |
| --- | --- |
| [CVE-2005-2541](https://security-tracker.debian.org/tracker/CVE-2005-2541) | tarがsetuid/setgid付きファイルを展開するときの警告不足。Debianは権限保存を意図した挙動と説明。対象ツールは搭載されるため、外部アーカイブの展開時に所有者・特殊権限を継承しないことを確認する必要がある。通常entrypointに展開処理はない |
| [CVE-2017-18018](https://security-tracker.debian.org/tracker/CVE-2017-18018) | chown/chgrp -R -Lでシンボリックリンクへの差し替え競合。Dockerfileの現行呼び出しは当該オプションと不一致。Debianのカーネル対策注記を、今回読み取れなかったカーネル設定の確認済み証拠にはしない |
| [CVE-2025-5278](https://security-tracker.debian.org/tracker/CVE-2025-5278) | sortの旧式キー引数による境界外読み取り。対象sortは搭載。攻撃者が引数を与える経路は確認できていないが、全依存・保守操作は未検証 |
| [CVE-2026-53910](https://security-tracker.debian.org/tracker/CVE-2026-53910) | diff3が細工されたdiff出力を処理する際の整数オーバーフロー。--diff-programなどで別プログラムを指定できる経路を含む。対象diff3は搭載。通常起動での利用はないが、利用者がプログラム/出力を制御できる経路の網羅検査は未実施 |
| [CVE-2026-56391](https://security-tracker.debian.org/tracker/CVE-2026-56391) | uniq -wでマルチバイト入力を扱う際の境界外読み取り。uniqは搭載。通常起動での利用はない。上流修正コミットがあることを搭載版の修正済み判定には使わない |
| [CVE-2026-56392](https://security-tracker.debian.org/tracker/CVE-2026-56392) | unexpandの大きな-t引数による整数オーバーフローとヒープ書き込み。unexpandは搭載。引数を外部入力から渡す機能を追加する際は制限・隔離・更新を検証する。現候補の修正済み判定は行わない |

Debianは対象バージョンの6件をvulnerable/unfixedとしている。重要度や上流の異議を根拠に一括除外しない。今回、攻撃入力の実行・所有者変更・アーカイブ展開は行っていない。

これでLOW 40件すべての一次評価を記録した。全件解決ではなく、OSスキャン48件（HIGH 1 / MEDIUM 1 / LOW 40 / UNSPECIFIED 6）と個別の未解決条件を維持する。[監査一覧](RUNTIME_OS_REVIEW_INDEX_2026-09-08.md)から残作業を追跡する。

文書のみの変更でDB・Secrets・権限・実環境・費用への変更はない。差分・日本語・UTF-8/LFを検証し、アプリテストは再実行しない。
