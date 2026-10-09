# 退会後のホーム通知と認証終了の確認

## 対象・原因・変更範囲

2026-10-09、`codex/main-account-recovery-20261009` の `b790f758` を起点に、
[main基準の復旧・作成入口候補](MAIN_ACCOUNT_RECOVERY_CANDIDATE_2026-10-09.md)の追加確認を行った。
同SHAの[CI](https://github.com/sheepdog0820/iaia/actions/runs/37871435925)は
5ジョブ成功、Playwrightが6件失敗/222件成功（16.3分）。失敗はログアウト・退会の2ケース×3ブラウザーで、
ログイン画面を期待する古い検査と、業務viewの公開homeへのredirectが不一致だった。
共通TemplateViewへの認証波及を修正した結果、以前の暗黙のlogin redirectがなくなった。

業務viewと設定をsource reviewし、ログアウト・退会後はhome、非公開dashboardはlogin要求という
現行仕様を維持した。テストをhomeへ合わせるだけでなく、保護画面の拒否、合成メールアドレス/passwordでの実フォーム再ログイン、
削除済み資格情報の拒否を検査する。退会キャンセル/誤password/非終了Stripe契約の保護は緩めない。

遷移検査修正後のローカル12ケースでは9件成功/3件失敗となり、追加した日本語成功通知の表示検査が失敗した。
アカウントは削除されていたが、viewが出したmessagesをhome/baseのどちらも描画していなかった。
これをテストから削除せず、homeの既存表示の手前だけに通知表示を追加した。

- success/info/warning/errorを既存Bootstrap alertで表示し、errorはdangerへ対応、未知のlevel tagはinfoへ戻す。
- 通知がない場合は空枠を作らず、匿名/認証済みの両方で通知を表示する。
- 本文は通常のtemplate autoescapeを維持し、HTMLのsafe化や新JavaScriptは追加しない。
- 日本語「閉じる」のbuttonと既存Bootstrap dismiss機能を使用する。
- 実画像レビューで明るい文字と本文/閉じるボタンの近接を発見し、通知だけに
  `text-reset`/`pe-5`を追加。閉じる記号も継承色を使い、ライト/ダークの本文色を維持する。

製品差分はhome templateだけ。DB schema/認証・削除・課金の業務code/settings/依存lock/
static/CI/インフラは変更しない。永続E2E2 files、新規integration test、検証記録を追加・更新する。

## TDD・ローカル検証

home表示の新規7テストは修正前9 failure（level subcaseを含む）/error0。
通知追加後7件成功（1.363秒）。読みやすさの回帰を加えた8件は補正前1 failure、
補正後8件成功（1.392秒）。本文spanの追加後も、最終関連回帰に含めて成功した。
新規Python testの60実行文/2分岐先は100%/除外0。
これはtest moduleの実行率で、template全体やアプリ全体の100%を意味しない。
テンプレートの有無、level mapping、複数通知、本文escape、認証済み表示は実renderで検査する。
実退会POST後の削除、session終了、dashboard拒否、通知の消費後の非再表示も確認する。

認証・ログイン障害・復旧・作成入口・production設定・法務表示・文書を含む
最終関連194件が成功（72.280秒、省略0）。最終 `green-stable` は
Chromium/Firefox/WebKitで4ケースずつ、12ケース成功（105.517秒、skip/retry/flaky0）。
Django runnerはDB後検査を含め成功、終了0（111.652秒）。
変更した認証/退会の2ケース×3ブラウザーはpageerror0。

実signup/CSRF form、キャンセルPOST0/誤password POST1/退会成功POST2、
公開homeの日本語通知、非公開dashboardの拒否、削除済み資格情報の拒否を検査した。
非終了Stripe契約のpast_due/revoked/activeでは削除拒否とログイン維持を保持する。
既存OAuth状態表示も含めた2 E2E files全体の検査で、実OAuthやStripe APIの試験ではない。

通知は3ブラウザー×1280/390px×ライト/ダークの12条件で測定した。
透明背景を親要素の背景へ合成した本文コントラストはライト12.769/ダーク14.752で、
4.5以上を確認。本文rangeと閉じるbuttonの左右座標は重ならず、documentの横溢れ0。
390px/ダークでfocus/Enterによるdismiss、reload後の通知非再表示を確認した。
12枚の通知画像を保存し、代表のPCとスマートフォン/両テーマを目視確認した。
最終文書39件も成功。

## 使い捨て環境と失敗記録

ローカルサーバースキルの標準起動は既存DBとenv fileを読むため使用せず、
Django所有のStaticLiveServerTestCase、一時SQLite file、一時media、locmem mailで実施する。
ENV_FILEは空、APP_ENV=local、課金開始/配送は無効、Stripe/AWSの実資格情報は読み込まない。
既存の契約保護E2Eのmanage.py subprocessも、明示した一時settings moduleと同じ一時DBだけを使う。
元checkoutと作業worktreeの実DBは試験対象にしない。

最初のRED fixtureはDEBUG条件でbrowser開始前に失敗し、試験classだけDEBUG=Trueにして再実行した。
そのRED browser6件は遷移不一致で失敗した。初回GREEN12件のうち退会通知3件が失敗した。
通知追加後の `green-final` はPlaywright JSON上12件成功/skip・flaky0だが、
runnerが結果stdoutをcp932で出力できず終了1。DB後検査まで未到達であり、最終合格に使わない。
fixtureのstdout/stderrだけUTF-8へ明示し、読みやすさ補正後に別evidence名で再実行する。
製品や共有Python環境の文字コード設定を変更していない。各失敗の生ログ/画像/JSONは保持する。

`green-reviewed` は9件成功/3件失敗。閉じる記号をbutton内に追加したため、
alert全体の文字が通知本文と完全一致せず、通知の可視性検査が失敗した。
本文を専用spanへ分離し、完全一致検査を維持する。コントラスト/重なりの検査も
その本文範囲を測るようにし、空のtext node測定で成功扱いしない。

`green-complete` は12ケース成功/skip・retry・flaky0、Django runnerも終了0（107.722秒）。
ただし実画像レビューでテーマ切替途中の画像を発見したため、E2Eに既存ライト/ダークの
body背景色と本文色の切替完了を待つ検査を追加し、別名 `green-stable` で最終確認する。
試験用CSSの追加・アニメーション停止・固定sleepで実表示を置き換えていない。
`green-stable` の最終成功は上記のとおりで、途中の失敗/途中色の画像を破棄・上書きしていない。

一時DBの後検査では通常signup3名、削除対象残0/契約保護fixture残0。
終了時にDjango所有server/一時DB/mediaを破棄し、fixture用ディレクトリを残さない。
元checkoutと作業worktreeの既存DB SHA-256を前後照合し、差0。
Black/isort/Flake8と新規testのBanditは成功。日本語UI、通常escape、認証/契約保護と
staged差分を自己レビューし、今回範囲に残る指摘なし。UTF-8/LFは7 text filesで成功。

生証拠: `D:/tmp/codex-auth-exit-browser-20261009` と
`D:/tmp/codex-main-account-recovery-20261009`。

## 反映境界と残タスク

main/ECR/AWS/共有DB・実ユーザー/Secrets/IAM/OAuth/課金・容量/外部通知は変更していない。
先行[通常配布物の検証](MAIN_ACCOUNT_RECOVERY_RUNTIME_2026-10-09.md)は `dbe8fca1` の証拠であり、
今回のhome修正を含まない。後続候補のCI・通常配布物・OS監査・承認後のAWS反映は別途必要。
HIGH2を含むOS指摘を解消したとは扱わず、[正式公開の判定](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)はNo-Go。
元checkoutの13件の別作業を保持する。共有環境の復旧先は実行時に再確認し、
先行限定案の定義54を使う想定だが、既存favicon承認を今回へ拡張しない。
