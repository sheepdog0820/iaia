# 統計画面の動的HTML表示保護（2026-09-22）

## 結論

Tindalos Metrics画面で、統計APIから返るグループ名、上位GM名、セッション名、グループ名、GM名、ランキング表示名を未エスケープのまま`innerHTML`へ挿入していた。保存済み名称にHTMLイベント属性が含まれる場合、統計を閲覧した利用者のブラウザで要素とイベントが生成され得るため、API由来の表示値を共通関数でHTMLエスケープするよう修正した。

この修正はローカルで検証済みだが、AWSへは未反映である。統計画面以外の全動的表示経路を監査済みという意味ではなく、正式公開No-Goを維持する。

## TDD再現

- 静的回帰テストを先に追加し、エスケープ関数と6種類の名前表示が未実装のためREDになることを確認した。
- Playwrightでは統計APIを差し替え、`<img src=x onerror="window.__statisticsXss += 1">表示名`を各名称へ返した。
- 修正前は`img`要素が生成され、Djangoログにも統計画面配下の`/x`取得が記録された。攻撃文字列が文字として残ることを期待したアサーションは失敗した。

## 実装

- 実装コミット: `c72ca1dc` (`fix: escape dynamic statistics labels`)
- DOMの`textContent`を使う`escapeStatisticsText`を追加した。
- 年間集計、グループ統計、最近のセッション、ランキングで`innerHTML`へ入るAPI値をエスケープした。
- CSSクラスは既存どおり、セッション役割の固定分岐とランキング順位の数値判定からだけ生成する。
- 表示文言、API形式、DBスキーマ、認証・認可は変更していない。

## ローカル検証

- 静的セキュリティ回帰1件成功。
- 悪意あるAPI値が文字として表示され、対象領域に`img`がなく、イベント実行回数が0であることをChromium、Firefox、WebKitの3件で確認した。
- `accounts.test_statistics`、`tests.unit.test_text_quality`など統計・文字品質の関連24件が成功した。
- `tests.system.test_additional_features.StatisticsFunctionTestCase`の4件が成功した。
- ブラウザ試験専用SQLiteは事前に利用者0件を確認し、CIと同じ属性の合成admin 1件だけを作成した。試験後は`finally`で対象を削除し、利用者0件を再確認した。

## 影響と残条件

- 共有DB、実利用者データ、AWS、Secrets、権限、料金への変更はない。
- 統計画面に保存済みの悪意ある値があっても、今回修正した領域では文字として表示される。
- 他テンプレートの動的HTML表示、Chart.js内部の描画、実AWS稼働版は別の監査・反映対象である。
