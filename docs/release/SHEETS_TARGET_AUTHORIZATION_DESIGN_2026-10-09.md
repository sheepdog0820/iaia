# Google Sheets共有対象の認可・濫用防止: 不足再現と方針案

## 判定・対象

2026-10-09。基準は `a3b487efb3a9a969f4240326a8f7de55b570cda8`、製品コードは679と同じ。
[対象制御設計](GOOGLE_TARGET_FENCE_DESIGN_2026-10-06.md)のT12にある「共有Sheet待機の認可・上限/濫用防止」を調査した。
**これは未配備候補の不足再現であり、修正・安全性合格・実Googleの攻撃実証ではない。正式公開No-Go。**
現main8567には今回の `google_write_ledger.py` / `google_target_execution.py` がないことをGit treeで確認した。
稼働AWSを再検査した記録ではなく、実ユーザー・Google ACL・共有環境には触れていない。

## 製品コードで確認した順序

1. `GoogleSheetsExportView.post` は連携有効・Sheets scope・資格情報のbinding・自分のキャラクターを検査する。
2. `register_sheets_intake` は指定されたopaque spreadsheet IDからowner/Google identityに依存しない共有keyを作り、provider照会なしでFIFO予約と暗号化snapshotを確定する。
3. `claim_targets` は未開始の古い予約でも後続を待たせる。workerは共有holderを取得した後にトークンを取得し、Sheets PUTを送る。指定ファイルの編集権限の事前証拠はない。
4. 403を受け取ればKNOWNの拒否を保存して安全に終了するが、送信応答を失った場合はUNKNOWNを保持する。job削除・7日保存期限で解除しないのは必要な安全性であり、この規則を弱めて修正しない。

現在の連携要求scopeは `calendar.events` と `spreadsheets`。`files.get` 用のDrive scopeは要求していない。
DRF基本設定/当該APIViewでは送信先予約の利用者別上限を確認できず、以下の33件受理を再現した。
33件の成功から無制限の受付能力・インフラの全防御不在・実攻撃成立を断定しない。

## 隔離再現

合成の二利用者/異なるGoogle UIDを登録し、実API→sealed admission/outbox→実taskを呼ぶ。
mock providerの方針は最初の利用者のPUTを拒否、二番目の利用者は編集可とする。
**このACL設定は試験側の仮定で、Google側で確認した権限ではない。** 全未mock Requestsは禁止する。

| ケース | 実際に観測した未配備候補の動作 | 判定 |
| --- | --- | --- |
| 未開始の未確認受付 | 最初の利用者の受付だけで、別identityのeditor jobがtarget-waiting。双方のHTTP/トークン照会0。元予約が未開始のまま保存期限で消えればeditorを開始できる | shared FIFOへ入る前の認可が不足 |
| 拒否応答喪失 | mock providerは拒否/未適用だが応答Timeout。事前GET0・PUT1、UNKNOWN holderが成立し、sourceの保存期限削除後も別identityのeditorのHTTP0。別Sheetへの出力は成功 | 権限未確認の送信でも長期共有禁止へ進める。実Google拒否の喪失を実証したものではない |
| 既知403の対照 | KNOWN/403・FINISHED・holder解除。その後editorのPUT1・成功 | 403自体が常に永久blockするとは扱わない |
| 33個の未確認送信先 | 同じ利用者の任意33 IDを全て202で受理し、33 target/admission/reservationを作る。execution/HTTP/トークン照会0 | 指定ファイル認可・受付上限の不足を確認 |

SQLite4ケース/1.353秒、専用PG4ケース/3.555秒、終了0。
これは診断assertionが不足と対照を再現した意味のOKであり、危険な挙動を正常回帰テストとして追加しない。
同一接続の順序制御で、実broker/独立worker競合・実Google・実編集権限の確認ではない。

既存固定679通常image `sha256:6de91d2a3c3fb4d2d4254c656b893352098a40d3dbd1bb3a75b7707c7e238874` に
probeとrunnerだけをread-only mountし、同じ4ケースを2.449秒で再現・終了0/skip0/OOM false。
製品/helper10ファイルとprobeの計11 hashがhostと一致し、実行前後不変。製品・依存・配布物の変更なし。
sourceはPython3.11.1/Django5.2.15、runtimeはPython3.11.17/Django5.2.17。
非root10001/read-only/cap-drop ALL/no-new-privileges、512MiB/1CPU、専用PG namespace内のloopbackを使い、実メールは禁止する。
証拠は `D:/tmp/codex-sheets-target-auth-20261009`。空の専用PG18.3/tmpfsからtest DBを生成/破棄し、
二つのbase DBのpublic表0を確認後、正確なID/name/label/image/mount/stateを検査して2container/tmpfsを撤去。
PG停止終了0/OOM false、所有container残0。source/probe/image/script/logと元の別作業は保持する。

