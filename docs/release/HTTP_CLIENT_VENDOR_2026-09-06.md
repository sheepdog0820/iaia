# 共通HTTPクライアントの固定配信

共通テンプレートはバージョン指定なしの外部Axios CDNを同期読み込みしていた。公開候補と配信時のライブラリが一致するよう、上流のAxios 1.20.0配布物を同梱してDjango staticから読み込む。既存fetch代替処理は変更しない。取得元・配布物ハッシュ・MITライセンス・更新時の監査手順は[同梱README](../../static/vendor/axios/1.20.0/README.md)に記録した。

## 検証

- テストファーストで、共通テンプレートの固定パスとmanifestへのAxios収集を追加。変更前はテンプレートと未配置ファイルの2件で失敗。変更後は2テストと5 subtestが成功。sourceMappingURLが参照するmapも配布物のまま配置し、manifest収集は終了0。
- 一時ディレクトリでexact指定したaxios@1.20.0のlockfileを作成し、npm auditは指摘0・終了0。配布アーカイブのSHA-512とSHA-1をnpmメタデータと照合。
- Chromium/Firefox/WebKitで共通HTTPクライアント、ホーム読み込み中の操作、smokeの関連27件成功。2026-09-06T06:40:14Z開始、70.24秒、expected=27、skipped/unexpected/flaky=0、retries=0。
- HTTPクライアントのケースは外部HTTPSを遮断し、同梱版はVERSION=1.20.0、同梱配信も止めたケースはVERSIONなしの代替処理であることを確認。日本語・特殊文字・配列・日付・既存クエリーの保持を両方で検証。
- テスト用イメージtableno-browser:playwright-1.63へ今回のbase.html、同梱Axios、HTTPテスト、現行Playwright設定を読み取り専用マウント。専用空SQLiteと合成ユーザー3件を使用し、コンテナは終了後削除。
- Black/isort/flake8の対象Python検査、同梱JSの構文、差分・文字コード・日本語文書のレビューは成功。製品の表示文言や権限は変更していない。

ローカル証跡: tmp/axios-manifest-red.log、tmp/axios-manifest-green.log、tmp/axios-package-audit.json、tmp/axios-browser-probe.log、tmp/axios-browser-probe-output/results.json。全体のリモートCIはpush後に確認する。新たなブラウザケース6件により全体は180件となる。

## ホーム遷移の未解決事項との区別

先のCIで発生したFirefoxの遷移失敗については、この変更前のアプリを使い、該当操作を10回・再試行なしで実行して全件成功した（72.69秒、tmp/home-firefox-probe-output/results.json）。再現できなかったという結果であり、原因の特定・解消ではない。本変更をその不具合の修正とは扱わない。CIのfailOnFlakyTestsにより、再試行でだけ成功する場合も以後は失敗として追跡する。

## 影響と復旧

全画面のブラウザ依存と配布静的ファイルが変わる。DB・Secrets・課金・外部サービス設定・実環境への反映は行っていない。以前の配備候補0b0cea6fには今回のAxios同梱を含まない。最終配備時には新候補の通常イメージを作成し、ハッシュ付きURL・圧縮配信を含めて再検証する。

問題が出た場合はこの変更単位をrevertできるが、未固定CDN参照が戻る。原因に応じて同梱版を維持した修正を優先する。サイト全体のオフライン対応や、ほかの同梱ライブラリの安全性を保証する変更ではない。
