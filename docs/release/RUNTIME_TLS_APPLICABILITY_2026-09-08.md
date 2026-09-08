# TLSライブラリのOS監査指摘の適用条件

2026-09-08、固定候補 `tableno-formal-release:10d21e42`（ID `sha256:dec00ade1cc08142732ee124b9082d2c19e88003cac4a40339d3efc302e69cf2`）のLOW 2件を調査した。

## 実測

ネットワークなし・読み取り専用・終了時削除のコンテナで検査した。`tmp/inspect-runtime-tls.py`（Git管理外）は終了0。TLS接続や実データ操作は行わない。

- CPUアーキテクチャはx86_64。PythonのsslはOpenSSL 3.5.7を使用する。
- libssl3t64は `3.5.7-1~deb13u2`、libgnutls30t64は `3.8.9-3+deb13u4`。
- `ssl.create_default_context().minimum_version` はTLSv1_2。
- [GnuTLS公開API](https://www.gnutls.org/manual/html_node/Core-TLS-API.html)のpriority_initにNULL（既定値）またはNORMALを渡し、priority_protocol_listで列挙したところ、いずれもTLS1.3/TLS1.2/TLS1.1/TLS1.0/DTLS1.2/DTLS1.0を返した。

この列挙は優先順位設定の検査であり、実際の接続でTLS 1.0が成立した証拠ではない。一方、GnuTLSの既定値がTLS 1.2以上に限定されるとの判断はできない。

インストール済みパッケージの逆依存はlibcurl4t64 → librtmp1 → libgnutls30t64。librtmp.so.1のlddでもlibgnutls.so.30へのリンクを確認した。curl本体のHTTPSバックエンドがOpenSSLでも、この別経路は残る。別候補のlibsrtパスを調べた初回コマンドはファイル不在で終了1、実在するlibrtmpでの再検査は終了0だった。RTMPSの実利用や接続時の暗号設定はまだ検証していない。

## 項目別評価

| CVE | 公式情報と固定候補の評価 |
| --- | --- |
| [CVE-2010-0928](https://security-tracker.debian.org/tracker/CVE-2010-0928) | OpenSSL 0.9.8iをLEON3 SoC/FPGA上で使用し、電源電圧を操作する物理的な故障注入攻撃の報告。今回のx86_64/OpenSSL 3.5.7は報告対象構成と一致しない。Debianは故障注入がOpenSSLの脅威モデル外と注記するが、これは全ハードウェアの耐タンパー性の証明ではない |
| [CVE-2011-3389](https://security-tracker.debian.org/tracker/CVE-2011-3389) | 古いTLSのCBCに関するBEAST。Debianはgnutls28をvulnerable/unfixedとし、より新しいTLSの利用を案内している。今回GnuTLSの既定値にTLS 1.0が残るため未解決。Pythonの最低TLS版だけで他ライブラリまで除外しない |

## 残作業と判定範囲

実際にGnuTLSを呼び出す依存経路・有効な接続設定を確認し、必要な経路でTLS 1.2以上を強制して互換性を検証する必要がある。ライブラリの設定列挙だけを理由に、アプリがBEASTで攻撃可能とも断定しない。外向き通信全般、公開HTTPS終端、DB TLSの交渉条件は別途実環境で検証する。今回、全体の暗号設定を独断で変更していない。

OSスキャン48件（HIGH 1 / MEDIUM 1 / LOW 40 / UNSPECIFIED 6）は維持する。個別評価はLOW 23件、未評価は17件。評価済みの未解決条件も維持し、指摘抑制・例外承認・正式公開合格には変更しない。

文書のみの変更で、DB・Secrets・権限・実環境・費用への変更はない。差分・日本語・UTF-8/LFを確認し、アプリテストは再実行しない。
