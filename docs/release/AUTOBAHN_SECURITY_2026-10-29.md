# Autobahnの追加セキュリティ更新（2026-10-29）

PR #31の依存監査で、既存固定Autobahn26.7.1のCVE-2026-116579を新たに検出した。整形・Banditとは別の失敗であり、過去のPRの監査成功を現在の安全性の証拠にしない。本修正はmain945441ffを基点に分離し、PR #28/#29/#30/#31の製品変更を混ぜない。

[公式アドバイザリーGHSA-pjh6-c8mg-3x7m](https://github.com/crossbario/autobahn-python/security/advisories/GHSA-pjh6-c8mg-3x7m)では、opt-inのpermessage-brotliを有効にしたサーバーで、メッセージ上限の確認前にフレームが展開され、未認証クライアントがメモリー枯渇を引き起こす問題が説明されている。26.7.1が対象で、修正版は26.10.1以上。[公式26.10.1リリース](https://github.com/crossbario/autobahn-python/releases/tag/v26_10_1)と[PyPI配布](https://pypi.org/project/autobahn/26.10.1/)を確認した。現行アプリの該当拡張の有効化や実被害は未確認であり、検出除外で合格にしない。

## 変更とロックの確認

`requirements.txt`に`autobahn>=26.10.1`のセキュリティ下限を追加し、3ロックのAutobahnだけを26.7.1→26.10.1へ更新する。Twisted26.10.0rc2、Daphne4.2.3、他の依存の版・追加/削除は変更しない。

Python3.11.18・pip-tools7.6.1のLinux環境で、対象パッケージだけを指定して再解決し、ハッシュを生成した。初回はMySQLのビルド用メタデータが不足して停止したため、検証用イメージにpkg-configと開発ヘッダーを追加した。通常配布物へのツール追加ではない。

Linuxでの全体再生成では、既存のWindows/旧Python向けasync-timeout・coloramaが落ちたため、そのまま採用しなかった。生成されたAutobahnのブロックだけを採用し、33個のハッシュがPyPI JSONの全未取り消し配布物と一致することを検査した。他のパッケージブロックはバイト単位で不変である。

## 検証と残作業

3ロックのpip-auditは通常用111・開発用167・テスト用207パッケージすべて既知指摘0件。ハッシュ付きテスト用ロックのインストールと`pip check`も成功した。監査失敗の無視・CVE除外・依存条件の強制無効化は行わない。

関連するサーバー・entrypoint・診断保護・本番設定・システム試験は、更新済み依存の隔離PostgreSQLで84テスト・46 subtests成功、省略なし。通常配布物内の実HTTP/WebSocket/Redis確認、実インストールの監査・OS再監査・最終CIの結果はDraft PRへ記録する。過去のイメージや旧headの成功を今回の検証完了へ拡張しない。

DBスキーマ・実データ・OAuth/Secrets/権限・AWSリソース・費用・料金・保存期間・外部通知への変更はない。作業ブランチのpushはCIのみを起動する。mainマージは最終headと検証を示して別途承認を確認する。revert PRでは古い依存と監査不合格が戻る。OS50指摘・Twisted RC2・実環境の未完了条件と正式公開No-Goを維持する。
