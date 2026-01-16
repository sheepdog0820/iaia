# テストデータ利用ガイド

## 概要
セッションとキャラクターのテストデータが作成されています。以下の情報を使用してシステムの動作を確認できます。

## ログイン情報

### GM（ゲームマスター）
- **keeper1** / keeper123
  - ニックネーム: 深淵の守護者
  - 権限: スタッフ権限あり
  - 担当セッション: 悪霊の家（進行中）、インスマスからの脱出（予定）

- **keeper2** / keeper123
  - ニックネーム: 古き印の管理人
  - 担当セッション: ミスカトニック大学の怪異（完了）、深海の呼び声（予定）

### プレイヤー
- **investigator1** / player123 - 真実の探究者
  - キャラクター: 佐藤健一（私立探偵）、ジョン・スミス（考古学者）
  
- **investigator2** / player123 - 闇を見つめる者
  - キャラクター: 田中美咲（医師）、エミリー・ブラウン（ジャーナリスト）
  
- **investigator3** / player123 - 古文書の解読者
  - キャラクター: 山田太郎（大学教授）、マイケル・ジョーンズ（警察官）
  
- **investigator4** / player123 - 深海の調査員
  - キャラクター: 鈴木花子（古書店主）
  
- **investigator5** / player123 - 星の観測者
  - キャラクター: サラ・ウィリアムズ（天文学者）
  
- **investigator6** / player123 - 遺跡の発掘者
  - キャラクター: 高橋一郎（船員）

### 管理者
- **admin** / arkham_admin_2024

## セッション情報

### 1. 悪霊の家（進行中）
- **GM**: keeper1（深淵の守護者）
- **状態**: 進行中
- **参加者**: 4人（全枠埋まり済み）
  - 枠1: investigator1（佐藤健一）- HO1: 友人の失踪
  - 枠2: investigator2（田中美咲）- HO2: 悪夢
  - 枠3: investigator3（山田太郎）- HO3: 祖父の日記
  - 枠4: investigator4（鈴木花子）- HO4: 新聞社の依頼

### 2. インスマスからの脱出（予定）
- **GM**: keeper1
- **日時**: 3日後
- **参加者**: 2/4人（枠1,2のみ埋まり）
- **場所**: 秋葉原会議室A

### 3. 深海の呼び声（今夜予定）
- **GM**: keeper2
- **日時**: 今日20:00
- **参加者**: 未定
- **場所**: オンライン（Discord）

### 4. ミスカトニック大学の怪異（完了）
- **GM**: keeper2
- **状態**: 1週間前に完了
- **参加者**: 3人

### 5. 狂気山脈にて（キャンセル）
- **GM**: keeper1
- **状態**: キャンセル済み

## グループ情報

### アーカムの探索者たち（プライベート）
- **管理者**: keeper1
- **メンバー**: keeper1, keeper2, investigator1-4
- **セッション**: 悪霊の家、インスマスからの脱出

### ミスカトニック大学研究会（公開）
- **管理者**: keeper2
- **メンバー**: keeper2, investigator3-6
- **セッション**: ミスカトニック大学の怪異、深海の呼び声

## 確認方法

### 1. Webブラウザでの確認
```
http://localhost:8000/
```

### 2. データ確認スクリプト
```bash
python3 check_test_data.py
```

### 3. 管理画面での確認
```
http://localhost:8000/admin/
ユーザー名: admin
パスワード: arkham_admin_2024
```

## テストシナリオ例

### シナリオ1: GMとしてハンドアウトを確認
1. keeper1でログイン
2. セッション一覧から「悪霊の家」を選択
3. 4つのハンドアウトが全て表示されることを確認

### シナリオ2: プレイヤーとして自分のHOのみ確認
1. investigator1でログイン
2. セッション一覧から「悪霊の家」を選択
3. HO1のみが表示されることを確認

### シナリオ3: 新規セッション参加
1. investigator5でログイン
2. 「深海の呼び声」セッションに参加
3. キャラクター「サラ・ウィリアムズ」を選択して参加

## データリセット
```bash
# 既存データを削除して再作成
echo "yes" | python3 manage.py create_session_test_data
```

## 追加: シナリオ→セッション→探索者（技能/推奨技能/ハンドアウト）導線テストデータ

以下のコマンドで、推奨技能付きシナリオ + シナリオ紐付けセッション + 技能設定済み探索者 + HO1〜HO4（秘匿）+ 共通（公開）ハンドアウトのテストデータを作成できます。

```bash
python manage.py create_flow_test_data
```

### ログイン情報
- **flow_gm** / flowpass123
- **flow_pl1** / flowpass123（PL2〜PL4も同様）

### 作成データ
- **シナリオ**: 【FLOWTEST】推奨技能ありシナリオ（推奨技能あり）
- **セッション**: 【FLOWTEST】シナリオ起点セッション（シナリオ紐付け）

## 追加: ISSUE-017 高度なスケジューリング（セッションシリーズ/日程調整/参加可能日投票）テストデータ

以下のコマンドで、ISSUE-017 の API を手動確認できるテストデータを作成できます。

```bash
# 既存のADVTESTデータを削除して作り直し
python manage.py create_advanced_scheduling_test_data --reset
```

### 作成されるデータ
- グループ: `【ADVTEST】高度なスケジューリング`
- セッションシリーズ: weekly / biweekly / monthly / custom（近日の日程が出るように設定）
- 日程調整（DatePoll）: `【ADVTEST】日程調整(オープン)` / `【ADVTEST】日程調整(確定済み)`
- 参加可能日投票（SessionAvailability）: session/occurrence の両方を作成

### ログイン情報
- `keeper1 / keeper123` と `investigator1-3 / player123` が存在する場合はそれらを利用します
- 存在しない場合は `adv_gm / advpass123` と `adv_pl1-3 / advpass123` を作成します

### API エンドポイント例
- `/api/schedules/session-series/`
- `/api/schedules/session-series/<id>/generate_sessions/`
- `/api/schedules/date-polls/`
- `/api/schedules/availability/vote/`
