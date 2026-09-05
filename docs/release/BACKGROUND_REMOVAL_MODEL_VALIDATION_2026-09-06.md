# 背景透過のモデル選択と隔離実推論

## 修正理由

唯一の有料機能となった背景透過を調査したところ、アプリが`rembg.remove`にモデルを渡していなかった。実際に固定依存rembg 2.0.81のsession_factoryを読み、既定が`bria-rmbg`であることを確認した。[BRIA RMBG-2.0の公式説明](https://huggingface.co/briaai/RMBG-2.0)は商用利用に別契約が必要としている。本タスクでは契約していないため、その既定に依存した正式公開は進められない。

`new_session("u2net", providers=["CPUExecutionProvider"])`を明示し、モデル初期化失敗時には別モデルへ切り替えない。[U²-Netの公式リポジトリ](https://github.com/xuebinqin/U-2-Net)と[Apache-2.0ライセンス](https://github.com/xuebinqin/U-2-Net/blob/master/LICENSE)を確認した。ライブラリの更新だけで利用モデルが変わることも防ぐ。

## 検証

- 明示モデル選択と初期化失敗時の既定モデル不使用の2テストが変更前に失敗。修正後は背景透過ジョブ関連を含む25件成功、9 warnings（tmp/background-model-red.log、同-green.log）。Black・isort・Flake8を確認。
- 本番用イメージtableno-formal-release:704c6f06の非rootユーザーに、修正したbackground_removal.pyだけを読み取り専用で差し替えた。依存ロックとこの関数以外の推論環境は同一。1 CPU、メモリ2 GiB、memory-swapも2 GiBに制限し、実AWSを使わないDockerで実行した。
- 256×384の単純な人物図形を生成し、実際のモデル取得・推論を行った。PNG/RGBA、元と同じ寸法、alphaの最小0・最大255を確認し、出力を目視した。白背景が透明になり人物図形が残った。初回取得を含む関数実行66.45秒、終了0。証跡tmp/background-u2net-probe.log、tmp/background-u2net-proof/input.png・output.png・result.json。モデルは実行時に取得され、コンテナ終了時に破棄された。
- 比較の既定モデル試験では約1.02 GBの重み取得とメモリ使用約1.997 GiBを観測したが、利用条件の確認後に手動停止した。OOMや推論失敗と判定した結果ではない。旧試験はmemory-swapを指定しておらず、新試験と厳密な性能比較もしない。ログtmp/background-runtime-preflight.log、tmp/background-runtime-probe.logを保持する。

## 未完了の公開条件

この結果は単純な入力1件の実推論であり、実際の立ち絵・髪・小物・複雑な背景の品質、最大入力、継続負荷、実Fargate起動、実S3配送、保持期間後の削除を証明しない。実モデル取得経路と運用条件の検証を続ける。AWS資源・権限・Secrets・契約・課金は変更していない。

同時実行中のSQLite/PostgreSQL全体テストはc816f8e4の固定ソースであり、このモデル選択の修正を含まない。全体テストの完了結果と、今回の追加検証を区別する。復旧時にも未確認の商用モデルを既定として使う旧実装を本番へ戻さない。
