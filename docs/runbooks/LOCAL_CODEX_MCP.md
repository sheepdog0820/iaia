# Codexでタブレノを参照する

CodexがタブレノのローカルMCPを起動します。タブレノのWebサーバーを起動せずに、既存のローカルSQLiteから次の卓と自分の探索者シートを参照できます。

## 設定

1. タブレノの仮想環境で `python -m pip install -r requirements.lock.txt -r requirements-mcp.txt` を実行します。
2. Codexのユーザー設定 `~/.codex/config.toml` に次の設定を追加します。Python、作業ディレクトリ、読み取るSQLiteファイルには絶対パスを設定します。`--username` にはそのDBで使用している本人のログイン名を指定します。
3. Codexで新しいチャットを開きます。

```toml
[mcp_servers.tableno]
command = "C:/path/to/iaia/.venv/Scripts/python.exe"
cwd = "C:/path/to/iaia"
args = ["-m", "tableno_mcp.server", "--database", "C:/path/to/iaia/db.sqlite3", "--username", "your-local-username"]
startup_timeout_sec = 30
```

macOS・Linuxでは、仮想環境のPythonのパスは通常 `.venv/bin/python` です。`codex mcp get tableno` で登録を確認できます。

## 利用例

- 「タブレノで次の卓はいつ？」
- 「自分の探索者シートを一覧にして」
- 「タブレノで〇〇の目星と現在SANを見て」

卓は本人が作成、担当、参加している予定と進行中の卓から、現在以降に開始する最も近い開催回を日本時間で返します。探索者は本人が所有するCoC 6版・7版のシートが対象です。詳細では能力値、HP・MP・SAN、技能値、装備名と個数を参照できます。

SQLiteは読み取り専用で開きます。Codexへ渡す項目はツールごとに決まっており、秘匿ハンドアウトやメモは含みません。設定はローカルファイルにアクセスできるPC所有者向けです。参照できるデータは指定したDBに保存されている範囲です。

設定を解除するときは `codex mcp remove tableno` を実行します。
