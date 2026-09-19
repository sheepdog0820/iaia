# 統合候補0f6b81feのコンテナ・反映準備

候補 `0f6b81feacf5a8fd77ad05128dea41f0ea5d2dc6` のクリーンな専用worktreeからローカルDockerイメージを作成し、[8項目の検証](STRIPE_CONTAINER_0F6B81FE_2026-09-19.json)がすべて成功した。ECR登録、mainマージ、AWS反映は実施していない。

## 検証結果

- 現在のAWSと同じ旧版イメージを、隔離PostgreSQL 18.3の空DBへ適用して比較用データを作成した。
- 新候補の未適用変更は0065・0066・0067の新規3テーブルだけであることを確認し、適用とmigrate --checkに成功した。
- 既存の利用者・購読・支払失敗監査データが一致した。新版の追加記録を残したまま旧版から読み取り、新版へ戻っても再試行キー・請求状態・未配送メールを保持した。
- 通常のコンテナentrypointで起動し、HTTP readinessのdatabase/cacheがokだった。
- pg_dump/pg_restoreで別の隔離DBへ復元し、既存データと追加3テーブルが一致した。
- コンテナ内の退会処理・利用者ビュー・退会テンプレートのSHA-256が対象コミットのファイルと一致した。

イメージ: `tableno:stripe-candidate-0f6b81fe`。
ローカルID: `sha256:246ffea363c028ffeee0095dde85307cac019626222e003eb6e2bca584348804`。
使い捨てDB・Webコンテナ・専用ネットワークは終了・削除済み。この試験はAWS上の性能や全サービス復旧試験の代替ではない。

## 開発AWS・mainの読み取り確認

2026-09-19 18:49 JST前後に対象アカウント083773015316を照合した。ECS tableno-aws-preは定義49、desired/running=1、pending=0、rollout=COMPLETED。CPU256・メモリ512で、イメージdigestは従来の `sha256:59542e45e5dc8e1e33cbf7202eb12911ffbb390156a778fe7eb11f0fe4c65f79` のまま。公開readinessはdatabase/cacheともokだった。

RDSはPostgreSQL 18.3・available・バックアップ保持7日。取得時のLatestRestorableTimeは2026-09-19 18:43:43 JSTだった。GitHubのmainもd875d028のままで、候補0f6b81feの祖先であることを確認した。これらは反映直前にも再確認する。

## 承認案の更新に必要な条件

前の[承認案](STRIPE_AWS_APP_APPROVAL_2026-09-19.md)は99acd8caを対象にしている。0f6b81feにはその後の退会安全対策・ブラウザーテスト・検証記録が含まれるため、旧案への承認を新候補への承認と解釈しない。

退会実装743e1e46の[CI run 35434803342](https://github.com/sheepdog0820/iaia/actions/runs/35434803342)は全6ジョブ成功。統合候補0f6b81feの[CI run 35435438622](https://github.com/sheepdog0820/iaia/actions/runs/35435438622)は記録時点で4ジョブ成功、Unit / Integration・Playwrightが実行中で、候補全体の合格はまだ確定していない。候補の全チェックが揃ってから、新SHAを明示した反映案を提示する。

想定する反映範囲は従来どおり、main通常マージ・既存Webのイメージ更新・追加3テーブルの事前適用・確認、異常時は定義49へ切戻し。購入・メール配送は無効のまま、Secrets・IAM・常設worker/Redis・継続費用増加は別承認とする。正式公開は引き続きNo-Go。
