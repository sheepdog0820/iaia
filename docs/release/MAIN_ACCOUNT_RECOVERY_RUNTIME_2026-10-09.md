# main基準の復旧・作成入口候補の通常配布物検証

## 対象と判定

2026-10-09、[限定候補](MAIN_ACCOUNT_RECOVERY_CANDIDATE_2026-10-09.md)
`dbe8fca17bab362d8125037b0c696ce634d76d3d` のclean archiveから、
通常Dockerfileを変更せず `--pull --no-cache` でビルドした。ビルド終了0。
mainへのマージ、ECR push、AWS反映、共有DB・実データ・Secrets/IAM・費用の変更はしていない。

- ローカルtag: `tableno:main-account-recovery-dbe8fca1`
- 固定image ID: `sha256:8e88edb13f98fe7d2af7cb6db82002d644387f315c1fb968b51bafe3e1b8d70d`
- OCI revision labelは対象SHA。配布物内の製品Python、template、static、関連test等の
  選択662ファイルをarchiveとSHA-256照合し、不一致0。
- lockの111依存と実インストール111 distributionの名前/版を照合し、不一致0・余分な依存0。
  pip/setuptools/wheelは通常Dockerfileに従って除去済み。検証用依存は追加していない。
- `/entrypoint.sh` と同梱 `docker/entrypoint.sh` のbytes一致、Python cache0。
  実UID10001、実env/SQLite DB/Terraform state・tfvars/cacheの禁止artifact漏出0。

通常配布物の起動・関連回帰は成功したが、OS監査は未合格。
正式公開No-Goと、[判定表](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)の他の必須条件を維持する。

## Linux回帰と通常起動

対象アプリ/依存を上書きせず、検証runnerだけを読み取り専用でmountした。
アプリはread-only/非root/cap-drop ALL/no-new-privilegesで、外部通信・host port公開なし。
テスト用media/DB/staticは使い捨て。テストrunnerの未mock Requestsも禁止した。

| 検証 | 結果と範囲 |
| --- | --- |
| 通常image内SQLite回帰 | 154件成功、76.384秒、省略0、終了0/OOMなし。作成入口、復旧、認証、ログイン障害、production設定、法務表示、作成静的UI、サーバーログを含む |
| PostgreSQL回帰 | PostgreSQL 18.3/`aws-pre`設定、追加2 integration modulesの17件成功、10.231秒、省略0、終了0/OOMなし |
| 通常entrypoint | 隔離DBへの全移行、静的収集232件/後処理624件、Daphne ASGI起動が成功。起動用製品codeのoverlayなし |
| 実HTTP | readiness正常に加えてGET/HEAD/POST計15要求が期待結果に一致。版選択・6版/7版・calendarの匿名拒否、実CSRFログイン後にこれらと一覧の表示を確認 |
| 読み取り・拒否操作 | 版選択GET/HEAD、auth POST405でキャラクター保存0。公開復旧完了画面200/日本語24時間案内、設定86400秒/DEBUG=False |
| セキュリティ設定 | 実HTTP応答のDENY/nosniff/HSTSを照合、同じ起動containerで `python manage.py check --deploy` 終了0/指摘0/抑制0 |

SQLiteの154件は先行host186件と別の範囲で、文書39件を除いた147件に
サーバーログ7件を加えたもの。`.dockerignore` がAGENTS.md等の文書を除くため、
文書検証をimage内で実行して成功扱いにはしない。
Windowsの既存Twisted import障害は修復していないが、Linux通常imageでは
同梱Twisted/Daphneのimport、ログ7件と実ASGI起動を確認できた。
文書更新後のhost文書39件も成功（0.046秒）。今回の製品code/依存変更はなく、
後続の記録commitは上記dbe8fca1の配布物検証と区別する。

PG testでは非TLS Django test clientのためSSL redirectを試験内で無効化し、メールはlocmem。
通常webはSSL設定を変更せず、HTTP probeがtrusted proxy相当のForwarded httpsを送った。
probe clientのみSecure cookieをloopbackで送れるようにしたため、実TLSの証明ではない。
web cache/sessionはlocmem/DB、S3/Redis/実SMTP・受信箱/実Google・Stripeは未検証。
隔離DB初期化・ローカル静的収集は配布物検査用で、共有環境での実施承認には含めない。

HTTP probe初回はreadinessのdatabase/cache階層、2回目はcalendar URLの誤りで失敗した。
製品の `checks` 契約と `reverse('calendar_view')` に合わせてprobeだけを修正し、
最終終了0を確認。製品不具合の修正や失敗の抑制ではなく、生ログも保持している。

## 新しい固定imageのOS監査

Docker Scout 1.26.0を同image IDに対してseverity/package除外なしで実行。
292 packagesをindex、16 vulnerable packages/38指摘でnative終了2。
内訳はCRITICAL0/HIGH2/MEDIUM1/LOW35、Python指摘0。先行Google imageの件数を流用していない。

| HIGH | 同imageの報告対象 | 判定 |
| --- | --- | --- |
| CVE-2026-107161 | cyrus-sasl2 2.1.28+dfsg1-9 | scannerのfixed versionはnot fixed。除外/リスク受容はしていない |
| CVE-2026-85091 | zlib 1:1.3.dfsg+really1.3.1-1 | scannerのfixed versionはnot fixed。対象範囲の不一致を解消扱いにしない |

当日の[Debian zlib tracker](https://security-tracker.debian.org/tracker/CVE-2026-85091)は
trixieをvulnerable/unfixedとする一方、説明上の上流対象は1.3.1.2以降で、非該当は未確定。
[Cyrus修正PR #892](https://github.com/cyrusimap/cyrus-sasl/pull/892)はhead repository削除による
closedであり、merge/修正版の配布成功ではない。今回も修正のある配布物として扱わない。
MEDIUMはCVE-2025-45582/tar 1.35+dfsg-3.1。LOWを含め全指摘を保持する。

## CI・後片付け・次の境界

10:41 JSTの[対象SHAのCI読み取り](https://github.com/sheepdog0820/iaia/actions/runs/37869962219)で
lint-security/production-database/infrastructure/systemの4件成功、
Unit/IntegrationとPlaywrightの2件は実行中。timeoutを失敗と扱って再起動していない。
全6件成功・OSゲート合格・AWS反映の証明は未完了。

10:43 JST、label/name/image/完全IDを照合して所有5 containersだけを停止・削除し、残0。
隔離PGと合成利用者はtmpfs破棄により復元対象外。image/archive・生ログ・SARIFは保存した。
証拠: `D:/tmp/codex-main-recovery-runtime-dbe8fca1-20261009`。
候補作成時の[AWS読み取りと限定反映準備](MAIN_ACCOUNT_RECOVERY_CANDIDATE_2026-10-09.md#aws読み取りと反映準備)
を保持するが、今回AWSは再照合・更新していない。実行時はmain/定義54/digest等を再確認する。
正式公開全体の課金・外部連携・権限・性能・DB/S3復旧・運営条件は継続タスクである。
