#!/usr/bin/env python
"""Fix character data with null HP/MP/SAN values"""

import os
import sys
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tableno.settings')
django.setup()

from accounts.character_models import CharacterSheet
import math

def fix_character_data():
    """Fix characters with null HP/MP/SAN values"""
    
    print("=== Fixing Character Data ===\n")
    
    # Find characters with null values
    characters_to_fix = CharacterSheet.objects.filter(
        hit_points_max__isnull=True
    ) | CharacterSheet.objects.filter(
        magic_points_max__isnull=True
    ) | CharacterSheet.objects.filter(
        sanity_max__isnull=True
    )
    
    print(f"Found {characters_to_fix.count()} characters to fix\n")
    
    fixed_count = 0
    
    for character in characters_to_fix:
        print(f"Fixing: {character.name} (ID: {character.id})")
        
        # Calculate max values based on edition
        if character.edition == '6th':
            # 6th edition calculations
            if character.hit_points_max is None:
                hp_max = math.ceil((character.con_value + character.siz_value) / 2)
                character.hit_points_max = hp_max
                print(f"  Set HP max: {hp_max}")
            
            if character.magic_points_max is None:
                mp_max = character.pow_value
                character.magic_points_max = mp_max
                print(f"  Set MP max: {mp_max}")
            
            if character.sanity_starting is None:
                san_start = character.pow_value * 5
                character.sanity_starting = san_start
                print(f"  Set SAN starting: {san_start}")
            
            if character.sanity_max is None:
                # Check if character has Cthulhu Mythos skill
                cthulhu_skill = character.skills.filter(
                    skill_name__icontains='クトゥルフ'
                ).first()
                
                if cthulhu_skill:
                    cthulhu_value = cthulhu_skill.current_value
                else:
                    cthulhu_value = 0
                
                san_max = 99 - cthulhu_value
                character.sanity_max = san_max
                print(f"  Set SAN max: {san_max}")
            
            # Set current values if null
            if character.hit_points_current is None:
                character.hit_points_current = character.hit_points_max
                print(f"  Set HP current: {character.hit_points_max}")
            
            if character.magic_points_current is None:
                character.magic_points_current = character.magic_points_max
                print(f"  Set MP current: {character.magic_points_max}")
            
            if character.sanity_current is None:
                character.sanity_current = character.sanity_starting
                print(f"  Set SAN current: {character.sanity_starting}")
        
        # Save changes
        try:
            character.save()
            fixed_count += 1
            print(f"  ✓ Fixed successfully")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        print()
    
    print(f"\n=== Summary ===")
    print(f"Total characters fixed: {fixed_count}")
    
    # Verify fix
    remaining = CharacterSheet.objects.filter(
        hit_points_max__isnull=True
    ).count()
    
    if remaining > 0:
        print(f"Warning: {remaining} characters still have null HP values")
    else:
        print("✓ All characters have valid HP/MP/SAN values")

if __name__ == '__main__':
    fix_character_data()