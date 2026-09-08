# 実行用イメージのOS監査一覧

2026-09-08。固定アプリ候補10d21e42のスキャンは48指摘（HIGH 1 / MEDIUM 1 / LOW 40 / UNSPECIFIED 6）、終了2。一次評価の記録が揃ったことと、指摘の解決・例外承認・正式公開可否は区別する。現時点の正式公開判定はNo-Go。

## 記録の対応表

| 対象 | 件数 | 証拠・評価記録 |
| --- | --- | --- |
| curl | LOW 6 | [バックエンド条件](RUNTIME_CURL_APPLICABILITY_2026-09-08.md)。検査イメージは旧候補。最新候補とのOS指摘集合一致だけで全構成一致とはしない |
| OpenLDAP | LOW 5 | [サーバー/ツール不在、証明書検証の残条件](RUNTIME_LDAP_APPLICABILITY_2026-09-08.md) |
| systemd | LOW 4 | [サービス不在、journalライブラリの残条件](RUNTIME_SYSTEMD_APPLICABILITY_2026-09-08.md) |
| SQLite | LOW 2 | [ZIP拡張不在、DB入力の残条件](RUNTIME_SQLITE_APPLICABILITY_2026-09-08.md) |
| Kerberos | LOW 4 | [管理機能不在、GSSAPIの残条件](RUNTIME_KRB5_APPLICABILITY_2026-09-08.md) |
| TLS | LOW 2 | [物理攻撃条件、GnuTLSのTLS 1.0](RUNTIME_TLS_APPLICABILITY_2026-09-08.md) |
| glibc | LOW 7 | [入力制限・メモリ保護の残条件](RUNTIME_GLIBC_APPLICABILITY_2026-09-08.md) |
| 管理ツール | LOW 4 | [権限・apt-key・File::Temp](RUNTIME_ADMIN_TOOLS_APPLICABILITY_2026-09-08.md) |
| ファイル操作 | LOW 6 | [tar/coreutils/diffutils](RUNTIME_FILE_TOOLS_APPLICABILITY_2026-09-08.md) |
| zlib/tar/MariaDB | HIGH 1 / MEDIUM 1 / UNSPECIFIED 6 | [先行監査](RUNTIME_OS_AUDIT_2026-09-06.md)、[最新候補スキャン](RUNTIME_CANDIDATE_10D21E42_2026-09-08.md)。以前のイメージでの実測と最新スキャンを区別する |

## 次の作業

1. HIGHのzlibは、報告対象関数・搭載ソース・Debian判定の不一致を解消する証拠を得る。現段階で非該当の確定や抑制はしない。
2. GnuTLSはlibcurl → librtmp経路で残る。RTMPSの実利用と接続時設定を確認し、必要ならTLSの最低版を制限して互換性を検証する。
3. libldapの証明書検証、GSSAPI、journal、SQLite、File::Temp、glibc/CLI入力について、現在の外部入力からの到達経路を優先して調べる。直接呼び出しの検索結果を依存内部の非該当証明にはしない。
4. 旧イメージの構成を根拠にした項目は、最終配備するイメージで再照合する。再スキャンだけでは実行条件の確認を代替できない。
5. 実配備のプロセス権限・書き込み範囲・リソース制限・ログ保護を確認する。ローカルDockerの観測をAWSの証拠に流用しない。
6. 修正可能なものは更新・必要な検証を行い、残るものは具体的な到達条件・影響・回避策・再評価条件を揃えて判断材料にする。未評価件数が0でも自動的にリスクを受容しない。

この一覧は指摘の無視設定ではない。DB・Secrets・実環境・権限・費用の変更は行っていない。Stripe保留や外部連携・復旧検証など、OS監査以外の受け入れ条件も引き続き必要。
