# ICS出力の整合性と購読認可の再検証（2026-10-28）

## 対象と依存関係

正式公開はNo-Goを維持する。main `e914b325` を基点とする[SDK保護のDraft PR #8](https://github.com/sheepdog0820/iaia/pull/8)の終点 `35e259855792d7358ebaccc26716030de99072ee` から、別ブランチ `codex/ics-release-followups-20261028` でICSの既知不具合を分離した。PR #8の承認を得る前にmainへ混ぜない。ICSのPRは当初PR #8の作業ブランチをbaseとし、差分をICSに限定する。PR #8のマージ後にmainへ付け替え、最終headのCI・差分・承認を改めて照合する。

元の修正は `f158a20ca066597936a17970451ac03ae5d3d30e` と `6b6c570c9df641244894930b497452491811aab2`。製品ファイルと回帰テストだけを適用し、過去の配布物・実サービス側の成功記録は今回の証拠にしない。

## 利用者への影響

- ログインして取得するICSファイルの名前・場所・説明・アラーム内の文字列をエスケープする。改行による偽のVEVENT/プロパティの混入を防ぎ、カンマ・セミコロン・バックスラッシュを元の文字列として保持する。
- 日本語や絵文字のUTF-8を途中で分割せず75 octets以内に折り返し、末尾までCRLFを付ける。購読フィードの既存ヘルパーを共有し、取得方法による差をなくす。[RFC 5545のcontent line/text規則](https://www.rfc-editor.org/rfc/rfc5545)を参照する。
- ファイルの開始・終了日時をUTCへ変換しZを付け、受け取り側のローカル時刻として誤解されないようにする。
- 購読URLはtoken所有者が有効な場合だけ出力する。停止中は匿名・他の利用者・管理者でアクセスしてもGET/HEADとも404となり、本文を生成しない。トークン自体は削除/変更せず、アカウント再有効化後は既存URLを利用できる。
- 購読ごとの参加・グループ管理権限の再確認、退会時の削除、トークン再発行による旧URL失効、`private, no-store` を維持する。

外部カレンダーが既に取得して保存した予定を、停止後に受信側から削除する仕組みは追加していない。Google Calendar同期やSheetsの配送基盤も変更しない。

## 隔離検証

現在の固定依存Python 3.11.18 / Django 5.2.17を使う補助Dockerイメージで、ソースは読み取り専用・外部通信なし。DBは使い捨てのメモリーSQLite、利用者・予定・購読トークンは全て合成データである。

1. 修正前: pytestで26失敗・9成功・1 collection error（失敗数にはsubtest失敗を含む）。空/長い日本語の出力、UTC識別子、改行混入、停止中のGET/HEAD、再有効化の前提で不足を確認した。新ヘルパー未実装のimport失敗も含む。
2. 修正後の新規3ファイル: 17成功・21 subtests成功、省略なし。
3. 既存の購読文字コード・カレンダーAPI・外部連携を含む6ファイル: **54成功・32 subtests成功、省略なし**。対象外の非公開予定が含まれないこと、参加解除や管理権限変更、token失効、利用者削除を含む。
4. 新ヘルパーは17実行文・4分岐とも100%。変更実行文はヘルパー17、integration_views 3、views 13の **33/33行**を通過。大きなviewモジュール全体や全製品が100%網羅という主張ではない。
5. 変更Python 6ファイルのBlack・isort・Flake8・Bandit（medium以上）と差分レビューを完了。既存の表示文言は維持し、技術文字列以外の英語UIは追加していない。

生ログは専用worktreeのGit管理外 `tmp/ics-main-red.log`、`tmp/ics-main-green.log`、`tmp/ics-main-regression-coverage.log`、`tmp/ics-coverage/coverage.json`、`tmp/ics-changed-coverage.json` に保持する。最終headのCIは[Draft PR #9](https://github.com/sheepdog0820/iaia/pull/9/checks)で照合し、他のSHAの成功を代用しない。

## 通常配布物

製品修正 `744eeb889b5bc204db7dfbe944186f5a6a95a97c` の `git archive` を通常Dockerfileで構築した。ローカルタグは `tableno:release-candidate-744eeb88`、イメージIDは `sha256:59fa4fcffa20ff601f46a80812719d075b70b62a545157d7f4402469344bc339`。ECRへのpushは未実施。

今回の製品ファイル・テスト・固定依存・SDK保護・entrypoint等14ファイルのGit blobとのSHA-256一致を確認。通常イメージ内のコードだけを使い、pip/pytest追加なし、UID10001・読み取り専用・外部通信なしで上記6ファイルの **Django runnerの54テストが成功**した。メモリーSQLite、locmem cache/mail、使い捨て保存先を指定する合成設定ファイルだけを読み取り専用で渡した。製品ソースのbind mount、実DB、外部受信側への送信はない。Webサービス起動や実ブラウザーでの購読成功の代わりにはしない。

構築・実行・ソース照合の証跡は `tmp/ics-normal-image-build.log`、`tmp/ics-normal-runtime-tests.log`、`tmp/ics-normal-source-manifest.json`。以後の検証資料だけのコミットは、この製品修正SHAと区別する。

## 残作業と承認

ICSの実購読先への取り込み・更新・失効の確認、実AWS反映は未実施であり、受け入れ条件I07全体は未完了。今回のAPI応答試験をGoogle/Apple等での実購読成功に読み替えない。

DB/移行ファイル、依存ロック、Secrets/IAM/OAuth、常設資源・費用、外部への送信、実データ変更はない。mainへのマージと共有環境への反映は別の承認対象。取り消す場合はrevert PRで戻せるが、停止中の購読や改行混入の問題が再発するため、単に保護を戻して公開可とはしない。
