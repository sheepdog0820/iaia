# OS HIGH: 署名済みAPT配布元の更新候補確認

## 結論と次の作業

2026-10-09 09:30 JST、アプリ候補 `6791357f468c9aa7debecd68c817629f38329459` の通常image
`sha256:6de91d2a3c3fb4d2d4254c656b893352098a40d3dbd1bb3a75b7707c7e238874` と同じ配布元で、
署名検証付きの新規APT metadata取得と更新simulationを完了した。対象zlib/SASLの更新候補は導入済み版と同じで、
**現時点ではこの配布元の通常更新だけでHIGH2を解消する新しいpackageは確認できない。**
全OS packageの最新性・CVE非該当・修正完了の証明ではない。新しいapp imageのbuild/scanは行っていない。
先行[HIGH利用条件調査](RUNTIME_HIGH_IMPACT_2026-10-09.md)の38指摘/HIGH2/MEDIUM1/LOW35・Scout終了2は未合格のまま。
正式公開No-Goを維持する。

同じpackage版を繰り返しbuild/scanして修正を期待する手順は次の作業にしない。
修正版配布または配布元の正式な影響判定を得て、実際に変わった配布物とnative利用経路を再検証する。
独自patchや別OSの混入、library削除、scanner除外を指摘件数を減らすためだけに採用しない。
Google認可不足など、並行して安全に進められる公開条件は別に継続する。

## 配布元・候補版

image内の唯一のsource設定 `debian.sources` を検査し、`deb.debian.org/debian` の
trixie/trixie-updatesと `deb.debian.org/debian-security` のtrixie-security/mainだけを利用した。
設定のsnapshot URLはコメントで、実際の取得先を過去snapshotへ固定する設定ではない。
両設定のSigned-Byは `/usr/share/keyrings/debian-archive-keyring.pgp`。
Trusted/Allow-Insecure設定なし、署名検証・認証を省略するオプションなし。

| binary package | 導入済み版 = fresh metadataのCandidate | source package |
| --- | --- | --- |
| zlib1g | `1:1.3.dfsg+really1.3.1-1+b1` | zlib `1:1.3.dfsg+really1.3.1-1` |
| libsasl2-2 | `2.1.28+dfsg1-9` | cyrus-sasl2 `2.1.28+dfsg1-9` |
| libsasl2-modules-db | `2.1.28+dfsg1-9` | cyrus-sasl2 `2.1.28+dfsg1-9` |
| libpq5 | `17.11-0+deb13u1` | postgresql-17 `17.11-0+deb13u1` |
| libldap2 | `2.6.10+dfsg-1` | openldap `2.6.10+dfsg-1` |

APT3.0.3/amd64で `apt-get update`、`apt-cache policy`、
`apt-get --simulate --only-upgrade install zlib1g libsasl2-2 libsasl2-modules-db` はすべて終了0。
simulationは対象3packageを更新せず、追加/削除0。出力には別の「1 not upgraded」があり、
この3packageの検査をOS全体が更新不要という結論へ拡張しない。

updateのstderrには、標準のAPT cleanup hookがread-onlyの
`/var/cache/apt/archives/partial/*.deb` を削除できないPermission deniedがある。
metadata取得は完了/終了0、署名・取得失敗/部分index利用を示すメッセージなし。
警告を隠さず生ログに保持する。package installやhost側cache削除は行っていない。

## 一次情報との照合

同日の[Debian zlib判定](https://security-tracker.debian.org/tracker/CVE-2026-85091)は、trixieのsource版をvulnerable/unfixedとしている。
上流影響版表と既存1.3.1 sourceの相違は先行調査の未解決事項であり、今回のAPT候補確認で非該当へ変更しない。
[Cyrus SASL PR892](https://github.com/cyrusimap/cyrus-sasl/pull/892)はhead repository削除によりOct8にclosedとなっており、
mergedや公式releaseへの修正取り込みの証拠として扱わない。今回、Debian CyrusのWeb取得は失敗しており、
同日先行調査の判定と今回の署名済みpackage候補の証拠を区別する。

## 隔離・不変性・片付け

rootは調査container内のみ。read-only rootfs/cap-drop ALL/no-new-privileges、512MiB/1CPU、
mount/volumeなし、専用 `/tmp` tmpfs256MiB。Dockerのdefault/bridge networkで公式APT metadataを取得し、
network noneの調査と混同しない。app設定・環境ファイル・OAuth/token・AWS資格情報を読み込まず、
entrypointをPythonの診断だけへ置き換えた。metadata/cache/logの書込み先は `/tmp/apt`。

導入済み5package、source設定、keyring、system zlib/SASLの実体hashは検査前後で一致した。
source設定SHA-256は `f02a6fd0c0a28e5f47d4512c0e5d264138378272850fe41dcb370ec885a3fcba`、
keyringは `506b815cbb32d9b6066b4a2aa524071e071761e7e7f68c3ac74f3061ba852017`。
生ログ・script・container検査結果は `D:/tmp/codex-high-package-readiness-20261009` に保存する。

初回は未開始containerのNetworkModeをbridgeと誤って期待したため事前検査を止め、
実際のdefault/bridgeを確認後、同じ未開始IDで続行した。
その後Signed-Byの拡張子をgpgと誤って期待して終了1、APT取得前に停止した。
実sourceのpgpを確認してfixtureだけを修正し、別の専用containerで終了0。アプリ修正とは扱わない。
停止済み2containerの正確なID/name/label/image/mount/stateを検査して撤去し、所有container残0。
tmpfsはcontainerとともに撤去、image・生証拠・元の別作業は保持する。

アプリ/依存/Dockerfile/schema/main/AWS/共有DB/Secrets/IAM/課金/容量/外部通知・承認範囲に変更なし。
文書の取り消しは通常revertで可能。実環境の復旧操作は不要。
