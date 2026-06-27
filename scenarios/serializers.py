from schedules.duration import effective_duration_expression
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from .models import (
    Scenario,
    ScenarioHandout,
    ScenarioHandoutRecommendedSkill,
    ScenarioRecommendedSkill,
    ScenarioNote,
    PlayHistory,
    ScenarioImage,
)
from accounts.serializers import UserSerializer, validate_character_image


class ScenarioImageSerializer(serializers.ModelSerializer):
    """シナリオ画像シリアライザー"""

    uploaded_by_detail = UserSerializer(source='uploaded_by', read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ScenarioImage
        fields = [
            'id',
            'image',
            'image_url',
            'title',
            'description',
            'order',
            'uploaded_by',
            'uploaded_by_detail',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'uploaded_by', 'created_at', 'updated_at']

    @extend_schema_field(OpenApiTypes.URI)
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def validate_image(self, value):
        return validate_character_image(value)


class ScenarioRecommendedSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScenarioRecommendedSkill
        fields = [
            'id',
            'name',
            'level',
            'description',
            'order',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ScenarioHandoutRecommendedSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScenarioHandoutRecommendedSkill
        fields = [
            'id',
            'name',
            'level',
            'description',
            'order',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ScenarioHandoutSerializer(serializers.ModelSerializer):
    recommended_skill_items = ScenarioHandoutRecommendedSkillSerializer(many=True, required=False)
    title = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = ScenarioHandout
        fields = [
            'id',
            'code',
            'name',
            'title',
            'content',
            'recommended_skills',
            'is_secret',
            'handout_number',
            'assigned_player_slot',
            'order',
            'recommended_skill_items',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        validators = []


class ScenarioSerializer(serializers.ModelSerializer):
    created_by_detail = UserSerializer(source='created_by', read_only=True)
    play_count = serializers.SerializerMethodField()
    total_play_time = serializers.SerializerMethodField()
    game_system = serializers.CharField(required=False)
    recommended_skills = serializers.CharField(allow_blank=True, required=False)
    semi_recommended_skills = serializers.CharField(allow_blank=True, required=False)
    recommended_skill_items = ScenarioRecommendedSkillSerializer(many=True, required=False)
    handout_templates = ScenarioHandoutSerializer(many=True, required=False)
    system = serializers.CharField(write_only=True, required=False)
    difficulty = serializers.CharField(required=False)
    estimated_duration = serializers.CharField(required=False)
    
    class Meta:
        model = Scenario
        fields = ['id', 'title', 'author', 'visibility', 'game_system', 'system', 'difficulty', 'estimated_duration',
                 'summary', 'public_info', 'gm_notes', 'investigator_requirements',
                 'scenario_tags', 'content_warnings', 'setting_era', 'setting_location',
                 'scenario_style', 'lost_rate', 'combat_level', 'pvp_level',
                 'recommended_skills', 'semi_recommended_skills', 'recommended_skill_items', 'handout_templates',
                 'url', 'recommended_players', 'min_players', 'max_players', 'player_count', 'estimated_time',
                 'created_by', 'created_by_detail', 'created_at', 'updated_at', 
                 'play_count', 'total_play_time']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    @extend_schema_field(OpenApiTypes.INT)
    def get_play_count(self, obj):
        return obj.play_histories.count()
    
    @extend_schema_field(OpenApiTypes.INT)
    def get_total_play_time(self, obj):
        from django.db.models import Sum
        total_minutes = obj.play_histories.filter(
            session__duration_minutes__isnull=False
        ).aggregate(total=Sum(effective_duration_expression('session__')))['total'] or 0
        return total_minutes

    def validate_recommended_skills(self, value):
        if value is None:
            return ''
        return value.strip()

    def validate_semi_recommended_skills(self, value):
        if value is None:
            return ''
        return value.strip()

    def validate(self, attrs):
        system = attrs.pop('system', None)
        if system and not attrs.get('game_system'):
            normalized = system.strip().lower()
            if normalized in ['cthulhu', 'coc', 'クトゥルフ', 'クトゥルフ神話', 'クトゥルフ神話trpg']:
                attrs['game_system'] = 'coc6'
            elif normalized in ['dnd', 'd&d', 'ダンジョンズ&ドラゴンズ']:
                attrs['game_system'] = 'dnd'
            elif normalized in ['sw', 'swordworld', 'ソードワールド']:
                attrs['game_system'] = 'sw'
            elif normalized in ['insane', 'インセイン']:
                attrs['game_system'] = 'insane'
            else:
                attrs['game_system'] = 'other'

        if 'game_system' in attrs:
            normalized_system = str(attrs['game_system']).strip().lower()
            if normalized_system in {'coc', 'cthulhu', 'coc6', '6', '6th'}:
                attrs['game_system'] = 'coc6'
            elif normalized_system in {'coc7', '7', '7th'}:
                attrs['game_system'] = 'coc7'
            elif normalized_system not in dict(Scenario.GAME_SYSTEM_CHOICES):
                raise serializers.ValidationError({'game_system': 'Invalid game_system value.'})

        if 'difficulty' in attrs:
            difficulty = attrs['difficulty']
            normalized = str(difficulty).strip().lower()
            difficulty_map = {
                'easy': 'beginner',
                'beginner': 'beginner',
                'medium': 'intermediate',
                'intermediate': 'intermediate',
                'hard': 'advanced',
                'advanced': 'advanced',
                'expert': 'expert',
            }
            mapped = difficulty_map.get(normalized, attrs['difficulty'])
            if mapped not in dict(Scenario.DIFFICULTY_CHOICES):
                raise serializers.ValidationError({'difficulty': 'Invalid difficulty value.'})
            attrs['difficulty'] = mapped

        if 'estimated_duration' in attrs:
            duration_value = attrs['estimated_duration']
            try:
                minutes = int(duration_value)
            except (TypeError, ValueError):
                minutes = None

            if minutes is not None:
                if minutes <= 180:
                    attrs['estimated_duration'] = 'short'
                elif minutes <= 360:
                    attrs['estimated_duration'] = 'medium'
                elif minutes <= 720:
                    attrs['estimated_duration'] = 'long'
                else:
                    attrs['estimated_duration'] = 'campaign'
            elif str(duration_value).strip().lower() not in dict(Scenario.DURATION_CHOICES):
                raise serializers.ValidationError({'estimated_duration': 'Invalid estimated_duration value.'})

        return attrs

    def create(self, validated_data):
        skill_items_data = validated_data.pop('recommended_skill_items', [])
        handouts_data = validated_data.pop('handout_templates', [])
        scenario = Scenario.objects.create(**validated_data)
        self._save_skill_items(scenario, skill_items_data)
        self._save_handouts(scenario, handouts_data)
        return scenario

    def update(self, instance, validated_data):
        skill_items_data = validated_data.pop('recommended_skill_items', None)
        handouts_data = validated_data.pop('handout_templates', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if skill_items_data is not None:
            instance.recommended_skill_items.all().delete()
            self._save_skill_items(instance, skill_items_data)
        if handouts_data is not None:
            instance.handout_templates.all().delete()
            self._save_handouts(instance, handouts_data)
        return instance

    def _save_skill_items(self, scenario, skill_items_data):
        for skill in skill_items_data:
            ScenarioRecommendedSkill.objects.create(
                scenario=scenario,
                **skill,
            )

    def _save_handouts(self, scenario, handouts_data):
        for handout in handouts_data:
            skill_items_data = handout.pop('recommended_skill_items', [])
            if not handout.get('name') and handout.get('title'):
                handout['name'] = handout['title']
            if not handout.get('title') and handout.get('name'):
                handout['title'] = handout['name']
            handout_instance = ScenarioHandout.objects.create(
                scenario=scenario,
                **handout,
            )
            for skill in skill_items_data:
                ScenarioHandoutRecommendedSkill.objects.create(
                    handout=handout_instance,
                    **skill,
                )


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
