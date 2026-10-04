# CCFOLIA出力JSONの版情報保持

## 修正・境界

main 8567f49fを含む作業ブランチで、7版のサーバー出力JSONとブラウザコピーに版情報がないことを確認した。取り込みAPIと画面には既に版情報の判定があるが、未指定時は6版として扱う。自分の7版JSONを未変更で再取り込みする回帰テストで、両出力経路とも7版が6版になる失敗を再現した。

`CharacterExportManager.export_ccfolia_format`と`CCFOLIACharacterCopy.buildCharacterClipboard`のトップレベルへ`edition`を追加した。サーバーはレジストリの版、ブラウザは既存の版別分岐に合わせた6th/7thを出力する。読み取り権限・無料インポート・版情報のない従来JSONの6版既定値・明示的な版選択は維持し、能力値の大きさやコマンドから版を推測しない。SANの現在値/最大値の出力規則と、公式形式のkind/dataは変更しない。

[公式Clipboard API](https://docs.ccfolia.com/developer-api/clipboard-api)はkind/data形式を定義する。editionはタブレノ側の追加メタデータであり、CCFOLIAによる保持や追加キーを含む新JSONの実ルーム取り込みは今回未確認。CCFOLIAからコピーしたJSONで版情報がなければ画面で7版を選ぶ必要がある。実ルーム往復の全体合格へ拡張しない。

## 検証結果

- RED: 新規3テスト中、サーバー/ブラウザ出力の7版サブテスト2件で6th≠7thの失敗。6版・従来JSONは成功。初回は継承されたENV_FILEの不在でセットアップ失敗したため、専用の仮設定・メモリーDBへ訂正後のREDと区別した。
- GREEN/回帰: 隔離SQLiteで出力・6版API・無料課金ライフサイクルの関連41テスト成功（16.814秒、終了0）。新規3テストの最終再実行も成功。6版/7版の8能力値、HP/MP、現在SAN、目星、7版幸運55/70、所有者、無料利用を照合。ブラウザの版未指定と従来JSONも検証した。
- Linux確認: 稼働版と同じ未変更イメージ`tableno:favicon-8567f49f`（ID `sha256:9c829979f8a69e075b61f7769c3b26d7a4fa003316c47d07e1982f7d7b94f4ad`）にモデル/新規テストと隔離設定だけをread-onlyで重ね、通信禁止・512 MiB上限の使い捨てコンテナでサーバー往復と従来JSONの2テスト成功（0.203秒、終了0）。版別サブテストを含む。初回ENV_FILE不在は設定の指定で修正した。イメージ本体は未変更で、候補の通常イメージ構築・Node検証・全配布物一致の証明ではない。
- 新規テストは63実行文・10分岐すべて実行、100%。モデル全体の100%を意味しない。追加したモデル辞書の文は実行済み。Node V8の新しい版選択式は7th/6th両分岐を実行（2/2）。式の期待値もJSONと保存値で検査した。
- ブラウザ: Chromium/Firefox/WebKit各4件、計12件成功、64.726秒、skip/retry/flaky/unexpected各0。通常登録の無料ユーザーで、6版/7版×サーバー出力/実コピーボタン操作からJSON貼り付け、版の自動選択、POST201、新しい保存レコードのGET、版別表示と7版幸運70を確認。pageerrorは0。クリップボードのwriteTextだけは試験用の受け取り先に置き換え、OSクリップボード権限・実CCFOLIAの貼り付け成功とはしない。
- 初回ブラウザ試験は2成功/10失敗。テスト側の操作メニュー未展開、存在しない7版専用詳細URL、遷移後の応答本文取得が原因。操作メニューと共通詳細経路へ訂正後は8成功/4失敗で、Chromiumの遷移時の応答本文消失が残った。最終版はPOST201と遷移後の新規IDを確認して保存済みAPIを独立GETする。保存値・版・画面表示の判定を省略せず、初回/途中結果も別ファイルで保持した。
- ローカルのPlaywrightは既存1.53.1、Node22.17.0。リポジトリ固定のPlaywright1.63.0を使う後続CIとは区別する。Pythonは3.11.1、Django5.2.17。新候補の全体CI・新規通常配布物・AWS反映は未完了。
- Black/isort/Flake8、JavaScript構文、差分検査は成功。変更Python2ファイルへのBanditは指摘0・解析エラー0・終了0。新規表示文言はなく、既存日本語の「その他の操作」「出力」「版」等を確認。テスト用Node起動の個別nosecは固定リポジトリスクリプト・固定argv・shellなしの既存方式に限定する。

## 証跡・影響

作業用の`C:/tmp/iaia-ccfolia-roundtrip-20261004/`に隔離設定・DB・検証レポートを保持。メモリー試験DBは終了時破棄し、画面試験のDBもこの専用ディレクトリだけを使う。外部メールはlocmem、Checkout/課金メールは無効で、実Stripe・実Google等は使っていない。

| 証跡 | SHA-256 |
| --- | --- |
| `results-final.json` | `dc777925f3e928b20042545c26541206873c26c54b5a371a16b4840295dccbc7` |
| `coverage.json` | `a4995428761e5c27acda3bfa21e9b3ef8f78411d8273bdfcc73627d37b1d7cc9` |
| `bandit.json` | `84860816a1ed4f7e26a01c3f85c68145d5e6bbf62e801e079185860a4cf0750b` |
| `check_changed_expression_coverage.py` | `15b5ebdb131b19bb5728623851623ceee089e60e6638c095a69414f7a6ab58e4` |

実ルームはChromeに接続先がなく、operate-cocofoliaスキルの外部作用の境界に従い、指定テストルームと合成駒・画像・ダイス送信の承認を確認中。画像・ダイス・受け取り側での逆方向取り込み・ICS購読は未検証。画像自動転送の[既存制限](CCFOLIA_IMAGE_COMPATIBILITY_2026-09-08.md)も維持する。

アプリ変更は作業ブランチだけで、main・AWS・共有DB・Secrets/IAM・実データ・課金・容量・通知は変更していない。DBスキーマ変更なし。復旧は本変更をrevertでき、保存済みキャラクターを削除・変更しない。[正式公開No-Go](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)は維持する。
