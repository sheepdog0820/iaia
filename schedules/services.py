"""
YouTube API連携サービス
"""

import requests
import re
from django.conf import settings


class YouTubeService:
    """YouTube API連携サービス"""
    
    @staticmethod
    def fetch_video_info(video_id):
        """YouTube APIを使用して動画情報を取得"""
        # 開発環境では環境変数が設定されていない場合がある
        api_key = getattr(settings, 'YOUTUBE_API_KEY', None)
        if not api_key:
            # モックデータを返す（開発用）
            return {
                'title': f'Mock Video Title ({video_id})',
                'channel_name': 'Mock Channel',
                'thumbnail_url': f'https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg',
                'duration': 300  # 5分
            }
        
        url = f"{settings.YOUTUBE_API_BASE_URL}/videos"
        params = {
            'key': api_key,
            'part': 'snippet,contentDetails',
            'id': video_id
        }
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get('items'):
                    item = data['items'][0]
                    
                    # サムネイルURLの取得（maxres > high > medium > default）
                    thumbnails = item['snippet']['thumbnails']
                    thumbnail_url = (
                        thumbnails.get('maxres', {}).get('url') or
                        thumbnails.get('high', {}).get('url') or
                        thumbnails.get('medium', {}).get('url') or
                        thumbnails.get('default', {}).get('url')
                    )
                    
                    return {
                        'title': item['snippet']['title'],
                        'channel_name': item['snippet']['channelTitle'],
                        'thumbnail_url': thumbnail_url,
                        'duration': YouTubeService.parse_duration(
                            item['contentDetails']['duration']
                        )
                    }
        except Exception as e:
            # エラーログを記録（本番環境ではloggingを使用）
            print(f"YouTube API error: {e}")
        
        return None
    
    @staticmethod
    def parse_duration(duration_str):
        """ISO 8601形式の期間を秒数に変換
        
        例: PT3M33S -> 213秒
        """
        if not duration_str:
            return 0
            
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            return hours * 3600 + minutes * 60 + seconds
        return 0