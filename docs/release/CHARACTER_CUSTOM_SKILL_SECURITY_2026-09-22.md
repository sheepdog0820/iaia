# カスタム技能名の動的HTML保護（2026-09-22）

## 結論

クトゥルフ神話TRPG 6版・7版のキャラクター作成画面で、カスタム技能名をHTML文字列へ直接埋め込む経路を修正した。技能名にタグ、引用符、イベント属性を含む文字列が渡されても、DOM要素やイベントを生成せず、入力欄の文字列として保持する。

実装コミットは`4cf3ad03`（`fix: escape custom skill names in character forms`）。CI安定化を含む検証済みアプリ候補は`1b051dba`。正式公開判定は引き続きNo-Goである。

## 実装内容

- `&`、`<`、`>`、`"`、`'`をHTMLエンティティへ変換する版別の共通処理を追加した。
- カスタム技能名の`value`、通常技能ラベルの本文と`title`、初期値・職業・趣味・その他入力の`aria-label`へ同じ安全化済み文字列を使用する。
- 技能名の表示値はブラウザによるHTML解析後に元の文字列へ戻るため、利用者が入力した技能名を改変しない。
- 技能キーは内部生成値、初期値は数値または固定式であり、今回の外部入力境界とは分離されている。

## 検証

- `node --check`で6版・7版JavaScriptの構文を確認した。
- `tests.unit.test_character_skill_ui_security`、既存の`tests.unit.test_character_create_ui_static`、`accounts.test_custom_skill_addition`の合計62件がSQLiteで成功した。
- 悪意ある文字列`"><img src=x onerror="window.__customSkillXss += 1">技能名`を使い、Chromium・Firefox・WebKitで6版・7版の計6件が成功した。
- 3ブラウザすべてで`img[src="x"]`が0件、イベント実行カウンターが0、カスタム技能名の入力値が元文字列と一致した。
- Black、isort、`git diff --check`、ステージ済みファイルのUTF-8/LF・BOM・置換文字・文字化け検査が成功した。
- 新しい利用者向け固定文言はなく、既存の日本語ラベルとアクセシビリティ文言を維持した。

## CIの完了と安定化

- 候補`caf4a9d1`の[CI](https://github.com/sheepdog0820/iaia/actions/runs/35693457184)は5/6ジョブ成功。Playwrightは既存の通常利用者フロー1件がWebKitで初回のみ401となり、再試行で200件すべては通過したが、`failOnFlakyTests`により正しく失敗扱いとなった。
- 該当フローの保存確認を別APIRequestContextからブラウザーと同じCookieを使うページ内`fetch`へ切り替え、複合フローに`test.slow()`を設定した。ローカルでChromium・Firefox・WebKitの3件とWebKit反復3件がすべて成功した。
- 安定化後候補`1b051dba`の[CI #334](https://github.com/sheepdog0820/iaia/actions/runs/35695689750)は全6ジョブが成功した。

ブラウザ検証はローカルSQLiteと開発用ログインを使用した。実ユーザーデータ、共有DB、AWS、外部サービスは使用していない。

## 未検証・境界

- 保存済みの悪意ある技能名を実AWSへ投入する試験は行っていない。
- キャラクター画面以外を含む全動的HTML経路の監査完了を意味しない。
- mainマージ、共有DB変更、AWS反映、Secrets・権限・課金設定変更は行っていない。

## 通常配布イメージの確認

2026-09-22にクリーンなHEAD `f8aa55a9`から通常Dockerfileで
`tableno:display-security-f8aa55a9`を構築した。イメージIDは
`sha256:a3dee0c7341a22304da025e343e1cd239de81a9d664b785d3b41132afc0f019f`、実行ユーザーは`tableno`だった。

ネットワークなしの一時コンテナで上記62テストが成功し、別の一時コンテナで静的ファイル227件の収集が成功した。両コンテナは`--rm`で終了時に削除した。
イメージ内とホストのJavaScriptのSHA-256は次の値で一致した。

| ファイル | SHA-256 |
| --- | --- |
| character6th.js | `1b42af1fddcd4b40693790d4dbcf01a53a7e288ab9e52614fb79730ced9a4b66` |
| character7th.js | `2fb55c4c16a4a131228a5c03b5a4edd7317b7b4f49641378cbc41d5abf6320c1` |

上記62テストはローカル設定・SQLiteを使用した。後続のPostgreSQL/Redis起動とOS再スキャンは下記を参照する。AWS配信確認は未実施である。
また、前述のWebKitの401はCIログで確認した事実だが、Cookie同期を根本原因と断定する通信証跡までは得られていない。テスト修正後の成功を、アプリ認証全体の問題不存在の証明にはしない。

## PostgreSQL・Redis起動とOS再監査

同日の後続検証で同じ固定イメージを使用し、外向き通信を禁止したDocker内部ネットワークに空のPostgreSQL 18.3とRedis 7-alpineを起動した。公開ポートや実資格情報は使用せず、DB領域はtmpfsとした。

- `APP_ENV=aws-pre`で本番用設定を読み込み、通常entrypointによる全マイグレーションと静的ファイル227件の収集・617件の後処理、Daphne起動が成功した。
- コンテナ内の実HTTPで`/health/ready/`が200、database/cacheがともに`ok`だった。`migrate --check`も終了0だった。
- 初回のPG確認は初期化中で`no response`だった。再確認で`accepting connections`となってからWebを起動した。
- 専用Web・PG・Redisコンテナと内部ネットワークを名前・イメージで照合して削除し、対象コンテナの不在を確認した。イメージはローカルに保持する。

Docker Scout 1.24.0で同イメージのdebパッケージを再監査した。259パッケージ中14脆弱パッケージ、36指摘（HIGH 2 / MEDIUM 1 / LOW 33）が残った。実行は非ゼロ終了（今回の呼び出し結果は1）であり、合格とはしない。SARIFは`C:/tmp/runtime-os-f8aa55a9-20260922.sarif.json`、SHA-256は`e970d0a297894c0113b10fc03e2b6d1e43125dd18e14a9e0af56c03d124a9ac5`。先行9889f4c8の監査ファイルと一致した。

OS指摘の解消、実RDS/S3、実外部連携、実メール、AWSの性能・配信を証明する検証ではない。正式公開No-Goを維持する。
