# glibcのOS監査指摘の適用条件

2026-09-08、固定候補 `tableno-formal-release:10d21e42`（ID `sha256:dec00ade1cc08142732ee124b9082d2c19e88003cac4a40339d3efc302e69cf2`）のLOW 7件を調査した。

## 実測と調査範囲

ネットワークなし・読み取り専用・終了時削除のコンテナで `getconf GNU_LIBC_VERSION`、dpkg-query、id、カーネル/プロセス状態を読み、終了0。

- glibcは2.41、libc6とlibc-binは `2.41-12+deb13u3`。
- uid/gidは10001（tableno）、有効capabilityは0。
- ローカルDockerホストの `randomize_va_space` は2、検査プロセスのSeccompは2。
- NoNewPrivsは0だったため、権限昇格禁止が設定済みとは報告しない。ここでのプロセスは検査用catであり、実環境のDaphneではない。

これらはローカルで今回起動したコンテナの観測値である。AWSのホストや実稼働タスクの設定・ASLRの強度・回避不能性を証明する値ではない。

accounts/schedules/scenarios/tableno配下のPython（test*とmigrations/**を除外する指定）をglob/rglob呼び出し、regexec/regcomp、subprocess、os.system、shell=Trueで検索し、一致なし。依存パッケージ内部のネイティブ呼び出し、別ディレクトリの管理スクリプト、外部入力の全経路は未検証。Pythonのパターン処理とglibcのPOSIX APIを同一の実装とみなさない。

## 項目別評価

| CVE | Debianの説明と本候補で残る条件 |
| --- | --- |
| [CVE-2010-4756](https://security-tracker.debian.org/tracker/CVE-2010-4756) | 細工されたglob式によるCPU/メモリ消費。DebianはPOSIXの挙動としてアプリ側で制限が必要と記載。主要アプリに直接呼び出しは見つからないが、ライブラリは搭載。信頼できない式がネイティブglobへ渡る経路の有無は未確定 |
| [CVE-2018-20796](https://security-tracker.debian.org/tracker/CVE-2018-20796) | POSIX正規表現の特定パターンで制御されない再帰。主要アプリにregexec/regcompの直接利用は見つからないが、依存内部まで非該当とは判定しない |
| [CVE-2019-9192](https://security-tracker.debian.org/tracker/CVE-2019-9192) | 20796とは別パターンの正規表現再帰。同じく入力からネイティブAPIまでの全経路は未検証。上流の異議だけで除外しない |
| [CVE-2019-1010022](https://security-tracker.debian.org/tracker/CVE-2019-1010022) | 別のスタックバッファオーバーフローを前提とするstack guard回避。非rootや有効capability 0でもメモリ破損の不在は保証できず、残リスクとして維持 |
| [CVE-2019-1010023](https://security-tracker.debian.org/tracker/CVE-2019-1010023) | 細工されたELFにlddを実行する経路。主要アプリに外部コマンド実行は見つからない。監査でのldd対象は固定イメージ同梱ライブラリに限定しており、利用者が送った実行ファイルの解析ではない。将来ファイル解析機能を追加する際は再評価 |
| [CVE-2019-1010024](https://security-tracker.debian.org/tracker/CVE-2019-1010024) | スレッドのスタック/ヒープキャッシュを使ったASLR回避。randomize_va_space=2はASLR有効の観測にとどまり、この回避が不可能との証明には使わない |
| [CVE-2019-1010025](https://security-tracker.debian.org/tracker/CVE-2019-1010025) | pthreadで作成したスレッドのヒープ位置の推測。前項と同様、ローカル設定値だけで除外しない |

Debianは対象バージョンの7件をvulnerable/unfixedと記載している。2019-1010022〜1010025は上流がセキュリティ問題として扱わないとの注記があるが、本サービスのリスク受容を代行するものではない。今回、攻撃パターンによる負荷試験やメモリ破損の再現は実施していない。

## 次の評価と完了条件

glob/正規表現は実際の外部入力経路を特定した場合に長さ・実行時間・隔離の検証を行う。メモリ保護回避はネイティブ依存の修正状況と実配備の制限を合わせて評価し、非rootだけで安全とは判定しない。glibcを独自パッチや別ディストリビューションのバイナリへ交換する変更は行っていない。

今回7件の条件を整理したが、修正済みや非該当確定にはしていない。LOW個別評価は30件、未評価は10件。OSスキャン48件（HIGH 1 / MEDIUM 1 / LOW 40 / UNSPECIFIED 6）と評価済みの残条件を維持する。指摘抑制・例外承認・正式公開合格は行っていない。

文書のみの変更でDB・Secrets・権限・実環境・費用への変更はない。差分・日本語・UTF-8/LFを確認し、アプリテストは再実行しない。
