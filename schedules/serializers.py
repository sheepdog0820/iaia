from rest_framework import serializers
from .models import TRPGSession, SessionParticipant, HandoutInfo
from accounts.serializers import UserSerializer


class SessionParticipantSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user', read_only=True)
    
    class Meta:
        model = SessionParticipant
        fields = ['id', 'session', 'user', 'user_detail', 'role', 
                 'character_name', 'character_sheet_url']
        read_only_fields = ['id']


class HandoutInfoSerializer(serializers.ModelSerializer):
    participant_detail = SessionParticipantSerializer(source='participant', read_only=True)
    
    class Meta:
        model = HandoutInfo
        fields = ['id', 'session', 'participant', 'participant_detail', 
                 'title', 'content', 'is_secret', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TRPGSessionSerializer(serializers.ModelSerializer):
    gm_detail = UserSerializer(source='gm', read_only=True)
    participants_detail = SessionParticipantSerializer(
        source='sessionparticipant_set', 
        many=True, 
        read_only=True
    )
    handouts_detail = HandoutInfoSerializer(
        source='handouts', 
        many=True, 
        read_only=True
    )
    participant_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TRPGSession
        fields = ['id', 'title', 'description', 'date', 'location', 
                 'youtube_url', 'status', 'visibility', 'gm', 'gm_detail',
                 'group', 'duration_minutes', 'participants_detail', 
                 'handouts_detail', 'participant_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'gm', 'created_at', 'updated_at']
    
    def get_participant_count(self, obj):
        return obj.participants.count()


class CalendarEventSerializer(serializers.ModelSerializer):
    """カレンダー表示用の軽量シリアライザー"""
    gm_name = serializers.CharField(source='gm.nickname', read_only=True)
    
    class Meta:
        model = TRPGSession
        fields = ['id', 'title', 'date', 'status', 'gm_name', 'location']


class SessionListSerializer(serializers.ModelSerializer):
    """セッション一覧表示用の見やすいシリアライザー"""
    gm_name = serializers.CharField(source='gm.nickname', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    participant_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    visibility_display = serializers.CharField(source='get_visibility_display', read_only=True)
    date_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = TRPGSession
        fields = [
            'id', 'title', 'description', 'date', 'date_formatted',
            'location', 'status', 'status_display', 'visibility', 'visibility_display',
            'gm_name', 'group_name', 'participant_count', 'duration_minutes',
            'youtube_url'
        ]
    
    def get_participant_count(self, obj):
        return obj.participants.count()
    
    def get_date_formatted(self, obj):
        if obj.date:
            return obj.date.strftime('%Y年%m月%d日 %H:%M')
        return None


class UpcomingSessionSerializer(serializers.ModelSerializer):
    """ホーム画面の次回セッション表示用シリアライザー"""
    gm_name = serializers.CharField(source='gm.nickname', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    participant_count = serializers.SerializerMethodField()
    date_formatted = serializers.SerializerMethodField()
    time_formatted = serializers.SerializerMethodField()
    date_display = serializers.SerializerMethodField()
    participants_summary = serializers.SerializerMethodField()
    duration_display = serializers.SerializerMethodField()
    
    class Meta:
        model = TRPGSession
        fields = [
            'id', 'title', 'description', 'date', 'date_formatted', 'time_formatted', 'date_display',
            'location', 'status', 'gm_name', 'group_name', 'participant_count',
            'participants_summary', 'duration_minutes', 'duration_display'
        ]
    
    def get_participant_count(self, obj):
        return obj.participants.count()
    
    def get_date_formatted(self, obj):
        if obj.date:
            return obj.date.strftime('%Y年%m月%d日')
        return None
    
    def get_time_formatted(self, obj):
        if obj.date:
            return obj.date.strftime('%H:%M')
        return None
    
    def get_date_display(self, obj):
        if obj.date:
            from datetime import datetime, timedelta
            now = datetime.now()
            session_date = obj.date.replace(tzinfo=None) if obj.date.tzinfo else obj.date
            
            # 今日の場合
            if session_date.date() == now.date():
                return f"今日 {obj.date.strftime('%H:%M')}"
            
            # 明日の場合
            elif session_date.date() == (now + timedelta(days=1)).date():
                return f"明日 {obj.date.strftime('%H:%M')}"
            
            # 今週内の場合
            elif session_date.date() <= (now + timedelta(days=7)).date():
                weekdays = ['月', '火', '水', '木', '金', '土', '日']
                weekday = weekdays[session_date.weekday()]
                return f"{session_date.strftime('%m/%d')}({weekday}) {obj.date.strftime('%H:%M')}"
            
            # それ以外
            else:
                return obj.date.strftime('%Y年%m月%d日 %H:%M')
        return None
    
    def get_participants_summary(self, obj):
        """参加者の簡易表示"""
        participants = obj.sessionparticipant_set.select_related('user').all()
        
        if not participants:
            return "参加者なし"
        
        # GMを除く参加者
        players = [p for p in participants if p.user != obj.gm]
        
        if len(players) == 0:
            return "GM のみ"
        elif len(players) <= 3:
            # 3人以下なら全員表示
            names = [p.user.nickname or p.user.username for p in players]
            return ", ".join(names)
        else:
            # 4人以上なら最初の2人 + 他○人
            names = [p.user.nickname or p.user.username for p in players[:2]]
            remaining = len(players) - 2
            return f"{', '.join(names)} 他{remaining}人"
    
    def get_duration_display(self, obj):
        if obj.duration_minutes:
            hours = obj.duration_minutes // 60
            minutes = obj.duration_minutes % 60
            if hours > 0 and minutes > 0:
                return f"{hours}時間{minutes}分"
            elif hours > 0:
                return f"{hours}時間"
            else:
                return f"{minutes}分"
        return None