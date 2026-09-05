# Bootstrap 5.3.0

共通画面のタブ・モーダル・ナビゲーションを外部CDNへの到達性に依存させないため、従来参照していた5.3.0を同梱する。バージョン更新ではない。

取得元: npmのbootstrap@5.3.0（npm pack --ignore-scripts）。配布アーカイブのSHA-1は0718a7cc29040ee8dbf1bd652b896f3436a87c29。MITライセンスはLICENSEに収録。CSS/JSは配布ファイルを変更せず配置した。開発用source mapは含めない。

| ファイル | SHA-256 |
| --- | --- |
| bootstrap.min.css | 7f1d37f0d90b6385354c2ac10e2bb91563c46bd7a266ed351222ebcac8496c2a |
| bootstrap.bundle.min.js | aa53d582f97eb594c2a5cc5824574707f9ba9837bce3046bfa5f3556860f4e04 |
| LICENSE | 3d0b0c88216e4752b9afd3d24e36faaf27873b5a45a61458bb3c83e794c26832 |

templates/base.htmlからDjango static経由で参照する。Font AwesomeやAxios等の外部参照はこの変更の対象に含まれず、サイト全体のオフライン対応や全依存の安全性を示すものではない。
