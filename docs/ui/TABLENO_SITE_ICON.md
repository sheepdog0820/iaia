# タブレノのサイトアイコン

## デザインと対象

既存のナビゲーションにある20面ダイスと、青・藍色のアクセントを基に作成した。青〜藍色の角丸背景に白いダイスを大きく配置し、文字や数字を入れず小さなタブでも識別できる形にした。既存の画面内ロゴ・テーマ・名称は変更しない。

内蔵の画像生成機能で作成した画像を、PillowのLANCZOS縮小とICO形式変換で配信用サイズにした。生成元の原寸画像はローカルに保持し、リポジトリには512pxのマスターを保存する。

| ファイル（static/branding配下） | 用途 |
| --- | --- |
| tableno-icon-source-v1.png | 512×512、保守用マスター |
| favicon-v1.ico | 16×16・32×32・48×48を内包、タブ・ブックマーク |
| favicon-32-v1.png | 32×32、PNG対応ブラウザー |
| apple-touch-icon-v1.png | 180×180、iOSのホーム画面等 |

`templates/includes/site_icons.html` を共通レイアウト、独立した500エラー画面、Django管理画面から読み込む。Android/PWAのmanifestやアプリインストール機能は今回追加しない。

## 配信と安全性

- `/favicon.ico` はICOを直接返し、ログインへのリダイレクトやCDNへの転送をしない。
- `/site-icons/` は配信用3ファイルのみ返す。このルートからマスター画像や任意のパス・環境設定・ユーザーファイルは取得できない。マスター画像自体は公開ブランド素材で、通常の静的収集の対象に含む。
- 未ログインでも取得でき、GET/HEAD・ETagによる304・public max-age=3600のキャッシュに対応する。更新時はv2等の新しいファイル名と参照を使う。
- アプリと同じoriginから配信するため、S3/CDNの資格情報やmanifest取得失敗に依存しない。通常のcollectstaticでの収集も検証する。
- DBモデル、課金、ユーザーデータ、Secrets、OAuth、IAM、常設容量は変更しない。

## 検証記録（2026-10-04）

実装前の7テストで、未実装のルート・ファイル・テンプレート参照による失敗を確認した。実装後はサイトアイコン7件、静的収集2件、既存フォント5件、ナビゲーション1件の計15件が成功。配信モジュールの行・分岐カバレッジは100%。HEADと304の本文なし、ICOの3サイズ、PNGの実寸、公開ファイルの限定、未認証取得、管理/共通/エラー画面のリンクを確認した。

実データと隔離したローカルSQLite環境を127.0.0.1:8006で起動し、Chromeのログイン画面→利用規約の遷移とconsole error/warn 0を確認。ブラウザーによるICO取得はHTTP 200。操作用ブラウザーでは拡張機能がfaviconに操作中バッジを重ねるため、サイト自身のHTMLリンク・取得ログ・画像ファイルを区別して検証した。AWS/本番での表示は未確認。

## 生成プロンプト

Use case: logo-brand. Asset type: production favicon / browser tab and bookmark icon for タブレノ (Tableno), a Japanese tabletop RPG session manager. Primary request: create ONE square app icon, polished minimalist geometric 20-sided tabletop die symbol, original design, NOT a mockup or icon sheet. Existing app identity uses a d20 dice mark and blue #3b82f6 / indigo #6366f1 accents. A deep royal blue-to-indigo rounded-square tile fills the square canvas edge to edge; centered very bold clean white d20 silhouette with a small number of thick blue triangular facet lines, immediately recognizable at 16x16 and 32x32. Large die occupies about 76 percent of tile with balanced safe margin. High-contrast, near-flat, precise geometric edges, restrained blue-indigo color depth, no bevel. White die and a few simple facet divisions only, avoid dense triangulation. No letters, no numbers, no words, no surrounding decoration, no shadows outside tile, no lighting glints, no border, no transparency, no watermark. Deliver just the standalone square artwork.
