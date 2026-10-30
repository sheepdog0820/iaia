# グループ管理・依存修正を含む更新統合候補（2026-10-31）

旧統合候補PR #41の承認待ち中に、pyasn1 0.6.4の依存監査が4件で失敗した。過去のCI成功を現在の合格として使わず、新しい専用ブランチ`codex/release-group-security-integration-20261031`で候補をまとめ直す。元のPR #41/#42/#43/#44のheadは変更せず、mainマージ・AWS反映・実データ操作は行わない。

## 含む変更と元の固定head

| 候補 | 固定head | 内容 |
| --- | --- | --- |
| PR #41 | `a78d15bf20cf4ac0fe6e050e72484fb7ef69fb4e` | 旧技能内訳の明示処理・DB準備とバックアップ記録・Twisted正式版・OS調査 |
| PR #42 | `ce18e45d1767cecda731cb548d872c263c784910` | 正式公開の状況、main/稼働版の訂正、MySQL/ORTの限定的調査範囲 |
| PR #43 | `9b2e266ff482e892445473c184d24f45f870266d` | グループの誤対象操作/500拒否、作成途中の失敗の取消、回帰とCI対象 |
| PR #44 | `a0d2e5527a8dff8de730d4ffa82b4c5650bc0c09` | pyasn1を0.6.5へ更新、通常/開発/テストのhashとsecurity floor |

固定headを通常のGit mergeで統合し、競合はなかった。製品の新規機能・所有権移譲、追加のDB移行や新しい権限は含まない。旧候補の`apply_verified_skill_adjustments`等は維持し、適用先を限定する運用条件も緩和しない。

## 既に得られた証拠と今回の検証

グループ修正は、合成データで旧挙動を再現してから別コミットで修正した。SQLite66成功/55 subtests、隔離PG69成功/55 subtests/省略0、通常image `49c30e3d`内PG66成功、最終headのCI全12チェック成功（全体2,390/123省略、PG617/288 subtests/省略0、UI243）。変更実行文28件と分岐arc18件は全実行。既存の実データに不整合があるかは未調査で、修復も実施していない。

pyasn1修正は、3ロックの既知指摘0件/省略0、公式suite1,261件、関連PG60件/40 subtests/省略0を確認した。通常Dockerfileで構築した固定image `98d2931793417af89c2219b30151c553cba4a4c32c99d98b026fe7dba19caa7d`でも、実111 package監査0件、Git由来562ファイルとentrypointの一致、UID10001/root read-only・pip/pytestなし・製品sourceの上書きなし、PG60件と公式1,261件成功を確認した。通常OS inventory101件は旧統合候補と一致する。同じimageのScout1.29監査も52指摘（C2/H9/M6/L35）・未除外exit2で不合格だった。専用PG/networkは08:54 JSTに削除し、endpoint残存0とabsenceを確認した。

上記はそれぞれの固定artifactの検証であり、更新統合候補のCI・通常配布物内の全関連回帰・source/依存の照合はこのcommit後に行う。候補間で結果を推測して移し替えない。新たな依存監査失敗・CI失敗があれば結果を保存し、合格扱いしない。

## 稼働版・未実施・承認範囲

共有RDS/Webの読み取りは08:29 JST時点でRDS18.3/available・暗号化、Web55/desired-running1/readiness200。固定digest `6d4050ec`と既存ローカルimageの照合ではDjango5.2.17/Twisted26.4.0/Stripe15.5.1/Autobahn26.7.1、追加のmetadata読み取りでpyasn1 0.6.4だった。mainのlockと稼働artifactを混同しない。共有DBの移行履歴は10月30日21:29 JST以降は再取得していない。

今回の候補は通常push/CIとローカル合成DB検証のみ。mainマージ、AWS反映・リソース/費用/IAM/Secrets/OAuth変更、共有DB0065〜0068適用、実利用者データの調査・修復、実Stripe/メールや外部通知、正式公開は含まない。非公開の実データコピーで4件を適用するリハーサルは固定a78d15bf/image7d5dfc5aの別の承認待ちであり、新候補へ自動で対象を変更しない。

最終マージ承認では、この統合候補の最終head・mainとの比較・CI/通常配布物の実結果・未確認事項を提示する。旧PR #41のa78d15bfへの回答だけを、新しい統合headの承認として使わない。復旧はrevert PRで、元に戻す修正単位に応じて技能の旧内訳処理、グループ誤対象/残存不具合、Twisted RC2やpyasn1の脆弱性が再発する。DBやAWSを戻す操作をrevertに含めない。

OS/nativeの52指摘（直近の候補監査C2/H9/M6/L35・未除外exit2）やPBDS/全native経路の未解決を維持する。この更新だけで既存配布物全体の安全性を証明したとは扱わない。正式公開No-Go、全25受け入れ条件、決定済みの無料範囲・画像5枚・480円/月/4,800円/年・開示方式は変更しない。
