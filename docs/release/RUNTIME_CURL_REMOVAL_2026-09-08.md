# 実行用イメージから不要なcurlを除去

確認日: 2026-09-08。ベースソースは `c8a5de97`。Dockerfileのapt導入対象からcurlを外す変更。

## 変更理由と使用経路

アプリ主要ディレクトリとDocker・依存定義を検索し、curl/pycurl/RTMPを使う処理は見つからなかった。追跡ファイル全体の検索で見つかった `deploy.sh` のcurlは、systemd/nginxを構成するホスト側スクリプトであり、今回変更するコンテナ内のコマンドではない。

TerraformのwebヘルスチェックはPythonのurllib.requestを使用する。AWSの `tableno-aws-pre:40` も読み取り専用のdescribe-task-definitionで同じコマンドと確認した。AWS設定・稼働イメージ・権限を変更していない。管理者が手動でコンテナ内curlを使う運用は利用できなくなる。必要なHTTP検査には既存のPythonを使用できる。

## 隔離した削除実験

元イメージ `tableno-formal-release:1edab4f2` から、ネットワークなしでcurlをpurgeする実験イメージを作成した。IDは `sha256:9d52967b8a0e615ca8218f553a98a16edde0484c7ff02ae759daea42e5b38e93`。

curl、libcurl4t64、libbrotli1、librtmp1、libgnutls30t64、libnghttp2-14、libnghttp3-9、libp11-kit0、libpsl5t64、libssh2-1t64、libtasn1-6の11パッケージが削除された。残るlibpq/libmariadb等は維持された。

- PostgreSQL 18.3・Redis 7と隔離した内部ネットワークで通常entrypointを起動。空DBへのマイグレーション、静的収集、6版・7版の画像HTTP14ケースと保存後の順序を確認した。すべて期待した結果で、所有コンテナ・ネットワークを削除した。
- ssl、psycopg、MySQLdb、Pillow、numpy、onnxruntime、rembg、requestsのimport成功。読み取り専用ルートではNUMBA_CACHE_DIRとXDG_CACHE_HOMEを使い捨て/tmp配下へ指定した。画像透過モデルの推論やモデル取得の試験ではない。
- 共有ライブラリをlddで照合。元838ファイル、削除後815ファイル。未解決リンクの10ファイルは元と同じ組であり、新たな欠落はない。wheel内ライブラリを単独でlddする制約や任意バックエンドもあるため、既存10件を動作不良とも安全とも断定しない。
- ctypesの検索でcurl・gnutls・rtmpは見つからなかった。

初回の補助スクリプトはpsycopg2という誤った依存名、inspect.pyという標準モジュールとの名前衝突、読み取り専用キャッシュで失敗した。依存ロックに合わせ、native_probe.pyへ改名し、Pythonの隔離モードと一時キャッシュで再検証した。初回失敗を成功件数へ含めない。

Docker Scout 1.24.0は272パッケージを索引化し、15パッケージに41件を検出。元48件との差分はcurlのLOW 6件とGnuTLSのLOW 1件の削除で、新規指摘なし。指摘の抑制設定を追加した結果ではない。スキャン時の一時アーカイブ削除警告は残り、レポートと専用キャッシュはGit管理外に保持した。今回は `--exit-code` を指定しておらず、終了0を脆弱性なしと解釈しない。

## 通常Dockerfileの再ビルド

Gitアーカイブの全要素が専用ディレクトリ内の通常ファイル・ディレクトリであることを検査して展開し、変更したDockerfileだけを反映した。通常のビルドを完了したイメージは `tableno-formal-release:no-curl`、ID `sha256:158c7301a238dc65e800d7979bb7bdc449e5792181aa64d1b8927f244f4c5b02`。

アプリ等553ファイルのSHA-256はアーカイブと一致し、ネイティブライブラリの未解決リンクも元と同じだった。Dockerfile自体は.dockerignoreで配布物から除外されるため、アプリファイルの照合対象には含めない。

通常イメージをアプリ0.25 CPU/512 MiB、隔離PostgreSQL 18.3・Redis 7で起動し、空DBのマイグレーション・静的収集が完了。画像HTTP14ケースすべてが期待どおりで、各版3件の保存と順序0・1・2を確認した。試験用リソースは所有ラベルを照合して削除した。実データは使用していない。内部HTTP・合成セッションを使うため、TLSや実ログインの試験とは区別する。

通常イメージのOSスキャン初回はキャッシュ初期化のタイムアウトで終了1、レポートなし。Scoutプロセスが残っていないことを確認して、別の専用キャッシュと `--exit-code` を指定して再実行した。268パッケージを索引化し、15パッケージに41件、終了2。内訳はHIGH 1 / MEDIUM 1 / LOW 33 / UNSPECIFIED 6で、削除実験とCVE・パッケージURL・深刻度の組が一致した。一時アーカイブ削除警告は出たが、SARIF生成は完了した。証跡 `os.sarif.json` のSHA-256は `3b03504b7fb43dceec819f6db7f34a012a83e8d9f0d6750394a5fba5c1b36000`。

通常イメージの証跡はGit管理外の `tmp/no-curl-runtime/`（source-match.json、links.json、http-results.log、server.log）。合成セッションやローカル設定はコミットに含めない。

ベースc8a5de97のCIは[PR](https://github.com/sheepdog0820/iaia/actions/runs/34207371278)・[push](https://github.com/sheepdog0820/iaia/actions/runs/34207365476)ともsuccessを確認済み。今回のDockerfile変更後のCIとは区別する。変更は導入対象1行と検証文書のみで、Python・JavaScript・UI文言の変更はない。Dockerfileに明示的なgitattributesのLF指定がなくGitの改行警告が出るが、今回の実ファイル・ステージ済みテキストはUTF-8/LF検査の対象とする。

## 制約と復旧

共有環境への反映、実DB/Secrets/権限/AWS資源/継続費用の変更はない。Dockerfileの1行を戻して再ビルドすればcurl導入を復元できる。稼働版を変更していないため、本番ロールバックは不要。

実外部連携、画像透過推論、全体負荷の同等性は今回の局所試験だけでは証明できない。OS指摘のHIGH/MEDIUMと他の残条件、正式公開の受け入れ条件は継続する。
