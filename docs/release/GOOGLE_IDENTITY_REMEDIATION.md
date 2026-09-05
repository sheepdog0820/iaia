# Google認証・アカウント連携の修正条件

2026-09-05。公開阻害事項。ブラウザの確認フラグ修正（07c752db）だけでは完了していない。

## 再現した問題

google_authはIDトークン/認証コードのsub、userinfoのidをユーザー選択へ引き継がず、emailでget_or_createしてトークンを発行する。専用SQLiteと模擬Google検証結果で次を再現した。

1. 未連携の別Google IDが第三者ドメインの同じメールとemail_verified=Trueを返すと、既存利用者への認証が200となる。
2. 既存SocialAccount(provider=google, uid=固定ID)があっても、そのIDの現在のメールが別利用者のメールと一致すると、元の利用者ではなく別利用者IDを返す。

証跡は `tmp/test_google_identity_probe.py` / `tmp/google-identity-probe.log`。6608de6dの固定イメージ、外部通信なし、実在しない@example.testの利用者だけを使用した。新規2件はともに失敗した。実OAuthトークン・実利用者・実サービスへの攻撃は行っていない。

## 必須の振る舞い

- 固定IDを保持し、SocialAccountのprovider/uidを優先して利用者を選ぶ。同じIDのメール変更で別利用者へ切り替えたり、別利用者のメール確認状態を更新したりしない。
- 新規連携と既存IDログインを区別する。未連携IDでメールが一致するだけでは既存アカウントを取得しない。
- [Googleの説明](https://developers.google.com/identity/sign-in/android/backend-auth?hl=en)に従い、Gmailまたはhd付きの確認済みアカウントと第三者メールを区別する。第三者メールはemail_verified=Trueだけでは現在の所有権を保証できないため、既存の認証手段・メール確認等によってローカルアカウントの所有権を確認してから連携する。
- 追加確認が必要な利用者にも、登録・ログイン・明示的連携の導線、日本語API応答、再試行方法を用意する。Gmailだけに公開対象を縮小して完了扱いにしない。
- IDトークン、認証コード、アクセストークン、allauthブラウザの判定を揃える。欠落ID、未確認/非booleanフラグ、無効・失効トークン、発行者/対象クライアントの検証も確認する。
- 利用者・SocialAccount・メール確認・DRF Tokenの作成/更新を原子的に扱う。同時初回ログインで誤連携や不要アカウントを残さず、無効化された利用者へトークンを発行しない。内部例外・認証トークンをエラーレスポンスに含めない。
- 未連携の第三者メール、既存IDのメール変更、別ローカル利用者の存在、同時初回ログイン、認証済み利用者の明示的連携、確認後の再試行をテストする。実OAuthは専用アカウントと承認された設定で別途検証する。

これは修正条件と再現証拠であり、実装完了の記録ではない。6608de6dの全体テストや配備用イメージ起動が成功しても、この認証不備が解消したことにはならない。I01/Q04と正式公開判定は未達を維持する。

## 固定IDによる認証と追加確認の実装・隔離検証

2026-09-05、上記の再現に対するアプリ修正を実施した。

- APIの3方式すべてでGoogleのsub/userinfo idを保持し、既存SocialAccountを優先する。メール変更で別利用者へ切り替えず、別のメールを確認済みにしない。新規のメール照合はbooleanの確認済みフラグとGmail/hdの条件を満たす場合に限定する。
- 未連携の第三者メールには409とgoogle_link_confirmation_required、login_url/signup_url/connections_urlを返す。通常メール登録は無効なので、signup_urlもログイン画面を示す。初回はブラウザでGoogle登録とメール確認を完了し、既存利用者は既存の認証手段でログインして明示的に連携後、再試行する。APIは認証済み利用者のlink=trueも受け付ける。他人が所有するUIDの移動は409。
- ブラウザでは第三者メールを未確認としてallauthの確認フローへ渡す。GoogleのVERIFIED_EMAIL一律指定を削除し、メール認証設定が有効でもこの条件を迂回しない。連携画面のGoogle/Discord/Xボタンはprocess=connectを指定する。
- ブラウザで作られたメール未確認のGoogle連携が、APIログインによって確認を迂回しないよう、既存UIDでもローカルの確認済みメールを要求する。無効利用者には403でトークンを発行しない。
- IDトークンと認証コードの発行者・SDKによる対象クライアント検証を維持し、クライアント設定欠落時は503。アクセストークンは[Google OAuth2 tokeninfo](https://developers.google.com/resources/api-libraries/documentation/oauth2/v2/python/latest/)のaudience/issued_to、有効期限、userinfoとのuser_id一致を検証する。認証コード交換には10秒timeoutを追加した。エラーレスポンスと変更したログに例外本文・トークンを出さない。
- APIの利用者・連携・確認済みメール・トークン作成を1トランザクションにまとめ、競合時はロールバック後に再照合する。PostgreSQLの独立した2接続による同時初回ログインで、利用者・連携・確認済みメール・トークンが各1件となることを確認した。

検証は6608de6dの固定テストイメージに変更ファイルを読み取り専用で載せた隔離環境。SQLiteは83件成功・PostgreSQL専用の行ロック試験1件skip、PostgreSQL 16は84件成功・skipなし。双方28 subtests成功、既存の非推奨警告9件。新規resolverは76/76実行行をカバーし、Google API部分にも未実行行なし。分岐網羅率の主張ではない。Google・Discord・X APIと既存認証テストを含む。

allauthの実処理を通した6件で、第三者メール登録の確認待ち、同じUIDのメール変更、既存メールへの誤認証拒否、明示的連携、他人のUID移動拒否、描画した連携リンクを確認した。Googleの外部応答を隔離fixtureで代替し、メールはlocmemへ保存しており、実OAuth・実メール配送や目視ブラウザ試験の証拠ではない。

証跡: tmp/google-identity-red.log、tmp/google-identity-sqlite.log、tmp/google-identity-postgres.log、tmp/google-identity-coverage-False.json、tmp/google-identity-coverage-True.json。途中のブラウザ試験2失敗はfixtureにproviderがなかったためで、実providerのsociallogin生成経路を使って修正し、最終実行で成功した。

残る公開条件: 実Googleアカウントによる3方式と確認メール到達・再試行の検証、ブラウザ新規登録の同時実行を含む追加監査、最終候補の全体テスト/CI/配備用イメージ検証。今回の修正だけでI01/Q04を完了扱いにしない。DBスキーマ変更なし。実環境・OAuth設定・権限・費用の変更なし。復旧は当該アプリ変更のrevertで可能だが、旧版の認証不備を再導入するため公開版への復帰判断には用いない。
