# 正式公開候補と開発AWSの再照合（2026-10-02）

## 結論

正式公開はNo-Go。9月25日の依頼されたmainマージは完了しているが、購入・外部連携・運用の受入条件が全て満たされた証拠はない。10月2日21:42〜21:46 JSTにGit/GitHub/AWSの読み取り確認を行った。共有環境への変更、DB操作、メール送信、Secrets取得・変更、リソース作成は行っていない。

旧[反映案](AWS_APP_APPROVAL_FEC10AA0_2026-09-22.md)の定義49・候補fec10aa0は、現在の投入先・復旧先として固定使用しない。現行サービスは後続機能を含む別のイメージに更新されている。

## 確認済みの版と状態

| 対象 | 読み取り結果 | 証拠の範囲 |
| --- | --- | --- |
| 依頼されたmainマージ | `5caeaf2c422a0f2470b8420f7102e141cb1e1eff` | [CI全6項目成功](https://github.com/sheepdog0820/iaia/actions/runs/36072947282)。`git merge-base --is-ancestor` で現在のmainに含まれることを確認 |
| 現在のmain | `35ecfd5c9b91cd0f6d5836660bbdac380afeb7e2` | `git ls-remote` / fetchで照合。[同SHAのCI成功](https://github.com/sheepdog0820/iaia/actions/runs/36116531620) |
| AWSイメージのタグに対応するGit履歴 | `c6226ddbbb3f66d0eb94a8d3f79158c0ef37f4ec` | mainに `f1d92121`（共有セッションのシナリオ画像修正）と `c6226ddb`（画像ギャラリー）を追加。[同SHAのCI成功](https://github.com/sheepdog0820/iaia/actions/runs/36122431014) |
| AWSアカウント/地域 | `083773015316` / `ap-northeast-1` | `tableno-pre` のSTSと明示リージョンで照合 |
| ECSサービス | `tableno-aws-pre`、定義52 | desired/running=1、pending=0、rollout=COMPLETED。実行タスクRUNNING/HEALTHY |
| 稼働イメージ | `tableno:aws-pre-c6226ddb` | ECRと実行タスクのdigestが下記で一致。タグ名だけでソース全ファイル一致を証明したとは扱わない |
| Web容量 | CPU `256` / memory `512` | 0.25 vCPU / 512 MiB。増量していない |
| 購入開始 | `STRIPE_CHECKOUT_ENABLED=False` | タスク定義の明示環境変数。実購入テスト未実施 |
| 起動時保守 | `RUN_MIGRATIONS=false`、`RUN_COLLECTSTATIC=false` | 自動実行フラグ。過去の一時タスクの適用結果は証明しない |
| readiness | status/database/cacheすべて `ok` | `https://stg.tableno.jp/health/ready/`、応答時刻 `2026-10-02T12:42:17.407426+00:00` |
| ECSサービス一覧 | Webサービス1件のみ | 対象cluster内の常設worker/beatサービスは確認できない。他方式・他clusterの不存在は断定しない |

ECR/実行タスクのdigest:

```text
sha256:bc951b76e612706ff8b50b590ea6add774d710fb8d8db05247f8c304b7e762b2
```

ECRのpush日時は2026-09-25 19:11:14 JST。ECR照会のscan情報はnullだったが、これだけで他方式によるスキャンの有無は判定しない。

## 未完了と次の判断

1. **版の統一**: 稼働版はmainより先。次回候補は画像ギャラリーの2コミットを保持し、担当作業のレビュー/マージ状況を確認する。今回そのブランチのマージ・上書きは行わない。
2. **共有DB**: accounts 0065〜0067の適用状況は今回未照合。readinessのDB接続成功は全テーブルの存在を証明しない。適用済み記録または承認範囲内の読み取りで確認し、必要な適用は別途承認を確認する。
3. **課金**: 購入開始は無効。長期運用Sandboxキー、Priceとの対応、AWS上の購入からWebhook・権限反映・解約までの実証は未完了。課金メールのフラグは今回絞り込んだ明示環境変数に見つからず、実効値の断定はしない。Secrets値は取得していない。
4. **非同期・外部連携**: worker/beat/Redisの継続構成と費用承認、限定したGoogle出力先・Discord宛先・SMTP受信先の実検証が必要。過去の一時通信試験やmockを実配送成功へ読み替えない。
5. **品質と運用**: 現行digestのOS監査、登録100人/同時10人・通常操作p95 3秒以内の実環境試験、DB/S3整合を含むRPO24時間/RTO4時間の復旧、事業者開示・問い合わせ対応が残る。旧fec10aa0のOS指摘件数を現行digestの最新スキャン結果とは扱わない。

個別の合格条件は[受入条件表](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。CI成功とreadiness成功は、これらの全件合格や本番公開の承認を意味しない。

## 変更・復旧の扱い

本更新は確認記録のみで、DB・権限・費用への変更はない。原作業フォルダーのハンドアウト関連の未コミット変更は保持した。文書を戻す場合はこの文書更新コミットのみをrevertし、稼働サービスには触れない。

次回デプロイ前に定義52以降の最新定義とイメージdigest、S3静的資産の世代、DB適用記録を再確認する。旧定義49へ戻す案は後続の修正・機能を失う可能性があり、自動的な復旧策として採用しない。
