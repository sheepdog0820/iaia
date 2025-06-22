# Tindalos統計API ドキュメント

## 概要
Tindalos統計APIは、TRPGプレイヤーのセッション統計を提供する包括的なAPIです。
基本的な統計から詳細な年度・月別分析まで、様々な観点からプレイデータを取得できます。

## エンドポイント

### 1. SimpleTindalosMetricsView
**エンドポイント**: `/api/accounts/statistics/tindalos/`

#### 基本モード
```
GET /api/accounts/statistics/tindalos/
```

**レスポンス例**:
```json
{
    "session_count": 42,
    "gm_session_count": 15,
    "player_session_count": 27,
    "total_play_time": 12360,  // 分単位
    "scenario_count": 18
}
```

#### 詳細モード
```
GET /api/accounts/statistics/tindalos/?detailed=true&year=2025
```

**レスポンス例**:
```json
{
    "session_count": 42,
    "gm_session_count": 15,
    "player_session_count": 27,
    "total_play_time": 12360,
    "scenario_count": 18,
    "yearly_trends": [
        {
            "year": 2023,
            "session_count": 12,
            "gm_session_count": 3,
            "player_session_count": 9,
            "total_hours": 36.0,
            "avg_session_hours": 3.0
        },
        // ...
    ],
    "monthly_details": [
        {
            "month": 1,
            "session_count": 3,
            "total_hours": 9.0,
            "scenarios": [
                {
                    "scenario__id": 1,
                    "scenario__title": "影の館",
                    "scenario__game_system": "coc",
                    "play_count": 2
                }
            ]
        },
        // ...
    ],
    "popular_scenarios": [
        {
            "scenario__id": 1,
            "scenario__title": "影の館",
            "scenario__game_system": "coc",
            "scenario__difficulty": "intermediate",
            "play_count": 8,
            "last_played": "2025-06-15T15:00:00Z",
            "game_system_display": "クトゥルフ神話TRPG"
        },
        // ...
    ],
    "system_trends": [
        {
            "system_code": "coc",
            "system_name": "クトゥルフ神話TRPG",
            "data": [
                {"year": 2023, "count": 10},
                {"year": 2024, "count": 15},
                {"year": 2025, "count": 18}
            ]
        },
        // ...
    ]
}
```

#### パラメータ
- `detailed` (boolean, optional): trueの場合、詳細統計を含む
- `year` (integer, optional): 特定年度でフィルタ
- `game_system` (string, optional): ゲームシステムでフィルタ（例: 'coc', 'dnd', 'sw'）

### 2. DetailedTindalosMetricsView
**エンドポイント**: `/api/accounts/statistics/tindalos/detailed/`

#### 統計タイプ別エンドポイント

##### 年度別推移
```
GET /api/accounts/statistics/tindalos/detailed/?type=yearly_trends&start_year=2022&end_year=2025
```

**レスポンス例**:
```json
{
    "period": "2022 - 2025",
    "years": [
        {
            "year": 2022,
            "sessions": {
                "total": 24,
                "as_gm": 8,
                "as_player": 16,
                "total_hours": 72.0
            },
            "scenarios": 12,
            "systems": {
                "クトゥルフ神話TRPG": 20,
                "D&D": 4
            }
        },
        // ...
    ],
    "total_years": 4
}
```

##### 月別詳細
```
GET /api/accounts/statistics/tindalos/detailed/?type=monthly_details&year=2025
```

**レスポンス例**:
```json
{
    "year": 2025,
    "months": [
        {
            "month": 1,
            "month_name": "1月",
            "sessions": {
                "total": 4,
                "as_gm": 1,
                "as_player": 3,
                "total_hours": 12.0
            },
            "top_scenarios": [
                {
                    "id": 1,
                    "title": "影の館",
                    "system": "クトゥルフ神話TRPG",
                    "difficulty": "intermediate",
                    "play_count": 2,
                    "as_gm": 1,
                    "as_player": 1
                }
            ]
        },
        // ...
    ]
}
```

##### 人気シナリオランキング
```
GET /api/accounts/statistics/tindalos/detailed/?type=popular_scenarios&year=2025
```

**レスポンス例**:
```json
{
    "year": 2025,
    "count": 10,
    "scenarios": [
        {
            "id": 1,
            "title": "影の館",
            "system": "クトゥルフ神話TRPG",
            "difficulty": "intermediate",
            "author": "田中太郎",
            "description": "古い屋敷で起こる恐怖の物語...",
            "stats": {
                "total_plays": 12,
                "as_gm": 4,
                "as_player": 8,
                "unique_sessions": 10
            },
            "dates": {
                "first_played": "2025-01-15T15:00:00Z",
                "last_played": "2025-06-15T18:00:00Z",
                "days_between": 151
            }
        },
        // ...
    ]
}
```

##### ゲームシステム推移
```
GET /api/accounts/statistics/tindalos/detailed/?type=system_trends
```

