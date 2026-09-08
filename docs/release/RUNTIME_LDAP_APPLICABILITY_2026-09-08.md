# OpenLDAPのOS監査指摘の適用条件

2026-09-08、固定候補 `tableno-formal-release:10d21e42`（ID `sha256:dec00ade1cc08142732ee124b9082d2c19e88003cac4a40339d3efc302e69cf2`）の保存済みSARIFからOpenLDAPのLOW 5件を抽出し、Debianの各追跡ページと実バイナリを照合した。

## 実測

ネットワークなし・読み取り専用・終了時削除のコンテナでdpkgのインストール状態、コマンド/パスの存在、libldap.so.2の動的リンク先を確認した。検査終了0。

- LDAP/LMDB/NSS関連のインストール済みパッケージは `libldap2:amd64 2.6.10+dfsg-1` のみ。
- slapd・ldapsearch・mdb_loadはPATH上になく、`/usr/sbin/slapd`・`/usr/lib/ldap`・`/usr/bin/mdb_load`も不在。
- libldap.so.2はlibssl.so.3/libcrypto.so.3へリンクする。NSSライブラリへのリンクなし。
- Debianの3276注記はGnuTLSと記載しているが、今回の実測はOpenSSL。注記のビルド構成を現候補の実測として転記しない。

初回のdpkg-queryは未搭載パッケージを指定したため終了1だった。上記の再検査では全パッケージのインストール状態を取得し、名前の存在だけを搭載済みとは扱わなかった。証跡はGit管理外の `tmp/inspect-runtime-ldap.py`、`tmp/runtime-ldap-10d21e42.log`。

## 項目別の判定

| CVE | 公式情報の対象 | この固定イメージの評価 |
| --- | --- | --- |
| [CVE-2015-3276](https://security-tracker.debian.org/tracker/CVE-2015-3276) | NSSの暗号文字列処理 | NSS不使用で条件不一致。GnuTLSという古い注記ではなくOpenSSLへの実リンクで照合 |
| [CVE-2017-14159](https://security-tracker.debian.org/tracker/CVE-2017-14159) | slapdのPIDファイルと停止スクリプト | slapd未搭載で条件不一致 |
| [CVE-2017-17740](https://security-tracker.debian.org/tracker/CVE-2017-17740) | slapdのnops/memberofモジュール | slapd/モジュール用パスが不在。Debianもnopsをビルドしないと注記 |
| [CVE-2026-22185](https://security-tracker.debian.org/tracker/CVE-2026-22185) | LMDBのmdb_loadが不正入力で境界外を読む | mdb_load未搭載。DebianもOpenLDAP同梱ソースから当該ツールをビルドしないと注記 |
| [CVE-2020-15719](https://security-tracker.debian.org/tracker/CVE-2020-15719) | libldapが不一致SANのある証明書でもCNを確認する挙動 | クライアントライブラリの問題なので未搭載サーバーを根拠に除外しない。上流はRFC4513との整合を理由に争っているが、本用途の安全性は未確定 |

アプリ主要ディレクトリとdocker/scripts/infrastructureのPython・シェル・Terraform・YAMLをLDAP URL/認証設定名で検索し、一致なし。依存ロックにもpython-ldap/ldap3/pyldapはない。ただしネイティブ依存やリポジトリ外の設定からLDAPが利用されないことを証明する検査ではない。15719は実際のLDAP利用経路・証明書検証設定を確認し、必要なら厳格化とTLSの異常系試験を実施する。

スキャナーの48指摘（HIGH 1 / MEDIUM 1 / LOW 40 / UNSPECIFIED 6）は維持し、指摘を抑制しない。今回4件の条件不一致と1件の未解決を整理したが、OS全体の合格・例外承認ではない。curlの6件と合わせて個別照合が済んだLOWは11件、残るLOW 29件は引き続き評価する。

アプリ、DB、Secrets、アクセス設定、費用、実環境は変更していない。再ビルドでライブラリ構成が変わる場合は再評価する。
