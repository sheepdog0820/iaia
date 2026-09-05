# Bootstrap 5.3.0

共通画面のタブ・モーダル・ナビゲーションを外部CDNへの到達性に依存させないため、従来参照していた5.3.0を同梱する。バージョン更新ではない。

取得元: npmのbootstrap@5.3.0（npm pack --ignore-scripts）。配布アーカイブのSHA-1は0718a7cc29040ee8dbf1bd652b896f3436a87c29。MITライセンスはLICENSEに収録。CSS/JSは配布ファイルを変更せず配置した。参照先source mapも公式配布のまま同梱し、ManifestStaticFilesStorage/S3ManifestStaticStorageのcollectstatic時に参照切れを起こさないようにする。source map追加時にnpmメタデータのSHA-512 integrityとSHA-1を再照合した。

| ファイル | SHA-256 |
| --- | --- |
| bootstrap.min.css | 7f1d37f0d90b6385354c2ac10e2bb91563c46bd7a266ed351222ebcac8496c2a |
| bootstrap.bundle.min.js | aa53d582f97eb594c2a5cc5824574707f9ba9837bce3046bfa5f3556860f4e04 |
| LICENSE | 3d0b0c88216e4752b9afd3d24e36faaf27873b5a45a61458bb3c83e794c26832 |
| bootstrap.bundle.min.js.map | 29f50fad80f38445bdaea573a5fbd6c98f31c06b63e0f6a8711547fe8da00de2 |
| bootstrap.min.css.map | 68ae84685ddbce0297bbcea4b470bdf0c94f78b4254bddc154a4a38673852f03 |

templates/base.htmlからDjango static経由で参照する。Font Awesomeは別ディレクトリに同梱。Axios等の外部参照もあり、サイト全体のオフライン対応や全依存の安全性を示すものではない。
