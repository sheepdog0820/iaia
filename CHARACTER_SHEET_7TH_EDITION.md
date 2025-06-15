# クトゥルフ神話TRPG 7版 キャラクターシート仕様書

**Call of Cthulhu RPG 7th Edition Character Sheet Specification**

## 📖 概要

本仕様書は、クトゥルフ神話TRPG 7版のキャラクターシート構造と計算ルールを定義します。7版は現代的にアップデートされたシステムで、プッシュロール、ボーナス・ペナルティダイスなど革新的な要素が特徴です。

---

## 📑 目次

1. [基本構造](#1-基本構造)
2. [基本情報](#2-基本情報)
3. [能力値システム](#3-能力値システム)
4. [副次ステータス](#4-副次ステータス)
5. [スキルシステム](#5-スキルシステム)
6. [戦闘システム](#6-戦闘システム)
7. [職業システム](#7-職業システム)
8. [計算ルール](#8-計算ルール)
9. [実装仕様](#9-実装仕様)

---

## 1. 基本構造

### 1.1 キャラクターシートの基本要素

```
┌─────────────────────────────────────┐
│            基本情報                │
│  名前・年齢・性別・職業・出身地     │
├─────────────────────────────────────┤
│            能力値 (8種)            │
│ STR CON POW DEX APP SIZ INT EDU    │
├─────────────────────────────────────┤
│          副次ステータス             │
│   HP MP SAN ビルド ムーブ ダッジ   │
├─────────────────────────────────────┤
│           スキル一覧               │
│  基本技能 + 職業技能 + 興味技能     │
├─────────────────────────────────────┤
│          武器・装備                │
│   武器データ・防具・所持品         │
└─────────────────────────────────────┘
```

### 1.2 7版の特徴

- **プッシュロール**: 失敗時の再挑戦システム
- **ボーナス・ペナルティダイス**: 状況に応じた修正
- **成功レベル**: 通常・ハード・エクストリーム成功
- **改良された戦闘システム**: ビルド値によるアクション順序

---

## 2. 基本情報

### 2.1 データ構造

```json
{
  "basic_info": {
    "name": "探索者名（必須）",
    "age": "年齢（15-90）",
    "gender": "性別",
    "occupation": "職業",
    "birthplace": "出身地",
    "residence": "現住所",
    "personal_description": "個人的な記述",
    "ideology_beliefs": "思想・信念",
    "significant_people": "重要な人々",
    "meaningful_locations": "意味のある場所",
    "treasured_possessions": "大切な所持品",
    "traits": "特性",
    "injuries_scars": "傷跡・負傷",
    "phobias_manias": "恐怖症・躁病",
    "arcane_tomes": "魔道書",
    "artifacts_spells": "アーティファクト・呪文",
    "encounters_with_strange": "奇怪な体験"
  }
}
```

### 2.2 フィールド詳細

| フィールド | 型 | 制約 | 説明 |
|------------|-----|------|------|
| name | VARCHAR(100) | NOT NULL | 探索者の名前 |
| age | INTEGER | 15-90 | 年齢（ゲーム的制約） |
| gender | VARCHAR(50) | | 性別（自由記述） |
| occupation | VARCHAR(100) | | 職業名 |
| birthplace | VARCHAR(100) | | 出身地 |
| residence | VARCHAR(100) | | 現在の居住地 |
| personal_description | TEXT | | 身体的特徴・性格 |
| ideology_beliefs | TEXT | | 信念・イデオロギー |
| significant_people | TEXT | | 重要な人物たち |
| meaningful_locations | TEXT | | 思い出の場所など |
| treasured_possessions | TEXT | | 大切にしている物 |
| traits | TEXT | | 性格的特徴 |
| injuries_scars | TEXT | | 古傷・障害など |
| phobias_manias | TEXT | | 恐怖症や強迫観念 |

---

## 3. 能力値システム

### 3.1 8つの能力値

| 能力値 | 英名 | 説明 | ダイス | 範囲 |
|--------|------|------|--------|------|
| 筋力 | STR | 物理的な力 | 3D6×5 | 15-90 |
| 体力 | CON | 持久力・健康 | 3D6×5 | 15-90 |
| 意思力 | POW | 精神力・魔法適性 | 3D6×5 | 15-90 |
| 敏捷性 | DEX | 素早さ・器用さ | 3D6×5 | 15-90 |
| 外見 | APP | 容姿・魅力 | 3D6×5 | 15-90 |
| 体格 | SIZ | 身長・体重 | (2D6+6)×5 | 30-90 |
| 知識 | INT | 知性・推理力 | (2D6+6)×5 | 40-90 |
| 教育 | EDU | 学識・教養 | (2D6+6)×5 | 40-90 |

### 3.2 7版の能力値特性

```python
# 7版では能力値から直接派生する値が多い
def calculate_half_value(ability_value):
    """半分値計算"""
    return ability_value // 2

def calculate_fifth_value(ability_value):
    """1/5値計算"""
    return ability_value // 5

# 判定レベル
def get_success_level(roll, skill_value):
    """成功レベル判定"""
    if roll > skill_value:
        return "failure"
    elif roll <= skill_value // 5:
        return "extreme_success"
    elif roll <= skill_value // 2:
        return "hard_success"
    else:
        return "regular_success"
```

---

## 4. 副次ステータス

### 4.1 計算式

```json
{
  "derived_stats": {
    "hit_points": {
      "formula": "(CON + SIZ) ÷ 10",
      "description": "ヒットポイント（耐久力）"
    },
    "magic_points": {
      "formula": "POW ÷ 5", 
      "description": "マジックポイント（魔法力）"
    },
    "sanity": {
      "initial": "POW",
      "maximum": 99,
      "description": "正気度（現在値・最大値）"
    },
    "luck": {
      "initial": "3D6 × 5",
      "description": "幸運（技能として扱う）"
    },
    "build": {
      "formula": "(STR + SIZ - 64) ÷ 20 + 1",
      "description": "ビルド値（戦闘順序等に影響）",
      "minimum": -2,
      "maximum": 4
    },
    "move_rate": {
      "formula": "基本8、年齢・能力値により修正",
      "description": "移動力"
    },
    "dodge": {
      "formula": "DEX ÷ 2",
      "description": "回避技能の初期値"
    }
  }
}
```

### 4.2 ビルド値計算

```python
def calculate_build_7th(str_val, siz_val):
    """7版ビルド値計算"""
    total = str_val + siz_val
    
    if total <= 64:
        return -2
    elif total <= 84:
        return -1
    elif total <= 124:
        return 0
    elif total <= 164:
        return 1
    elif total <= 204:
        return 2
    elif total <= 284:
        return 3
    else:
        return 4

def get_damage_bonus_from_build(build):
    """ビルド値からダメージボーナス算出"""
    build_to_db = {
        -2: "-2",
        -1: "-1", 
        0: "0",
        1: "+1d4",
        2: "+1d6",
        3: "+2d6",
        4: "+3d6"
    }
    return build_to_db.get(build, "0")
```

### 4.3 移動力計算

```python
def calculate_move_rate_7th(age, str_val, dex_val, siz_val):
    """7版移動力計算"""
    base_move = 8
    
    # 年齢による修正
    if age >= 80:
        base_move -= 5
    elif age >= 70:
        base_move -= 4
    elif age >= 60:
        base_move -= 3
    elif age >= 50:
        base_move -= 2
    elif age >= 40:
        base_move -= 1
    
    # STRとDEXがSIZより小さい場合の修正
    if str_val < siz_val and dex_val < siz_val:
        base_move -= 1
    
    # STRまたはDEXがSIZより大きい場合の修正
    elif str_val > siz_val or dex_val > siz_val:
        base_move += 1
    
    return max(base_move, 1)  # 最低1
```

---

## 5. スキルシステム

### 5.1 基本スキル一覧（7版）

```json
{
  "basic_skills_7th": {
    "accounting": {"base": 5, "description": "経理"},
    "anthropology": {"base": 1, "description": "人類学"},
    "appraise": {"base": 5, "description": "鑑定"},
    "archaeology": {"base": 1, "description": "考古学"},
    "art_craft": {"base": 5, "description": "芸術/制作"},
    "charm": {"base": 15, "description": "魅惑"},
    "climb": {"base": 20, "description": "登攀"},
    "computer_use": {"base": 5, "description": "コンピューター"},
    "credit_rating": {"base": 0, "description": "信用"},
    "cthulhu_mythos": {"base": 0, "description": "クトゥルフ神話"},
    "disguise": {"base": 5, "description": "変装"},
    "dodge": {"base": "DEX/2", "description": "回避"},
    "drive_auto": {"base": 20, "description": "運転（自動車）"},
    "electrical_repair": {"base": 10, "description": "電気修理"},
    "electronics": {"base": 1, "description": "電子工学"},
    "fast_talk": {"base": 5, "description": "言いくるめ"},
    "fighting_brawl": {"base": 25, "description": "格闘（組み付き）"},
    "firearms_handgun": {"base": 20, "description": "射撃（拳銃）"},
    "firearms_rifle": {"base": 25, "description": "射撃（ライフル/ショットガン）"},
    "first_aid": {"base": 30, "description": "応急手当"},
    "history": {"base": 5, "description": "歴史"},
    "intimidate": {"base": 15, "description": "威圧"},
    "jump": {"base": 20, "description": "跳躍"},
    "language_other": {"base": 1, "description": "他国語"},
    "language_own": {"base": "EDU", "description": "母国語"},
    "law": {"base": 5, "description": "法律"},
    "library_use": {"base": 20, "description": "図書館"},
    "listen": {"base": 20, "description": "聞き耳"},
    "locksmith": {"base": 1, "description": "鍵開け"},
    "mechanical_repair": {"base": 10, "description": "機械修理"},
    "medicine": {"base": 1, "description": "医学"},
    "natural_world": {"base": 10, "description": "博物学"},
    "navigate": {"base": 10, "description": "ナビゲート"},
    "occult": {"base": 5, "description": "オカルト"},
    "operate_heavy_machinery": {"base": 1, "description": "重機械操作"},
    "persuade": {"base": 10, "description": "説得"},
    "pilot": {"base": 1, "description": "操縦"},
    "psychology": {"base": 10, "description": "心理学"},
    "psychoanalysis": {"base": 1, "description": "精神分析"},
    "ride": {"base": 5, "description": "乗馬"},
    "science": {"base": 1, "description": "科学"},
    "sleight_of_hand": {"base": 10, "description": "手さばき"},
    "spot_hidden": {"base": 25, "description": "目星"},
    "stealth": {"base": 20, "description": "隠密"},
    "survival": {"base": 10, "description": "サバイバル"},
    "swim": {"base": 20, "description": "水泳"},
    "throw": {"base": 20, "description": "投擲"},
    "track": {"base": 10, "description": "追跡"}
  }
}
```

### 5.2 7版スキル計算システム

```python
def calculate_skill_levels_7th(base_value):
    """7版スキルレベル計算"""
    return {
        'regular': base_value,
        'hard': base_value // 2,
        'extreme': base_value // 5
    }

def push_roll_7th(skill_name, skill_value, gm_approval=True):
    """プッシュロール実行"""
    if not gm_approval:
        return {"error": "GM承認が必要です"}
    
    # プッシュロール時のリスク
    risks = {
        'physical_skills': ['登攀', '跳躍', '水泳', '運転', '操縦'],
        'mental_skills': ['図書館', 'オカルト', 'クトゥルフ神話'],
        'social_skills': ['魅惑', '威圧', '説得', '言いくるめ']
    }
    
    # プッシュロール実行
    new_roll = roll_d100()
    
    # 失敗時のペナルティ判定
    if new_roll > skill_value:
        if new_roll >= 96:  # ファンブル
            return {
                'result': 'fumble',
                'roll': new_roll,
                'consequence': 'severe_penalty'
            }
        else:
            return {
                'result': 'failure', 
                'roll': new_roll,
                'consequence': 'minor_penalty'
            }
    
    return {
        'result': get_success_level(new_roll, skill_value),
        'roll': new_roll,
        'pushed': True
    }

def bonus_penalty_dice_7th(bonus_dice=0, penalty_dice=0):
    """ボーナス・ペナルティダイス"""
    if bonus_dice > 0 and penalty_dice > 0:
        # 相殺される
        net_bonus = bonus_dice - penalty_dice
        if net_bonus > 0:
            penalty_dice = 0
            bonus_dice = net_bonus
        else:
            bonus_dice = 0
            penalty_dice = abs(net_bonus)
    
    # 基本のd100
    tens = roll_d10() * 10
    ones = roll_d10()
    if ones == 10:  # 0として扱う
        ones = 0
    
    base_roll = tens + ones
    
    # 追加ダイスロール
    additional_tens = []
    for _ in range(max(bonus_dice, penalty_dice)):
        additional_tens.append(roll_d10() * 10)
    
    if bonus_dice > 0:
        # 最も低い十の位を選ぶ
        best_tens = min([tens] + additional_tens)
        final_roll = best_tens + ones
    elif penalty_dice > 0:
        # 最も高い十の位を選ぶ
        worst_tens = max([tens] + additional_tens)
        final_roll = worst_tens + ones
    else:
        final_roll = base_roll
    
    # 100は特別扱い
    if final_roll == 0:
        final_roll = 100
    
    return {
        'final_roll': final_roll,
        'base_roll': base_roll,
        'additional_rolls': additional_tens,
        'bonus_dice': bonus_dice,
        'penalty_dice': penalty_dice
    }
```

---

## 6. 戦闘システム

### 6.1 武器データ構造（7版）

```json
{
  "weapon_7th": {
    "name": "拳銃",
    "skill": "射撃（拳銃）",
    "damage": "1d10",
    "range": "15/30/60",
    "attacks": "1 or 2",
    "ammo": 6,
    "malfunction": 100,
    "build_required": 0
  }
}
```

### 6.2 基本武器一覧（7版）

```json
{
  "weapons_7th": {
    "unarmed": {
      "name": "素手",
      "skill": "格闘（組み付き）",
      "damage": "1d3+DB",
      "range": "タッチ",
      "attacks": 1,
      "build_required": 0
    },
    "knife": {
      "name": "ナイフ",
      "skill": "格闘（組み付き）",
      "damage": "1d4+DB",
      "range": "タッチ",
      "attacks": 1,
      "build_required": 0
    },
    "baseball_bat": {
      "name": "野球バット",
      "skill": "格闘（組み付き）",
      "damage": "1d8+DB",
      "range": "タッチ",
      "attacks": 1,
      "build_required": 0
    },
    "handgun_light": {
      "name": "小型拳銃",
      "skill": "射撃（拳銃）",
      "damage": "1d8",
      "range": "10/20/40",
      "attacks": "1 or 2",
      "ammo": 6,
      "malfunction": 100,
      "build_required": 0
    },
    "handgun_heavy": {
      "name": "大型拳銃",
      "skill": "射撃（拳銃）", 
      "damage": "1d10+2",
      "range": "15/30/60",
      "attacks": "1 or 2", 
      "ammo": 7,
      "malfunction": 100,
      "build_required": 0
    },
    "shotgun": {
      "name": "ショットガン",
      "skill": "射撃（ライフル/ショットガン）",
      "damage": "4d6/2d6/1d6",
      "range": "10/50/100",
      "attacks": 1,
      "ammo": 2,
      "malfunction": 100,
      "build_required": 1
    },
    "rifle": {
      "name": "ライフル",
      "skill": "射撃（ライフル/ショットガン）",
      "damage": "2d6+4",
      "range": "80/250/500", 
      "attacks": 1,
      "ammo": 6,
      "malfunction": 100,
      "build_required": 1
    }
  }
}
```

### 6.3 戦闘順序（7版）

```python
def calculate_combat_initiative_7th(dex, build):
    """7版戦闘順序計算"""
    base_initiative = dex
    
    # ビルド修正
    build_modifier = {
        -2: -2,
        -1: -1,
        0: 0,
        1: 1,
        2: 2,
        3: 3,
        4: 4
    }
    
    initiative = base_initiative + build_modifier.get(build, 0)
    return initiative

def fighting_maneuvers_7th():
    """7版戦闘マニューバー"""
    return {
        'all_out_attack': {
            'description': '全力攻撃',
            'effect': 'ボーナスダイス1個、回避-20'
        },
        'fighting_back': {
            'description': '反撃',
            'effect': '攻撃成功時に反撃可能'
        },
        'dodge': {
            'description': '回避専念',
            'effect': '回避にボーナスダイス1個'
        },
        'full_defense': {
            'description': '全防御',
            'effect': '全ての回避にボーナスダイス1個'
        }
    }
```

---

## 7. 職業システム

### 7.1 代表的な職業（7版）

```json
{
  "occupations_7th": {
    "antiquarian": {
      "name": "骨董商",
      "description": "古い品物の価値を見極める専門家",
      "credit_rating": "30-70",
      "skill_points": "EDU × 2 + (APP × 2 or POW × 2)",
      "skills": {
        "required": ["鑑定", "芸術/制作", "歴史", "図書館", "他国語", "目星", "ひとつの対人技能"],
        "choice_count": 1,
        "choice_options": ["経理", "運転", "オカルト"]
      }
    },
    "detective": {
      "name": "探偵",
      "description": "事件を調査する私立探偵",
      "credit_rating": "20-45", 
      "skill_points": "EDU × 2 + (DEX × 2 or STR × 2)",
      "skills": {
        "required": ["芸術/制作（写真術）", "変装", "法律", "図書館", "心理学", "目星", "ひとつの対人技能"],
        "choice_count": 1,
        "choice_options": ["経理", "コンピューター", "射撃", "他国語", "鍵開け"]
      }
    },
    "doctor_physician": {
      "name": "医師",
      "description": "医療の専門家",
      "credit_rating": "30-80",
      "skill_points": "EDU × 4",
      "skills": {
        "required": ["応急手当", "他国語", "医学", "心理学", "科学（生物学）", "科学（薬学）"],
        "choice_count": 2,
        "choice_options": ["精神分析", "科学（化学）"]
      }
    },
    "journalist": {
      "name": "ジャーナリスト",
      "description": "記事を書く報道関係者",
      "credit_rating": "9-30",
      "skill_points": "EDU × 4",
      "skills": {
        "required": ["歴史", "図書館", "母国語", "心理学", "ひとつの対人技能"],
        "choice_count": 3,
        "choice_options": ["芸術/制作", "他国語", "科学"]
      }
    },
    "professor": {
      "name": "大学教授",
      "description": "大学で教鞭をとる学者",
      "credit_rating": "20-70",
      "skill_points": "EDU × 4", 
      "skills": {
        "required": ["図書館", "他国語", "母国語", "心理学"],
        "choice_count": 4,
        "specialty": "専門分野に関連する学術技能"
      }
    }
  }
}
```

### 7.2 7版職業適用ルール

```python
def apply_occupation_7th(character, occupation_data, skill_choices):
    """7版職業適用"""
    # 技能ポイント計算（複数パターン対応）
    edu_points = character['abilities']['edu'] * 2
    
    # 職業によって異なる追加ポイント計算
    additional_options = occupation_data.get('additional_skill_points', [])
    max_additional = 0
    
    for option in additional_options:
        if option == 'APP × 2':
            points = character['abilities']['app'] * 2
        elif option == 'POW × 2':
            points = character['abilities']['pow'] * 2
        elif option == 'DEX × 2':
            points = character['abilities']['dex'] * 2
        elif option == 'STR × 2':
            points = character['abilities']['str'] * 2
        else:
            points = 0
        
        max_additional = max(max_additional, points)
    
    total_skill_points = edu_points + max_additional
    
    # 必須技能と選択技能の処理
    required_skills = occupation_data['skills']['required']
    choice_skills = skill_choices
    
    # クレジットレーティングの設定
    credit_rating_range = occupation_data['credit_rating']
    
    return {
        'total_skill_points': total_skill_points,
        'required_skills': required_skills,
        'chosen_skills': choice_skills,
        'credit_rating_range': credit_rating_range
    }
```

---

## 8. 計算ルール

### 8.1 キャラクター作成手順（7版）

```python
def create_character_7th():
    """7版キャラクター作成"""
    
    # 1. 能力値の決定
    abilities = {
        'str': roll_3d6() * 5,
        'con': roll_3d6() * 5,
        'pow': roll_3d6() * 5,
        'dex': roll_3d6() * 5,
        'app': roll_3d6() * 5,
        'siz': (roll_2d6() + 6) * 5,
        'int': (roll_2d6() + 6) * 5,
        'edu': (roll_2d6() + 6) * 5
    }
    
    # 2. 副次ステータスの計算
    derived = {
        'hit_points': (abilities['con'] + abilities['siz']) // 10,
        'magic_points': abilities['pow'] // 5,
        'sanity_starting': abilities['pow'],
        'sanity_maximum': 99,
        'luck': roll_3d6() * 5,
        'build': calculate_build_7th(abilities['str'], abilities['siz']),
        'move_rate': 8,  # 年齢考慮後に再計算
        'dodge': abilities['dex'] // 2
    }
    
    # 3. 基本技能値の設定
    skills = set_basic_skills_7th(abilities)
    
    # 4. 職業技能の割り振り
    # （職業選択後に実行）
    
    # 5. 興味技能の割り振り
    # （INT × 2 ポイントを任意に配分）
    
    return {
        'abilities': abilities,
        'derived': derived,
        'skills': skills
    }

def set_basic_skills_7th(abilities):
    """7版基本技能値設定"""
    skills = {}
    
    # 固定基本値スキル
    fixed_skills = {
        'accounting': 5, 'anthropology': 1, 'appraise': 5,
        'archaeology': 1, 'art_craft': 5, 'charm': 15,
        'climb': 20, 'computer_use': 5, 'credit_rating': 0,
        'cthulhu_mythos': 0, 'disguise': 5, 'drive_auto': 20,
        'electrical_repair': 10, 'electronics': 1, 'fast_talk': 5,
        'fighting_brawl': 25, 'firearms_handgun': 20, 'firearms_rifle': 25,
        'first_aid': 30, 'history': 5, 'intimidate': 15,
        'jump': 20, 'language_other': 1, 'law': 5,
        'library_use': 20, 'listen': 20, 'locksmith': 1,
        'mechanical_repair': 10, 'medicine': 1, 'natural_world': 10,
        'navigate': 10, 'occult': 5, 'operate_heavy_machinery': 1,
        'persuade': 10, 'pilot': 1, 'psychology': 10,
        'psychoanalysis': 1, 'ride': 5, 'science': 1,
        'sleight_of_hand': 10, 'spot_hidden': 25, 'stealth': 20,
        'survival': 10, 'swim': 20, 'throw': 20, 'track': 10
    }
    
    for skill, base_value in fixed_skills.items():
        skills[skill] = base_value
    
    # 能力値依存スキル
    skills['dodge'] = abilities['dex'] // 2
    skills['language_own'] = abilities['edu']
    
    return skills
```

### 8.2 技能成長（7版）

```python
def skill_improvement_7th(current_value, experience_check_passed=False):
    """7版技能成長"""
    if not experience_check_passed:
        return current_value
    
    improvement_roll = roll_d100()
    
    # 現在値より高い値が出れば成長
    if improvement_roll > current_value:
        improvement = roll_1d10()
        new_value = current_value + improvement
        
        # 7版では技能値に上限なし（ただし実用的な上限は99）
        return min(new_value, 99)
    
    return current_value

def experience_check_7th(skill_value, used_successfully=False):
    """7版経験チェック"""
    # 使用して成功した技能のみ経験チェック可能
    if not used_successfully:
        return False
    
    roll = roll_d100()
    return roll > skill_value
```

---

## 9. 実装仕様

### 9.1 データベーススキーマ（7版専用）

```sql
CREATE TABLE characters_7th (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    
    -- 基本情報
    name VARCHAR(100) NOT NULL,
    age INTEGER CHECK (age BETWEEN 15 AND 90),
    gender VARCHAR(50),
    occupation VARCHAR(100),
    birthplace VARCHAR(100),
    residence VARCHAR(100),
    
    -- 背景情報（7版拡張）
    personal_description TEXT,
    ideology_beliefs TEXT,
    significant_people TEXT,
    meaningful_locations TEXT,
    treasured_possessions TEXT,
    traits TEXT,
    injuries_scars TEXT,
    phobias_manias TEXT,
    
    -- 能力値
    str INTEGER CHECK (str BETWEEN 15 AND 90),
    con INTEGER CHECK (con BETWEEN 15 AND 90),
    pow INTEGER CHECK (pow BETWEEN 15 AND 90),
    dex INTEGER CHECK (dex BETWEEN 15 AND 90),
    app INTEGER CHECK (app BETWEEN 15 AND 90),
    siz INTEGER CHECK (siz BETWEEN 30 AND 90),
    int INTEGER CHECK (int BETWEEN 40 AND 90),
    edu INTEGER CHECK (edu BETWEEN 40 AND 90),
    
    -- 副次ステータス
    hit_points_max INTEGER,
    hit_points_current INTEGER,
    magic_points_max INTEGER,
    magic_points_current INTEGER,
    sanity_starting INTEGER,
    sanity_maximum INTEGER,
    sanity_current INTEGER,
    
    -- 7版固有
    luck_points INTEGER,
    build_value INTEGER CHECK (build_value BETWEEN -2 AND 4),
    move_rate INTEGER,
    dodge_value INTEGER,
    
    -- 狂気・負傷状態
    temporary_insanity BOOLEAN DEFAULT FALSE,
    indefinite_insanity BOOLEAN DEFAULT FALSE,
    major_wound BOOLEAN DEFAULT FALSE,
    dying BOOLEAN DEFAULT FALSE,
    unconscious BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 9.2 API設計（7版専用）

```python
# 7版キャラクター作成
POST /api/characters/7th/
{
    "name": "田中花子",
    "age": 25,
    "occupation": "ジャーナリスト",
    "abilities": {
        "str": 50,
        "con": 60,
        "pow": 65,
        "dex": 70,
        "app": 60,
        "siz": 55,
        "int": 80,
        "edu": 75
    },
    "background": {
        "ideology_beliefs": "真実は隠されてはならない",
        "significant_people": "恩師の山田教授",
        "meaningful_locations": "母校の大学図書館"
    }
}

# 7版能力値ロール
POST /api/characters/7th/roll-abilities/
{
    "method": "standard",
    "point_buy": false
}

# 7版プッシュロール
POST /api/characters/7th/{id}/push-roll/
{
    "skill_name": "図書館",
    "original_roll": 75,
    "gm_approval": true
}

# 7版ボーナス・ペナルティダイス
POST /api/characters/7th/{id}/bonus-penalty-roll/
{
    "skill_name": "目星",
    "bonus_dice": 1,
    "penalty_dice": 0,
    "reason": "有利な状況"
}

# 7版戦闘処理
POST /api/characters/7th/{id}/combat-action/
{
    "action_type": "attack",
    "weapon": "handgun_light",
    "target_range": "close",
    "maneuver": "aimed_shot"
}
```

### 9.3 バリデーションルール（7版）

```python
class Character7thValidator:
    @staticmethod
    def validate_abilities(abilities):
        """7版能力値検証"""
        rules = {
            'str': (15, 90),
            'con': (15, 90),
            'pow': (15, 90), 
            'dex': (15, 90),
            'app': (15, 90),
            'siz': (30, 90),
            'int': (40, 90),
            'edu': (40, 90)  # 7版ではEDU最低40
        }
        
        for ability, value in abilities.items():
            min_val, max_val = rules[ability]
            if not min_val <= value <= max_val:
                raise ValidationError(f"{ability}は{min_val}-{max_val}の範囲で入力してください")
    
    @staticmethod
    def validate_luck_points(luck_value):
        """幸運値検証"""
        if not 15 <= luck_value <= 90:
            raise ValidationError("幸運値は15-90の範囲で入力してください")
    
    @staticmethod
    def validate_skill_improvement(current_value, improvement_amount):
        """技能成長検証"""
        new_value = current_value + improvement_amount
        if new_value > 99:
            raise ValidationError("技能値は99を超えることはできません")
    
    @staticmethod
    def validate_push_roll_eligibility(skill_name, last_roll_result):
        """プッシュロール実行可能性検証"""
        if last_roll_result in ['success', 'hard_success', 'extreme_success']:
            raise ValidationError("成功した判定はプッシュロールできません")
        
        non_pushable_skills = ['幸運', 'クトゥルフ神話']
        if skill_name in non_pushable_skills:
            raise ValidationError(f"{skill_name}はプッシュロールできません")
```

---

## 📋 7版の特徴まとめ

### ✅ 革新的要素
- **プッシュロール**: 失敗時の再挑戦システム
- **ボーナス・ペナルティダイス**: 柔軟な修正システム  
- **成功レベル**: 通常・ハード・エクストリーム成功
- **ビルド値**: 戦闘でのアクション順序決定
- **拡張された背景設定**: より詳細なキャラクター描写

### ⚠️ 複雑性の増加
- **判定システムの多様化**: 複数の成功レベル
- **プッシュロールのリスク管理**: ペナルティの考慮が必要
- **ボーナス・ペナルティダイスの計算**: 追加のダイス処理
- **戦闘システムの複雑化**: ビルド値による順序管理

### 🔄 6版からの主要変更点
- アイデア・幸運・知識ロールの削除
- 幸運の技能化
- ビルド値の導入
- 移動力計算の変更
- スキル基本値の調整
- 戦闘マニューバーの追加

---

*7版仕様書 - 最終更新日: 2025-06-14*