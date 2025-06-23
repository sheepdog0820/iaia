"""
Character sheet management views
"""
from .common_imports import *
from .base_views import BaseViewSet, PermissionMixin
from .mixins import CharacterSheetAccessMixin, CharacterNestedResourceMixin, ErrorHandlerMixin


class CharacterSheetViewSet(CharacterSheetAccessMixin, PermissionMixin, viewsets.ModelViewSet):
    """Character sheet management ViewSet"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get user's character sheets only"""
        return CharacterSheet.objects.filter(user=self.request.user).select_related(
            'parent_sheet', 'sixth_edition_data', 'user'
        ).prefetch_related(
            'skills', 'equipment'
        ).order_by('-updated_at')
    
    def get_serializer_class(self):
        """Action-based serializer selection"""
        if self.action == 'list':
            return CharacterSheetListSerializer
        elif self.action == 'create':
            return CharacterSheetCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CharacterSheetUpdateSerializer
        else:
            return CharacterSheetSerializer
    
    # get_object is now handled by CharacterSheetAccessMixin
    
    @action(detail=False, methods=['get'])
    def by_edition(self, request):
        """Get character sheets by edition"""
        edition = request.query_params.get('edition')
        if not edition or edition not in ['6th']:
            return Response(
                {'error': 'edition parameter is required (6th)'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(edition=edition)
        serializer = CharacterSheetListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active character sheets"""
        queryset = self.get_queryset().filter(is_active=True)
        serializer = CharacterSheetListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def create_version(self, request, pk=None):
        """Create new version of character sheet"""
        original_sheet = self.get_object()
        
        # Set parent sheet
        if original_sheet.parent_sheet:
            parent_sheet = original_sheet.parent_sheet
        else:
            parent_sheet = original_sheet
        
        # Set new version number
        latest_version = CharacterSheet.objects.filter(
            parent_sheet=parent_sheet
        ).order_by('-version').first()
        
        if latest_version:
            new_version = latest_version.version + 1
        else:
            new_version = parent_sheet.version + 1
        
        # Copy original data
        new_data = {
            'user': request.user,
            'edition': original_sheet.edition,
            'name': original_sheet.name,
            'player_name': original_sheet.player_name,
            'age': original_sheet.age,
            'gender': original_sheet.gender,
            'occupation': original_sheet.occupation,
            'birthplace': original_sheet.birthplace,
            'residence': original_sheet.residence,
            'str_value': original_sheet.str_value,
            'con_value': original_sheet.con_value,
            'pow_value': original_sheet.pow_value,
            'dex_value': original_sheet.dex_value,
            'app_value': original_sheet.app_value,
            'siz_value': original_sheet.siz_value,
            'int_value': original_sheet.int_value,
            'edu_value': original_sheet.edu_value,
            'hit_points_max': original_sheet.hit_points_max,
            'hit_points_current': original_sheet.hit_points_current,
            'magic_points_max': original_sheet.magic_points_max,
            'magic_points_current': original_sheet.magic_points_current,
            'sanity_starting': original_sheet.sanity_starting,
            'sanity_max': original_sheet.sanity_max,
            'sanity_current': original_sheet.sanity_current,
            'version': new_version,
            'parent_sheet': parent_sheet,
            'notes': original_sheet.notes,
            'is_active': original_sheet.is_active,
        }
        
        # Copy character image if exists
        if original_sheet.character_image:
            new_data['character_image'] = original_sheet.character_image
        
        # Override with request data
        for key, value in request.data.items():
            if key not in ['id', 'version', 'created_at', 'updated_at', 'parent_sheet', 'user']:
                new_data[key] = value
        
        # Create new character sheet
        new_sheet = CharacterSheet.objects.create(**new_data)
        
        # Update current values individually to avoid save method auto-calculation
        update_fields = {}
        for key, value in request.data.items():
            if key in ['hit_points_current', 'magic_points_current', 'sanity_current']:
                update_fields[key] = value
        
        if update_fields:
            CharacterSheet.objects.filter(id=new_sheet.id).update(**update_fields)
            new_sheet.refresh_from_db()
        
        # Copy original skills
        for skill in original_sheet.skills.all():
            CharacterSkill.objects.create(
                character_sheet=new_sheet,
                skill_name=skill.skill_name,
                base_value=skill.base_value,
                occupation_points=skill.occupation_points,
                interest_points=skill.interest_points,
                other_points=skill.other_points
            )
        
        # Copy original equipment
        for equipment in original_sheet.equipment.all():
            CharacterEquipment.objects.create(
                character_sheet=new_sheet,
                item_type=equipment.item_type,
                name=equipment.name,
                skill_name=equipment.skill_name,
                damage=equipment.damage,
                base_range=equipment.base_range,
                attacks_per_round=equipment.attacks_per_round,
                ammo=equipment.ammo,
                malfunction_number=equipment.malfunction_number,
                armor_points=equipment.armor_points,
                description=equipment.description,
                quantity=equipment.quantity
            )
        
        # Copy edition-specific data  
        if original_sheet.edition == '6th' and hasattr(original_sheet, 'sixth_edition_data'):
            sixth_data = original_sheet.sixth_edition_data
            CharacterSheet6th.objects.create(
                character_sheet=new_sheet,
                mental_disorder=sixth_data.mental_disorder
            )
        
        # Return created character sheet
        response_serializer = CharacterSheetSerializer(new_sheet)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """Get character sheet version history"""
        sheet = self.get_object()
        
        if sheet.parent_sheet:
            base_sheet = sheet.parent_sheet
        else:
            base_sheet = sheet
        
        # Get all versions
        versions = CharacterSheet.objects.filter(
            parent_sheet=base_sheet
        ).order_by('version')
        
        # Include parent version
        all_versions = [base_sheet] + list(versions)
        
        serializer = CharacterSheetListSerializer(all_versions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Toggle character sheet active status"""
        sheet = self.get_object()
        sheet.is_active = not sheet.is_active
        sheet.save()
        
        serializer = CharacterSheetSerializer(sheet)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def ccfolia_json(self, request, pk=None):
        """Export to CCFOLIA format JSON"""
        sheet = self.get_object()
        
        # Use model's export_ccfolia_format method
        ccfolia_data = sheet.export_ccfolia_format()
        
        return Response(ccfolia_data)
    
    @action(detail=True, methods=['get'])
    def export_version_data(self, request, pk=None):
        """Export version data"""
        sheet = self.get_object()
        
        # Version data including history
        version_data = {
            "current_version": {
                "id": sheet.id,
                "version": sheet.version,
                "created_at": sheet.created_at.isoformat(),
                "updated_at": sheet.updated_at.isoformat(),
                "data": CharacterSheetSerializer(sheet).data
            },
            "version_history": []
        }
        
        # Get history if parent sheet exists
        if sheet.parent_sheet:
            base_sheet = sheet.parent_sheet
            versions = CharacterSheet.objects.filter(
                parent_sheet=base_sheet
            ).order_by('version')
            
            # Include parent sheet
            all_versions = [base_sheet] + list(versions)
            
            for version in all_versions:
                version_info = {
                    "id": version.id,
                    "version": version.version,
                    "created_at": version.created_at.isoformat(),
                    "updated_at": version.updated_at.isoformat(),
                    "is_current": version.id == sheet.id
                }
                version_data["version_history"].append(version_info)
        
        return Response(version_data)
    
    @action(detail=False, methods=['post'])
    def create_6th_edition(self, request):
        """6th edition character creation endpoint (Cthulhu Mythos TRPG exclusive)"""
        # Data validation
        required_fields = ['name', 'str_value', 'con_value', 'pow_value', 'dex_value', 
                          'app_value', 'siz_value', 'int_value', 'edu_value']
        
        for field in required_fields:
            if field not in request.data:
                return Response(
                    {'error': f'{field} is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 6th edition ability value range check (3-18)
        ability_fields = ['str_value', 'con_value', 'pow_value', 'dex_value', 
                         'app_value', 'int_value', 'edu_value']
        for field in ability_fields:
            value = request.data.get(field)
            if not isinstance(value, int) or value < 3 or value > 18:
                return Response(
                    {'error': f'{field} must be between 3 and 18 for 6th edition'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # SIZ range check (8-18)
        siz_value = request.data.get('siz_value')
        if not isinstance(siz_value, int) or siz_value < 8 or siz_value > 18:
            return Response(
                {'error': 'siz_value must be between 8 and 18 for 6th edition'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Create basic character sheet
            character_data = {
                'user': request.user,
                'edition': '6th',
                'name': request.data['name'],
                'player_name': request.data.get('player_name', request.user.nickname or request.user.username),
                'age': request.data.get('age', 25),
                'gender': request.data.get('gender', ''),
                'occupation': request.data.get('occupation', ''),
                'birthplace': request.data.get('birthplace', ''),
                'residence': request.data.get('residence', ''),
                'str_value': request.data['str_value'],
                'con_value': request.data['con_value'],
                'pow_value': request.data['pow_value'],
                'dex_value': request.data['dex_value'],
                'app_value': request.data['app_value'],
                'siz_value': request.data['siz_value'],
                'int_value': request.data['int_value'],
                'edu_value': request.data['edu_value'],
                'notes': request.data.get('notes', ''),
                'is_active': True
            }
            
            # Handle character image if provided
            if 'character_image' in request.FILES:
                character_data['character_image'] = request.FILES['character_image']
            
            # Create character sheet (save method auto-calculates secondary stats)
            character_sheet = CharacterSheet.objects.create(**character_data)
            
            # Create 6th edition specific data
            CharacterSheet6th.objects.create(
                character_sheet=character_sheet,
                mental_disorder=request.data.get('mental_disorder', '')
            )
            
            # Create skills data if provided
            skills_data = request.data.get('skills', [])
            for skill_data in skills_data:
                if 'skill_name' in skill_data:
                    CharacterSkill.objects.create(
                        character_sheet=character_sheet,
                        skill_name=skill_data['skill_name'],
                        base_value=skill_data.get('base_value', 0),
                        occupation_points=skill_data.get('occupation_points', 0),
                        interest_points=skill_data.get('interest_points', 0),
                        other_points=skill_data.get('other_points', 0)
                    )
            
            # Create equipment data if provided
            equipment_data = request.data.get('equipment', [])
            for equipment in equipment_data:
                if 'name' in equipment:
                    CharacterEquipment.objects.create(
                        character_sheet=character_sheet,
                        item_type=equipment.get('item_type', 'item'),
                        name=equipment['name'],
                        skill_name=equipment.get('skill_name', ''),
                        damage=equipment.get('damage', ''),
                        base_range=equipment.get('base_range', ''),
                        attacks_per_round=equipment.get('attacks_per_round'),
                        ammo=equipment.get('ammo'),
                        malfunction_number=equipment.get('malfunction_number'),
                        armor_points=equipment.get('armor_points'),
                        description=equipment.get('description', ''),
                        quantity=equipment.get('quantity', 1)
                    )
            
            # Handle multiple character images
            image_files = []
            # Check for single image in character_image field
            if 'character_image' in request.FILES:
                image_files.append(request.FILES['character_image'])
            
            # Check for multiple images in character_images field
            if 'character_images' in request.FILES:
                for image in request.FILES.getlist('character_images'):
                    image_files.append(image)
            
            # Create CharacterImage entries for each uploaded image
            for index, image_file in enumerate(image_files):
                CharacterImage.objects.create(
                    character_sheet=character_sheet,
                    image=image_file,
                    is_main=(index == 0),  # First image is main
                    order=index
                )
            
            # Return created character sheet
            response_serializer = CharacterSheetSerializer(character_sheet)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Character sheet creation failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def skill_points_summary(self, request, pk=None):
        """技能ポイントサマリー取得API"""
        sheet = self.get_object()
        
        summary = {
            'total_occupation_points': sheet.calculate_occupation_points(),
            'total_hobby_points': sheet.calculate_hobby_points(),
            'used_occupation_points': sheet.calculate_used_occupation_points(),
            'used_hobby_points': sheet.calculate_used_hobby_points(),
            'remaining_occupation_points': sheet.calculate_remaining_occupation_points(),
            'remaining_hobby_points': sheet.calculate_remaining_hobby_points()
        }
        
        return Response(summary)
    
    @action(detail=True, methods=['post'])
    def allocate_skill_points(self, request, pk=None):
        """技能ポイント割り振りAPI"""
        sheet = self.get_object()
        
        skill_id = request.data.get('skill_id')
        occupation_points = request.data.get('occupation_points', 0)
        interest_points = request.data.get('interest_points', 0)
        
        if not skill_id:
            return Response(
                {'error': 'skill_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            skill = CharacterSkill.objects.get(
                id=skill_id,
                character_sheet=sheet
            )
        except CharacterSkill.DoesNotExist:
            return Response(
                {'error': '技能が見つかりません'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # ポイント不足チェック
        if occupation_points > sheet.calculate_remaining_occupation_points() + skill.occupation_points:
            return Response(
                {'error': '職業技能ポイントが不足しています'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if interest_points > sheet.calculate_remaining_hobby_points() + skill.interest_points:
            return Response(
                {'error': '趣味技能ポイントが不足しています'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # ポイント更新
        skill.occupation_points = occupation_points
        skill.interest_points = interest_points
        skill.save()
        
        # 更新された技能データを返す
        serializer = CharacterSkillSerializer(skill)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def batch_allocate_skill_points(self, request, pk=None):
        """一括技能ポイント割り振りAPI"""
        sheet = self.get_object()
        allocations = request.data.get('allocations', [])
        
        if not allocations:
            return Response(
                {'error': 'allocations are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        updated_count = 0
        total_occupation_used = 0
        total_hobby_used = 0
        
        for allocation in allocations:
            skill_id = allocation.get('skill_id')
            occupation_points = allocation.get('occupation_points', 0)
            interest_points = allocation.get('interest_points', 0)
            
            if not skill_id:
                continue
            
            try:
                skill = CharacterSkill.objects.get(
                    id=skill_id,
                    character_sheet=sheet
                )
                
                skill.occupation_points = occupation_points
                skill.interest_points = interest_points
                skill.save()
                
                updated_count += 1
                total_occupation_used += occupation_points
                total_hobby_used += interest_points
                
            except CharacterSkill.DoesNotExist:
                continue
        
        # 残りポイントを計算
        remaining_occupation = sheet.calculate_occupation_points() - sheet.calculate_used_occupation_points()
        remaining_hobby = sheet.calculate_hobby_points() - sheet.calculate_used_hobby_points()
        
        return Response({
            'updated_count': updated_count,
            'remaining_occupation_points': remaining_occupation,
            'remaining_hobby_points': remaining_hobby
        })
    
    @action(detail=True, methods=['post'])
    def reset_skill_points(self, request, pk=None):
        """技能ポイントリセットAPI"""
        sheet = self.get_object()
        
        # 全技能のポイントをリセット（個別にsaveしてcurrent_valueを自動計算）
        skills = CharacterSkill.objects.filter(character_sheet=sheet)
        for skill in skills:
            skill.occupation_points = 0
            skill.interest_points = 0
            skill.save()
        
        return Response({'message': '技能ポイントがリセットされました'})
    
    @action(detail=True, methods=['get'])
    def combat_summary(self, request, pk=None):
        """戦闘サマリー取得API"""
        sheet = self.get_object()
        
        # 武器・防具の取得
        weapons = CharacterEquipment.objects.filter(
            character_sheet=sheet,
            item_type='weapon'
        )
        armors = CharacterEquipment.objects.filter(
            character_sheet=sheet,
            item_type='armor'
        )
        
        # ダメージボーナスの取得
        damage_bonus = "+0"
        if sheet.edition == '6th' and hasattr(sheet, 'sixth_edition_data'):
            damage_bonus = sheet.sixth_edition_data.damage_bonus
        
        # 総防護点の計算
        total_armor_points = sum(armor.armor_points or 0 for armor in armors)
        
        summary = {
            'damage_bonus': damage_bonus,
            'total_armor_points': total_armor_points,
            'weapons_count': weapons.count(),
            'armor_count': armors.count(),
            'weapons': [
                {
                    'id': weapon.id,
                    'name': weapon.name,
                    'skill_name': weapon.skill_name,
                    'damage': weapon.damage,
                    'base_range': weapon.base_range,
                    'attacks_per_round': weapon.attacks_per_round,
                    'ammo': weapon.ammo,
                    'malfunction_number': weapon.malfunction_number
                }
                for weapon in weapons
            ],
            'armors': [
                {
                    'id': armor.id,
                    'name': armor.name,
                    'armor_points': armor.armor_points,
                    'description': armor.description
                }
                for armor in armors
            ]
        }
        
        return Response(summary)
    
    @action(detail=True, methods=['get'])
    def financial_summary(self, request, pk=None):
        """財務サマリー取得API"""
        sheet = self.get_object()
        
        # 6版データの取得
        if sheet.edition != '6th' or not hasattr(sheet, 'sixth_edition_data'):
            return Response(
                {'error': '6版キャラクターシートのみサポートします'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        sixth_data = sheet.sixth_edition_data
        
        summary = {
            'cash': str(sixth_data.cash),
            'assets': str(sixth_data.assets),
            'annual_income': str(sixth_data.annual_income),
            'real_estate': sixth_data.real_estate,
            'total_wealth': str(sixth_data.calculate_total_wealth())
        }
        
        return Response(summary)
    
    @action(detail=True, methods=['patch'])
    def update_financial_data(self, request, pk=None):
        """財務データ更新API"""
        from decimal import Decimal, InvalidOperation
        
        sheet = self.get_object()
        
        # 6版データの取得
        if sheet.edition != '6th' or not hasattr(sheet, 'sixth_edition_data'):
            return Response(
                {'error': '6版キャラクターシートのみサポートします'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        sixth_data = sheet.sixth_edition_data
        
        try:
            # 各フィールドの更新
            if 'cash' in request.data:
                sixth_data.cash = Decimal(str(request.data['cash']))
            
            if 'assets' in request.data:
                sixth_data.assets = Decimal(str(request.data['assets']))
            
            if 'annual_income' in request.data:
                sixth_data.annual_income = Decimal(str(request.data['annual_income']))
            
            if 'real_estate' in request.data:
                sixth_data.real_estate = request.data['real_estate']
            
            # 保存（バリデーション含む）
            sixth_data.save()
            
            return Response({
                'message': '財務データが更新されました',
                'cash': str(sixth_data.cash),
                'assets': str(sixth_data.assets),
                'annual_income': str(sixth_data.annual_income),
                'real_estate': sixth_data.real_estate,
                'total_wealth': str(sixth_data.calculate_total_wealth())
            })
            
        except (ValueError, InvalidOperation) as e:
            return Response(
                {'error': f'数値変換エラー: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except ValidationError as e:
            return Response(
                {'error': f'バリデーションエラー: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'財務データ更新に失敗しました: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def inventory_summary(self, request, pk=None):
        """インベントリサマリー取得API"""
        sheet = self.get_object()
        
        # アイテムの取得
        items = CharacterEquipment.objects.filter(
            character_sheet=sheet,
            item_type='item'
        )
        
        # 総重量の計算
        total_weight = sum(
            (item.weight or 0) * item.quantity 
            for item in items
        )
        
        # 運搬能力の計算
        carry_capacity = sheet.calculate_carry_capacity()
        movement_penalty = sheet.calculate_movement_penalty(total_weight)
        
        summary = {
            'items': [
                {
                    'id': item.id,
                    'name': item.name,
                    'quantity': item.quantity,
                    'weight': item.weight,
                    'total_weight': (item.weight or 0) * item.quantity,
                    'description': item.description
                }
                for item in items
            ],
            'total_items': len(items),
            'total_weight': total_weight,
            'carry_capacity': carry_capacity,
            'movement_penalty': movement_penalty,
            'is_overloaded': total_weight > carry_capacity
        }
        
        return Response(summary)
    
    @action(detail=True, methods=['post'])
    def bulk_update_items(self, request, pk=None):
        """アイテム一括更新API"""
        sheet = self.get_object()
        
        items_data = request.data.get('items', [])
        if not items_data:
            return Response(
                {'error': 'items data is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        updated_count = 0
        errors = []
        
        for item_data in items_data:
            item_id = item_data.get('id')
            if not item_id:
                errors.append('item id is required')
                continue
            
            try:
                item = CharacterEquipment.objects.get(
                    id=item_id,
                    character_sheet=sheet
                )
                
                # 数量更新
                if 'quantity' in item_data:
                    item.quantity = item_data['quantity']
                
                # 重量更新
                if 'weight' in item_data:
                    item.weight = item_data['weight']
                
                item.save()
                updated_count += 1
                
            except CharacterEquipment.DoesNotExist:
                errors.append(f'Item with id {item_id} not found')
            except Exception as e:
                errors.append(f'Failed to update item {item_id}: {str(e)}')
        
        response_data = {
            'updated_count': updated_count,
            'message': f'{updated_count}件のアイテムが更新されました'
        }
        
        if errors:
            response_data['errors'] = errors
        
        return Response(response_data)
    
    @action(detail=True, methods=['get'])
    def background_summary(self, request, pk=None):
        """背景情報サマリー取得API"""
        sheet = self.get_object()
        
        try:
            background = sheet.background_info
        except AttributeError:
            # 背景情報が存在しない場合は空のデータを返す
            return Response({
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
                'fellow_investigators': '',
                'notes_memo': ''
            })
        
        summary = {
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
            'fellow_investigators': background.fellow_investigators,
            'notes_memo': background.notes_memo
        }
        
        return Response(summary)
    
    @action(detail=True, methods=['patch'])
    def update_background_data(self, request, pk=None):
        """背景情報更新API"""
        from ..character_models import CharacterBackground
        
        sheet = self.get_object()
        
        try:
            # 既存の背景情報を取得
            background = sheet.background_info
        except AttributeError:
            # 背景情報が存在しない場合は新規作成
            background = CharacterBackground.objects.create(character_sheet=sheet)
        
        try:
            # 各フィールドの更新
            update_fields = [
                'appearance_description', 'beliefs_ideology', 'significant_people',
                'meaningful_locations', 'treasured_possessions', 'traits_mannerisms',
                'personal_history', 'important_events', 'scars_injuries',
                'phobias_manias', 'fellow_investigators', 'notes_memo'
            ]
            
            for field in update_fields:
                if field in request.data:
                    setattr(background, field, request.data[field])
            
            # 保存（バリデーション含む）
            background.save()
            
            return Response({
                'message': '背景情報が更新されました',
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
                'fellow_investigators': background.fellow_investigators,
                'notes_memo': background.notes_memo
            })
            
        except ValidationError as e:
            return Response(
                {'error': f'バリデーションエラー: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'背景情報更新に失敗しました: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get', 'post'])
    def growth_records(self, request, pk=None):
        """成長記録の取得・作成API"""
        from ..character_models import GrowthRecord
        
        sheet = self.get_object()
        
        if request.method == 'GET':
            # 成長記録一覧取得
            growth_records = GrowthRecord.objects.filter(character_sheet=sheet)
            
            records_data = []
            for record in growth_records:
                records_data.append({
                    'id': record.id,
                    'session_date': record.session_date,
                    'scenario_name': record.scenario_name,
                    'gm_name': record.gm_name,
                    'sanity_gained': record.sanity_gained,
                    'sanity_lost': record.sanity_lost,
                    'net_sanity_change': record.calculate_net_sanity_change(),
                    'experience_gained': record.experience_gained,
                    'special_rewards': record.special_rewards,
                    'notes': record.notes,
                    'skill_growths_count': record.skill_growths.count()
                })
            
            return Response(records_data)
        
        elif request.method == 'POST':
            # 成長記録作成
            try:
                growth_record = GrowthRecord.objects.create(
                    character_sheet=sheet,
                    session_date=request.data.get('session_date'),
                    scenario_name=request.data.get('scenario_name'),
                    gm_name=request.data.get('gm_name', ''),
                    sanity_gained=request.data.get('sanity_gained', 0),
                    sanity_lost=request.data.get('sanity_lost', 0),
                    experience_gained=request.data.get('experience_gained', 0),
                    special_rewards=request.data.get('special_rewards', ''),
                    notes=request.data.get('notes', '')
                )
                
                return Response({
                    'id': growth_record.id,
                    'session_date': growth_record.session_date,
                    'scenario_name': growth_record.scenario_name,
                    'gm_name': growth_record.gm_name,
                    'sanity_gained': growth_record.sanity_gained,
                    'sanity_lost': growth_record.sanity_lost,
                    'net_sanity_change': growth_record.calculate_net_sanity_change(),
                    'experience_gained': growth_record.experience_gained,
                    'special_rewards': growth_record.special_rewards,
                    'notes': growth_record.notes,
                    'message': '成長記録が作成されました'
                }, status=status.HTTP_201_CREATED)
                
            except ValidationError as e:
                return Response(
                    {'error': f'バリデーションエラー: {str(e)}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                return Response(
                    {'error': f'成長記録作成に失敗しました: {str(e)}'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
    
    @action(detail=True, methods=['post'], url_path='growth-records/(?P<record_id>[^/.]+)/add-skill-growth')
    def add_skill_growth(self, request, pk=None, record_id=None):
        """技能成長記録追加API"""
        from ..character_models import GrowthRecord, SkillGrowthRecord
        
        sheet = self.get_object()
        
        try:
            growth_record = GrowthRecord.objects.get(
                id=record_id,
                character_sheet=sheet
            )
        except GrowthRecord.DoesNotExist:
            return Response(
                {'error': '成長記録が見つかりません'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            skill_growth = SkillGrowthRecord.objects.create(
                growth_record=growth_record,
                skill_name=request.data.get('skill_name'),
                had_experience_check=request.data.get('had_experience_check', False),
                growth_roll_result=request.data.get('growth_roll_result'),
                old_value=request.data.get('old_value'),
                new_value=request.data.get('new_value'),
                growth_amount=request.data.get('growth_amount', 0),
                notes=request.data.get('notes', '')
            )
            
            return Response({
                'id': skill_growth.id,
                'skill_name': skill_growth.skill_name,
                'had_experience_check': skill_growth.had_experience_check,
                'growth_roll_result': skill_growth.growth_roll_result,
                'old_value': skill_growth.old_value,
                'new_value': skill_growth.new_value,
                'growth_amount': skill_growth.growth_amount,
                'is_growth_successful': skill_growth.is_growth_successful(),
                'notes': skill_growth.notes,
                'message': '技能成長記録が追加されました'
            }, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return Response(
                {'error': f'バリデーションエラー: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'技能成長記録追加に失敗しました: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def growth_summary(self, request, pk=None):
        """成長サマリー取得API"""
        from ..character_models import GrowthRecord
        
        sheet = self.get_object()
        
        growth_records = GrowthRecord.objects.filter(character_sheet=sheet)
        
        # 基本統計
        total_sessions = growth_records.count()
        total_sanity_lost = sum(record.sanity_lost for record in growth_records)
        total_sanity_gained = sum(record.sanity_gained for record in growth_records)
        total_experience = sum(record.experience_gained for record in growth_records)
        
        # 最近のシナリオ
        recent_scenarios = []
        for record in growth_records[:5]:  # 最新5件
            recent_scenarios.append({
                'date': record.session_date,
                'scenario': record.scenario_name,
                'sanity_change': record.calculate_net_sanity_change()
            })
        
        summary = {
            'total_sessions': total_sessions,
            'total_sanity_lost': total_sanity_lost,
            'total_sanity_gained': total_sanity_gained,
            'net_sanity_change': total_sanity_gained - total_sanity_lost,
            'total_experience': total_experience,
            'recent_scenarios': recent_scenarios,
            'average_sanity_loss_per_session': total_sanity_lost / total_sessions if total_sessions > 0 else 0
        }
        
        return Response(summary)


class CharacterSkillViewSet(CharacterNestedResourceMixin, ErrorHandlerMixin, viewsets.ModelViewSet):
    """Character skill management ViewSet"""
    serializer_class = CharacterSkillSerializer
    permission_classes = [IsAuthenticated]
    
    # get_queryset and perform_create are now handled by CharacterNestedResourceMixin
    
    @action(detail=False, methods=['post'])
    def create_custom_skill(self, request):
        """Create custom skill (specializations, languages, etc.)"""
        try:
            character_sheet = self.get_character_sheet()
        except (ValidationError, Http404):
            return self.handle_not_found("キャラクターシート")
        
        # Validate required fields
        skill_name = request.data.get('skill_name')
        if not skill_name or skill_name.strip() == '':
            return self.handle_validation_error("skill_name is required")
        
        try:
            # Use custom skill creation helper
            skill = CharacterSkill.create_custom_skill(
                character_sheet=character_sheet,
                skill_name=skill_name,
                category=request.data.get('category', '特殊・その他'),
                base_value=request.data.get('base_value', 5),
                occupation_points=request.data.get('occupation_points', 0),
                interest_points=request.data.get('interest_points', 0),
                bonus_points=request.data.get('bonus_points', 0),
                other_points=request.data.get('other_points', 0),
                notes=request.data.get('notes', '')
            )
            
            serializer = CharacterSkillSerializer(skill)
            return self.handle_creation_success(serializer.data, "カスタム技能が作成されました")
            
        except Exception as e:
            return self.handle_validation_error(f'Custom skill creation failed: {str(e)}')
    
    @action(detail=False, methods=['get'])
    def skill_categories(self, request):
        """Get available skill categories"""
        categories = [
            {'value': 'explore', 'label': '探索系'},
            {'value': 'social', 'label': '対人系'},
            {'value': 'combat', 'label': '戦闘系'},
            {'value': 'knowledge', 'label': '知識系'},
            {'value': 'technical', 'label': '技術系'},
            {'value': 'action', 'label': '行動系'},
            {'value': 'language', 'label': '言語系'},
            {'value': 'special', 'label': '特殊・その他'}
        ]
        return Response(categories)
    
    @action(detail=False, methods=['get'])
    def common_custom_skills(self, request):
        """Get list of common custom skill templates"""
        custom_skills = [
            {
                'name': '芸術（絵画）',
                'category': '特殊・その他',
                'base_value': 5,
                'description': 'イラスト、油絵、水彩画などの絵画技術'
            },
            {
                'name': '芸術（音楽）',
                'category': '特殊・その他',
                'base_value': 5,
                'description': '楽器演奏、作曲、歌唱などの音楽技術'
            },
            {
                'name': '芸術（写真）',
                'category': '特殊・その他',
                'base_value': 5,
                'description': '写真撮影、現像、画像加工などの写真技術'
            },
            {
                'name': '制作（プログラミング）',
                'category': '技術系',
                'base_value': 5,
                'description': 'ソフトウェア開発、システム設計'
            },
            {
                'name': '制作（料理）',
                'category': '技術系',
                'base_value': 5,
                'description': '調理技術、レシピ開発、食材知識'
            },
            {
                'name': '他の言語（英語）',
                'category': '言語系',
                'base_value': 1,
                'description': '英語の読み書き、会話能力'
            },
            {
                'name': '他の言語（中国語）',
                'category': '言語系',
                'base_value': 1,
                'description': '中国語の読み書き、会話能力'
            },
            {
                'name': '他の言語（フランス語）',
                'category': '言語系',
                'base_value': 1,
                'description': 'フランス語の読み書き、会話能力'
            }
        ]
        return Response(custom_skills)
    
    @action(detail=False, methods=['patch'])
    def bulk_update(self, request, character_sheet_id=None):
        """Bulk update/create skills"""
        skills_data = request.data.get('skills', [])
        if not skills_data:
            return Response(
                {'error': 'skills data is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        character_sheet_id = self.kwargs.get('character_sheet_id') or self.kwargs.get('character_sheet_pk')
        if not character_sheet_id:
            return Response(
                {'error': 'character_sheet_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            character_sheet = CharacterSheet.objects.get(
                id=character_sheet_id,
                user=self.request.user
            )
        except CharacterSheet.DoesNotExist:
            return Response(
                {'error': 'Character sheet not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        updated_skills = []
        created_skills = []
        
        for skill_data in skills_data:
            skill_id = skill_data.get('id')
            
            if skill_id:
                # Update existing skill
                try:
                    skill = CharacterSkill.objects.get(
                        id=skill_id,
                        character_sheet__user=self.request.user
                    )
                    
                    # Process updatable fields only
                    updatable_fields = [
                        'base_value', 'occupation_points', 
                        'interest_points', 'bonus_points', 'other_points'
                    ]
                    
                    for field in updatable_fields:
                        if field in skill_data:
                            setattr(skill, field, skill_data[field])
                    
                    skill.save()
                    updated_skills.append(skill)
                    
                except CharacterSkill.DoesNotExist:
                    continue
            else:
                # Create new custom skill
                skill_name = skill_data.get('skill_name')
                if skill_name and skill_name.strip():
                    try:
                        skill = CharacterSkill.create_custom_skill(
                            character_sheet=character_sheet,
                            skill_name=skill_name,
                            category=skill_data.get('category', '特殊・その他'),
                            base_value=skill_data.get('base_value', 5),
                            occupation_points=skill_data.get('occupation_points', 0),
                            interest_points=skill_data.get('interest_points', 0),
                            bonus_points=skill_data.get('bonus_points', 0),
                            other_points=skill_data.get('other_points', 0),
                            notes=skill_data.get('notes', '')
                        )
                        created_skills.append(skill)
                    except Exception:
                        continue
        
        all_skills = updated_skills + created_skills
        serializer = CharacterSkillSerializer(all_skills, many=True)
        return Response(serializer.data)


class CharacterEquipmentViewSet(CharacterNestedResourceMixin, viewsets.ModelViewSet):
    """Character equipment management ViewSet"""
    serializer_class = CharacterEquipmentSerializer
    permission_classes = [IsAuthenticated]
    
    # get_queryset and perform_create are now handled by CharacterNestedResourceMixin
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get equipment list by type"""
        item_type = request.query_params.get('type')
        if not item_type or item_type not in ['weapon', 'armor', 'item']:
            return Response(
                {'error': 'type parameter is required (weapon, armor, or item)'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(item_type=item_type)
        serializer = CharacterEquipmentSerializer(queryset, many=True)
        return Response(serializer.data)


# Django Web Views for Character Management

@method_decorator(login_required, name='dispatch')
class CharacterListView(TemplateView):
    """Character sheet list view"""
    template_name = 'accounts/character_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Edition-based filtering
        edition = self.request.GET.get('edition', 'all')
        is_active = self.request.GET.get('active', 'all')
        
        # Base queryset (show all users' character sheets)
        queryset = CharacterSheet.objects.all().select_related(
            'parent_sheet', 'sixth_edition_data', 'user'
        ).prefetch_related('skills', 'equipment').order_by('-updated_at')
        
        # Apply filters
        if edition in ['6th']:
            queryset = queryset.filter(edition=edition)
        
        if is_active == 'active':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Edition-based statistics (all users)
        sixth_count = CharacterSheet.objects.filter(edition='6th').count()
        active_count = CharacterSheet.objects.filter(is_active=True).count()
        total_count = CharacterSheet.objects.count()
        
        context.update({
            'character_sheets': queryset,
            'sixth_count': sixth_count,
            'active_count': active_count,
            'total_count': total_count,
            'current_edition': edition,
            'current_active': is_active,
        })
        
        return context


@method_decorator(login_required, name='dispatch')
class CharacterDetailView(TemplateView):
    """Character sheet detail view"""
    template_name = 'accounts/character_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        character_id = kwargs.get('character_id')
        
        try:
            character = CharacterSheet.objects.select_related(
                'parent_sheet', 'sixth_edition_data', 'user'
            ).prefetch_related(
                'skills', 'equipment', 'versions'
            ).get(id=character_id)
            
            # Filter skills to those above base value only
            assigned_skills = character.skills.filter(
                current_value__gt=models.F('base_value')
            ).order_by('skill_name')
            
            # Classify equipment by type
            weapons = character.equipment.filter(item_type='weapon')
            armor = character.equipment.filter(item_type='armor')
            items = character.equipment.filter(item_type='item')
            
            # Version history
            if character.parent_sheet:
                base_sheet = character.parent_sheet
            else:
                base_sheet = character
            
            versions = CharacterSheet.objects.filter(
                parent_sheet=base_sheet
            ).order_by('version')
            all_versions = [base_sheet] + list(versions)
            
            context.update({
                'character': character,
                'assigned_skills': assigned_skills,
                'weapons': weapons,
                'armor': armor,
                'items': items,
                'versions': all_versions,
            })
            
        except CharacterSheet.DoesNotExist:
            raise Http404("キャラクターシートが見つかりません")
        
        return context


@method_decorator(login_required, name='dispatch')
class CharacterEditView(TemplateView):
    """Character sheet edit view"""
    template_name = 'accounts/character_edit.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        character_id = kwargs.get('character_id')
        
        if character_id:
            # Edit mode
            try:
                character = CharacterSheet.objects.select_related(
                    'sixth_edition_data'
                ).prefetch_related(
                    'skills', 'equipment'
                ).get(id=character_id, user=self.request.user)
                
                context['character'] = character
                context['mode'] = 'edit'
                
            except CharacterSheet.DoesNotExist:
                raise Http404("キャラクターシートが見つかりません")
        else:
            # Create mode
            context['mode'] = 'create'
        
        # Common skill list (6th/7th edition common basic skills)
        common_skills = [
            '応急手当', '鍵開け', '隠す', '隠れる', '聞き耳', 'こぶし', 
            'キック', 'グレップル', '頭突き', '投擲', 'マーシャルアーツ',
            '拳銃', 'サブマシンガン', 'ショットガン', 'マシンガン', 'ライフル',
            '回避', '運転（自動車）', '機械修理', '重機械操作', '乗馬',
            '水泳', '制作', '操縦（航空機）', '跳躍', '電気修理',
            'ナビゲート', '変装', 'コンピューター', '考古学', '人類学',
            '鑑定', '経理', '図書館', 'オカルト', '化学', '地質学',
            '生物学', '博物学', '物理学', '天文学', '医学', '心理学',
            '精神分析', '法律', 'クトゥルフ神話', '母国語', '他の言語',
            '芸術', '威圧', '言いくるめ', '信用', '値切り', '説得',
            '魅惑', 'ナチュラルワールド', 'サバイバル', 'トラック'
        ]
        
        context['common_skills'] = common_skills
        
        return context


@method_decorator(login_required, name='dispatch')
class Character6thCreateView(FormView):
    """Cthulhu Mythos TRPG 6th edition character creation view"""
    template_name = 'accounts/character_sheet_6th.html'
    form_class = CharacterSheet6thForm
    success_url = '/accounts/character/list/'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['edition'] = '6th'
        context['edition_name'] = '6版'
        
        # 6th edition basic skill list
        sixth_skills = [
            '応急手当', '鍵開け', '隠す', '隠れる', '聞き耳', 'こぶし', 
            'キック', 'グレップル', '頭突き', '投擲', 'マーシャルアーツ',
            'ピストル', 'サブマシンガン', 'ショットガン', 'マシンガン', 'ライフル',
            '回避', '運転', '機械修理', '重機械操作', '乗馬',
            '水泳', '制作', '操縦', '跳躍', '電気修理',
            'ナビゲート', '変装', 'コンピューター', '考古学', '人類学',
            '鑑定', '経理', '図書館', 'オカルト', '化学', '地質学',
            '生物学', '博物学', '物理学', '天文学', '医学', '心理学',
            '精神分析', '法律', 'クトゥルフ神話', '母国語', '他の言語',
            '芸術', '威圧', '言いくるめ', '信用', '値切り', '説得',
            '魅惑', '忍び歩き', '写真術', '目星'
        ]
        
        context['available_skills'] = sixth_skills
        return context
    
    def form_valid(self, form):
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info("Form validation successful, saving character sheet...")
            character_sheet = form.save()
            logger.info(f"Character sheet saved with ID: {character_sheet.id}")
            
            # 画像処理はフォームのsaveメソッドで既に実行されているため、ここでは何もしない
            
            messages.success(
                self.request, 
                f'クトゥルフ神話TRPG 6版探索者「{character_sheet.name}」が作成されました！'
            )
            
            # 作成したキャラクターの詳細画面にリダイレクト
            logger.info(f"Redirecting to character detail page: {character_sheet.id}")
            return redirect('character_detail', character_id=character_sheet.id)
            
        except Exception as e:
            logger.error(f"Error in form_valid: {str(e)}", exc_info=True)
            messages.error(
                self.request,
                f'探索者の作成中にエラーが発生しました: {str(e)}'
            )
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        # 詳細なエラー情報をログに出力
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Form validation errors: {form.errors}")
        logger.error(f"Form data: {form.data}")
        logger.error(f"Form files: {form.files}")
        
        # エラーメッセージを詳細化
        error_messages = []
        for field, errors in form.errors.items():
            if field == '__all__':
                error_messages.extend(errors)
            else:
                field_label = form.fields.get(field, {}).label or field
                for error in errors:
                    error_messages.append(f"{field_label}: {error}")
        
        if error_messages:
            messages.error(
                self.request, 
                f'探索者の作成に失敗しました。<br>' + '<br>'.join(error_messages),
                extra_tags='safe'
            )
        else:
            messages.error(
                self.request, 
                '探索者の作成に失敗しました。入力内容を確認してください。'
            )
        return super().form_invalid(form)