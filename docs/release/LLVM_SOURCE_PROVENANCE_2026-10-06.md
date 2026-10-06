# LLVM上流ソース署名・現在のnative入力再確認（2026-10-06）

## 結論

[先行のLLVMレシピ・ソース調査](LLVM_SOURCE_BOUNDARY_2026-10-06.md)で未確認だった、LLVM 22.1.0公式source archiveの署名付き来歴を検証した。公式JSONL bundleと既存のGitHub CLI 2.96.0を使用し、固定repository・workflow identity・OIDC issuer・tag・source/signer commit・GitHub-hosted runnerを指定した正例は終了0。誤identity・誤source digest・誤issuerの3負例はそれぞれ終了1で拒否した。

新しい証拠は **上流source tarballの生成・配布来歴**。numbaのconda archiveやllvmlite wheelのコンパイル来歴、実compiler headers・生成物・他native依存の全入力を証明しない。PBDS文字列不在をCVE非該当の確定にせず、HIGH3の抑制・リスク受容・解消判定を行わない。正式公開 **No-Go** を維持する。

アプリ固定候補は `39b432869372aa6c6c4619b8c5bc5bf23ebba6a4`、通常imageは `sha256:d100f388c5d764b647435cfb8a55085dbbc0be83ab6cbfefbe0f776ee911858e`。[通常配布物・実Sentry収集検証](SENTRY_RUNTIME_39B43286_2026-10-06.md)を変更せず使用した。今回の文書親は `5deb9b6da4313921a09b21ef95768940f799430e`。main/AWSへの追加反映はしていない。

## 署名subject・固定ソース・workflowの照合

