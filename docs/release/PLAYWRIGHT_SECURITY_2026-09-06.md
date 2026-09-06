# Playwright依存関係の監査と更新

配備用候補0b0cea6fのGitHub Actionsは全5ジョブ成功したが、ブラウザジョブのnpm ciログにHigh 2件の警告があった。Pythonのpip-audit成功はnpm依存の安全性を示さないため、npm auditで再確認した。

旧ロックは@playwright/test/playwright/playwright-core 1.53.1。npm auditはPlaywrightのCVE-2025-59288を報告し、直接依存への波及を含めHigh 2件、終了1だった。同じ脆弱性の依存経路2件であり、独立した脆弱性2種類とは数えない。

[Microsoftの修正](https://github.com/microsoft/playwright/pull/37532)は一部のブラウザ導入スクリプトから証明書検証を無効にするcurl -kを除去している。[監査情報](https://github.com/advisories/GHSA-7mvr-c777-76hp)で対象は1.55.1未満、具体例はmacOSのChrome/Edge導入スクリプトと確認した。今回のCIはLinuxで標準の3ブラウザを導入しており、その実行が侵害された証拠ではない。テスト用依存であり、通常のDjango本番イメージはnpmパッケージをインストールしていない。

2026-09-06のnpm registryと[Microsoftのリリース](https://github.com/microsoft/playwright/releases/tag/v1.63.0)で現行安定版1.63.0を確認し、exact指定とlockfileを更新した。必要なNode.jsを20以上と明示し、開発ガイドも更新した。CIの既存ブラウザジョブでnpm ciの後にnpm auditを実行し、指摘があればジョブを失敗させる。重大度の除外や終了コードの無視は行わない。

更新後のホスト監査と、Node 20.20.2の隔離Docker内でのnpm ci/npm auditは指摘0・終了0。関連するCI設定テスト22件成功。ブラウザのバージョンも変わるため、3d8845cfのgit archiveへ更新したpackage.json/package-lock.json/CIを重ねた専用イメージで、174ケースを再試行なし・既定タイムアウトで実行する。DBは空の専用SQLite、アカウントはCIと同じ合成ユーザー3件。通常利用者の登録フローも既存ケースに含む。

アプリ機能・DBスキーマ・実環境・課金設定は変更しない。承認待ちDB検査のイメージ0b0cea6fとタスクJSONも変更しない。更新前へのrevertは技術的に可能だが既知の監査指摘が戻るため、ブラウザ互換性の不具合は修正済みバージョンを維持して是正する。

## 更新後のブラウザ検証結果

2026-09-06T06:04:56Z開始、721.14秒、終了0。25フローファイル・Chromium/Firefox/WebKit各58件、合計174件成功。結果JSONのexpected=174、unexpected/skipped/flaky=0、全resultがpassed、retry合計0を確認した。テストの再試行やタイムアウト緩和、アプリの権限変更は行っていない。

証跡はtmp/playwright-1.63-build.log、tmp/playwright-1.63-e2e.log、tmp/playwright-1.63-output/results.json。専用コンテナは終了・削除済み。ローカルのnode_modulesもnpm lsで1.63.0と一致した。設定・ロック・文書の7ファイルはUTF-8/LF・差分・リンク・日本語文言をレビューし、追加指摘なし。通常アプリのPythonコードは本変更で変わらないため、バックエンド全体の重複ローカル実行はせず、関連設定22件とブラウザ全体で検証した。更新後のリモートCIはpush後に別途確認する。

## リモートCIで判明した再試行合格の問題

05cc979bの[CI実行34016080319](https://github.com/sheepdog0820/iaia/actions/runs/34016080319)は全5ジョブがsuccess。npm auditは指摘0、PostgreSQLは223件・subtest 10件成功。しかしブラウザの詳細ログは173 passed / 1 flakyであり、ローカルの174件・再試行なしという結果と区別する。

Firefoxのsmoke「home quick actions render and navigate」で、セッション参加リンクのclick後もホームURLのまま15秒経過し、初回が失敗した。再試行では成功したため従来設定はジョブをsuccessにした。失敗時だけのartifactアップロードも動かず、この実行のartifact一覧は空だった。クリックの失敗原因はまだ特定できていない。待ち時間や再試行回数の追加で解決した扱いにしない。

CI設定に `failOnFlakyTests: !!process.env.CI` を追加する。診断のための既存の再試行2回は維持するが、初回失敗から回復したケースがあればCIを失敗させ、既存のfailure条件によるトレース等の保存へつなげる。

本番DBやブラウザを使わない一時的な試験ケースで、実際の設定をimportし、初回は失敗・再試行時に成功する挙動を実行した。変更前は1 flaky・終了0、変更後は1 flaky・終了1。安定して成功する対照ケースは終了0。実E2Eの収集は従来どおり25ファイル174件。証跡はtmp/ci-flaky-gate-before.log、tmp/ci-flaky-gate-after.log、tmp/ci-flaky-gate-stable.log、tmp/ci-flaky-gate-discovery.log。

変更は合格判定のみで、ホーム画面の修正完了を意味しない。次のCIと再現検証で遷移失敗を追跡する。アプリ・DB・権限・実環境には変更なし。差分・UTF-8/LF・日本語文書をレビューした。
