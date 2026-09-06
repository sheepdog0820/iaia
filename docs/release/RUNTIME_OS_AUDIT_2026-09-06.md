# 配備候補のOSパッケージ監査

2026-09-06、通常Dockerfileで作成した候補0b0cea6fec716ed7dfda15546b471c9e90cc0d34を監査した。Pythonとnpmの監査成功だけではOSパッケージの確認にならないため追加した検査である。指摘の修正完了・例外承認・本番公開可とは判定しない。

## 対象と再現

- イメージ: `tableno-formal-release:0b0cea6f`
- イメージID: `sha256:5d2c113a6488c0c772f798b250ef45d59878ac110c9cef851e0a677a29cfedd1`
- Docker Scout CLI: 1.5.0。実行時に1.24.0への更新案内あり。最新版による再評価は未実施。
- コマンド: `docker scout cves --only-package-type deb --format sarif --exit-code --output tmp/runtime-os-0b0cea6f.sarif.json local://tableno-formal-release:0b0cea6f`
- 終了コード: 2。SBOMの索引366パッケージのうち、指摘されたソースパッケージ20、脆弱性ルール113件。
- 重大度: High 1、Medium 1、Low 105、Unspecified 6。全ルールのfixed_versionはnot fixed。これは取得した監査情報の表示であり、すべての実行経路が脆弱という意味でも、リスクを受容できるという意味でもない。
- SARIFのSHA-256: `4ec9ea24bc5c2e63d77e03991b704c591d16b07d7443890aabe4a72fdb1f58aa`
- ローカル証跡: `tmp/runtime-os-0b0cea6f.sarif.json`、`tmp/runtime-os-0b0cea6f-scout.log`、`tmp/runtime-os-0b0cea6f-packages.txt`。これらはGit管理外のため、配備承認時には候補を再監査し、正式な証跡保管先へ保存する。

## 優先指摘の調査

### High: CVE-2026-85091 / zlib

[Debianの追跡情報](https://security-tracker.debian.org/tracker/CVE-2026-85091)の説明は1.3.1.2から1.3.2のgz_vacate関数を対象としている。一方、同じページのパッケージ表はtrixieの1.3.1もvulnerableとし、注記にcheck detailsが残る。[上流の修正](https://github.com/madler/zlib/commit/e3dc0a85b7032e98380dec011bc8f2c2ee0d8fca)はgzwrite.cでNULLポインターの判定を追加している。

候補内のzlib1g/zlib1g-devは `1:1.3.dfsg+really1.3.1-1+b1`。PythonのZLIB_VERSIONとZLIB_RUNTIME_VERSIONはいずれも1.3.1。[Debian公開ソースのgzwrite.c](https://sources.debian.org/src/zlib/1%3A1.3.dfsg%2Breally1.3.1-1/gzwrite.c/)を取得したところ、gz_vacateは存在せずgzvprintfは存在した。取得ファイルは19,237バイト、SHA-256は `469b1e58932ea11bdda2a153f6655f7b3c13254240fae157181b49ed1bc93b47`、ローカル保存先は `tmp/debian-zlib-1.3.1-gzwrite.c`。

以上は適用範囲に食い違いがある証拠であり、誤検知の確定ではない。Debianのパッチ一覧は取得に失敗しており、実バイナリと適用済みソースの照合は未完了。指摘を抑制せず、パッケージ提供元の判定更新と最終候補の再監査を公開前の残条件とする。

### Medium: CVE-2025-45582 / tar

候補にはtar `1.35+dfsg-3.1` がある。[Debianの追跡情報](https://security-tracker.debian.org/tracker/CVE-2025-45582)は、同じディレクトリへ連続して展開する不正なアーカイブとシンボリックリンクを説明し、上流の仕様どおりとして争われている指摘と記載する。

accounts/api/schedules/scenarios/support/tableno/scriptsのPython・シェルを対象にtarfile、extractall、unpack_archive、gzprintf、gzvprintf、gzwriteを検索し一致なし。ただし依存ライブラリや全運用経路の到達不能を証明する検索ではない。利用者提供アーカイブの取り扱いと運用スクリプトの展開先分離を最終候補で確認する。現時点では例外承認していない。

### UnspecifiedとLow

Unspecified 6件はMariaDBソースパッケージに対応するCVE-2026-47023、60184、60331、60585、60747、61081。dpkg一覧にはクライアントライブラリ・開発パッケージ・commonがあり、MariaDBサーバーパッケージは見当たらない。これだけでクライアントへの非該当とは判定せず、各CVEの対象コンポーネントとの照合を残す。

Low 105件は個別の適用範囲・緩和策を未評価。Dockerfileではbuild-essentialなどのビルド依存も最終イメージに残る。ランタイムからの除去は改善候補だが、必要な共有ライブラリを壊さないビルド・起動・機能検証を伴う別の修正単位で扱う。件数を減らす目的だけでパッケージを削除しない。

## 影響と残条件

今回は読み取り監査と文書化のみ。アプリ、DB、Secrets、AWS、課金設定、配備候補の内容は変更していない。既存の読み取り専用AWS検査の承認依頼も未実行のまま。この監査で新たな未解決事項が判明したため、同候補の公開承認には本記録を含める。

公開前には、最新のスキャナー・脆弱性情報と固定した最終イメージで再検査し、Highの適用範囲の不一致、MariaDB各項目、残るLowを評価する。修正可能なものは修正・再検証し、残るリスクは根拠と緩和策を示して公開責任者の判断対象にする。自動スキャンの終了2を成功へ読み替えない。
