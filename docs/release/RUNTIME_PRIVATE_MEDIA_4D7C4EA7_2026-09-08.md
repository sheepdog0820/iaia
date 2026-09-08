# 最新配布物の非公開ファイルHTTP検証

2026-09-08。候補 `4d7c4ea7d005e2ddee26c1ef8d72d58cdccab43e` のGitアーカイブから通常Dockerfileでビルドした。アーカイブの展開前に、通常ファイル/ディレクトリだけであり、全展開先が専用ディレクトリ内に収まることを確認した。

イメージは `tableno-formal-release:4d7c4ea7`、ID `sha256:73c235a6e14a86fc90d26958f5e2b6c5c5c5ddb09e8647e8415cd7ed237ba3bd`。アプリソースのマウントやイメージ内への差し替えはしていない。

## 配布物・起動

- accounts/api/scenarios/schedules/support/tableno/static/templates配下のPython・JS・CSS・HTML、514ファイルのSHA-256がアーカイブと一致。バイナリ資産・トップレベル設定・他のディレクトリを含む全ファイル照合とは区別する。
- 前候補7fc6b61eのno-curlイメージと、dpkg-queryの全出力・Python配布パッケージ名/バージョン一覧が一致。新たなOSスキャンや全ライブラリのバイナリ一致検査の代わりにはしない。前候補のOS指摘41件は未解決のまま。
- アプリ0.25 CPU/512 MiB、PostgreSQL 18.3、Redis 7を内部ネットワークに隔離し、通常entrypointで空DBへの移行・静的収集・HTTP起動が成功した。DBはtmpfs、メディアは試験コンテナ内のFileSystemStorage。メール等も隔離した設定を使用した。
- 同じ隔離HTTP設定でcheck --deployを実行すると、試験用のSECURE_SSL_REDIRECT=falseについてW008警告が出た。別のネットワークなしコンテナでこの値だけtrueにして検査し、指摘0を確認した。共有環境のHTTPS転送や証明書を検証した結果ではない。

## 実HTTPの結果

| 対象 | 件数と結果 |
| --- | --- |
| 6版/7版の画像アップロード | 14件成功。保存6件、復号後容量/幅/高さ制限の拒否8件。保存後は各版3枚・順序0/1/2 |
| 問い合わせ添付APIと旧media URL | 4アクター×2経路、8件。権限付きスタッフだけ200で本文一致、一般所有者/部外者/匿名は404 |
| 透過結果API | 4件。所有者だけ200で生成PNGのSHA-256一致、他人は404、匿名は401 |
| 透過入力・結果の旧media URL | 4アクター×2経路、8件。全件404 |

計34件が期待どおり。認可付き取得の200応答には、attachment、nosniff、private/no-store、Vary: Cookieを確認し、透過結果にはVary: Authorizationも確認した。拒否応答に問い合わせ本文や透過PNGが含まれないことも検査した。エラー応答の全ヘッダーは、この実HTTP試験ではなく[局所回帰テスト](BACKGROUND_REMOVAL_RESPONSE_CACHE_2026-09-08.md)で検証している。

セッションは使い捨てDBへ直接作成した合成認証情報であり、ログインUI・実OAuth・実APIトークン発行の検証ではない。問い合わせ画像と透過ジョブは試験用に保存した生成ファイルで、実LINE受信・通知やこの候補でのモデル推論を実行していない。HTTPは隔離ネットワーク内であり、TLS・実S3/CDN・共有キャッシュ・実負荷の合格を証明しない。DEBUG時の拒否は[別のテスト](PRIVATE_MEDIA_FALLBACK_2026-09-08.md)で検証済み。

## 同じアプリ候補の全体CI

[PR実行34214020802](https://github.com/sheepdog0820/iaia/actions/runs/34214020802)と[push実行34214015906](https://github.com/sheepdog0820/iaia/actions/runs/34214015906)は、ともにhead 4d7c4ea7、completed/successをAPIで確認。追加pushで打ち切らず完了を待った。以下はPR側の完了ログから取得した。

| ジョブ | 結果 |
| --- | --- |
| Unit / Integration | 1,775 passed、30 skipped、159 warnings。カバレッジ86.87%（CI基準70%） |
| production-database | 286 passed、9 warnings、38 subtests passed |
| playwright | 186 passed、12.3分。flakyの記載なし |
| system | 12 passed、11 warnings |
| lint-security | success。BanditはNo issues identified、Python依存監査はNo known vulnerabilities found |

Banditには個別指定による559件の抑制と警告があり、無抑制の検査ではない。30件の省略を実行済みに数えず、全体カバレッジから全新規コードの100%を推定しない。CIは外部連携の実サービス検証・OS監査・実RDS/S3復元の代替ではない。後続の文書コミットに対する新CIは、このアプリ候補の完了した実行と区別する。

## 後片付け・証跡

所有ラベルを照合して専用アプリ/DB/Redisコンテナとネットワークを削除し、残存一覧が空であることを確認した。Git管理外の `tmp/runtime-4d7c4ea7/` にHTTP結果、ソース照合、依存一覧、試験スクリプトを保存した。合成セッション・環境ファイル・アクセスログはコミットしない。

依存比較の最初のPowerShell一行コマンドは引用符の解釈でSyntaxErrorとなり、専用Pythonスクリプトで再実行した。実HTTP試験は初回成功。今回のアプリコード変更はなく、実環境・実データ・Secrets・権限付与・AWS資源・費用を変更していない。新候補の配布物検証であり、共有環境への配備完了ではない。
