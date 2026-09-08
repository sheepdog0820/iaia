# テーマフォントの自己配信

Inter（300/400/500/600/700）とPoppins（400/500/600/700）をGoogle Fontsの2026-09-08配信CSSから取得し、同じfont-face・unicode-range・font-display: swapで配信する。ブラウザからGoogleへのフォント要求をなくし、外部応答をページ読み込みの前提にしない。

WOFF2の内容は変更していない。19ファイル、計429,332バイト。重複URLは1ファイルにまとめた。出典URL・SHA-256・サイズはsources.json、ライセンスはInter-OFL.txtとPoppins-OFL.txtに保存。いずれもSIL Open Font License 1.1。再配布時も著作権とライセンスを保持する。

fonts.cssのURLだけをローカル相対パスに置換した。共通CSSの相対importとともにDjango collectstaticのmanifest書き換え対象になる。更新時は出典・ライセンス・ハッシュ・必要なweightを照合し、collectstaticと外部通信なしのブラウザ検証を行う。
