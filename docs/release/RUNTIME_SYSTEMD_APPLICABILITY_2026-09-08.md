# systemdのOS監査指摘の適用条件

2026-09-08、固定候補 `tableno-formal-release:10d21e42`（ID `sha256:dec00ade1cc08142732ee124b9082d2c19e88003cac4a40339d3efc302e69cf2`）のLOW 4件をDebianの追跡情報と照合した。

## 実測と実行経路

ネットワークなし・読み取り専用・終了時削除のコンテナで検査し、終了0。証跡はGit管理外の `tmp/inspect-runtime-systemd.py` と `tmp/runtime-systemd-10d21e42.log`。

- systemd由来のインストール済みパッケージはlibsystemd0とlibudev1、いずれも `257.13-1~deb13u1`。
- systemd・systemd-tmpfiles・journalctlはPATH上にない。
- `/usr/lib/systemd/systemd`、`/usr/lib/systemd/systemd-journald`、`/usr/bin/systemd-tmpfiles`、`/usr/bin/journalctl` は存在しない。
- `/var/log/journal` と `/run/log/journal` は存在しない。
- アプリのPython・シェル・Dockerfile・依存ファイルの検索ではjournald/JournalHandler/SysLogHandlerの直接利用を検出しなかった。`tableno/settings.py` と `settings_production.py` のコンソール出力はStreamHandlerで、コンテナは `tableno.server` からDaphneを直接起動する。

検索範囲に一致がないことは、ネイティブ依存や外部設定を含む全経路の不在証明ではない。libsystemd0は残っており、journal関連APIまで未搭載とは判定しない。

## 項目別評価

| CVE | Debianが記載する条件・問題 | 固定候補での評価 |
| --- | --- | --- |
| [CVE-2013-4392](https://security-tracker.debian.org/tracker/CVE-2013-4392) | systemdとSELinuxを利用するシステムで、シンボリックリンク経由の権限・コンテキスト変更 | コンテナ内にsystemd実行ファイルがなく、通常起動もDaphne直接実行のため、記載された実行条件と不一致 |
| [CVE-2023-31437](https://security-tracker.debian.org/tracker/CVE-2023-31437) | 封印済みjournalの変更により、一部表示でメッセージが見えなくなる | journald・journalctl・journal保存先がなく、アプリの通常ログ処理で当該経路を確認できない。ライブラリ全体の非該当は未確定 |
| [CVE-2023-31438](https://security-tracker.debian.org/tracker/CVE-2023-31438) | 封印済みjournalを切り詰め、封印を再開して改変が検知されない | 上記と同じ。journalの完全性検証を本アプリの証跡保護として利用する構成は確認していない |
| [CVE-2023-31439](https://security-tracker.debian.org/tracker/CVE-2023-31439) | 過去イベントを変更・調整して完全性検証で改変が検知されない | 上記と同じ。libsystemd0の存在を理由にしたスキャナー指摘は維持 |

Debianは4件とも対象ソースパッケージをvulnerable/unfixedとしており、2023年の3件には上流が異議を唱えているとの注記がある。異議や重要度だけを根拠に安全とは判定しない。

この評価は固定コンテナの構成に限定する。ホストOS、ログ転送先、保存済みログの改変耐性は未検証で、コンテナにjournaldがないことからホストの安全性を推定しない。journalのマウント、ログ設定、ベースイメージが変わる場合は再評価する。

OSスキャンは48件（HIGH 1 / MEDIUM 1 / LOW 40 / UNSPECIFIED 6）のまま。curl/OpenLDAPと合わせLOW 15件の個別評価を記録し、残るLOW 25件は未評価。今回のjournal 3件を含む残条件や他重要度の未解決項目は引き続き扱う。指摘抑制・例外承認・正式公開合格は行っていない。

文書のみの変更で、DB・Secrets・アクセス設定・実環境・費用への変更はない。差分とUTF-8/LFを確認する。アプリの変更を含まないためアプリテストの再実行は不要。
