# カスタム技能名の動的HTML保護（2026-09-22）

## 結論

クトゥルフ神話TRPG 6版・7版のキャラクター作成画面で、カスタム技能名をHTML文字列へ直接埋め込む経路を修正した。技能名にタグ、引用符、イベント属性を含む文字列が渡されても、DOM要素やイベントを生成せず、入力欄の文字列として保持する。

実装コミットは`4cf3ad03`（`fix: escape custom skill names in character forms`）。正式公開判定は引き続きNo-Goである。

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

ブラウザ検証はローカルSQLiteと開発用ログインを使用した。実ユーザーデータ、共有DB、AWS、外部サービスは使用していない。

## 未検証・境界

- 保存済みの悪意ある技能名を実AWSへ投入する試験は行っていない。
- キャラクター画面以外を含む全動的HTML経路の監査完了を意味しない。
- mainマージ、共有DB変更、AWS反映、Secrets・権限・課金設定変更は行っていない。
