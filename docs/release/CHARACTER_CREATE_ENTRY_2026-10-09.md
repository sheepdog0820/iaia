# 版未指定キャラクター作成URLの復旧

## 変更・仕様

2026-10-09、基準 `ff7d49ec6c31cee247b77cb429ec90df331a665d`。
[アカウント復旧検証](ACCOUNT_RECOVERY_FLOW_2026-10-09.md)で見つけた
`/accounts/character/create/` の認証済み500を修正した。
存在しない `accounts/character_sheet.html` を復元せず、
[現行の一覧仕様](../specifications/CHARACTER_LIST_SPECIFICATION.md)とメニューに合わせて、
6版・7版の両方を選ぶ日本語画面へ接続する。

- URL名 `character_create` とログイン要件を維持する。
- 既存6版/7版の作成画面と一覧への通常リンクを使う。追加JavaScriptはない。
- GET/HEADは読み取りのみ。認証済みPOSTは405で保存しない。
- 版・編集ID・外部転送先のqueryを新しい画面に引き継がない。
  既存版別URLでの編集・シナリオ/セッション連携は変更しない。
- 旧URLを除外していた復旧テストを戻し、10非公開URLすべてを認証済み200で確認する。

## 検証

実Django Clientと使い捨てSQLiteで新規6テストを追加。
変更前はテンプレート欠落の4エラー、認証/POSTの2件成功だった。
変更後の復旧11件との局所17件は成功（9.741秒）。
作成画面静的検査・認証・production設定・法務表示・文書を含む関連194件が成功
（77.434秒、省略0）。Black整形後も局所17件が成功（10.337秒）。
最終source coverageは新規test76実行文/6分岐先、復旧test124文/8分岐先が
100%/除外0、accounts URL module28文が全実行。キャラクター機能全体の100%ではない。

永続Playwright検査を通常CIのflows配下へ追加した。
ローカルではDjango StaticLiveServerTestCaseの合成利用者・使い捨てDB/media・ランダムportで、
同じ検査をchromium/firefox/webkit × 1280/390pxの6ケース実行した。
健康確認200、未ログイン302とnext、開発ログインの実CSRF POST、両版/一覧への遷移、
キーボードEnter、戻る、reload、画面の横溢れなし、pageerror0、前後API内容不変を確認。
6成功（29.362秒、retry/skip/flaky0）、Python側でもキャラクター保存0を確認した。
新しい選択画面の390px実スクリーンショットを目視し、日本語・ボタン・余白を確認した。
API応答mockなし、外部originは遮断。実メール/Google/Stripeには接続しない。

初回はrunnerのimport順で旧 `browser_probe` を選び、意図しない復旧ブラウザー検査の
reset form待機が失敗した。この結果を今回の作成画面検証に流用しない。
専用名 `entry_browser_probe` に変更後も、Django test runner既定DEBUG=Falseにより
開発ログインが403になった。専用NodeプロセスのPID/command lineを照合して子も含め停止し、
DB/serverの通常終了を確認した。試験クラスだけDEBUG=Trueに合わせて再実行し6成功。
製品の認証・DEBUG設定、上限や合格条件は緩めていない。
最後のNodeプロセス残0を確認し、所有server/DB/mediaもrunner終了で破棄した。
既存serverや実DBは使わず、証拠は `D:/tmp/codex-character-create-entry-20261009` に保持する。
初回REDは先行 `D:/tmp/codex-account-recovery-20261009/create-entry-red.log` にある。

変更3 PythonのBlack/isort/Flake8と、URL/new testのBandit指摘0/解析エラー0を確認した。
最終文書39テストも成功（0.036秒）、変更文書と判定表の相対リンク266件に欠落なし。
日本語literalと実リンク/差分をレビューし、変更範囲に残る指摘なし。
UTF-8/LFとstaged整合の検査も9 text filesで成功した。
先行Windows Twisted import不具合は環境を変えず別課題として残す。
今回は新通常配布image/稼働AWS/実機での検証ではない。

## 残作業・承認境界・復旧

main/AWS未反映。最新SHAのCI、配布物照合と反映計画、実環境の全作成/編集/保存を継続する。
この修正だけでF04全体、OS HIGH2、Google安全性、課金/外部連携/性能/復旧等を合格にしない。
正式公開No-Goを維持する。全Google候補を今回の修正へ混ぜて配備しない。
mainマージ/AWS、共有DB・実データ、Secrets/IAM/OAuth、課金・容量・通知は変更しない。
元checkoutの13件の別作業も保持する。sourceは当該commitの通常revertで戻せる。
