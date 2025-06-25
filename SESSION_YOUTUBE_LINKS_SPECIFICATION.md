# セッションYouTubeリンク機能 仕様書

**作成日**: 2025年6月25日  
**バージョン**: 1.0.0  
**ステータス**: 設計中

---

## 📋 目次

1. [概要](#概要)
2. [機能要件](#機能要件)
3. [データ構造](#データ構造)
4. [API仕様](#api仕様)
5. [UI/UX仕様](#uiux仕様)
6. [技術仕様](#技術仕様)
7. [実装計画](#実装計画)

---

## 概要

### 目的
TRPGセッションに関連するYouTube動画（リプレイ動画、BGM、参考資料など）を複数リンクできる機能を提供する。各リンクには動画タイトル、時間、備考を自動取得・管理できるようにする。

### 主要機能
- 🎥 **複数動画リンク**: 1セッションに複数のYouTube動画をリンク
- 📝 **自動情報取得**: YouTube APIを使用して動画タイトル・時間を自動取得
- 💬 **備考管理**: 各動画に対する備考・説明文を追加
- 🔢 **表示順序**: 動画の表示順序を管理
- 🔒 **権限管理**: GMと参加者のみが追加・編集可能

---

## 機能要件

### 1. 動画リンク管理

#### 1.1 動画追加
- YouTube URLの入力
- 動画情報の自動取得
  - タイトル
  - 再生時間（duration）
  - サムネイル画像URL
  - チャンネル名
- 備考欄の入力（任意）
- 表示順序の設定

#### 1.2 動画編集
- 備考の編集
- 表示順序の変更
- URLの変更（再取得）

#### 1.3 動画削除
- 個別削除
- 一括削除（GM権限）

### 2. 権限管理

#### 2.1 追加権限
- GM: 無制限に追加可能
- 参加者: 追加可能（GMが許可設定可能）

#### 2.2 編集権限
- GM: すべての動画を編集可能
- 追加者: 自分が追加した動画のみ編集可能

#### 2.3 削除権限
- GM: すべての動画を削除可能
- 追加者: 自分が追加した動画のみ削除可能

### 3. 表示機能

#### 3.1 一覧表示
- サムネイル表示
- タイトル表示（最大2行で省略）
- 再生時間表示（HH:MM:SS形式）
- 備考表示（折りたたみ可能）
- 追加者情報

#### 3.2 プレイヤー埋め込み
- モーダルでのYouTubeプレイヤー表示
- 外部リンクオプション

### 4. 集計機能

#### 4.1 合計時間計算
- セッション内の全動画の合計再生時間
- HH:MM:SS形式での表示
- リアルタイム更新（動画追加・削除時）

#### 4.2 統計情報
- 動画本数
- 合計再生時間
- 平均再生時間
- チャンネル別集計

---

## データ構造

### SessionYouTubeLinkモデル

```python
class SessionYouTubeLink(models.Model):
    """セッションに関連するYouTube動画リンク"""
    
    # リレーション
    session = models.ForeignKey(
        'TRPGSession',
        on_delete=models.CASCADE,
        related_name='youtube_links'
    )
    added_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='added_youtube_links'
    )
    
    # YouTube情報
    youtube_url = models.URLField(max_length=500)
    video_id = models.CharField(max_length=50, db_index=True)
    title = models.CharField(max_length=200)
    duration_seconds = models.PositiveIntegerField(default=0)
    channel_name = models.CharField(max_length=100, blank=True)
    thumbnail_url = models.URLField(max_length=500, blank=True)
    
    # メタ情報
    description = models.TextField(
        blank=True,
        verbose_name="備考",
        help_text="この動画についての説明やメモ"
    )
    order = models.PositiveIntegerField(default=0)
    
    # タイムスタンプ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        unique_together = ['session', 'video_id']
        indexes = [
            models.Index(fields=['session', 'order']),
        ]
    
    def __str__(self):
        return f"{self.session.title} - {self.title}"
    
    @property
    def duration_display(self):
        """再生時間を HH:MM:SS 形式で表示"""
        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        seconds = self.duration_seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    
    def save(self, *args, **kwargs):
        # video_idを抽出
        if self.youtube_url and not self.video_id:
            self.video_id = self.extract_video_id(self.youtube_url)
        
        # 新規作成時、orderを自動設定
        if not self.pk and self.order == 0:
            max_order = SessionYouTubeLink.objects.filter(
                session=self.session
            ).aggregate(
                max_order=models.Max('order')
            )['max_order']
            self.order = (max_order or 0) + 1
        
        super().save(*args, **kwargs)
    
    @staticmethod
    def extract_video_id(url):
        """YouTube URLから動画IDを抽出"""
        import re
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?]+)',
            r'(?:youtube\.com\/embed\/)([^&\n?]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    @classmethod
    def get_session_total_duration(cls, session):
        """セッションの動画合計時間を取得"""
        from django.db.models import Sum
        result = cls.objects.filter(session=session).aggregate(
            total=Sum('duration_seconds')
        )
        return result['total'] or 0
    
    @classmethod
    def get_session_statistics(cls, session):
        """セッションの動画統計情報を取得"""
        from django.db.models import Sum, Avg, Count
        videos = cls.objects.filter(session=session)
        
        stats = videos.aggregate(
            count=Count('id'),
            total_duration=Sum('duration_seconds'),
            avg_duration=Avg('duration_seconds')
        )
        
        # チャンネル別集計
        channel_stats = videos.values('channel_name').annotate(
            video_count=Count('id'),
            total_duration=Sum('duration_seconds')
        ).order_by('-video_count')
        
        return {
            'video_count': stats['count'] or 0,
            'total_duration_seconds': stats['total_duration'] or 0,
            'total_duration_display': cls.format_duration(stats['total_duration'] or 0),
            'average_duration_seconds': int(stats['avg_duration'] or 0),
            'average_duration_display': cls.format_duration(int(stats['avg_duration'] or 0)),
            'channel_breakdown': list(channel_stats)
        }
    
    @staticmethod
    def format_duration(seconds):
        """秒数を HH:MM:SS 形式にフォーマット"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
```

---

## API仕様

### エンドポイント

#### 1. YouTube動画リンク管理
```
GET    /api/schedules/sessions/{session_id}/youtube-links/
POST   /api/schedules/sessions/{session_id}/youtube-links/
GET    /api/schedules/youtube-links/{id}/
PUT    /api/schedules/youtube-links/{id}/
DELETE /api/schedules/youtube-links/{id}/
```

#### 2. 特殊エンドポイント
```
POST   /api/schedules/youtube-links/fetch-info/
       - YouTube URLから動画情報を取得
       
POST   /api/schedules/youtube-links/{id}/reorder/
       - 表示順序の変更
       
GET    /api/schedules/sessions/{session_id}/youtube-links/statistics/
       - セッションの動画統計情報を取得
```

### リクエスト/レスポンス例

#### 動画追加
```json
// Request
POST /api/schedules/sessions/123/youtube-links/
{
    "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "description": "セッションのハイライトシーン"
}

// Response
{
    "id": 1,
    "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "video_id": "dQw4w9WgXcQ",
    "title": "Rick Astley - Never Gonna Give You Up",
    "duration_seconds": 213,
    "duration_display": "3:33",
    "channel_name": "Rick Astley",
    "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
    "description": "セッションのハイライトシーン",
    "order": 1,
    "added_by": {
        "id": 1,
        "username": "gm_user",
        "nickname": "GM太郎"
    },
    "created_at": "2025-06-25T10:00:00Z"
}
```

#### 動画情報取得
```json
// Request
POST /api/schedules/youtube-links/fetch-info/
{
    "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}

// Response
{
    "video_id": "dQw4w9WgXcQ",
    "title": "Rick Astley - Never Gonna Give You Up",
    "duration_seconds": 213,
    "channel_name": "Rick Astley",
    "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"
}
```

#### 統計情報取得
```json
// Request
GET /api/schedules/sessions/123/youtube-links/statistics/

// Response
{
    "video_count": 5,
    "total_duration_seconds": 3600,
    "total_duration_display": "1:00:00",
    "average_duration_seconds": 720,
    "average_duration_display": "12:00",
    "channel_breakdown": [
        {
            "channel_name": "Channel A",
            "video_count": 3,
            "total_duration": 2100
        },
        {
            "channel_name": "Channel B",
            "video_count": 2,
            "total_duration": 1500
        }
    ]
}
```

---

## UI/UX仕様

### 1. セッション詳細画面での表示

#### 1.1 YouTube動画セクション
```html
<div class="youtube-links-section">
    <h3>関連動画 <span class="badge">3</span></h3>
    <button class="btn btn-primary btn-sm" onclick="addYouTubeLink()">
        <i class="fas fa-plus"></i> 動画を追加
    </button>
    
    <div class="youtube-links-grid">
        <!-- 動画カード -->
        <div class="youtube-link-card">
            <div class="thumbnail-wrapper">
                <img src="thumbnail.jpg" alt="動画サムネイル">
                <span class="duration-badge">3:33</span>
            </div>
            <div class="video-info">
                <h4 class="video-title">動画タイトル</h4>
                <p class="channel-name">チャンネル名</p>
                <p class="description">備考テキスト...</p>
                <div class="meta-info">
                    <span class="added-by">追加: GM太郎</span>
                    <span class="added-date">2025/06/25</span>
                </div>
            </div>
            <div class="actions">
                <button class="btn-icon" title="再生">
                    <i class="fas fa-play"></i>
                </button>
                <button class="btn-icon" title="編集">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn-icon" title="削除">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    </div>
</div>
```

#### 1.2 追加モーダル
```html
<div class="modal" id="addYouTubeLinkModal">
    <div class="modal-content">
        <h3>YouTube動画を追加</h3>
        <form id="youtubeLinksForm">
            <div class="form-group">
                <label>YouTube URL <span class="required">*</span></label>
                <input type="url" id="youtube_url" required>
                <button type="button" onclick="fetchVideoInfo()">
                    動画情報を取得
                </button>
            </div>
            
            <!-- 動画情報プレビュー -->
            <div id="videoPreview" style="display:none;">
                <img id="previewThumbnail" src="">
                <div>
                    <p id="previewTitle"></p>
                    <p id="previewDuration"></p>
                </div>
            </div>
            
            <div class="form-group">
                <label>備考</label>
                <textarea id="description" rows="3"></textarea>
            </div>
            
            <button type="submit">追加</button>
        </form>
    </div>
</div>
```

### 2. デザイン仕様

#### 2.1 レイアウト
- グリッドレイアウト（PC: 3列、タブレット: 2列、モバイル: 1列）
- カード型デザイン
- ホバー効果

#### 2.2 カラー
- 再生ボタン: YouTube Red (#FF0000)
- 時間バッジ: 半透明黒背景
- カードボーダー: ライトグレー

---

## 技術仕様

### 1. YouTube API連携

#### 1.1 API設定
```python
# settings.py
YOUTUBE_API_KEY = env('YOUTUBE_API_KEY')
YOUTUBE_API_BASE_URL = 'https://www.googleapis.com/youtube/v3'
```

#### 1.2 動画情報取得サービス
```python
import requests
from django.conf import settings

class YouTubeService:
    @staticmethod
    def fetch_video_info(video_id):
        """YouTube APIを使用して動画情報を取得"""
        url = f"{settings.YOUTUBE_API_BASE_URL}/videos"
        params = {
            'key': settings.YOUTUBE_API_KEY,
            'part': 'snippet,contentDetails',
            'id': video_id
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data['items']:
                item = data['items'][0]
                return {
                    'title': item['snippet']['title'],
                    'channel_name': item['snippet']['channelTitle'],
                    'thumbnail_url': item['snippet']['thumbnails']['maxres']['url'],
                    'duration': YouTubeService.parse_duration(
                        item['contentDetails']['duration']
                    )
                }
        return None
    
    @staticmethod
    def parse_duration(duration_str):
        """ISO 8601形式の期間を秒数に変換"""
        # PT3M33S -> 213秒
        import re
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            return hours * 3600 + minutes * 60 + seconds
        return 0
```

### 2. フロントエンド実装

#### 2.1 YouTube URL検証
```javascript
function validateYouTubeUrl(url) {
    const regex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+$/;
    return regex.test(url);
}

function extractVideoId(url) {
    const regex = /(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?]+)/;
    const match = url.match(regex);
    return match ? match[1] : null;
}
```

#### 2.2 動画情報取得
```javascript
async function fetchVideoInfo() {
    const url = document.getElementById('youtube_url').value;
    if (!validateYouTubeUrl(url)) {
        alert('有効なYouTube URLを入力してください');
        return;
    }
    
    try {
        const response = await fetch('/api/schedules/youtube-links/fetch-info/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ youtube_url: url })
        });
        
        if (response.ok) {
            const data = await response.json();
            displayVideoPreview(data);
        }
    } catch (error) {
        console.error('動画情報の取得に失敗しました:', error);
    }
}
```

---

## 実装計画

### Phase 1: 基本機能（必須）
1. ✅ データモデル作成
2. ✅ マイグレーション実行
3. ✅ API実装（CRUD）
4. ✅ 権限チェック実装
5. ✅ テストケース作成
6. ✅ 集計機能実装
7. ✅ 統計APIエンドポイント実装

### Phase 2: YouTube API連携
1. ⬜ YouTube API設定
2. ⬜ 動画情報取得サービス実装
3. ⬜ APIエンドポイント実装
4. ⬜ エラーハンドリング

### Phase 3: UI実装
1. ⬜ 一覧表示UI
2. ⬜ 追加/編集モーダル
3. ⬜ 削除確認ダイアログ
4. ⬜ 並び替え機能

### Phase 4: 拡張機能
1. ⬜ プレイリスト対応
2. ⬜ 埋め込みプレイヤー
3. ⬜ キャッシュ機能
4. ⬜ 一括インポート

---

## セキュリティ考慮事項

1. **API キー保護**: YouTube API キーは環境変数で管理
2. **レート制限**: API呼び出しの制限実装
3. **URL検証**: 悪意のあるURLの排除
4. **XSS対策**: 動画タイトル等のエスケープ

---

## 今後の拡張案

1. **Twitch対応**: Twitchクリップの追加
2. **ニコニコ動画対応**: ニコニコ動画の追加
3. **タイムスタンプ**: 特定シーンへのリンク
4. **自動プレイリスト**: セッション動画の自動再生

---

**最終更新**: 2025年6月25日