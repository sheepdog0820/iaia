# Google連携の期限不明トークン更新

対象実装コミット: `78f84feeba354274b81722992d0ab71acd0abe76`。

## 修正内容

Google Calendar・Sheetsのバックグラウンド処理で使う`SocialToken.expires_at`が未設定の場合、従来はアクセストークンを期限なしとしてそのまま使用していた。[Google公式のWeb server OAuth](https://developers.google.com/identity/protocols/oauth2/web-server)ではアクセストークン応答に有効期間があり、オフライン処理はrefresh tokenで更新する前提であるため、期限を確認できない資格情報を有効扱いしないよう修正した。

- `expires_at`が現在から2分より後なら、保存済みアクセストークンを継続使用する。
- 期限切れ、期限間近、または期限不明なら、保存済みrefresh tokenとOAuth client設定で更新する。
- 更新応答に新しいrefresh tokenがない場合は既存値を保持する。
- 更新後のexpiryがnaive UTCならaware UTCへ正規化して保存する。
- アクセストークン、refresh token、client設定が不足する場合は、ジョブ画面に表示され得る案内を日本語で固定し、Google再連携を求める。
- Googleの認可更新失敗時は従来どおり外部エラー詳細を表示せず、固定の日本語案内でジョブを失敗終了する。

DBマイグレーション、OAuth scope、Secrets、権限、料金、外部送信先は変更していない。

## TDDと検証

期限不明の資格情報が更新されるテストを先に追加し、旧実装が保存済みアクセストークンを返して失敗することを確認した。実装後、次を確認した。

- Google連携の対象クラス16件成功。
- Calendar/Sheets配送、ジョブ再試行、OAuthコールバック、Google ID固定・競合を含む関連75件成功、Google browser依存の3件skip。
- `schedules/google_tokens.py` は35実行行すべてを通過し、行カバレッジ100%。
- Black、isort、flake8、Bandit、差分・UTF-8/LF検査が成功。
- 新規・変更した利用者向けエラーは日本語。秘密値や外部エラー詳細を表示しない。

テストはSQLiteとGoogle応答のmockを使用した。実Google API、実refresh token、AWS worker、失効・取消後の実応答は未検証であり、I01/I04/I05と正式公開No-Goを維持する。共有環境への反映、Secrets変更、Google Cloud設定・公開OAuth審査は行っていない。