[公式release](https://github.com/llvm/llvm-project/releases/tag/llvmorg-22.1.0)が案内する `gh attestation verify` を使用した。[source archive](https://github.com/llvm/llvm-project/releases/download/llvmorg-22.1.0/llvm-project-22.1.0.src.tar.xz)と[JSONL bundle](https://github.com/llvm/llvm-project/releases/download/llvmorg-22.1.0/llvm-project-22.1.0.src.tar.xz.jsonl)をTLS検証を迂回せず取得した。archiveは167,040,408 bytes、SHA-256 `25d2e2adc4356d758405dd885fcfd6447bce82a90eb78b6b87ce0934bd077173`。同梱conda recipe・[release asset metadata](https://api.github.com/repos/llvm/llvm-project/releases/tags/llvmorg-22.1.0)・署名subjectのdigestが一致した。

| 検証したclaim/条件 | 値 |
| --- | --- |
| predicate | `https://slsa.dev/provenance/v1` |
| source subject | `llvm-project-22.1.0.src.tar.xz` / SHA-256 `25d2e2ad…`（上記完全値） |
| repository | `llvm/llvm-project` |
| source ref | `refs/tags/llvmorg-22.1.0` |
| source/signer digest | `4434dabb69916856b824f68a64b029c67175e532` |
| cert identity | `https://github.com/llvm/llvm-project/.github/workflows/release-sources.yml@refs/tags/llvmorg-22.1.0` |
| cert OIDC issuer | `https://token.actions.githubusercontent.com` |
| runner | `github-hosted`、self-hostedを拒否する指定あり |
| Rekor Tlog timestamp | 2026-02-24 08:12:33 UTC |
| run invocation | [22341967379 / attempt 1](https://github.com/llvm/llvm-project/actions/runs/22341967379/attempts/1) |

[tag ref](https://api.github.com/repos/llvm/llvm-project/git/ref/tags/llvmorg-22.1.0)はannotated tag object `cf192f561b113a2c422197d92944d7852e0b2996` を指す。[tag object](https://api.github.com/repos/llvm/llvm-project/git/tags/cf192f561b113a2c422197d92944d7852e0b2996)のcommitは上記4434dabbと一致し、GitHub metadataのtag署名判定はverified/valid。これはCLIによるsource attestation検証とは別の照合結果として区別する。

[固定commitのrelease-sources workflow](https://github.com/llvm/llvm-project/blob/4434dabb69916856b824f68a64b029c67175e532/.github/workflows/release-sources.yml)はversion ref checkout後にexport.shでtarballを生成し、artifact uploadとsource attestationを行う。コンパイルしたconda package・wheel・アプリELFのbuild attestationではない。署名付きsourceを検証したことを、先行の公開wheel `publish/v1` がbuild provenanceに変わった証拠とも扱わない。

## CLI正例・負例と初回の誤指定

正例はarchiveとbundleを与え、`--repo`、`--cert-identity`、`--cert-oidc-issuer`、`--source-ref`、`--source-digest`、`--signer-digest`、`--deny-self-hosted-runners` を上表の値で指定した。検証結果からcertificate/subject/timestampを保持し、trust/TLS検証の無効化やbundle中のstatementだけの読み取りを成功証拠にしていない。GPG .sigは今回は取得・検証していない。

| ケース | verifier終了コード | 観測 |
| --- | --- | --- |
| 固定sourceと正しい全条件 | 0 | 上表のcertificate/subject/timestampを確認 |
| cert identityを合成の別workflowへ変更 | 1 | 署名検証拒否。表示はissuer検証の汎用エラーであり、内部の失敗箇所までは断定しない |
| source digestを40桁の0へ変更 | 1 | expected SourceRepositoryDigestと4434dabbの不一致 |
| issuerを合成 `https://example.test/wrong-synthetic-issuer` へ変更 | 1 | expected Issuerとtoken.actions.githubusercontent.comの不一致 |

負例のshell wrapperは期待するverifier終了1を確認して終了0。verifier自身の終了0と混同しない。archiveの改変負例は今回行っていない。正例結果のidentity.issuerにはregexp `.*` の表示もあるが、明示issuer条件・certificateの実値と上記issuer負例の拒否を確認しており、この表示だけでissuer固定を証明したとは扱わない。

初回のstrict commandは排他的な `--cert-identity` と `--signer-workflow` を同時指定し、flag検証で終了1。署名不正の判定ではない。重複する後者を除いて全条件を指定した正例・負例を完了した。CLIの認証設定やSecretsは変更していない。

## 再確認したソース・archive・現在のELF（新規来歴証明とは区別）

[公開conda archive](https://api.anaconda.org/download/numba/llvmdev/22.1.0/linux-64/llvmdev-22.1.0-manylinux_1.conda)の893,725,486 bytes・SHA-256 `c8603c82c26fb6b65c7bace30eaef09ce7287770d8e187ca5c93ec58b53e8c2d` を[Anaconda metadata](https://api.anaconda.org/package/numba/llvmdev)と再照合した。同梱recipeはmanylinux_1/build1/patches:null。後の固定b5a0ba74公開recipeのbuild0とは区別する。先行調査で固定f3dbf3bb recipeとの一致まで確認済みであり、今回それを新たな発見として数えない。同梱info/gitは空、hash_inputは空object。patches:nullでもbuild.shのsed変更があるため「完全無変更」とはしない。実compiler headers・当時のconda artifact digestとrunのbindingは引き続き未証明。先行のHTTP410/artifacts0の問い合わせは繰り返していない。

ZIP内の名前を確認し、指定したinfo/payload compressed tarと選定metadata・PriorityQueueヘッダーのみをGit外へ読み出した。全payload2,677 entriesを一覧化したが、全native payloadを再ハッシュした検証ではない。native binaryや同梱build/test scriptは実行・インストールしていない。

公式source全通常ファイルを新readerでstream読み取りし、先行結果と同じ168,946ファイル・2,023,461,242 bytes・省略0を確認。非通常entries15,814は内容走査しない（linkの追跡なし）。4 literal `__gnu_pbds` / `ext/pb_ds` / `binary_heap_` / `erase_fn_imps.hpp` の一致ファイル0、chunk境界の全marker合成正例・通常std::priority_queue負例は成功。各通常memberのread sizeとSHAを計算し、固定PriorityQueue headerを照合した。source全体ハッシュは別のdownload check/署名で確認する設計で、このreader単体のCLIにarchive全体digest引数・不一致拒否はない。先行readerのdigest不一致負例と混同しない。

condaとsourceの `llvm/ADT/PriorityQueue.h` は2,763 bytes・SHA-256 `df172d4a3b83ad759c04ebbd8dfdce4db199491d5e8b101aedb18a92f5737ca4` で一致し、std::priority_queueを使用する。この1ファイルや文字列不在だけで、生成code・forced include・compiler外部headers・他nativeを解決したCVE非該当とは判定しない。

通常39b43286 imageの267 ELFをRECORDと再照合し、unowned0・RECORD mismatch0・PBDS indicator files0。[先行1a738d2a再照合](RUNTIME_NATIVE_REVALIDATION_2026-10-06.md)の267ファイルとpaths差分0・SHA変更0。このbytes同一性は新しいnative build closureの証明ではない。

## Debian修正版・CIの現時点

同じ通常imageの使い捨てoverlayでsigned APT metadataを更新し、policyだけを確認した（package install/upgradeなし）。libstdc++6/libgcc-s1/libgomp1はinstalled=candidate `14.2.0-19`、zlib1gはinstalled=candidate `1:1.3.dfsg+really1.3.1-1+b1`。通常アプリimageやホストOSは変更していない。公式Debian trackerの [CVE-2026-102010](https://security-tracker.debian.org/tracker/CVE-2026-102010)、[CVE-2026-95619](https://security-tracker.debian.org/tracker/CVE-2026-95619)、[CVE-2026-85091](https://security-tracker.debian.org/tracker/CVE-2026-85091) も確認したが、対象の修正candidateは得られなかった。OS全体の新規scanは行わず、[直近Scout監査](SDK_LOG_RUNTIME_DC0B053E_2026-10-06.md)の39指摘（HIGH3/MEDIUM1/LOW35、Python0）/終了2を維持する。

CIはhead SHAと6 jobsを照合した。[39b43286 run37400351318](https://github.com/sheepdog0820/iaia/actions/runs/37400351318)は5success・Playwright failure。ログはWebKit account-deletion.spec.tsの確認clickに30秒timeoutを示し、290 passed/1 flaky・終了1。testが出したflaky分類であり、根本原因や製品不具合の不存在は断定しない。[5deb9b6d run37401541570](https://github.com/sheepdog0820/iaia/actions/runs/37401541570)は全6success、pytest2,285成功/85省略/coverage87.57%、Playwright291成功。親差分は文書2件のみでアプリ/test/workflowコード同一。後続成功を先行run成功やflake修正に読み替えず、今回文書commitのCI結果も未確認として区別する。

connectorのjob/check直接取得は未定義URL/許可endpoint制約で拒否、host ghログ取得は未認証で拒否された。認証や権限を変えず、既存connectorの専用job-log読取で上記ログを確認した。上流の消失artifact問題と、今回CIログの取得経路の問題を混同しない。

## 変更・承認境界・検証

repo変更はこの文書と[受け入れ条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)だけ。アプリ/lock/image・main/AWS・共有DB/実データ・Secrets/IAM・課金/継続費用/容量・外部通知への変更なし。通常imageの--rm診断コンテナ残存0、元checkoutの無関係13 itemsは保持。大容量archiveと検証工具はGit外で保持し、旧証跡は削除しない。文書復旧は当該commitのrevertで可能。既存favicon8567f49fの承認済み反映へ、後続変更の承認を追加しない。

文書関連39テスト成功（0.037秒）、変更2文書の相対参照212件/欠落0、固定workflow/CI照合snapshotを含む最終15ハッシュ一致、差分検査成功。署名付きsource生成の証明をcompiled bytesの全入力へ拡張しない観点で自己レビューし、修正を要する指摘なし。ステージ済み2文書のUTF-8/LF/BOMなし検査も成功。アプリ/UI変更なしのため全体ローカルtest・ブラウザー確認は行わない。正式公開に必要な実AWS/課金/外部連携/運用/性能/復旧/事業者体制の不足は維持する。

## 保持証跡

保存先は `D:/tmp/codex-tableno-native-closure-20261006`（Git外）。以下は実ファイルSHA-256。署名ログの要約は公開証明書・subject等であり、statementの転載だけをcrypto検証成功とは扱わない。

| ファイル | SHA-256 |
| --- | --- |
| llvm-project-22.1.0.src.tar.xz.jsonl | af52546636a389bf4a01a27e9c8a4c56d68a45a2bc45b39b822e82f3f998a6fa |
| llvm-source-download-check.json | dc3ae2a75b8f47936cdc8f7db8c8abb2724a8d16e130446ecafcd6dddb731cf9 |
| llvm-source-signature-strict.log | 5cfad1a24b387758364ec5ea4e98fe62b2bd58371d6c482ae69d3437a1f11a18 |
| llvm-wrong-identity.log | 2ca67e09bed7c06410222b4f873d67ddc7e01a6b76e896981e496dcf8c7b3f92 |
| llvm-wrong-source-digest.log | 111f9d381cc9574f02d3f5ddf5bc153f9f44847f1ba34c0d0271f1d4995519cc |
| llvm-wrong-issuer.log | b85b886bfaef70151afbfee1ab3be03f5e49fe16b4daea78473b29e41f1f2d83 |
| llvm-signature-flag-conflict.log | bc09584c68f57d56c56beb5b2d6a751b8d9072a6c1264476f7820d7ab2444489 |
| llvm-source-scan.json | f3dc45609e66cda6939e9de130497b7b745a10fdf508e302a12a639744247167 |
| scan_llvm_source.py | d90e6708a2238e816fbd3fa8f9c54b2117bda513f0bb3832f4fa2b0ec93f95e3 |
| native-comparison.json | c8c65e276b98acf32a66a1ac881cc817e2492e7c6e26ecac4e02b1c9bbffba2c |
| native-records-39b43286.json | eced44ffb6c9cbf9e08e451d78754659bc33aa634ead26c6e9dea79081f980ee |
| apt-policy.log | fd06bc63f85471f3e4ffca633c369e24c20f99d7280e531da65acce53473f17b |
| llvmdev-download-check.json | 79eb212bfe247f51dccca758c206ea59a653b48b60fd95ca1b3b995acb637a63 |
| primary-crosschecks.json | 42a52dd69af282992ab6876e9d2c076c982c27e28e7037a898b62e0b050ffc34 |
| release-sources-4434dabb.yml | a54959bdae5ba49d712b26e4b0a1541962611612faf4c560d1ecf7860bafe204 |
