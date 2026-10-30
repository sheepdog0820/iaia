# Twisted正式版26.10.0への更新候補（2026-10-30）

10月30日18:24 JSTに[Twisted26.10.0の正式版](https://pypi.org/project/Twisted/26.10.0/)が公開された。朝の確認ではRC2が最新だったが、21:43 JSTのPyPI JSON再確認で正式版の未取り消し配布を確認した。これを受け、main deddd772を基点に、`requirements.txt`と通常/開発/テストの3ロックのTwistedを26.10.0rc2から26.10.0へ更新する。PR #38の製品変更や、別ブランチのOS調査文書を混ぜない独立候補である。

## 配布物と差分

RC2/正式版それぞれのPyPI metadataとwheelを取得し、wheel実ファイルのSHA256を公式metadataと照合した。下表のsdistハッシュも公式metadataから取得した。要求Pythonは双方とも>=3.10、requires_distも同一で、現在のPython3.11環境の条件を変えない。

| 正式版artifact | SHA256 |
| --- | --- |
| `twisted-26.10.0-py3-none-any.whl` | `3732f42af218925a0fe78d6668db55853f7fb532245a89a2669babe7d3000fa8` |
| `twisted-26.10.0.tar.gz` | `5f0355403e507fc23ceea85e9dbb4bc59335aabde41dd324e8b8cea180dd38de` |

wheelの追加/削除ファイルは0件。変更はdist-info3件とPython5件で、Python側は`_version.py`の正式版番号、`internet/ssl.py`・`trial/runner.py`の非推奨警告に使うVersion値と、それに対応する上流テストの変更だった。差分をレビューし、SSL/TLSの処理アルゴリズムやtrial runnerの動作を変更する差分がないことを確認した。RC2で保持していた修正を、脆弱性のある古い正式版へのdowngradeで失わせない。

Python3.11.18/pip-tools7.6.1で全3 scopeを再解決し、生成されたTwistedブロックだけを採用した。2ハッシュは公式未取り消し配布物と一致する。ほかのpackageの版・hash・ブロックはバイト単位で不変で、Linux再生成時に省略された既存のWindows/旧Python向けasync-timeout・coloramaも保持した。Autobahn26.10.1等の既存security floorは維持する。

## 完了した検証と未完了

- ハッシュ付きのテスト用ロックを使った更新と`pip check`は成功した。テスト用imageの依存だけを更新し、通常配布物へpip等のツールを追加しない。
- 3ロックのpip-auditは通常111・開発167・テスト207パッケージすべて既知指摘0件。無視・CVE除外・hashの無効化は行っていない。
- 更新済み依存の隔離PostgreSQL18.3で、server logging・entrypoint・診断保護・本番設定・systemの関連86テスト/28 subtestsが成功、省略なし。テストDBだけを使用し、実DBには接続していない。
- UTF-8/LF、差分、lock blockの同一性、依存条件とwheel差分の自己レビューを確認する。製品の画面文言やAPIの変更はない。

## 通常配布物の検証

製品変更のcommit `7afaada33987d0d50a112d54d9fc3eef808663b2`をgit archiveし、通常のDockerfileでimage `sha256:7b5c3e73f7c7f46718dd52f266f98cc7ff78c9f4567921494d5b4f666fe0946a`を構築した。UID10001・root read-only・cap-dropで実行し、Git由来のアプリ/静的/テンプレート/依存入力等560ファイルとentrypointが一致した。pip/pytestは通常imageに存在せず、製品sourceの上書きもしていない。

隔離PG18.3/Redis7上で、通常entrypointの全移行と静的収集からASGI server起動までを確認した。HTTP readiness200/database-cache ok、未認証WebSocket403、認証済みのRedis/msgpack通知配送、別利用者への非漏えい、切断が成功した。利用者とsessionは合成データだけである。初回は検証用フラグを`True`と記述して移行が起動しなかった失敗を保存し、entrypointが受理する`true`に修正して同じ隔離DBで確認し直した。

通常imageに実インストールされた111パッケージにはTwisted26.10.0が入り、その全inventoryのpip-auditも既知指摘0件だった。OS101パッケージは別に記録した。Scout1.29.0の新しい未除外監査は298 packageを識別し、**52指摘（Critical2/High9/Medium6/Low35）、exit2**。Python指摘はなかったが、OS/native全体の合格ではない。

専用のローカルASGI/Redis/PG container3件とnetworkは22:05 JSTに削除し、合成envファイルも削除した。Docker imageと検証記録は保持する。通常配布物の結果はこのcode commitに限定し、文書だけの後続commitは対象source blobの同一性で区別する。

最終CIは確認中である。旧head・RC2 imageの成功を正式版候補の成功として扱わない。候補ではRC2を置き換えたが、mainや稼働AWSへ反映したとは報告しない。

## 影響と復旧

本変更は依存の固定と文書だけで、DB schema/実データ・IAM/Secrets/OAuth・AWS反映/リソース・費用・外部通知・料金等は変更しない。通常pushはCIのみを起動し、mainマージ・共有適用・AWS反映は最終対象と検証を示して必要な承認を確認する。既存の承認はこの追加マージへ拡張しない。

復旧はrequirements入力と3ロックを同時に戻すrevert PRで、RC2へ戻る。OS/nativeの指摘と、実課金/外部連携・性能・DB/S3全体復旧・運用を含む正式公開条件は未完了で、**正式公開No-Go** を維持する。

ローカル証拠：`tmp/twisted-stable-artifacts-20261030/release-comparison-proof.json`、`tmp/twisted-stable-lock-adoption-proof.json`、`tmp/twisted-stable-lock-audits.log`、`tmp/twisted-stable-related-pg.log`、`tmp/twisted-stable-wire-proof.json`、`tmp/twisted-stable-runtime-proof.json`、`tmp/current-release-7afaada3-1.29.sarif`、`tmp/current-release-7afaada3-129-scan-summary.json`。これらのprivate artifactをGitに含めない。
