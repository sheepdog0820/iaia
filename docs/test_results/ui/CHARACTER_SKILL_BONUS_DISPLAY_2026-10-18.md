# キャラクター詳細の技能ボーナス表示修正

確認日: 2026-10-18（日本時間）

## 原因と修正

対象: `https://stg.tableno.jp/accounts/character/6th/413/`（レオニー）

技能の合計値にはボーナスが反映済みだったが、通常の技能APIが `bonus_points` を返さず、詳細画面の内訳にもボーナスがなかった。
APIに読み取り専用のボーナス値を追加し、正の値を「ボーナス」として表示する。合計の再計算やデータへの加算は行わない。

| 技能 | ボーナス | 確認した合計 |
| --- | ---: | ---: |
| 重機械操作 | 30 | 71 |
| 電気修理 | 20 | 65 |
| 説得 | 30 | 70 |

変更ファイル: `accounts/serializers.py`、`templates/accounts/character_detail.html`、回帰テスト2ファイル、`docs/character_sheet/SKILL_TAB_SPECIFICATION.md`。

## 検証

- 6版・7版の技能API、ボーナス既存機能、キャラクターAPI、作成画面の関連テスト129件が成功。
- Node.jsで実際の技能描画関数を実行する4ケースが成功。ボーナスのみ、0・未設定、その他との併用、保存済み合計の維持を確認。
- デプロイ用コンテナーでも13件成功（Node.js未導入のため描画テスト1件はスキップ。描画は上記ローカル実行で検証済み）。
- Black・isort・Flake8、JavaScript構文、差分、UTF-8・LFのチェック成功。変更したUI文言は日本語。ソースレビューに追加の指摘なし。
- 対象ページの再読み込みで3技能のボーナス内訳と既存の合計を確認。ブラウザーのエラーログなし。
- GitHub CI全体の完了は未確認。ローカル検証とCIの成功を区別する。

## 開発環境への反映

- アプリのコミット: `cbf52dc5c2ecfcef6fb5f5484ae4537d74470675`（通常push済み）。
- イメージ: `aws-pre-cbf52dc5` / `sha256:6d4050ec19ba5d34740643d515436baa5dd27b99a912b9c20ad7a9af0812af06`。
- 稼働中だった `aws-pre-8567f49f` のdigestを基に、今回の実行コード2ファイルと回帰テスト2ファイルだけを追加したイメージを構築。元の作業場所にある無関係の未コミット変更は含めていない。
- ECSタスク定義: `tableno-aws-pre:54` → `tableno-aws-pre:55`。更新後はdesired/runningともに1、deploymentは1。
- `collectstatic --noinput` 単発タスク: `8edd7f9e96f14fd58ce9203fc5b15495`、コンテナー終了コード0。
- DBマイグレーション・実データ・権限・Secretsの変更なし。継続リソースや継続費用の追加なし。
- 静的アセットの内容変更はないためCloudFront無効化は実施していない。
- `/health/ready` は `status=ok`、database/cacheともに `ok`。
- 復旧はECSサービスを旧タスク定義 `tableno-aws-pre:54` に戻す。DB復旧は不要。

元の作業場所の未コミット変更はそのまま保持し、修正は専用worktreeと `codex/character-skill-bonus-20261018` ブランチで作成した。
