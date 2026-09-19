# 最新Stripe候補のOS監査

2026-09-19、候補 `6ff9a1f9b9fe965b2461de0694530d3e18ffda96` の配布イメージをDocker Scout 1.24.0で再スキャンした。対象は `tableno:stripe-candidate-6ff9a1f9`、イメージIDは `sha256:5e8f4f132ae472f0bd2a5d64c7019e501aab0303bfecfa9860f1769a64e7f702`。アプリのCI成功とは別の検査であり、正式公開No-Goを維持する。

## 結果と再現

```text
docker-scout.exe cves --only-package-type deb --format sarif --exit-code --output runtime-os-6ff9a1f9-20260919.sarif.json local://tableno:stripe-candidate-6ff9a1f9
```

既存SBOMキャッシュから259パッケージを索引化し、14パッケージ・35指摘（HIGH 1 / MEDIUM 1 / LOW 33）を報告した。終了コード1で、スキャン結果ファイルの出力は完了。指摘ID・パッケージ・修正版欄・SARIFハッシュを[結果JSON](RUNTIME_OS_6FF9A1F9_2026-09-19.json)に保存した。元SARIFはGit管理外の `C:/Users/endke/Workspace/iaia/tmp/runtime-os-6ff9a1f9-20260919.sarif.json`。deb限定であり、Python依存・アプリ経路や設定全体の安全性を証明するものではない。

旧候補a32b6a86の保存済みSARIFとID集合を比較すると、新規指摘は0、MariaDB関連のUNSPECIFIED 6件が消えている。ただし最新イメージ内の `libmariadb3` と `mariadb-common` はともに `1:11.8.6-0+deb13u1` で、過去記録と同じ。指摘が消えたことをパッケージ更新・修正済み・例外承認の証拠にしない。今回のスキャナー出力の変化として記録する。

## HIGHの更新情報

zlibのCVE-2026-85091は引き続きHIGH、fixed_versionはnot fixed。ネットワークなし・読み取り専用の一時コンテナで確認した `zlib1g` は `1:1.3.dfsg+really1.3.1-1+b1`。

9月8日の監査と異なり、[Debian追跡情報](https://security-tracker.debian.org/tracker/CVE-2026-85091)に[上流修正df84af25](https://github.com/madler/zlib/commit/df84af25dc1942490e1d1c899a07619152a46148)への参照が追加された。上流コミットは当該CVEへの対処を明記し、non-blocking gzwriteの失敗時に入力バッファの残量と参照先を戻す変更である。[上流Issue #1310](https://github.com/madler/zlib/issues/1310)もclosedになった。ただし取得できたページには解決コメント本文がなく、コミットの明示的なCVE参照を根拠とする。

Debianのtrixieパッケージ判定は依然vulnerableで、説明にある対象バージョンとパッケージ表の不一致も残る。上流の解決だけでは配布済みライブラリが修正済みとはいえない。次の判断には、修正の搭載版への適用範囲とDebianの対応状況の照合が必要。独自ビルドやバックポートを選ぶ場合はABI・Pythonの圧縮処理・画像処理等の回帰検証を伴う別の変更として扱う。指摘の抑制や未検証ライブラリへの置換は行っていない。

## MEDIUMと残る範囲

tarのCVE-2025-45582も残り、イメージのtarは `1.35+dfsg-3.1`。[Debian追跡情報](https://security-tracker.debian.org/tracker/CVE-2025-45582)は、同じ場所への連続展開とシンボリックリンクを使う条件、および上流が仕様として争っている旨を記載している。前回の限定的なソース検索を、全依存・運用経路の非該当証明へ広げない。

LOW 33件の過去の個別評価は[監査一覧](RUNTIME_OS_REVIEW_INDEX_2026-09-08.md)にあるが、最終イメージ・実配備条件への適用確認は残る。今回、AWS、main、共有DB、Secrets、権限を変更していない。一時検査コンテナは `--rm` で終了済み。実装候補・ローカルイメージを変更していないため、既存の反映承認案の対象SHAは変わらない。
