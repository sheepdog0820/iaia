from rest_framework import serializers
from .models import Scenario, ScenarioNote, PlayHistory
from accounts.serializers import UserSerializer


class ScenarioSerializer(serializers.ModelSerializer):
    created_by_detail = UserSerializer(source='created_by', read_only=True)
    play_count = serializers.SerializerMethodField()
    total_play_time = serializers.SerializerMethodField()
    recommended_skills = serializers.CharField(allow_blank=True, required=False)
    
    class Meta:
        model = Scenario
        fields = ['id', 'title', 'author', 'game_system', 'difficulty', 'estimated_duration',
                 'summary', 'recommended_skills', 'url', 'recommended_players', 'player_count', 'estimated_time',
                 'created_by', 'created_by_detail', 'created_at', 'updated_at', 
                 'play_count', 'total_play_time']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    def get_play_count(self, obj):
        return obj.play_histories.count()
    
    def get_total_play_time(self, obj):
        from django.db.models import Sum
        total_minutes = obj.play_histories.filter(
            session__duration_minutes__isnull=False
        ).aggregate(total=Sum('session__duration_minutes'))['total'] or 0
        return total_minutes

    def validate_recommended_skills(self, value):
        if value is None:
            return ''
        return value.strip()


class ScenarioNoteSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user', read_only=True)
    scenario_title = serializers.CharField(source='scenario.title', read_only=True)
    
    class Meta:
        model = ScenarioNote
        fields = ['id', 'scenario', 'scenario_title', 'user', 'user_detail',
                 'title', 'content', 'is_private', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class PlayHistorySerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user', read_only=True)
    scenario_detail = ScenarioSerializer(source='scenario', read_only=True)
    session_title = serializers.CharField(source='session.title', read_only=True)
    
    class Meta:
        model = PlayHistory
        fields = ['id', 'scenario', 'scenario_detail', 'user', 'user_detail',
                 'session', 'session_title', 'played_date', 'role', 'notes', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']
