# 確認ダイアログの選択保持と終了処理（2026-10-04）

## 対象と再現

先行 `ebe0bec3` / アプリ候補 `cea7e76b` を基準に、共通 `ARKHAM.confirm` を専用ブランチで検証した。[先行CI失敗の記録](RECONCILE_RUNTIME_CANDIDATE_2026-10-04.md)ではWebKitのnewPageが23.740秒を要した。今回の単独試験で見つかった不具合を、あのCI失敗の原因と断定しない。

実際の同梱Bootstrap5.3.0とarkham.jsをブラウザーへ読み込み、アプリを修正する前に以下を再現した。

- 通常の確認でも、Promiseが背景・modal・スクロール制御の後片付け前にtrueを返す。
- 表示アニメーション中のhideはBootstrapに無視される。先に押したキャンセルが失われ、直後の確認がtrueとして採用され、modal/背景が残る。
- Bootstrapなしの経路はshowを持たないオブジェクトへshow()を呼び、`modal.show is not a function` で拒否される。

初回REDは4 passed/4 failed、最大失敗数4で残り7件未実施。表示中操作の別REDは2 failed、最大失敗数2で残り3件未実施。停止したREDを全件実施とは扱わない。

## 修正と自己レビュー

最初の選択を一度だけ保持し、表示中ならshown.bs.modalで閉じる。実行/キャンセル/閉じる/Escape/背景クリックを同じ選択処理へ通す。アニメーションは維持し、制限時間・CI再試行・failOnFlakyTestsは変更しない。

hidden.bs.modalでBootstrap instanceをdisposeし、modalを取り除いた後で結果を返す。外部から閉じられた場合はfalse。Bootstrapなしにもshowを用意し、背景・スクロール制御・表示/終了イベントを一貫させた。既存呼出側の確認文・ボタン文言とboolean契約は維持する。

初回実装のstrict directive位置を構文検査で検出し、進行中試験を停止して修正した。修正後node --checkは成功。自己レビューではダイアログ内から外へドラッグした場合までキャンセルする回帰を追加試験で2件とも検出し、mousedown/clickが同じ背景面で始終した場合だけ閉じるよう修正した。最初のGREEN45件、ドラッグ追加後51件、最終57件を区別する。

今回の差分に未解消の自己レビュー指摘はない。本文は従来どおりtextContentで設定し、認可・CSRF・実削除・課金ガードのサーバー処理は変更していない。共有ヘルパーであり、退会だけでなくキャラクター・シナリオ・セッション等の確認にも影響するため、全CIの確認は引き続き必要。

## 検証結果

- 最終19シナリオ×Chromium/Firefox/WebKit = **57 passed（1.5分）**。省略/再試行0。通常の5操作、Tabの非終了、表示中の5操作と相反する二度押し、ドラッグ非終了、背景そのもののクリック、外部終了、繰り返し表示、結果確定時のmodal/背景0・scroll unlock・instance解放を確認した。
- 実退会画面の既存2シナリオ×3ブラウザー = **6 passed（1.4分）**。省略/再試行0、30秒の通常予算を維持。キャンセルはPOST0、誤パスワード拒否、正しい退会とログイン失効、past_due/revoked/active契約による退会拒否を確認した。実Stripeは呼び出していない。
- node --check static/js/arkham.js / git diff --check成功。日本語の確認タイトル/本文/キャンセルをブラウザーassertで確認した。
- ChromiumのV8カバレッジを19シナリオで別途収集（19 passed、24.569秒、skipped/unexpected/flaky0）。確認領域14関数が全て実行され、変更行の非空白1317 bytesに未実行0。各sampleの最内範囲が上位範囲を上書きする方式で集約した。これはV8範囲/変更byteの限定計測であり、全arkham.js・アプリ全体・AST statement/branchカバレッジ100%の主張ではない。
- 実Bootstrap/Tableno CSSの単独描画を1280/390pxで撮影・目視確認。日本語タイトル/本文/2ボタンがviewport内に収まり、キャンセル後の背景とscroll lockが残らず、pageerror0。これは合成背景のmodal描画で、AWS全画面/端末固有フォントの検証ではない。

ローカルサーバースキルで8010が空いていることを確認し、専用settingsとDB `C:/tmp/iaia-confirmation-20261004/browser-fixture.sqlite3` だけへ移行した。合成SECRET_KEY、ENV_FILE空、APP_ENV=local、メールlocmem/cache locmem/Celery memory、Stripeキー空/購入無効。共有DB・元checkoutのDB・Secretsを参照していない。試験後に利用者0件を読み取り確認し、今回の専用サーバーPID41864を停止、ポート非稼働を確認した。再現用の合成DB/画像/工具は一時領域に保持し、Gitへ含めない。

## 証跡と反映境界

専用証跡は `C:/tmp/iaia-confirmation-20261004`。coverage-tests.jsonはSHA-256 `cb3bad6228f85c51b09ade8c8eb73238cf87806c222018b4b6118328634f85aa`、範囲検査器check-confirm-coverage.cjsは `d8507959e48b8589e0c385efff32076ebe2d537bd4288cec2cc65dbd2f55ec97`。スクリーンショットconfirm-1280.pngは `52656588375d8fc16fbd724e7e3b763d5769ffaeffd1fe0a36909db070cce3eb`、confirm-390.pngは `466807f0eb6bbe907f19afbbfb3432a58b8018fff772bd00b6ae6a0bf631c9e7`。

今回修正後の通常Docker配布物・全CI・AWSは未検証。先行401テストや旧imageのmanifest/OS監査を今回修正後の証拠にはしない。main/ECR/ECS/共有DB/S3/CloudFront/Secrets/IAM/課金/容量/継続費用の変更は未実施。元checkoutのハンドアウト差分は保持し、固定承認案6b6c570cを拡張していない。復旧は作業ブランチ上で今回の修正コミットをrevertする方法で、他の課金/ICS/CCFOLIA修正を破棄しない。[正式公開No-Go](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。
