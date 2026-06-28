from rest_framework import serializers

from accounts.character_models import CharacterEquipment, CharacterSheet, CharacterSkill
from accounts.models import ShareLink
from scenarios.models import Scenario, ScenarioHandout
from schedules.models import SessionParticipant, TRPGSession


class ShareLinkSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = ShareLink
        fields = [
            'id',
            'resource_type',
            'object_id',
            'expires_at',
            'revoked_at',
            'allow_anonymous',
            'view_level',
            'is_active',
            'created_at',
        ]
        read_only_fields = ['id', 'revoked_at', 'created_at', 'is_active']


class ShareLinkIssueSerializer(serializers.Serializer):
    resource_type = serializers.ChoiceField(choices=ShareLink.ResourceType.choices)
    object_id = serializers.IntegerField(min_value=0)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    allow_anonymous = serializers.BooleanField(required=False, default=True)
    view_level = serializers.ChoiceField(
        choices=ShareLink.ViewLevel.choices,
        required=False,
        default=ShareLink.ViewLevel.STANDARD,
    )


class FixedShareUrlIssueSerializer(serializers.Serializer):
    resource_type = serializers.ChoiceField(
        choices=[
            ShareLink.ResourceType.CHARACTER,
            ShareLink.ResourceType.SESSION,
            ShareLink.ResourceType.SCENARIO,
        ]
    )
    object_id = serializers.IntegerField(min_value=0)
    auto_enable_link = serializers.BooleanField(required=False, default=False)


class SharedCharacterSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = CharacterSkill
        fields = [
            'id',
            'skill_name',
            'category',
            'base_value',
            'occupation_points',
            'interest_points',
            'bonus_points',
            'other_points',
            'current_value',
        ]
        read_only_fields = fields


class SharedCharacterEquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CharacterEquipment
        fields = [
            'id',
            'item_type',
            'name',
            'skill_name',
            'damage',
            'base_range',
            'attacks_per_round',
            'ammo',
            'malfunction_number',
            'armor_points',
            'description',
            'quantity',
            'weight',
        ]
        read_only_fields = fields


class SharedCharacterSheetSerializer(serializers.ModelSerializer):
    skills = SharedCharacterSkillSerializer(many=True, read_only=True)
    equipment = SharedCharacterEquipmentSerializer(many=True, read_only=True)
    abilities = serializers.DictField(read_only=True)
    character_image_url = serializers.SerializerMethodField()
    background_info = serializers.SerializerMethodField()

    class Meta:
        model = CharacterSheet
        fields = [
            'id',
            'edition',
            'name',
            'player_name',
            'status',
            'version',
            'age',
            'gender',
            'occupation',
            'birthplace',
            'residence',
            'recommended_skills',
            'str_value',
            'con_value',
            'pow_value',
            'dex_value',
            'app_value',
            'siz_value',
            'int_value',
            'edu_value',
            'hit_points_max',
            'hit_points_current',
            'magic_points_max',
            'magic_points_current',
            'sanity_starting',
            'sanity_max',
            'sanity_current',
            'abilities',
            'skills',
            'equipment',
            'background_info',
            'character_image_url',
            'session_count',
        ]
        read_only_fields = fields

    def get_character_image_url(self, obj):
        if not obj.character_image:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.character_image.url)
        return obj.character_image.url

    def get_background_info(self, obj):
        try:
            background = obj.background_info
        except AttributeError:
            return {
                'appearance_description': '',
                'beliefs_ideology': '',
                'significant_people': '',
                'meaningful_locations': '',
                'treasured_possessions': '',
                'traits_mannerisms': '',
                'personal_history': '',
                'important_events': '',
                'scars_injuries': '',
                'phobias_manias': '',
                'arcane_tomes_spells_artifacts': '',
                'encounters_with_strange_entities': '',
                'fellow_investigators': '',
                'notes_memo': '',
            }

        return {
            'appearance_description': background.appearance_description,
            'beliefs_ideology': background.beliefs_ideology,
            'significant_people': background.significant_people,
            'meaningful_locations': background.meaningful_locations,
            'treasured_possessions': background.treasured_possessions,
            'traits_mannerisms': background.traits_mannerisms,
            'personal_history': background.personal_history,
            'important_events': background.important_events,
            'scars_injuries': background.scars_injuries,
            'phobias_manias': background.phobias_manias,
            'arcane_tomes_spells_artifacts': background.arcane_tomes_spells_artifacts,
            'encounters_with_strange_entities': background.encounters_with_strange_entities,
            'fellow_investigators': background.fellow_investigators,
            'notes_memo': background.notes_memo,
        }


class SharedSessionParticipantSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    character_sheet = serializers.SerializerMethodField()

    class Meta:
        model = SessionParticipant
        fields = [
            'display_name',
            'role',
            'character_name',
            'character_sheet_url',
            'player_slot',
            'character_sheet',
        ]
        read_only_fields = fields

    def get_character_sheet(self, obj):
        sheet = obj.character_sheet
        if not sheet or sheet.access_scope not in ('link', 'public'):
            return None
        return {
            'id': sheet.id,
            'name': sheet.name,
            'access_scope': sheet.access_scope,
        }


class SharedSessionSerializer(serializers.ModelSerializer):
    gm_name = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()
    scenario = serializers.SerializerMethodField()
    participant_count = serializers.SerializerMethodField()
    duration_minutes = serializers.IntegerField(source='effective_duration_minutes')

    class Meta:
        model = TRPGSession
        fields = [
            'id',
            'title',
            'description',
            'date',
            'status',
            'gm_name',
            'participants',
            'participant_count',
            'duration_minutes',
            'youtube_url',
            'scenario',
        ]
        read_only_fields = fields

    def get_gm_name(self, obj):
        gm_participant = obj.sessionparticipant_set.select_related(
            'user',
            'participant_identity',
        ).filter(role='gm').order_by('id').first()
        if gm_participant:
            return gm_participant.display_name
        return obj.gm.nickname or obj.gm.username

    def get_participants(self, obj):
        participants = obj.sessionparticipant_set.select_related(
            'user',
            'participant_identity',
            'character_sheet',
        ).order_by(
            'role',
            'player_slot',
            'id',
        )
        return SharedSessionParticipantSerializer(
            participants,
            many=True,
            context=self.context,
        ).data

    def get_participant_count(self, obj):
        return obj.sessionparticipant_set.count()

    def get_scenario(self, obj):
        if not obj.scenario:
            return None
        scenario = obj.scenario
        return {
            'id': scenario.id,
            'title': scenario.title,
            'public_info': scenario.public_info,
            'recommended_skills': scenario.recommended_skills,
            'semi_recommended_skills': scenario.semi_recommended_skills,
        }


class SharedScenarioHandoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScenarioHandout
        fields = [
            'id',
            'code',
            'name',
            'title',
            'content',
            'recommended_skills',
            'handout_number',
            'assigned_player_slot',
            'order',
        ]
        read_only_fields = fields


class SharedScenarioSerializer(serializers.ModelSerializer):
    handout_templates = serializers.SerializerMethodField()

    class Meta:
        model = Scenario
        fields = [
            'id',
            'title',
            'author',
            'game_system',
            'difficulty',
            'estimated_duration',
            'summary',
            'public_info',
            'investigator_requirements',
            'scenario_tags',
            'content_warnings',
            'setting_era',
            'setting_location',
            'scenario_style',
            'lost_rate',
            'combat_level',
            'pvp_level',
            'recommended_skills',
            'semi_recommended_skills',
            'recommended_players',
            'min_players',
            'max_players',
            'player_count',
            'estimated_time',
            'url',
            'handout_templates',
        ]
        read_only_fields = fields

    def get_handout_templates(self, obj):
        handouts = obj.handout_templates.filter(is_secret=False).order_by('order', 'id')
        return SharedScenarioHandoutSerializer(handouts, many=True).data


class SharedStatsSerializer(serializers.Serializer):
    resource_type = serializers.CharField(default='session_participant_stats')
    session = serializers.SerializerMethodField()
    totals = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()

    def get_session(self, obj):
        return {
            'id': obj.id,
            'title': obj.title,
            'date': obj.date.isoformat() if obj.date else None,
        }

    def get_totals(self, obj):
        participants = obj.sessionparticipant_set.all()
        return {
            'participation_count': participants.count(),
            'gm_count': participants.filter(role='gm').count(),
            'player_count': participants.filter(role='player').count(),
            'duration_minutes': obj.effective_duration_minutes,
        }

    def get_participants(self, obj):
        return [
            {
                'display_name': participant.display_name,
                'role': participant.role,
                'character_name': participant.character_name,
                'character_sheet_url': participant.character_sheet_url,
            }
            for participant in obj.sessionparticipant_set.select_related(
                'user',
                'participant_identity',
            ).order_by('role', 'player_slot', 'id')
        ]
