# OS53指摘の追加判定と残る確認（2026-11-01）

正式公開は **No-Go**。元25条件とQ04「情報保護の重大な既知欠陥がなく、セキュリティ指摘に判定がある」を維持する。今回の変更は調査記録だけで、OS更新、リスク受容、ignore/VEX、severity変更ではない。

## 対象と記録の不足

| 項目 | 固定した対象 |
| --- | --- |
| main | `4627cdd04eea48dd9b81c1cb558acb73bd1b47f6`（PR #66マージ後） |
| 検証source | `62d3cc0591a04c79114167533a7b7c47d19ba405`。mainと同じtree |
| 通常image | `sha256:1e4d66ab3c788786e257a1445a3596eb83a22aeee142fb9ddf1e58655976cb09` |
| 元の全件監査 | source `dac04381efe03341055c4ffac2472792af2e15ac`、image `sha256:ddb493e310c75d7b93b1f9312b87e00d99d1801e12b1784c13ba640fbda9fb8f`、Scout1.29.0 |
| 元SARIFのSHA256 | `33077c5051582c66746cd4278b36e01035370fa49fa25a79cc32a0a34dbee5f4` |
| 未除外の結果 | **53指摘（Critical2 / High10 / Medium6 / Low35）、exit2** |

通常imageのPython111・dpkgパッケージ構成は前候補と同じで、既知のPython native ELF268件もSHA256一致を確認した。ただし、これは新しい全件スキャンや全nativeコードの安全性の証明ではない。

元SARIFの53 CVEと既存リリース文書255件を照合したところ、45件にはCVE名の記載があり、下記8件にはGit管理下の記録がなかった。この照合は記録の所在を探すためのもので、45件の判定が最新・妥当・完了であるとは扱わない。今回8件を記録しても、全53件の意味内容の再評価は完了しない。

## MariaDB MEDIUM 5件の技術判定

固定imageに含まれるOSのConnector/Cバイナリには、次の問題のサーバー実装が含まれないと判定する。対象は `libmariadb3:amd64` / `mariadb-common` `1:11.8.6-0+deb13u1`。外部MariaDBサーバー、別image、vendorが別に同梱するサーバー実装へ拡張しない。

