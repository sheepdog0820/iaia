# SQLiteのOS監査指摘の適用条件

2026-09-08、固定候補 `tableno-formal-release:10d21e42`（ID `sha256:dec00ade1cc08142732ee124b9082d2c19e88003cac4a40339d3efc302e69cf2`）のLOW 2件を確認した。

## 実測

ネットワークなし・読み取り専用・終了時削除のコンテナで、Python標準sqlite3モジュールとメモリ上の使い捨てDBを検査。終了0。実データには接続していない。再現用スクリプトはGit管理外の `tmp/inspect-runtime-sqlite.py`。

- インストール済みは `libsqlite3-0:amd64 3.46.1-7+deb13u1`。sqlite3コマンドはPATH上にない。
- PythonのSQLite実行時バージョンは3.46.1。`_sqlite3` は `/lib/x86_64-linux-gnu/libsqlite3.so.0` に動的リンクする。
- `pragma_function_list` と `pragma_module_list` のzipを含む名前はどちらも0件。
- `SELECT * FROM zipfile(NULL)` は `no such table: zipfile`。ファイルは読み込まない。

## 項目別評価

| CVE | 公式情報と固定候補の評価 |
| --- | --- |
| [CVE-2025-70873](https://security-tracker.debian.org/tracker/CVE-2025-70873) | SQLiteのzipfile拡張が細工されたZIPを処理する場合の情報漏えい。Debianはバイナリパッケージで当該拡張をビルドしないと注記。今回のPython接続でも拡張を利用できず、標準構成では条件不一致。後から拡張をロードする構成に変更した場合は再評価する |
| [CVE-2021-45346](https://security-tracker.debian.org/tracker/CVE-2021-45346) | 細工されたDBファイルに対するクエリで、想定外のレコード範囲を読めるとの報告。開発者は脆弱性という扱いに異議を唱えている。本番のDjango DB経路ではSQLiteを使わないが、ライブラリ自体は搭載されており、非該当を断定しない |

本番設定 `tableno/settings_production.py` はmysql/mariadb/postgres/postgresql以外のDB_ENGINEをRuntimeErrorで拒否する。ローカル設定 `tableno/settings.py` はSQLiteに対応するため、環境を区別する。accounts/schedules/scenarios/tableno/scriptsのPythonを `sqlite3.connect`・`load_extension`・`enable_load_extension` で検索し、一致なし。これは依存パッケージ内部や外部設定からのSQLite利用の不在証明ではない。

45346については、将来DBインポート機能やSQLiteを使う依存を追加する際、信頼できないDBファイルを開く経路を調査し、必要に応じて隔離・制限を検証する。今回、破損DBの攻撃再現試験やライブラリ全呼び出しの網羅検査は実施していない。

Debianはソースパッケージの両指摘をvulnerable/unfixedとしている。OSスキャン48件（HIGH 1 / MEDIUM 1 / LOW 40 / UNSPECIFIED 6）は維持し、抑制・例外承認・公開合格の扱いにはしない。既存評価と合わせLOW 17件の個別評価を記録し、未評価は23件。個別評価済みの項目にも未解決条件が残る。

アプリ・DB・Secrets・アクセス権・実環境・費用の変更はない。文書の差分・UTF-8/LF・日本語記述を検証し、アプリ変更を含まないためアプリテストは再実行しない。
