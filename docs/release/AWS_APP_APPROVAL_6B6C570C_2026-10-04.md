# CCFOLIA・ICS候補のmain＋開発AWS反映承認案

## 対象・承認範囲

対象アプリコミットを **`6b6c570c9df641244894930b497452491811aab2`** に固定する。前回のfavicon `8567f49f` の承認は今回に流用しない。今回承認を求める操作は、この履歴のmainマージ/通常pushと、**開発AWS `aws-pre` / `stg.tableno.jp`** のWeb image更新・静的収集・CloudFront静的cache無効化。正式公開・本番・課金有効化・共有DB移行は対象外。後続の証跡文書コミットは配布imageの対象へ自動追加しない。

追加するアプリ変更は以下の3点。mainの画像ギャラリー・favicon・依存更新を保持する。履歴には先行の検証文書/仕様追記も含む。

1. CCFOLIA JSONのrootへ6版/7版を保持し、7版の6版誤取り込みを防ぐ。サーバーexportとブラウザーcopyの両経路。
2. ICSダウンロードのTEXTエスケープ・日本語長文のUTF-8 folding・UTC指定を修正し、購読側と共通helperを使う。
3. 停止中アカウントのICS購読GET/HEADを404で拒否する。再有効化時の既存URL再開・既存の再発行による失効は維持。

[通常配布物の証拠](ICS_CCFOLIA_RUNTIME_CANDIDATE_2026-10-04.md): 固定image `sha256:cdaa475f53dc0f24c6f612d756a61f6047aed4f138a99cc94166194458da3391`、575ファイル同一、76関連テスト成功、省略0、隔離PG/Redisで通常起動・19 HTTP確認成功。候補[CI全6項目success](https://github.com/sheepdog0820/iaia/actions/runs/37181732546)を確認済み。

**全OS監査は39指摘（HIGH2/MEDIUM2/LOW35、Python0）・終了1で未合格。稼働版とのCVE ID差分0であり、今回これを解消したとは扱わない。** この残存リスクを明示した開発環境への限定反映判断を求めるもので、正式公開のリスク受容・No-Go解除ではない。実CCFOLIA・実ICS受信アプリ・AWS操作画面の確認、既存共有DBの履歴/スキーマ、課金実運用なども未完了。

## 現在版・維持する条件

2026-10-04 15:24 JSTの読み取りでmainは `8567f49f`、AWSはタスク定義 **54**、image **`sha256:adafc0705ded3dabf2a9d2223a5c460b48ff00b2c949f221a4edef3eedee695e`**。直前確認ではdesired/running=1/1・pending0・HEALTHY・readinessのDB/cache正常。実行直前にも再確認し、他の更新があれば独断で上書きしない。

- AWS profile/account/regionを `tableno-pre` / `083773015316` / `ap-northeast-1` に限定。
- 既存task role/execution role、network/logging/volume、plain env52・Secrets参照19を保持し、Web imageのみ差し替える。Secrets値の表示・更新はしない。
- CPU256/memory512・desired1を維持。Redis/worker/beatや新規AWSリソースの作成、継続容量費用の増加はしない。
- RUN_MIGRATIONS/RUN_COLLECTSTATIC=falseを保持。変更マイグレーション0で、共有DBへmigrateを実行しない。既存0065〜0067の適用状況は別の未達条件。
- STRIPE_CHECKOUT_ENABLED=Falseを保持。有料販売・実決済・外部通知・OAuth/IAM/権限変更・実利用者の停止/参加資格変更はしない。
- image保存、短時間のone-off collectstatic/rollout、log/通信/cache無効化には従量利用が生じ得る。継続容量は増やさない。

## 承認後の操作と検証

1. クリーンな専用checkoutでmainと候補の祖先関係/差分を再確認する。対象をmainへマージし通常pushする。mainへ直接修正コミット・force push・元checkoutの変更取り込みはしない。main CIを別に確認し、失敗時はAWS反映を進めない。
2. 検証済みimageを既存ECR `tableno` の `aws-pre-6b6c570c` tagへpushし、digestを記録する。tag同名の異なる既存imageがあれば上書きせず止める。ローカルimage IDとECR manifest digestを混同しない。
3. 現在定義54を基にWeb imageだけを検証済みECR digestへ変更し、新しいtask revisionを登録。差分を確認して既存serviceを更新し、stable/HEALTHYとrunning image digestを検証する。
4. 同じ新定義・serviceの現行networkで `python manage.py collectstatic --noinput` のone-off taskを実行（`--clear` は使わない）。終了0とlogを確認し、CCFOLIA helperの元/hashed objectとmanifest内容をS3で照合する。
5. 既存CloudFront **E3RQ829D1NVY28** の `/static/*` のみ無効化し、Completedを確認。元/hash JavaScriptの公開取得・bytes照合・Node構文検査、favicon公開URL保持、readiness DB/cache、login画面を確認する。
6. 対象画面のCCFOLIA copy/APIとICSを確認する際は、許可された専用テスト対象だけを使う。今回の承認だけで共有DBにfixtureを作成したり、実利用者の予定/権限/購読を変えない。対象が未提供なら認証済みAWS操作の未確認を明示する。実CCFOLIAルーム・テストダイス送信は別途回答待ちの承認境界。

static mappingは現在/候補とも232件で、差分は `js/ccfolia_character_copy.bb432b817259.js` → `js/ccfolia_character_copy.bf50da761ab5.js` の1件。S3 storageで実際に生成されたmapping/bytesを実行時に検証し、ローカルWhiteNoise収集結果だけで成功とは扱わない。

## 復旧・停止条件

反映前の静的manifest: bucket `tableno-aws-pre-assets-083773015316`、key `static/staticfiles.json`、VersionId **`aWvgNwDceWv4joe9MTqBJGBblRKGz.aZ`**、ETag `388634289af5fba73ae51f1910c952fe`。実行直前に保持/取得可能性を再確認し、旧hash objectを削除しない。

Webが不健康・静的収集が非0・配信が不一致なら後続操作を止め、定義 **54** と上記稼働digestへserviceを戻してstable/readinessを確認する。必要な場合のみ、保存済みVersionIdのmanifestを現行keyへ新しいversionとして復元し、同じ `/static/*` を無効化する。DBは変更しないためDB rollbackは行わない。旧hash/static世代とECR imageを保持する。

定義54への復旧は今回のCCFOLIA/ICS不備を再導入するので、応急復旧と明示し、修正を保持したfix-forwardを優先して検討する。main履歴は破壊しない。main revertが必要になった場合は対象を示して判断を求める。

本案は承認待ち。既存favicon承認を新候補へ拡張せず、[正式公開No-Go](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。