| CVE | 公式修正の製品コード | 固定配布物との対応 |
| --- | --- | --- |
| [CVE-2026-85745](https://security-tracker.debian.org/tracker/CVE-2026-85745) | [2bf355e](https://github.com/MariaDB/server/commit/2bf355e361db85153fdfba7b8a0f0d114d6a26ce)の `sql/spatial.cc`。サーバーの空間データ解析 | Connector/Cのビルド対象外 |
| [CVE-2026-107817](https://security-tracker.debian.org/tracker/CVE-2026-107817) | [851f524](https://github.com/MariaDB/server/commit/851f52470d470a96a66e0b7e5599f3b6c2e45907)の `plugin/type_mysql_json/mysql_json.cc` | サーバー用JSON pluginは配布物にない |
| [CVE-2026-85985](https://security-tracker.debian.org/tracker/CVE-2026-85985) | [4f66ca1](https://github.com/MariaDB/server/commit/4f66ca1b69daf1b7e6a562ca8e86d77a6a70abfe)の `storage/connect/`。ファイルアクセスUDFの権限検査 | CONNECT engineと該当サーバー実装は配布物にない |
| [CVE-2026-107816](https://security-tracker.debian.org/tracker/CVE-2026-107816) | [0931994](https://github.com/MariaDB/server/commit/0931994096b84ecc9ffc8eb3517c7e09e6e8631e)の `plugin/qc_info/qc_info.cc` | query cache情報用サーバーpluginは配布物にない |
| [CVE-2026-107822](https://security-tracker.debian.org/tracker/CVE-2026-107822) | [67ea07d](https://github.com/MariaDB/server/commit/67ea07dd3400004e4f7ae01bf977f4344bbe064b)の `sql/sql_acl.cc` | サーバーの権限cache実装はConnector/Cのビルド対象外 |

各Debian記録はtrixieの同source版をvulnerableと表示していた。forky/sidの修正版表示を理由に、別suiteのパッケージを導入していない。source package全体の表示は残し、実際のbinary packageの適用範囲を判定した。

根拠は[先行するCritical/High判定](RUNTIME_OS_HIGH_CRITICAL_SCOPE_2026-10-30.md)の公式Debian artifact・ビルド定義に加え、今回の次の照合である。

1. 固定imageの `libmariadb.so.3` とclient認証plugin6件が、先行検査の公式DEB内の7ファイルとSHA256一致した。
2. 正確な元source archiveからConnector/C配下の269入力を再照合した。5修正の製品コードはこのビルド対象外だった。新設の `storage/connect/filechk.*` はclientへの修正ではない。
3. `mariadbd` / `mysqld`、embedded server library、CONNECT・mysql_json・qc_infoの対象server pluginが固定imageにないことを確認した。単にDB接続先がPostgreSQLであることを根拠にしていない。
4. libraryのロード、SQL接続、アプリ/worker起動、AWS操作は行っていない。検査用コンテナは同じIDでexit0・restart0と削除を確認した。

| 照合したartifact | SHA256 |
| --- | --- |
| 公式 `libmariadb3_11.8.6-0+deb13u1_amd64.deb` | `b2a2d1cdf7493c75d43916a18947700740964513ff5ff603cf5cbbf61e9e6385` |
| 固定imageの `libmariadb.so.3` | `d283268434adf3cc3ffcb0580b384f3e13c91bd24b58114022073694dbcc2928` |
| 元source archive | `b126581a8ca89376d2a3ce63fee97c114c3e15315345e769b9d00c51e1b7d619` |
| `current-medium-client-scope-proof.json` | `53e7f26cfb2975a95b17fe0836b9c27f398aa63a59de451fa7361e9837b0b7c6` |

ローカル証拠は調査worktreeの `tmp/mariadb-medium-scope-20261101/` に保持する。元archiveのdsc checksum照合と公式DEBのhash照合を用いたが、PGP署名・再現ビルドは未検証である。

自己レビューでは、検査helperのDEB digest条件が意図より弱い連鎖不等号だったことを発見した。実行時helperを保存し、実artifact・記録・既知の公式SHAが一致することと7バイナリを独立に再確認した。実sourceの条件を取り出す5試験で旧条件の2失敗を再現し、3者の等値を必須に修正後、通常・最適化実行の各5試験が成功した。修正前の証拠を修正後helperの実行結果に置き換えず、履歴と独立確認を `independent-artifact-and-guard-review.json` に残した。

## glibc HIGH 1件の条件と未完了

[CVE-2026-84243](https://security-tracker.debian.org/tracker/CVE-2026-84243)はLANGUAGEを用いたgettextのcatalog読込みの問題で、非C系locale・細工された読取可能catalog・環境変数の信頼境界が関係する。trixieの `2.41-12+deb13u4` は未修正の表示であり、**判定保留**とする。

- 固定候補と現行AWSのmanifestに一致するローカルcacheの双方で、UID10001、LANG=C.UTF-8、LANGUAGE/LC_ALL/LC_MESSAGES/LOCPATH未設定を観測した。Pythonの初期LC_MESSAGESはC、環境反映後はC.UTF-8だった。`locale -a` はC/C.utf8/POSIXのみ。一般的な英語・日本語locale名4件の設定は失敗した。
- 両imageのlibc SHAは `9792e3cbb541c8f44c7acf5f14f4022ea62998ecc787d326bed4d8b6547dfd92`。`/usr/lib/locale` と `/usr/share/locale` はroot所有0755、POSIX access ACLなし。検査した他の3配置pathは不在だった。この限定したpathのmetadataを全filesystemの書込み不可証明にしない。
- 共有Web定義55の読み取りでは旧manifest `sha256:6d4050ec19ba5d34740643d515436baa5dd27b99a912b9c20ad7a9af0812af06`、desired/running1。locale・外部ENVファイル等の対象overrideなし、image既定user、privilegedなし、追加capabilityなし、mount pointなし。ただし **実taskのroot filesystemはread-only設定ではない**。ローカルprobeのread-only制約と区別する。
- 既定設定、選択したsource loaderのAST、entrypoint/runtime_envのbytesを照合した。稼働中プロセスへのexec、実process localeや全native経路の測定は行っていない。Secrets Managerの値は取得せず、SDK応答中の選択外ENVは保存・表示していない。

[glibc 2.41のgettext実装](https://github.com/bminor/glibc/blob/glibc-2.41/intl/dcigettext.c)にはC系localeでLANGUAGEを使わない分岐がある。一方、[locale選択実装](https://github.com/bminor/glibc/blob/glibc-2.41/locale/findlocale.c)は絶対pathのlocale名も扱うため、一般名4件の失敗だけで追加・私有localeや全呼出しを除外できない。参照したupstream sourceは、正確なDebian修正済みsourceや実binary分岐の検証とは区別する。

既知のPython ELF268件と補助ELF3件を、GNU readelf 2.38で静的に調べた。直接の未定義gettext参照はllvmlite、psycopg同梱Kerberos3件、OS libstdc++、CPython shared libraryの計6ファイルだった。補助path1件の不在は機能不在・安全の根拠にしない。import/同名定義/不正ELFの対照も確認したが、静的同梱・間接呼出し・実入力の到達性まで判定していない。製品ELFは実行していない。

証拠は `tmp/glibc-language-boundary-20261101/` と `tmp/native-gettext-index-v2-20261101/`。最初のindex作成時のoptional pathコピー失敗は保存し、検証済み240行を同一parserで再利用して残りを解析した。検査用コンテナは作成した同じIDを観測・削除済み。次は外部入力がlocale/catalogへ渡る具体的な経路を優先し、必要な修正・運用条件を判断する。無関係な全ビルド入力の来歴証明を、新しい一律の公開条件として追加しない。

## dash LOW 2件の限定した起動経路レビュー

対象版はSARIF記録上 `0.5.12-12`。Debianは次の2件を未修正・unimportantとしているが、その表示だけで例外承認や全imageの非該当とはしない。

| CVE | 問題の条件 | first-party entrypointで確認できた範囲 |
| --- | --- | --- |
| [CVE-2026-102473](https://security-tracker.debian.org/tracker/CVE-2026-102473) | libc fnmatchを使わないbuildの内部matcherに、多数のstarを含むpattern等を渡す場合の過大な計算 | `case` のpatternは固定の真偽値・環境名・単独のcatch-all |
| [CVE-2026-102474](https://security-tracker.debian.org/tracker/CVE-2026-102474) | printf等へ特定のUnicode escapeを渡す場合の領域超過 | entrypointのecho引数は固定ASCIIの状態表示。printf・eval・shellの `-c` は使っていない |

レビュー対象は [docker/entrypoint.sh](../../docker/entrypoint.sh)、SHA256 `0e5d175e8a6678f0c85b94dbb41479fcc952af25cc440c2f3eda2ada86cd1c01`。候補と現行manifestのローカルcacheで同じbytesだった。固定case/状態表示の入力には上記の条件が見つからなかった。ただし `DAPHNE_APPLICATION_CLOSE_TIMEOUT` には引用符のない展開があり、運用側が設定する値のpathname展開は別途確認が必要である。`exec "$@"` で起動できる任意の管理コマンド、依存内部のshell利用、image全体の到達性も未判定。実dashのfnmatchビルド条件は未検証。CVE再現・DoS入力は実行していない。**両件の全imageへの適用範囲は判定保留**とする。

## 公開までの残作業と変更影響

1. 全53件について、古いCVE名の記載だけで終えず、最終配備image・実経路・影響・対処・再評価条件と対応させる。今回のMariaDB 5件の限定判定を、他のCVEの完了へ流用しない。
2. glibcのlocale/catalog信頼境界、gcc PBDS、dashを含む依存内部の利用条件を具体化し、必要な修正と検証を行う。新しい配布物・設定・依存が変われば対象とhashを再確認する。
3. 現行AWSは旧imageのままである。DB0065〜0069・code/staticの一体切替、復旧、実有料プラン・外部連携・性能・監視等、[元25条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を満たす。GitマージやCI成功を配備・公開の完了にしない。

製品コード・DB schema・料金・権限・保存期間・契約・公開日は変更なし。AWS/共有DB/実データ・Secrets/IAM・実Stripe・外部通知への書込みは0。文書の復旧は当該文書commitのrevertで足りる。全体テストは文書変更の検証としては再実行せず、差分・根拠・リンク・文字コードを確認する。今回の調査は正式公開可否や承認待ちのAWS操作を代替しない。