## 一次情報と方針の比較

Googleの[files.get](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/get)はDrive scopeを要求するため、現在のSheets scopeだけで同APIの利用を保証しない。
[file capabilities](https://developers.google.com/workspace/drive/api/reference/rest/v3/files)は利用者の `canEdit` 等を示すが、他の制限もある。[共有ガイド](https://developers.google.com/workspace/drive/api/guides/manage-sharing)は動的capabilitiesを利用する案内を提供する。
Sheetsの[spreadsheets.get](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/get)はreadonly scopeでも利用可能なので、200だけを編集権限の証拠にする案は採らない（仕様からの推論）。

| 方針案 | 利用者への変更 | 権限・公開審査の観点 | 状態 |
| --- | --- | --- | --- |
| 推奨: Google Pickerとdrive.file | 出力先を選択する操作へ変更。既存利用者は再連携が必要 | 選択してアプリに許可したファイル単位。Googleが推奨するnon-sensitive scope。新規認可は旧spreadsheets要求を縮小する方向 | 方針確認待ち。実OAuth/Google設定の変更承認ではない |
| ID入力を維持しDrive metadata readonlyを追加 | ID入力を残し、再連携後にサーバーでファイルcapabilitiesを照会 | Drive全体のメタデータへ及ぶrestricted scope。審査/評価の負担とプライバシー影響が増える。Sheets書き込みscopeは別途必要 | 比較案。未採用/未承認 |

分類・Picker推奨の根拠は[Google Drive scope案内](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)と[Sheets scope案内](https://developers.google.com/workspace/sheets/api/scopes)。
新しいscopeを要求するだけで既存の広いgrantが消えると説明しない。既存grant/refresh tokenの扱い、Google側の取消と再連携、Calendar連携の維持を別途設計・実証する。
空のbatchUpdateや「後で戻す」書き込みを認可検査の代わりに使わない。owner別keyへ変更して共有Sheetの競合を分離したり、UNKNOWNをTTL解除する案も採らない。

## 方針確定後の実装・受け入れ条件

- scope・選択先を利用者へ日本語で説明し、クライアントの「編集可」フラグや任意IDだけを信用しない。サーバーが選択先ID/MIME/trashed/capabilitiesの厳密なprovider証拠を検査する。保護範囲等を含む全書き込み成功の保証ではない。
- 事前認可/入力・資源制限を共有FIFO登録より前に置く。ネットワーク中はSQL lockを保持せず、provider不明/拒否はtarget/reservation/holderを作らない。非同期確認段階と暗号化immutable受付、FIFOの順序定義を設計し、API transaction内へ単純にGETを足すだけの変更にしない。
- proofをowner/Google identity/credential incarnation/canonical targetへ結び、取消/再連携/権限失効・古いproofを拒否する。受付後にも送信直前の認可・snapshot/holder確認を維持する。待機中の権限変化を許可したまま長期間予約しない。
- 受付数/保留数/ID・payloadサイズ/同時照会数の利用者別限度とサーバー検査を加える。具体値は利用方針と負荷試験を踏まえて決める。レート制限だけで今回の共有認可不足が解消したことにはしない。
- 権限なし/閲覧のみ/同意不足/失効/照会障害は共有待ち行列へ入らず、対象を知らない他人の情報も漏らさない。編集可の同一Sheet/別owner/別rangeは従来どおり一つの対象として直列化し、別Sheetは独立することをPG/通常worker/UIで実証する。
- legacy producer/workerを止めてdrainし、既存予約と未解決holderを安全に扱う。既存UNKNOWNを「今は権限がない」という理由だけで解除しない。限定回復・保存/退会方針・実Googleの照会/書き込みは別条件として残す。
- 正常/失敗/権限確認中/対象待ち/再連携の3ブラウザ表示、前記負荷制限と登録100人/同時10人の性能、キー/ログ/backup privacy、移行/ロールバックを検証する。

## 今回の変更・承認境界

診断/設計記録だけを作成する。アプリ・model/migration・依存・OAuth要求・Google Cloud設定・実grant/token・main/AWS/共有DB/Secrets/IAM/課金/容量/外部通知は変更しない。
ユーザーへPicker/drive.file案の**ローカル実装・隔離検証だけ**を確認している。実OAuth・設定変更・main/AWS反映や利用者への公開約束は別の具体案と承認対象で、favicon承認は拡張しない。
文書の取り消しは通常revertで可能。実環境の切戻しは不要。製品変更がないため全アプリ試験の再実行で修正済みを演出しない。
先行aab CI37860184627の全6成功は確認済み。a3と今回文書commitのCIは別に扱い、正式公開No-Goを維持する。
今回の文書39テストは成功（0.036秒）。変更3文書の相対リンク280件の存在を確認し、記述と差分をレビューした。製品修正の合格を意味しない。
