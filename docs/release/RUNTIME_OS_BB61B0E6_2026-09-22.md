# 最新Stripe候補のOS再監査（2026-09-22）

対象は最新アプリ候補 `bb61b0e6244aa5c9726dca4b8b00c3dd29e9cf05` の通常配布イメージ `tableno:stripe-candidate-bb61b0e6`、イメージID `sha256:e2d81b173fd6e7b632c0c2990e198559d6a669442bce85e6c7e4530961616fd3`。旧候補6ff9a1f9の結果を最新候補へ読み替えず、同イメージを直接再スキャンした。

## スキャン結果

Docker Scout 1.24.0のWindows amd64公式配布物をGitHub Release APIから取得し、公開SHA-256 `1b7afb489e9224411fafe848eb5002cdc5c59a5cf2b77d6ccffcb44ffdf4f350` と一致することを確認して使用した。

```text
docker-scout.exe cves --only-package-type deb --format sarif --exit-code --output runtime-os-bb61b0e6-20260922-v124.sarif.json local://tableno:stripe-candidate-bb61b0e6
```

259パッケージを索引化し、14パッケージ・36指摘（HIGH 2 / MEDIUM 1 / LOW 33）。終了コードは2で、合格扱いにしていない。元SARIFはGit管理外の `C:/tmp/runtime-os-bb61b0e6-20260922-v124.sarif.json`、SHA-256は `e970d0a297894c0113b10fc03e2b6d1e43125dd18e14a9e0af56c03d124a9ac5`。要約を[結果JSON](RUNTIME_OS_BB61B0E6_2026-09-22.json)に保存した。

9月19日の旧候補監査と比べ、LOW 33件とtar・zlibの指摘は同じ。新たにPerlのCVE-2026-82560がHIGHとして加わった。これは候補イメージが変わったためではなく、更新された脆弱性データで同じパッケージ集合を再評価した結果である。

## HIGH 2件の評価

### CVE-2026-82560（Perl Pod::Text）

[Debian追跡情報](https://security-tracker.debian.org/tracker/CVE-2026-82560)は、攻撃者が用意したPOD文書をPod::Text 6.1.1未満で整形すると、入れ子の`=over`によりCPU・メモリ枯渇へ至る問題としている。trixieのPerlは未修正判定。

候補内にあるバイナリパッケージは `perl-base 5.40.1-6+deb13u1`。ネットワークなしの一時コンテナで `Pod::Text` モジュールと `pod2text` コマンドが存在しないことを確認した。リポジトリの実行コードにもPerl、Pod::Text、pod2textの起動経路はない。したがって、説明されたPOD整形経路はこの配布物に存在しないという限定的な証拠がある。

ただしDocker ScoutはDebianのソースパッケージ単位でHIGHを報告し、終了コードも非ゼロのまま。全Perl経路の安全性や将来の依存追加を証明するものではないため、指摘を削除・抑制せず、正式公開のセキュリティゲート通過とも扱わない。

### CVE-2026-85091（zlib）

[Debian追跡情報](https://security-tracker.debian.org/tracker/CVE-2026-85091)では、trixieの `1:1.3.dfsg+really1.3.1-1` を引き続きvulnerable・unfixedとしている。候補の `zlib1g` は `1:1.3.dfsg+really1.3.1-1+b1`、実行時zlibは1.3.1。

アプリソースには問題のC APIであるgzwrite/gzprintf/gzvprintfの直接呼び出しがなく、Pythonのgzip試験はPython標準のzlibバインディングを使う。9月19日の書き込み停止試験でも限定した経路は後続出力を拒否した。しかし間接依存やC拡張を含む全到達可能性、部分書き込み、エラー解除後の経路は未証明。Debianの修正版がないため未解消として維持し、独自バックポートや未検証ライブラリ差し替えは行わない。

## MEDIUMとベース更新確認

tarのCVE-2025-45582は `tar 1.35+dfsg-3.1` に残る。[Debian追跡情報](https://security-tracker.debian.org/tracker/CVE-2025-45582)は、同じ場所への2回の展開とシンボリックリンクを必要とし、上流が仕様として争っている旨を記載する。アプリ実行コードにtar展開はないが、パッケージ自体は配布物に残るためMEDIUM未解消とする。

2026-09-22に `python:3.11-slim` の最新digest `sha256:da047cb8f9d1d98e5c070f5300ba9f7274e33b8fc0e5be5ed88740aed1b95ba9` を取得したが、zlibとtarの版は候補と同じだった。単純なベース再ビルドではHIGH/MEDIUMを解消しない。

今回の確認でアプリ、イメージ、main、AWS、共有DB、Secrets、権限は変更していない。正式公開はNo-Goを維持する。

## AWS・mainの再確認

2026-09-22 09:10 JST頃、GitHubの `origin/main` は `d875d028ede0b3172780d54d4baacdb226a1d3b3`。開発AWSはECS定義49、CPU256・メモリ512、稼働イメージdigest `sha256:59542e45e5dc8e1e33cbf7202eb12911ffbb390156a778fe7eb11f0fe4c65f79`、desired/runningは1/1、readinessのdatabase/cacheはok。RDS PostgreSQL 18.3はavailable、バックアップ保持7日、最新復元可能時刻は2026-09-22 00:14:01 UTCだった。

8時台のECSイベントは既存定義49の夜間再開であり、bb61b0e6の反映ではない。最新Stripe候補はmain・AWS・共有DBへ未反映のまま。反映案、Web増強、Stripeキー、常設worker/beat/Redisは引き続きそれぞれの承認待ちである。
