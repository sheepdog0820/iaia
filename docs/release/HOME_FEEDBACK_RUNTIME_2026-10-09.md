# 退会通知を含む候補の通常配布物検証

## 対象・ソース照合

2026-10-09、[退会通知修正](HOME_ACCOUNT_EXIT_FEEDBACK_2026-10-09.md)
`0a6876310b9c76b06d15d6db88d82a58a168abc6` のclean archiveから通常Dockerfileを
`--pull --no-cache` でビルドした。終了0、Dockerfile/依存/製品codeの検証用変更はない。
main/ECR/AWS/共有DB・実ユーザー/Secrets/IAM/OAuth/課金・容量/外部通知は変更していない。

- ローカルtag: `tableno:home-feedback-0a687631`
- 固定image: `sha256:9d9f48b3e4ac3596b6cdac45efbe56f2a7a113206e4e5eb21d7355584e912627`
- OCI revisionは対象SHA。製品Python/template/static/関連test/lock/entrypoint等の
  選択663ファイルをarchiveとSHA-256照合し、不一致0。
- lock111依存と実インストール111 distributionの名前/版が一致、余分な依存0。
  packaging toolsは通常Dockerfileに従い除去済み。検証用依存の追加なし。
- `/entrypoint.sh` と同梱sourceのbytes一致、Python cache0、実UID10001。
  実env/SQLite DB/Terraform state・tfvars/cacheの禁止artifact漏出0。

先行[復旧・作成入口の配布物](MAIN_ACCOUNT_RECOVERY_RUNTIME_2026-10-09.md)の結果を流用せず、
home修正を含む新しいimage IDに対して以下を検査した。正式公開はNo-Goを維持する。

## 回帰・通常起動・実HTTP

製品source/依存をoverlayせず、試験runnerだけを読み取り専用で使用した。
Webは非root/read-only/cap-drop ALL/no-new-privilegesで、host portを公開しない。
隔離PostgreSQL 18.3の固定imageは
`sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7`。
PG自体はnetwork none、Web/PG testはそのnamespaceを共有し、外部への経路を持たない。
DB/media/static/tmpは使い捨て、回帰試験の未mock Requestsも禁止した。

| 検証 | 結果と範囲 |
| --- | --- |
| Linux/SQLite回帰 | 162件成功、73.217秒、省略0、終了0/OOMなし。復旧・作成入口・home通知・認証・設定・法務表示・静的UI・サーバーログを含む |
| PostgreSQL回帰 | aws-pre/production設定、復旧・作成入口・home通知の25件成功、12.564秒、省略0、終了0/OOMなし |
| 通常entrypoint | 隔離DBへの全移行、静的232件収集/624件後処理、Daphne ASGI起動が成功 |
| 実HTTP | readiness正常に加え、GET/HEAD/POST計25要求が期待結果に一致。24時間案内、版選択/両版/一覧/calendarの認証拒否と実login後の表示、保存0/POST405を保持 |
| 実退会 | CSRF欠落403で利用者保持、誤passwordで退会画面302/日本語errorと保持、正しいCSRF/passwordでhome302と削除。日本語成功通知200、再取得で通知なし、元session行の削除、dashboard302、削除済み資格情報の実login form拒否200を確認 |
| 設定・HTTP header | DEBUG=False/復旧期限86400、DENY/nosniff/HSTSを照合。同じ通常Webで `manage.py check --deploy` 終了0/指摘0/抑制0 |

162件はhost194件と別範囲で、文書39件を除いた155件にサーバーログ7件を加えたもの。
`.dockerignore` が文書を除くため、image内で文書テストを成功扱いしない。
PG testの非TLS clientだけSSL redirectを無効化し、メールはlocmem。
通常WebのSSL設定は変更せず、HTTP probeがtrusted proxy相当のForwarded httpsを送った。
loopbackにTLS listenerがないためclientのSecure cookie送出条件だけを緩めた。
実TLS・実SMTP/受信箱・S3/Redis・実Google/Stripeの成功を意味しない。
通常Webのcache/sessionはlocmem/DB、購入開始・課金メール配送は無効。
隔離DBの移行・ローカル静的収集は試験のみで、共有環境への実施承認ではない。

## 同imageのOS監査

Docker Scout 1.26.0、severity/package除外なしで292 packagesをindex。
16 vulnerable packages/38指摘（CRITICAL0/HIGH2/MEDIUM1/LOW35、Python0）、native終了2。
CIのPython依存監査成功と、OSを含む全配布物の合格を区別する。

| HIGH | 報告対象 | 判定 |
| --- | --- | --- |
| CVE-2026-107161 | cyrus-sasl2 2.1.28+dfsg1-9 | scannerはnot fixed。除外/リスク受容していない |
| CVE-2026-85091 | zlib 1:1.3.dfsg+really1.3.1-1 | scannerはnot fixed。影響範囲の不一致を非該当扱いにしていない |

当日の[Debian zlib tracker](https://security-tracker.debian.org/tracker/CVE-2026-85091)では
trixieがvulnerable/unfixedである一方、説明の上流範囲は1.3.1.2以降。
この不一致だけで解消としない。[Cyrus PR #892](https://github.com/cyrusimap/cyrus-sasl/pull/892)は
head repository削除でclosed、merge/修正版配布の証拠ではない。
CyrusのDebian CVEページは今回web toolで取得できず、公式判定の再確認済みとは扱わない。
MEDIUMはtar/CVE-2025-45582、LOWも全件保持し、OSゲート未合格。

## CI・後片付け・次の境界

11:43〜11:44 JSTの[修正SHAのCI](https://github.com/sheepdog0820/iaia/actions/runs/37874963631)は
infrastructure/production-database/system/lint-security/Unit・Integrationの5ジョブ成功、Playwrightは実行中。
修正ブランチのCIを記録pushで途中キャンセルしないよう、記録は同SHAから分けた
`codex/home-feedback-runtime-evidence-20261009` にまとめる。両ブランチの製品内容を変えない。

11:39:49 JST、name/label/完全ID/imageを照合し、終了0の試験と起動中Web/PGの
所有5 containersだけを停止・削除、残0。使い捨てDB/合成利用者はtmpfs破棄で復元対象外。
固定image/archive・生ログ・SARIFは `D:/tmp/codex-home-runtime-0a687631-20261009` に保持する。

この候補のCI全6成功・OS対応/判定・main/AWS反映は未完了。
[限定候補の反映案](MAIN_ACCOUNT_RECOVERY_CANDIDATE_2026-10-09.md#aws読み取りと反映準備)は
実行時に稼働版/復旧先を再確認し、既存favicon承認へ追加しない。
[正式公開の受入条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)の課金・外部連携・権限・性能・
DB/S3復旧・運営条件も残る。No-Goを維持し、今回の局所的成功を全体合格へ拡張しない。
