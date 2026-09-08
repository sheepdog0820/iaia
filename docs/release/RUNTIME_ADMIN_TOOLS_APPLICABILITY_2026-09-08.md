# 管理ツール・一時ファイルのOS監査指摘

2026-09-08、固定候補 `tableno-formal-release:10d21e42`（ID `sha256:dec00ade1cc08142732ee124b9082d2c19e88003cac4a40339d3efc302e69cf2`）のLOW 4件を照合した。

## 実測

ネットワークなし・読み取り専用・終了時削除のコンテナで検査し、終了0。再現用スクリプトはGit管理外の `tmp/inspect-runtime-admin.py`。権限変更や認証ログの内容の読み取りは行わない。

- `/var/log/btmp` はroot所有、gid 43、0660、サイズ0。`LOG_UNKFAIL_ENAB no`、sshdはPATH上にない。
- apt-keyはPATHにも `/usr/bin/apt-key` にもない。Debianのsourcesファイルはローカルの `/usr/share/keyrings/debian-archive-keyring.pgp` をSigned-Byに指定する。
- chfn/chshはpasswdパッケージが提供し、lddにReadlineへのリンクはない。両方root所有の04755で、setuid権限自体は残っている。
- Perlの `File::Temp` はロード可能で、バージョン0.2311。

## 項目別評価

| CVE | 公式情報と固定候補の評価 |
| --- | --- |
| [CVE-2007-5686](https://security-tracker.debian.org/tracker/CVE-2007-5686) | 認証失敗ログbtmpの不適切なアクセス権。今回のbtmpは一般ユーザーへの読み取り権限がなく、Debianが注記する未知のユーザー名を記録しない設定も一致する。今回の初期状態は報告条件と不一致。実運用のログローテーション後の権限や別マウントは未検証 |
| [CVE-2011-3374](https://security-tracker.debian.org/tracker/CVE-2011-3374) | apt-keyの鍵検証。今回apt-keyは未搭載、標準sourcesはローカルの署名鍵を指定。対象経路はない。ベースイメージ作成以前の供給経路まで検証したものではない |
| [CVE-2022-0563](https://security-tracker.debian.org/tracker/CVE-2022-0563) | Readlineを使うutil-linux版chfn/chshで、INPUTRCの解釈エラーから特権ファイル内容が漏れる問題。Debianは当該コマンドをshadowが提供すると注記。実測でもpasswd提供かつReadlineリンクなしで条件不一致。setuid全般の安全性は別問題 |
| [CVE-2011-4116](https://security-tracker.debian.org/tracker/CVE-2011-4116) | Perl File::Tempの_is_safeによるシンボリックリンクの扱い。モジュールが存在するため未搭載として除外できない。実際の呼び出しと一時ディレクトリの信頼境界を確認する必要がある |

Dockerfile/docker/accounts/schedules/scenarios/tableno/scriptsのPython・シェル・Perl・DockerfileからFile::Temp/apt-key/perl/chfn/chshを検索した。一致は `scripts/test/install_chrome_wsl.sh` のapt-key addだけで、ローカルChrome導入用のスクリプトだった。File::Tempの直接利用は見つからないが、依存やOS保守処理からの呼び出し不在の証明にはならない。ローカル導入スクリプトの鍵管理は今回の固定コンテナ評価とは別に扱う。

File::Tempの攻撃再現や全依存の呼び出し追跡は未実施。管理ツールのsetuid除去や実稼働の権限昇格禁止を検討する場合は、必要な起動・保守処理と互換性を検証し、実環境の権限変更は承認境界に従う。今回、権限やファイルを変更していない。

LOWの個別評価は34件、未評価は6件。OSスキャン48件（HIGH 1 / MEDIUM 1 / LOW 40 / UNSPECIFIED 6）と評価済みの未解決条件を維持する。指摘の抑制・例外承認・正式公開合格は行っていない。

文書のみの変更でDB・Secrets・権限・実環境・費用への変更はない。差分・日本語・UTF-8/LFを検証し、アプリテストは再実行しない。
