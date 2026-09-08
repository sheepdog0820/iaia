# KerberosのOS監査指摘の適用条件

2026-09-08、固定候補 `tableno-formal-release:10d21e42`（ID `sha256:dec00ade1cc08142732ee124b9082d2c19e88003cac4a40339d3efc302e69cf2`）のLOW 4件を調査した。

## 固定イメージでの実測

ネットワークなし・読み取り専用・終了時削除のコンテナで検査し、終了0。再現用スクリプトはGit管理外の `tmp/inspect-runtime-krb5.py`。

- krb5ソース由来のインストール済みパッケージはlibgssapi-krb5-2・libk5crypto3・libkrb5-3・libkrb5support0。すべて `1.21.3-5+deb13u1`。
- kdb5_util・krb5kdc・kadmind・kadmin・kinitはPATH上にない。
- `/usr/lib` 以下にlibkdb*・libgssrpc*・libkadm*、kdbプラグインディレクトリはない。
- libpq.so.5はlibgssapi_krb5.so.2を参照し、推移的にlibkrb5・libk5crypto・libkrb5supportもロードする。クライアントライブラリを未使用と断定して削除することはできない。

## 項目別評価

| CVE | 公式情報と固定候補の評価 |
| --- | --- |
| [CVE-2018-5709](https://security-tracker.debian.org/tracker/CVE-2018-5709) | kadmin/dbutil/dump.cのDBダンプ処理。対象の管理ツールは未搭載で条件不一致。Debianも信頼された入力を扱う経路との注記があるが、今回の判定は管理機能の不在に基づく |
| [CVE-2026-11850](https://security-tracker.debian.org/tracker/CVE-2026-11850) | KDC/kadmindのLDAP KDBバックエンドが不正なkrbExtraDataを読む際の境界外読み取り。サーバー・KDBライブラリ・プラグインが未搭載で条件不一致。クライアントのLDAPライブラリ搭載とは区別する |
| [CVE-2024-26458](https://security-tracker.debian.org/tracker/CVE-2024-26458) | RPCのpmap_rmtcallにおけるメモリリーク。libgssrpcが未搭載。上流もkrb5内部から呼ばれない関数と説明しており、今回の標準搭載構成で該当経路を確認できない |
| [CVE-2024-26461](https://security-tracker.debian.org/tracker/CVE-2024-26461) | GSSAPIエンコード関数の境界チェック経路でのメモリリーク。対象ライブラリは搭載されるため、サーバー不在を理由に除外しない。DebianはAPI経由で到達できないと記載するが、今回その全入力条件を独立に検証していない |

[MITの上流説明](https://mailman.mit.edu/pipermail/kerberos/2024-March/023095.html)では26458の関数はkrb5内で未使用、26461はメモリ上有効なAPI入力で当該境界チェックに到達する可能性が低いと説明されている。後者は数学的な到達不能証明として扱わない。DB接続のGSSAPI交渉やネイティブAPIの全経路検証も今回は実施していない。

Debian上の対象バージョンは4件ともvulnerable。11850はsid/forkyの1.22.1-3で修正済みだが、今回のtrixieイメージが修正済みとはしない。ディストリビューションを混在させる更新や、必要なクライアントライブラリの削除は行っていない。

OSスキャン48件（HIGH 1 / MEDIUM 1 / LOW 40 / UNSPECIFIED 6）は維持する。これまでと合わせてLOW 21件を個別評価し、未評価は19件。評価済みの残条件も維持し、抑制・例外承認・正式公開合格には変更しない。構成変更時は再評価する。

文書のみの変更でDB・Secrets・権限・実環境・費用への変更はない。差分・日本語・UTF-8/LFを検証する。アプリコード変更を含まないためアプリテストは再実行しない。
