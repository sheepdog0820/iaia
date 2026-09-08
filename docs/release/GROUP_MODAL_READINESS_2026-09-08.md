# グループ作成後の検索入力の準備確認

2026-09-08、af39ecedの[CI](https://github.com/sheepdog0820/iaia/actions/runs/34172460104)でPlaywrightが185成功/1 flakyとなり終了1。Firefoxのgroup-management.spec.tsが、作成したグループを検索結果から見つけられず失敗した。再試行成功でCI合格にはしない。他の4ジョブは成功。

## 失敗記録

CIアーティファクト10036381639のtraceを調査。グループ作成POSTは201で成功している。検索入力の直前・操作中はbodyにmodal-openが残り、検索欄は空だった。入力直後にbodyのmodal-openは消えたが、検索値は空のままで、15秒後にも変化がなかった。グループ作成モーダル自体は既にdisplay:noneだったため、モーダルの非表示だけでは開閉処理の完了を判定できない。

モーダル終了処理と検索入力が重なった証拠であり、入力を失わせた瞬間のfocusイベントまで記録したものではない。バックエンドの作成失敗として扱わない。

ローカル証跡はtmp/poll-ci-af39eced.zip、tmp/group-ci-failure-trace.zip、tmp/inspect-group-click-snapshots.py。既存のスナップショット差分参照を復元して状態を確認した。ZIP内のログ・認証情報を公開文書に転記しない。

## テストの修正と確認

- モーダルを開いた後、表示だけでなくモーダルへのフォーカス移動を待ってから入力する。
- 作成POSTの201を明示的に確認する。
- 閉じたモーダルが非表示となり、起動ボタンへフォーカスが戻った後に検索する。
- 検索入力値と、作成したグループのカード表示の両方を確認する。
- POST後に登録していた一覧GET待機は削除。保存・モーダル終了・入力・検索結果という利用者の操作結果を待つ。固定sleep・forceクリック・試験の再試行・失敗の許容は追加しない。

隔離SQLiteとPlaywright 1.63の既存ブラウザ検証イメージで、Chromium/Firefox/WebKit各5回、合計15件が再試行なしで成功（73.840秒）。skip/flakyは0。現行グループテンプレートと共通CSS・対象テストを重ねた対象検証であり、現行候補全体の検証ではない。tmp/run-group-modal-validation.ps1、tmp/group-modal-validation.log、tmp/group-modal-validation-output/results.jsonを参照。専用コンテナは終了時に削除済み。

変更はテストと本記録のみ。アプリ・DBスキーマ・実データ・Secrets・料金は変更していない。差分と文字コード、テスト手順をレビューし、追加の指摘なし。ユーザー向けUI文言の変更はない。最新候補全体のCI成功は別途確認する。
