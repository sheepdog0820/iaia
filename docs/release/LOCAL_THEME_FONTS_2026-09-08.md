# テーマフォントを外部通信なしで配信

共通CSSからGoogle Fontsへのimportを除き、InterとPoppinsのWOFF2を静的資材として同梱した。既存のweight・unicode-range・font-display: swapを維持し、CSSの参照URLだけを変更。19ファイル計429,332バイトで、出典・SHA-256・SIL OFL 1.1ライセンスをstatic/vendor/theme-fontsに保存した。利用者のブラウザからGoogleへのフォント要求をなくす。新規契約は不要だが、通常の静的配信量にフォントが加わる。

2026-09-08、ネットワークnone・公開ポートなしのDocker内でDjangoとPlaywrightを実行。専用コピーと合成SQLiteを使い、共有DB・実環境は変更していない。回帰テストは旧CSSで失敗後、変更後に成功。collectstatic/manifest検証2件も成功し、CSSの相対importとフォントURLの処理を確認した。

既存のゲスト参加・登録・引継ぎE2Eに、両ブラウザcontextでGoogle Fontsを遮断し外部要求0件を確認する検査と、Inter/PoppinsのFontFaceがloadedとなる検査を追加した。再試行0、既定30秒を維持。初回はChromium/Firefox成功、WebKitはフォント確認後の登録入力で失敗し、[自動フォーカスの問題](SIGNUP_FOCUS_2026-09-08.md)を特定して別コミットで修正した。修正後は3ブラウザすべて成功（51.6秒）。失敗した初回を合格には数えない。

Firefox/WebKitのモバイル幅の引継ぎカードを目視確認。日本語のラベル・説明・ボタンが読め、フォント変更による明らかな崩れは見られない。画像は合成データの引継ぎコードをマスクして保存。日本語のフォールバック指定とUI文言は変更していない。

証跡はGit管理外のtmp/local-fonts-fixed-run.logとtmp/offline-guest-candidate/test-results。Black/isort・差分・UTF-8/LFを確認し、ライセンスとファイル参照を自己レビューした。過去Firefox CIのload待ちの直接原因は未確定であり、今回の局所成功をCI全体成功とはしない。CIの最新SHA確認、実環境への反映は残る。実データ・DB・Secrets・アクセス権の変更はない。復旧はこのフォント同梱コミットを戻して静的資材を再配信する。
