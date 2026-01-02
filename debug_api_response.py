#!/usr/bin/env python
"""Debug API response for character list"""

import os
import sys
import django
import json

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tableno.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()

def debug_api_response():
    # Setup
    user = User.objects.get(username='testuser')
    
    client = Client()
    client.force_login(user)
    
    print("=== API Response Debug ===\n")
    
    # Get API response
    response = client.get('/api/accounts/character-sheets/')
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response Type: {type(data)}")
        print(f"Number of characters: {len(data)}")
        
        if data:
            print("\nFirst character data:")
            char = data[0]
            print(json.dumps(char, indent=2, ensure_ascii=False))
            
            print("\nHP/MP/SAN fields:")
            print(f"  max_hp: {char.get('max_hp')}")
            print(f"  current_hp: {char.get('current_hp')}")
            print(f"  max_mp: {char.get('max_mp')}")
            print(f"  current_mp: {char.get('current_mp')}")
            print(f"  max_san: {char.get('max_san')}")
            print(f"  current_san: {char.get('current_san')}")
            
            # Check old field names too
            print("\nOld field names:")
            print(f"  hit_points_max: {char.get('hit_points_max')}")
            print(f"  hit_points_current: {char.get('hit_points_current')}")
            print(f"  magic_points_max: {char.get('magic_points_max')}")
            print(f"  magic_points_current: {char.get('magic_points_current')}")
            print(f"  sanity_max: {char.get('sanity_max')}")
            print(f"  sanity_current: {char.get('sanity_current')}")

if __name__ == '__main__':
    debug_api_response()