**レスポンス例**:
```json
{
    "period": "2021 - 2025",
    "systems": [
        {
            "system_code": "coc",
            "system_name": "クトゥルフ神話TRPG",
            "yearly_data": [
                {
                    "year": 2021,
                    "sessions": 10,
                    "unique_scenarios": 5,
                    "as_gm": 3,
                    "as_player": 7
                },
                // ...
            ],
            "summary": {
                "total_sessions": 80,
                "average_per_year": 16.0,
                "trend": "increasing"  // "increasing", "decreasing", "stable"
            }
        },
        // ...
    ]
}
```

#### パラメータ
- `type` (string, required): 統計タイプ
  - `summary`: 総合サマリー（デフォルト）
  - `yearly_trends`: 年度別推移
  - `monthly_details`: 月別詳細
  - `popular_scenarios`: 人気シナリオランキング
  - `system_trends`: ゲームシステム推移
- `year` (integer, optional): 特定年度でフィルタ
- `start_year` (integer, optional): 開始年度（yearly_trends用）
- `end_year` (integer, optional): 終了年度（yearly_trends用）

## フィルタ機能

### 年度フィルタ
すべてのエンドポイントで`year`パラメータを使用して特定年度のデータを取得できます。

### ゲームシステムフィルタ
SimpleTindalosMetricsViewで`game_system`パラメータを使用して特定のゲームシステムのデータのみを取得できます。

利用可能なゲームシステムコード:
- `coc`: クトゥルフ神話TRPG
- `dnd`: D&D
- `sw`: ソード・ワールド
- `insane`: インセイン
- `other`: その他

## 実装詳細

### 統計計算方法

#### 年度別推移
- プレイ履歴の最初の年から現在年までのデータを集計
- 各年度のセッション数、GM/プレイヤー別カウント、総プレイ時間を計算
- ゲームシステム別の内訳も提供

#### 月別詳細
- 指定年度の12ヶ月分のデータを提供（データがない月も0で表示）
- 各月の上位5シナリオをランキング表示
- GM/プレイヤー別のプレイ回数も集計

#### 人気シナリオランキング
- プレイ回数順でソート（上位10〜20件）
- 初回・最終プレイ日、プレイ期間を計算
- GM/プレイヤー別のプレイ回数を集計
- ユニークセッション数（重複を除いた実際のセッション数）も提供

#### ゲームシステム推移
- 過去5年間のシステム別プレイ推移を表示
- 各年のセッション数、ユニークシナリオ数を集計
- トレンド（増加/減少/横ばい）を自動判定
  - 20%以上増加: "increasing"
  - 20%以上減少: "decreasing"
  - それ以外: "stable"

### パフォーマンス考慮事項

1. **データ集計の最適化**
   - Django ORMのaggregation機能を活用
   - 必要なフィールドのみをselect
   - 適切なインデックスの使用

2. **レスポンスサイズ**
   - 人気シナリオは上位10〜20件に制限
   - 説明文は200文字で切り詰め
   - 月別シナリオは上位5件に制限

3. **将来的な拡張性**
   - キャッシュ機構の実装検討
   - ページネーションの追加
   - 非同期処理の導入

## 使用例

### Python (requests)
```python
import requests

# 基本統計の取得
response = requests.get(
    'https://your-domain.com/api/accounts/statistics/tindalos/',
    headers={'Authorization': 'Token your-token'}
)
basic_stats = response.json()

# 詳細統計の取得
response = requests.get(
    'https://your-domain.com/api/accounts/statistics/tindalos/',
    params={'detailed': 'true', 'year': 2025},
    headers={'Authorization': 'Token your-token'}
)
detailed_stats = response.json()

# 年度別推移の取得
response = requests.get(
    'https://your-domain.com/api/accounts/statistics/tindalos/detailed/',
    params={'type': 'yearly_trends', 'start_year': 2020, 'end_year': 2025},
    headers={'Authorization': 'Token your-token'}
)
yearly_trends = response.json()
```

### JavaScript (fetch)
```javascript
// 基本統計の取得
fetch('/api/accounts/statistics/tindalos/', {
    headers: {
        'Authorization': 'Token your-token'
    }
})
.then(response => response.json())
.then(data => console.log(data));

// 人気シナリオランキングの取得
fetch('/api/accounts/statistics/tindalos/detailed/?type=popular_scenarios&year=2025', {
    headers: {
        'Authorization': 'Token your-token'
    }
})
.then(response => response.json())
.then(data => {
    data.scenarios.forEach(scenario => {
        console.log(`${scenario.title}: ${scenario.stats.total_plays}回プレイ`);
    });
});
```

## エラーレスポンス

### 401 Unauthorized
```json
{
    "detail": "認証情報が提供されていません。"
}
```

### 400 Bad Request
```json
{
    "detail": "無効なパラメータです。"
}
```

### 404 Not Found
```json
{
    "detail": "データが見つかりません。"
}
```

## 更新履歴
- 2025年6月20日: 初版作成
  - SimpleTindalosMetricsViewの詳細モード追加
  - DetailedTindalosMetricsViewの実装
  - 年度・月別詳細集計機能
  - ゲームシステム別統計機能
  - 期間指定フィルタ機能