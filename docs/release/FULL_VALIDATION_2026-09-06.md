# 2026-09-06 全体検証の記録

対象アプリのスナップショットは `c816f8e4`。後続の U2-Net モデル指定はこの全体実行には含まず、別途 [画像透過の検証記録](BACKGROUND_REMOVAL_MODEL_VALIDATION_2026-09-06.md) を参照する。

## バックエンド

実データと隔離した Docker 環境で accounts、api、scenarios、schedules、support、tableno、tests/unit、tests/integration を実行した。

| DB | 成功 | 失敗 | スキップ | カバレッジ |
| --- | ---: | ---: | ---: | ---: |
| SQLite | 1662 | 9 | 10 | 86.96% |
| PostgreSQL 16 | 1672 | 9 | 0 | 87.53% |

両方とも終了コード 1。元の全体実行を合格として扱わない。ローカル証跡は `tmp/full-c816f8e4-output/` の DB 別ログ、JUnit、カバレッジに保存した（Git 管理外）。

失敗は両 DB で一致した。

- CI の環境設定テスト 1 件：Playwright の `ENV_FILE` 未設定を要求していたが、独立した SQLite 検証のため明示的な空文字を設定済みだった。空文字と SQLite を検証するよう期待値を更新した。Compose 検証だけで `.env.example` を指定する検証は維持した。
- リポジトリ・文字品質検査 8 件（サブテストを含む）：Git archive の 847 ファイルは検証イメージと一致したが、`/candidate` に Git 管理情報がなく、Git コマンドが失敗した。アプリ機能の失敗とは区別する。

使い捨てコンテナ内で、生成物のないアーカイブの全ファイルを Git インデックスに登録し、修正したテストを読み取り専用で重ねて再検証した。対象は `test_docker_entrypoint.py`、`test_repository_hygiene.py`、`test_text_quality.py` の 3 ファイル。**32 件成功、4 サブテスト成功、警告 4 件、終了コード 0**。証跡は `tmp/full-fixture-regression.log`。ホストの Git 設定・インデックスには検証用の変更を加えていない。

この再検証は失敗箇所に限定しており、修正後の全体一括実行や GitHub CI の成功を示すものではない。実データ、DB スキーマ、アクセス権限、課金の変更はない。
