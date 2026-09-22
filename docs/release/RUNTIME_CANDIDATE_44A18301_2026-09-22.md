# 表示・探索者履歴の最新配布候補

## 固定対象

- コミット: `44a18301fcc3d5f9c9070314aaf0e7f37946f357`（構築時差分なし）
- イメージ: `tableno:history-security-44a18301`
- ID: `sha256:52662f3ba2c0d00b31b6761d848a32a42ab5cc6293c6334410cb1dcb29822f08`
- 通常Dockerfileで構築。依存層はキャッシュ利用、実行ユーザーは `tableno`。コミットをOCI revisionラベルにも保存。
- 旧候補 `f8aa55a9` 後の一覧・成長・詳細のHTML保護、探索者履歴取得修正と実API保存/表示テストを含む。

## 配布物の検証

外部通信禁止（`--network none`）・ホストDB/資格情報のマウントなし・一時コンテナで実施。

- SQLite/ローカル設定で関連144テスト成功（66.647秒、skipなし、終了0）。対象は `scenarios`、`tests.unit.test_character_create_ui_static`、`tests.unit.test_character_skill_ui_security`、`accounts.test_custom_skill_addition`。
- 別コンテナで `collectstatic --noinput` が227ファイル収集、終了0。
- 全コンテナは `--rm` で削除され、当該イメージを使用する残存コンテナ0を確認。イメージは保持。
- ソース/配布物のSHA-256が一致:

| ファイル | SHA-256 |
| --- | --- |
| templates/accounts/character_detail.html | `ee292df0ca7e9402f12e48aac26c682ed22c51bdf822eea21b0e596446cd89f3` |
| templates/accounts/character_list.html | `4f70acee90528dba416a0c05a696b1ffa3c85e9e6c0435e13639378932a1e134` |
| scenarios/views.py | `5e2bfb33692cb4fdca7a4515ec147bdad548d0ae4a8d6779c16a95b91e16371f` |

## OS監査

Docker Scout 1.24.0で同イメージのdebパッケージを再監査。259パッケージ中14脆弱パッケージ、36指摘（HIGH 2 / MEDIUM 1 / LOW 33）が残り、実行終了コードは1。成功/解消とは扱わない。

SARIF: `C:/tmp/runtime-os-44a18301-20260922.sarif.json`。SHA-256: `e970d0a297894c0113b10fc03e2b6d1e43125dd18e14a9e0af56c03d124a9ac5`。先行f8aa55a9のSARIFと一致することを確認した。

## CI・未完了

[44a18301のCI](https://github.com/sheepdog0820/iaia/actions/runs/35701286422)は確認時点で実行中。Lint/Security・Infrastructure・Systemは成功、Playwright・Unit/Integration・Production Databaseは実行中で、全体成功とはしない。

最新固定イメージのPostgreSQL/Redis・aws-pre設定の起動確認、実AWS・RDS/S3配信、実外部連携、実メール、総合性能・復旧は未実施。先行f8aa55a9の起動成功をこのイメージの成功へ拡張しない。反映承認案も旧f8aa55a9対象のままで、最新候補への更新が必要。

mainマージ・ECR push・共有DB変更・AWS反映・認可/課金/継続費用の変更なし。正式公開No-Goを維持する。
