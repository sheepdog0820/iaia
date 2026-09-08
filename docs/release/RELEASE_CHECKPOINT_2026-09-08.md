# 正式公開準備の検証チェックポイント

確認日: 2026-09-08。作業ブランチ: `codex/formal-release-resume`。検証したHEADは `bea93461f0b7e39dcf277745c167b7f3caf463ad`、アプリ変更の最新コミットは `1edab4f2`。この文書の追加は検証対象の後続コミットとなる。

## CI結果

[PR側の実行](https://github.com/sheepdog0820/iaia/actions/runs/34205615503)と[push側の実行](https://github.com/sheepdog0820/iaia/actions/runs/34205608831)は、ともに5ジョブすべてsuccess。実行中の追加push・キャンセル・再実行は行わず、完了を確認した。以下の件数はPR側の各ジョブログによる。

| ジョブ | 結果 |
| --- | --- |
| Unit / Integration | 1,761 passed、30 skipped、159 warnings。カバレッジ86.81%（CI基準70%） |
| system | 12 passed、11 warnings |
| production-database | 286 passed、38 subtests passed、9 warnings。マイグレーションファイル差分なし |
| playwright | 186 passed。結果にflaky・失敗の記載なし |
| lint-security | success。BanditはNo issues identified、Python依存監査はNo known vulnerabilities found |

SQLite側の画像同時追加テスト2件はスキップされるが、PostgreSQL側の明示した実行対象に含まれる。30件すべてのスキップ理由を今回個別再調査したわけではない。Banditには個別指定による559件の抑制と警告があり、無抑制・無警告の監査結果ではない。全体カバレッジの合格は新規コード100%の証明とは区別する。

## 直近の修正と実配布物の検証

- 画像の同時追加をキャラクター単位で直列化し、残り1枠へ同時に2件送っても5枚を超えないように修正。6版・7版でPostgreSQLの再現試験を実施した。[詳細](CHARACTER_IMAGE_CONCURRENCY_2026-09-08.md)
- 画像順序0を空扱いしていた処理を修正。自動追加と明示順序の混在を両版で検証した。[詳細](CHARACTER_IMAGE_ORDER_2026-09-08.md)
- アップロード試験のキャラクターを分離し、5枚制限とファイル容量制限が混ざらないようにした。実HTTP27件を検証した。[詳細](IMAGE_UPLOAD_PROBE_2026-09-08.md)
- 通常Dockerfileのイメージでソース553ファイルの一致と画像解像度の実HTTP14件を確認した。[詳細](IMAGE_RESOLUTION_RUNTIME_2026-09-08.md)

## 同じ配布イメージのOS再監査

対象は `tableno-formal-release:1edab4f2`、ID `sha256:f0cc1aed8c16e4080e77d28610053fd104216bbfe68930c9b8e17cd9cb17b127`。既存のDocker Scout 1.24.0を専用キャッシュで実行し、292パッケージを索引化。17パッケージに48件を検出し、プロセス終了値は2だった。

内訳はHIGH 1、MEDIUM 1、LOW 40、UNSPECIFIED 6。CVE ID・パッケージURL・深刻度の組の集合は旧候補10d21e42の証跡と一致し、増減はない。指摘が解決した結果ではない。適用条件と残事項は[OS監査一覧](RUNTIME_OS_REVIEW_INDEX_2026-09-08.md)を参照する。

Git管理外の証跡は `tmp/runtime-os-1edab4f2-scout124.sarif.json` と同名の `.log`。SARIFのSHA-256は `b48d57647501ec2a8a60b15cbeb1c4f4abae132a8b4c226c27b8437618254056`。専用キャッシュ内の一時アーカイブ削除にファイル使用中の警告が出たが、レポート出力は完了した。キャッシュは保持している。

## 残タスクと停止点

1. Stripe接続・決済試験はユーザーの準備待ちとして保留を継続する。
2. 実環境のGoogle連携、CCFOLIA、ストレージと通知経路を最終候補で確認する。外部への実通知送信は別途承認が必要。
3. OS監査48件の未解決条件を詰める。CIのPython依存監査成功で代替しない。
4. 性能の合格値と必要容量、監視・運用体制、RPO/RTOを確定する。[現状の負荷測定](READ_API_CAPACITY_2026-09-08.md)は正式な性能合格判定ではない。
5. 実RDS復旧試験は[具体的な承認案](RDS_RESTORE_APPROVAL_2026-09-08.md)への回答待ち。新規リソース・権限変更を実行していない。
6. 共有環境への候補反映と未適用マイグレーション、最終的なmainマージ・本番反映を実施する際は、対象と既存承認を照合する。今回それらを実行していない。

[Draft PR #2](https://github.com/sheepdog0820/iaia/pull/2)はレビュー対象として残す。CI合格と正式公開可能の判断を区別し、公開完了とはしない。修正・証跡は作業ブランチへ保存済みとし、この文書のコミット後のCIは別の実行になる。

今回の検証記録追加によるアプリ・DB・Secrets・アクセス権・AWS資源・継続費用の変更はない。文書の訂正は後続コミットで可能。アプリ修正の取り消しが必要な場合は該当コミットをレビューしてrevertし、関連テストを再実行する。稼働環境へのデプロイは行っていないため、本記録追加に伴う本番ロールバックは不要。
