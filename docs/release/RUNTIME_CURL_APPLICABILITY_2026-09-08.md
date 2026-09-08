# curlのOS監査指摘と実行用イメージの照合

2026-09-08、保存済みOS監査のcurl LOW 6件について公式情報と実バイナリを照合した。対象は `tableno-runtime-build-deps:clean`、ID `sha256:ce8767d4e6dea73fc701a26098e3e4c4daa7626a91e698909d198d94778246ae`。最新アプリ候補そのものの再ビルド・再スキャンではない。

## 実測

ネットワークなし・読み取り専用・終了時削除のコンテナで `curl --version` と `ldd /usr/bin/curl` を実行し、双方終了0。

- curl/libcurl 8.14.1、Debianパッケージ表示 `8.14.1-2+deb13u4`。
- TLSはOpenSSL 3.5.7、SSHはlibssh2 1.11.1、LDAPはOpenLDAP 2.6.10。
- 動的リンク先にlibssl.so.3、libssh2.so.1、libldap.so.2を確認。wolfSSH・wolfSSL・libsshはリンク先にない。
- ローカル証跡は `tmp/runtime-curl-backends-20260908.txt` と `tmp/runtime-curl-links-20260908.txt`。Git管理外なので最終候補でも再実行して正式な証跡を保管する。

## 条件別評価

以下の「条件不一致」は上記固定イメージのcurlに限定した技術判断であり、他のライブラリ、外部DB、ホストOS、全アプリへの安全宣言ではない。

| CVE | 公式情報が示す条件 | 実測との照合 |
| --- | --- | --- |
| [CVE-2025-10966](https://security-tracker.debian.org/tracker/CVE-2025-10966) | wolfSSHバックエンドでSFTPのホスト確認が不足。DebianもwolfSSH不使用と注記 | libssh2のため条件不一致 |
| [CVE-2025-15079](https://security-tracker.debian.org/tracker/CVE-2025-15079) | libsshバックエンドのknown_hosts取り扱い。Debianはlibssh2と注記 | libssh2のため条件不一致 |
| [CVE-2025-15224](https://curl.se/docs/CVE-2025-15224.html) | libsshのSSH公開鍵認証でエージェントを誤って使用。上流はlibssh2を対象外と説明 | libssh2のため条件不一致 |
| [CVE-2026-9547](https://curl.se/docs/CVE-2026-9547.html) | libsshの鍵確認コールバック。上流はlibssh2およびCLIを対象外と説明 | libssh2のため条件不一致 |
| [CVE-2026-82208](https://security-tracker.debian.org/tracker/CVE-2026-82208) | wolfSSLのCAキャッシュと独自信頼ストアの組み合わせ。DebianはwolfSSL不使用と注記 | OpenSSLのため条件不一致 |
| [CVE-2025-14017](https://curl.se/docs/CVE-2025-14017.html) | legacy LDAPで並行通信時にTLS設定が混線。上流はOpenLDAPおよびCLIを対象外と説明 | OpenLDAPのため条件不一致 |

Debianのソースパッケージ表は取得できた5ページでtrixieをvulnerableと表示しており、注記や上流の適用条件と分けて読む必要がある。9547のDebianページは取得できず、上流アドバイザリーを参照した。

## アプリからの利用と限界

アプリ主要ディレクトリ、docker、scripts、infrastructure、GitHub Actionsで `curl` / `pycurl` / `libcurl` / `curl_cffi` を検索し、Dockerfileの導入指定だけが一致した。requirements・Compose・TerraformについてもPythonバインディング名を検索し一致なし。ただし依存ライブラリによる動的ロード、リポジトリ外の運用コマンドの不使用を証明する検査ではない。

スキャナー抑制・例外登録・パッケージ削除は行わない。保存済みの48指摘（HIGH 1 / MEDIUM 1 / LOW 40 / UNSPECIFIED 6）と終了2は維持し、この6件には適用条件の照合根拠ができたと扱う。残るLOW 34件、zlib HIGH、tar MEDIUM、MariaDB 6件の残条件は別途評価する。最終候補でバックエンドが変われば判定も再評価する。

今回は読み取り調査と文書化のみで、DB・Secrets・AWS・費用・アプリ動作への変更はない。
