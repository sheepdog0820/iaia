# Python依存更新と稼働イメージ監査（2026-10-02）

## 発見と更新範囲

文書更新 `89f999a0` の[CI](https://github.com/sheepdog0820/iaia/actions/runs/37008809641)で、Lint/Black/isort/Banditは成功したが、依存脆弱性監査が失敗した。9月25日のCI成功は10月2日時点の監査成功を保証しない。

旧 `requirements-test.lock.txt` をpip-audit 2.10.1で照合すると4パッケージ・25指摘エントリー（virtualenvの重複IDを除くと21 ID）、終了1。runtime/dev/testの3ロックを、既存のPython 3.11 / pip-compile / ハッシュ付き生成方式で更新した。

| 依存 | 旧版 | 更新版 | 範囲・根拠 |
| --- | --- | --- | --- |
| oauthlib | 3.3.1 | 4.0.0 | runtime/dev/test。[上流変更記録](https://raw.githubusercontent.com/oauthlib/oauthlib/v4.0.0/CHANGELOG.rst)のPKCE比較修正。プロバイダー側の破壊的変更があるため既存の認証テストで互換性を確認する |
| PyJWT | 2.13.0 | 2.15.1 | runtime/dev/test。[上流変更記録](https://pyjwt.readthedocs.io/en/stable/changelog.html)の鍵検証・不正入力処理修正と、後続のBase64URL padding互換性修正を含む |
| urllib3 | 2.7.0 | 2.8.0 | runtime/dev/test。[上流リリース](https://github.com/urllib3/urllib3/releases/tag/2.8.0)のHTTPS proxy検証修正 |
| virtualenv | 21.7.5 | 21.7.13 | dev/test。[上流変更記録](https://virtualenv.pypa.io/en/latest/changelog.html#v21-7-13-2026-09-18)の環境作成・activation scriptの修正 |
| python-discovery | 1.5.3 | 1.6.1 | dev/test。virtualenv更新版が要求する `>=1.6` に合わせた推移依存更新 |

無関係なパッケージの全体更新、監査の無効化・除外は行っていない。アプリ・DBの仕様、料金、権限、外部送信先、AWS設定は変更しない。

## 検証

- 3ロックそれぞれに `python -m pip_audit -r <lock> --no-deps --disable-pip` を実行し、いずれも既知指摘なし・終了0。固定された全行を監査する方式であり、実インストールの依存整合性確認は別に行う。
- JWT回帰テスト4件を追加。旧PyJWT 2.13.0では深いJSONのRecursionErrorと9種類の不正日時claimのTypeErrorがライブラリの認証例外契約から逸脱することを再現（10 errors）。2.15.1では4件成功し、正常tokenの往復と誤署名拒否も維持した。実サービスのエンドポイントに対する悪用可能性全体を証明する試験ではない。
- 検証用venvを `C:/tmp/iaia-security-venv-20261002` に分離。初回のsystem-site-packages案はグローバルrequestsとの不整合を検出したため採用せず、外部site-packagesを無効にして全テストロックを導入する方式へ変更。初期pip 22.3.1でのハッシュ付きextras解決失敗後、CIと同じpip更新手順で26.2.1へ更新して再試行した。元の開発venvは変更していない。
- 全テストロック導入は成功、pip checkは依存不整合なし。実インストール環境での `python -m pip_audit` も既知指摘なし・終了0。
- 認証/外部通信の関連132テストは130成功・2省略（23.911秒）。Google/Discord/X API認証、allauthのGoogle連携callback、アカウント連携安全性、Calendar/Sheets配送、外部HTTP失敗処理と新JWT回帰を対象とした。省略2件はSQLiteに行ロックがないためのOAuth競合テストで、PostgreSQL CIの確認を別途要する。外部APIはmockであり実認可・実配送の代替ではない。
- 新JWTテスト4件・9 subtests成功、テストファイル24実行行は100%到達。Django check、makemigrations --check --dry-run（変更なし）、対象ファイルのBlack/isort/Flake8/Bandit、差分チェックは成功。利用者向けUI文言の変更はない。
- ロック差分の機械照合ではruntime 111パッケージ中3件、dev 167/test 207パッケージ中各5件のみ変更、パッケージの追加・削除なし。修正後の全体CIと通常配布イメージの検証は別途必要。

## 稼働イメージの監査（更新前）

[稼働版照合](RELEASE_STATE_2026-10-02.md)で確認したECR/実行タスクのdigestと、ローカルイメージのRepoDigestsが一致した。

- digest: `sha256:bc951b76e612706ff8b50b590ea6add774d710fb8d8db05247f8c304b7e762b2`
- ローカルimage ID: `sha256:8dacb5cbf8a61eaeb02bc981066cc45f6cc3081a6b16e2598f086a5070008821`
- 通信禁止・read-only・capabilities除去の使い捨てコンテナで、Git `c6226ddb` のaccounts/api/scenarios/schedules/support/tableno/templates/static/docker配下およびmanage.py/requirements.lock.txtの581ファイルを照合。578件はGit blobハッシュ一致、SVG1件とvendor LICENSE2件はCRLF→LF正規化後に一致。内容差分/不足なし。Dockerfileは `.dockerignore` の除外対象で、イメージ内にないことは仕様どおり。全イメージ内ファイルや実S3静的資産の一致までは証明しない。
- Docker Scout 1.24.0、専用キャッシュで全パッケージ種別を監査。268パッケージをindexingし、脆弱な20パッケージに71指摘、終了1。内訳はCRITICAL 1 / HIGH 12 / MEDIUM 15 / LOW 43。
- Debian指摘53件（HIGH 5 / MEDIUM 5 / LOW 43）、Python指摘18件（CRITICAL 1 / HIGH 7 / MEDIUM 10）。9月22日のOSのみの36件とは対象・配布物・監査日時が違う。
- OS側のHIGHにはgcc-14由来2件、pcre2、openssl、zlibがある。pcre2は `10.46-1~deb13u3`、opensslは `3.5.7-1~deb13u3` が修正版として報告されている。gcc-14というソースパッケージ名からコンパイラー実行ファイルの存在や攻撃到達性は断定しない。その他は適用性・修正版の確認が残る。
- アーカイブ削除時のfile-in-use警告があったがSARIF生成は完了。キャッシュは保持し強制削除しない。

監査ファイルはGit管理外に保持:

| ファイル | SHA-256 |
| --- | --- |
| `C:/tmp/runtime-os-c6226ddb-20261002.sarif.json` | `ac9b94ef74dcbef213717da07e22dc9a8ceaabee394240352208c3b7e0eeaca9` |
| `C:/tmp/pip-audit-release-20261002.json` | `98212084fdfe5c379043472d555cd9612228ddb45a1c90a3bd366d0a50c8c3bc` |

## 残条件・復旧

Pythonロック更新はAWSへ未反映。mainとの差分に画像ギャラリーの2コミットがあるため、次回配布候補ではそれらを保持して統合し、実イメージを再構築・再監査する。今回のPython監査0件はOS監査合格を意味しない。旧ロックへrevertすれば元の依存へ戻せるが、既知指摘を再導入するため安全な復旧完了とは扱わない。

共有DB0065〜0067の9月25日の適用ログは検索結果なしだった。CloudWatchの保持期間は3日、ECS Execは無効であり、今回の読み取りでは適用済み/未適用を判断できない。未確認のまま再適用したり、Execを有効化したりしない。正式公開No-Goを維持する。
