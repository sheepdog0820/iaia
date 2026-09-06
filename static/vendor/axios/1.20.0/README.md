# Axios 1.20.0

全画面のHTTPクライアントが外部CDNの未固定バージョンに依存しないよう、ブラウザ用UMD配布物を同梱する。templates/base.htmlでDjango static経由で読み込む。静的配信が失敗した場合の既存fetch代替処理は維持する。

取得日: 2026-09-06。取得元: [npm axios 1.20.0](https://registry.npmjs.org/axios/-/axios-1.20.0.tgz)。[上流リリース](https://github.com/axios/axios/releases/tag/v1.20.0)と版を照合した。

アーカイブのSHA-512 integrityは `sha512-r8aOh8j9cGKpgQAqpzrUHnSIc6a59Y3Xf/cv8sy1DrHCkZHzQGEuoq1tARk6qSyDdtQGSDgpb9kFlruzPvrgwg==`、SHA-1は `515513445aa60e71d04b6521ca6210829ccb4786`。npmメタデータとの一致を確認し、下記ファイルを変更せず配置した。MITライセンスを同梱する。

| ファイル | SHA-256 |
| --- | --- |
| axios.min.js | 7c433c881c3b0903317193a0dd5af714ce0f65cf77d5c7f067f18b96f0e8e2c7 |
| axios.min.js.map | 15fd3ff1dae38f059a7d7be7b7cc1fa641d7833f93b62a1832eb9c5fa4f62ad1 |
| LICENSE | 82761059eaedacb3356803aea8a170d8298609f91b14fc32ee1bfb40d690183c |

取得時に別の一時ディレクトリでaxios@1.20.0をexact指定したlockfileを作り、npm auditの指摘0・終了0を確認した。同梱ファイルはアプリのpackage-lock.jsonの管理対象ではないため、通常のCIのnpm auditだけでは継続監査されない。更新時と公開候補の確定時には上流のセキュリティ情報・npm監査を再確認し、配布物のハッシュ照合、manifest収集、通常と代替クライアントのブラウザ検証を行う。
