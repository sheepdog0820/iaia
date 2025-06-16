# クトゥルフ神話TRPG 6版 キャラクターシート仕様書

**Call of Cthulhu RPG 6th Edition Character Sheet Specification**

## 📖 概要

本仕様書は、クトゥルフ神話TRPG 6版のキャラクターシート構造と計算ルールを定義します。6版は長年親しまれてきた伝統的なシステムで、シンプルな判定システムと直感的なルールが特徴です。

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
│   HP MP SAN アイデア 幸運 知識     │
├─────────────────────────────────────┤
│           スキル一覧               │
│  基本技能 + 職業技能 + 興味技能     │
├─────────────────────────────────────┤
│          武器・装備                │
│   武器データ・防具・所持品         │
└─────────────────────────────────────┘
```

### 1.2 6版の特徴

- **シンプルな判定**: d100で技能値以下を出せば成功
- **ロールベース**: アイデア・幸運・知識ロールの存在
- **固定基本値**: スキルの基本値は固定
- **ダメージボーナス表**: STR+SIZから表参照

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
    "mental_disorder": "精神的障害（任意）"
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
| mental_disorder | TEXT | NULL | 精神的障害の詳細 |

---

## 3. 能力値システム

### 3.1 8つの能力値

| 能力値 | 英名 | 説明 | 標準ダイス | 標準範囲 |
|--------|------|------|------------|----------|
| 筋力 | STR | 物理的な力 | 3D6 | 3-18 |
| 体力 | CON | 持久力・健康 | 3D6 | 3-18 |
| 意思力 | POW | 精神力・魔法適性 | 3D6 | 3-18 |
| 敏捷性 | DEX | 素早さ・器用さ | 3D6 | 3-18 |
| 外見 | APP | 容姿・魅力 | 3D6 | 3-18 |
| 体格 | SIZ | 身長・体重 | 2D6+6 | 8-18 |
| 知識 | INT | 知性・推理力 | 2D6+6 | 8-18 |
| 教育 | EDU | 学識・教養 | 3D6+3 | 6-21 |

### 3.2 動的ダイス設定システム

**重要**: Arkham Nexusでは、能力値のダイス設定を動的に変更可能です。

#### 3.2.1 設定可能項目
- **ダイス数**: 1～10個
- **ダイス面数**: 2～100面（d2, d4, d6, d8, d10, d12, d20, d100等）
- **ボーナス値**: -50～+50

#### 3.2.2 実装要件
```javascript
// 動的ダイス設定の取得関数
function getDiceSettings(ability) {
    return {
        count: getDiceCount(ability),    // 設定から動的取得
        sides: getDiceSides(ability),    // 設定から動的取得
        bonus: getDiceBonus(ability)     // 設定から動的取得
    };
}

// 能力値ロール実行（固定値禁止）
function rollAbility(ability) {
    const settings = getDiceSettings(ability);
    let total = 0;
    
    for (let i = 0; i < settings.count; i++) {
        total += Math.floor(Math.random() * settings.sides) + 1;
    }
    
    return total + settings.bonus;
}
```

#### 3.2.3 プリセット設定

**標準6版プリセット**
```json
{
    "name": "標準6版設定",
    "settings": {
        "STR": {"count": 3, "sides": 6, "bonus": 0},
        "CON": {"count": 3, "sides": 6, "bonus": 0},
        "POW": {"count": 3, "sides": 6, "bonus": 0},
        "DEX": {"count": 3, "sides": 6, "bonus": 0},
        "APP": {"count": 3, "sides": 6, "bonus": 0},
        "SIZ": {"count": 2, "sides": 6, "bonus": 6},
        "INT": {"count": 2, "sides": 6, "bonus": 6},
        "EDU": {"count": 3, "sides": 6, "bonus": 3}
    }
}
```

**高能力値プリセット**
```json
{
    "name": "高能力値6版設定",
    "settings": {
        "STR": {"count": 4, "sides": 6, "bonus": -3},
        "CON": {"count": 4, "sides": 6, "bonus": -3},
        "POW": {"count": 4, "sides": 6, "bonus": -3},
        "DEX": {"count": 4, "sides": 6, "bonus": -3},
        "APP": {"count": 4, "sides": 6, "bonus": -3},
        "SIZ": {"count": 3, "sides": 6, "bonus": 3},
        "INT": {"count": 3, "sides": 6, "bonus": 3},
        "EDU": {"count": 4, "sides": 6, "bonus": 0}
    }
}
```

#### 3.2.4 制約事項
- **固定値禁止**: ハードコードされた固定ダイス値は使用不可
- **リアルタイム反映**: 設定変更は即座にダイスロール計算に反映
- **設定永続化**: ユーザー設定は保存・復元可能
- **バリデーション**: 範囲外値の入力を防止

### 3.2 能力値の使用

```python
# 基本的な判定
def ability_check(ability_value, dice_roll):
    """能力値判定"""
    return dice_roll <= ability_value

# 対抗判定
def opposed_check(ability1, ability2):
    """対抗判定（高い方が勝利）"""
    roll1 = roll_d100()
    roll2 = roll_d100()

    success1 = roll1 <= ability1
    success2 = roll2 <= ability2

    if success1 and not success2:
        return "player1_wins"
    elif success2 and not success1:
        return "player2_wins"
    elif success1 and success2:
        return "both_succeed_compare_rolls"
    else:
        return "both_fail"
```

---

## 4. 副次ステータス

### 4.1 計算式

```json
{
  "derived_stats": {
    "hit_points": {
      "formula": "(CON + SIZ) ÷ 2",
      "description": "ヒットポイント（耐久力）"
    },
    "magic_points": {
      "formula": "POW",
      "description": "マジックポイント（魔法力）"
    },
    "sanity": {
      "initial": "POW × 5",
      "maximum": 99,
      "description": "正気度（クトゥルフ神話知識で減少）"
    },
    "idea_roll": {
      "formula": "INT × 5",
      "description": "アイデアロール（ひらめき判定）"
    },
    "luck_roll": {
      "formula": "POW × 5",
      "description": "幸運ロール（運試し判定）"
    },
    "know_roll": {
      "formula": "EDU × 5",
      "description": "知識ロール（知っているか判定）"
    }
  }
}
```

### 4.2 ダメージボーナス表

```python
def calculate_damage_bonus_6th(str_val, siz_val):
    """6版ダメージボーナス計算"""
    total = str_val + siz_val
    
    if total <= 64:
        return "-1d4"
    elif total <= 84:
        return "-1d2"
    elif total <= 124:
        return "+0"
    elif total <= 164:
        return "+1d4"
    elif total <= 204:
        return "+1d6"
    elif total <= 284:
        return "+2d6"
    elif total <= 364:
        return "+3d6"
    elif total <= 444:
        return "+4d6"
    else:
        return "+5d6"
```

---

## 5. スキルシステム

### 5.1 基本スキル一覧

```json
{
  "basic_skills": {
    "anthropology": {"base": 1, "description": "人類学"},
    "archaeology": {"base": 1, "description": "考古学"},
    "art": {"base": 5, "description": "芸術"},
    "astronomy": {"base": 1, "description": "天文学"},
    "bargain": {"base": 5, "description": "値切り"},
    "biology": {"base": 1, "description": "生物学"},
    "chemistry": {"base": 1, "description": "化学"},
    "climb": {"base": 40, "description": "登攀"},
    "computer_use": {"base": 1, "description": "コンピューター"},
    "conceal": {"base": 15, "description": "隠す"},
    "credit_rating": {"base": 0, "description": "信用"},
    "cthulhu_mythos": {"base": 0, "description": "クトゥルフ神話"},
    "dodge": {"base": "DEX×2", "description": "回避"},
    "drive_auto": {"base": 20, "description": "運転"},
    "electrical_repair": {"base": 10, "description": "電気修理"},
    "electronics": {"base": 1, "description": "電子工学"},
    "fast_talk": {"base": 5, "description": "言いくるめ"},
    "first_aid": {"base": 30, "description": "応急手当"},
    "geology": {"base": 1, "description": "地質学"},
    "hide": {"base": 10, "description": "隠れる"},
    "history": {"base": 20, "description": "歴史"},
    "jump": {"base": 25, "description": "跳躍"},
    "language_other": {"base": 1, "description": "他国語"},
    "language_own": {"base": "EDU×5", "description": "母国語"},
    "law": {"base": 5, "description": "法律"},
    "library_use": {"base": 25, "description": "図書館"},
    "listen": {"base": 25, "description": "聞き耳"},
    "locksmith": {"base": 1, "description": "鍵開け"},
    "martial_arts": {"base": 1, "description": "マーシャルアーツ"},
    "mechanical_repair": {"base": 20, "description": "機械修理"},
    "medicine": {"base": 5, "description": "医学"},
    "natural_world": {"base": 10, "description": "博物学"},
    "navigate": {"base": 10, "description": "ナビゲート"},
    "occult": {"base": 5, "description": "オカルト"},
    "operate_heavy_machine": {"base": 1, "description": "重機械操作"},
    "persuade": {"base": 15, "description": "説得"},
    "pharmacy": {"base": 1, "description": "薬学"},
    "photography": {"base": 10, "description": "写真術"},
    "physics": {"base": 1, "description": "物理学"},
    "pilot": {"base": 1, "description": "操縦"},
    "psychoanalysis": {"base": 1, "description": "精神分析"},
    "psychology": {"base": 5, "description": "心理学"},
    "ride": {"base": 5, "description": "乗馬"},
    "sneak": {"base": 10, "description": "忍び歩き"},
    "spot_hidden": {"base": 25, "description": "目星"},
    "swim": {"base": 25, "description": "水泳"},
    "throw": {"base": 25, "description": "投擲"},
    "track": {"base": 10, "description": "追跡"}
  }
}
```

### 5.2 スキル計算

```python
def calculate_skill_total(base, occupation, interest, other=0):
    """スキル合計値計算"""
    total = base + occupation + interest + other
    return min(total, 90)  # 6版では90%が上限

def skill_check(skill_value, modifier=0):
    """スキル判定"""
    adjusted_value = skill_value + modifier
    roll = roll_d100()
    
    if roll <= adjusted_value:
        if roll <= 5:
            return "critical_success"
        else:
            return "success"
    else:
        if roll >= 96:
            return "fumble"
        else:
            return "failure"
```

---

## 6. 戦闘システム

### 6.1 武器データ構造

```json
{
  "weapon": {
    "name": "拳銃",
    "skill": "拳銃",
    "damage": "1d10",
    "base_range": "15m",
    "uses_per_round": 3,
    "bullets_in_gun": 6,
    "ammo": 6,
    "jam_number": 100
  }
}
```

### 6.2 基本武器一覧

```json
{
  "weapons_6th": {
    "fist_punch": {
      "name": "こぶし/パンチ",
      "skill": "こぶし（パンチ）",
      "damage": "1d3+db",
      "range": "タッチ",
      "uses_per_round": 1
    },
    "head_butt": {
      "name": "頭突き",
      "skill": "頭突き",
      "damage": "1d4+db",
      "range": "タッチ", 
      "uses_per_round": 1
    },
    "kick": {
      "name": "キック",
      "skill": "キック",
      "damage": "1d6+db",
      "range": "タッチ",
      "uses_per_round": 1
    },
    "grapple": {
      "name": "組み付き",
      "skill": "組み付き",
      "damage": "特殊",
      "range": "タッチ",
      "uses_per_round": 1
    },
    "knife": {
      "name": "ナイフ",
      "skill": "ナイフ",
      "damage": "1d4+db",
      "range": "タッチ",
      "uses_per_round": 1
    },
    "baseball_bat": {
      "name": "野球バット",
      "skill": "こん棒",
      "damage": "1d8+db",
      "range": "タッチ",
      "uses_per_round": 1
    },
    "pistol_38": {
      "name": ".38口径リボルバー",
      "skill": "拳銃",
      "damage": "1d10",
      "range": "15m",
      "uses_per_round": 3,
      "bullets": 6
    },
    "pistol_45": {
      "name": ".45口径自動拳銃",
      "skill": "拳銃", 
      "damage": "1d10+2",
      "range": "15m",
      "uses_per_round": 3,
      "bullets": 7
    },
    "shotgun": {
      "name": "12ゲージショットガン",
      "skill": "ショットガン",
      "damage": "4d6/2d6/1d6",
      "range": "50m",
      "uses_per_round": 1,
      "bullets": 2
    },
    "rifle": {
      "name": ".30-06ライフル",
      "skill": "ライフル",
      "damage": "2d6+4",
      "range": "110m",
      "uses_per_round": 1,
      "bullets": 6
    }
  }
}
```

### 6.3 防具システム

```json
{
  "armor_6th": {
    "leather_jacket": {
      "name": "革ジャケット",
      "protection": 1,
      "locations": ["胸部", "腹部", "腕"]
    },
    "heavy_coat": {
      "name": "厚手のコート", 
      "protection": 1,
      "locations": ["胸部", "腹部", "腕", "脚部"]
    },
    "motorcycle_leathers": {
      "name": "バイク用革スーツ",
      "protection": 2,
      "locations": ["全身"]
    },
    "kevlar_vest": {
      "name": "ケブラーベスト",
      "protection": 4,
      "locations": ["胸部", "腹部"]
    }
  }
}
```

---

## 7. 職業システム

### 7.1 代表的な職業

```json
{
  "occupations_6th": {
    "antiquarian": {
      "name": "骨董商",
      "description": "古い品物の価値を見極める専門家",
      "credit_rating": "30-70",
      "skill_points": "EDU × 20",
      "skill_points_method": "edu20",
      "required_skills": ["鑑定", "歴史", "図書館", "他国語", "値切り"],
      "choice_skills": {
        "count": 3,
        "options": ["経理", "芸術", "工芸"]
      }
    },
    "detective": {
      "name": "探偵",
      "description": "事件を調査する私立探偵",
      "credit_rating": "20-45",
      "skill_points": "EDU × 20 または EDU × 10 + DEX × 10",
      "skill_points_method": "edu20",
      "required_skills": ["図書館", "法律", "説得", "心理学"],
      "choice_skills": {
        "count": 4,
        "options": ["経理", "変装", "拳銃", "写真術", "目星"]
      }
    },
    "doctor": {
      "name": "医師",
      "description": "医療の専門家",
      "credit_rating": "30-80",
      "skill_points": "EDU × 20",
      "skill_points_method": "edu20",
      "required_skills": ["応急手当", "医学", "心理学", "他国語"],
      "choice_skills": {
        "count": 4,
        "options": ["精神分析", "薬学", "生物学", "化学"]
      }
    },
    "journalist": {
      "name": "ジャーナリスト",
      "description": "記事を書く報道関係者",
      "credit_rating": "9-30",
      "skill_points": "EDU × 20",
      "skill_points_method": "edu20",
      "required_skills": ["母国語", "心理学"],
      "choice_skills": {
        "count": 6,
        "options": ["歴史", "図書館", "他国語", "説得", "写真術"]
      }
    },
    "professor": {
      "name": "大学教授",
      "description": "大学で教鞭をとる学者",
      "credit_rating": "20-70",
      "skill_points": "EDU × 20",
      "skill_points_method": "edu20",
      "required_skills": ["図書館", "母国語", "他国語"],
      "choice_skills": {
        "count": 5,
        "specialty": "専門分野に関連する学術技能"
      }
    }
  }
}
```

### 7.2 職業技能ポイント計算

6版では職業技能ポイントの計算方法が複数存在し、職業によって使用する計算式が異なります：

- **EDU × 20**: 教育重視の職業（学者、医師など）
- **EDU × 10 + APP × 10**: 社交的な職業（芸能人、外交官など）
- **EDU × 10 + DEX × 10**: 器用さが必要な職業（探偵、泥棒など）
- **EDU × 10 + POW × 10**: 精神力重視の職業（聖職者、占い師など）
- **EDU × 10 + STR × 10**: 力仕事の職業（警官、兵士など）
- **EDU × 10 + CON × 10**: 体力重視の職業（農夫、労働者など）
- **EDU × 10 + SIZ × 10**: 体格が重要な職業（用心棒など）

```python
def calculate_occupation_skill_points(character, method='edu20'):
    """職業技能ポイント計算"""
    edu = character.abilities['edu']
    app = character.abilities['app']
    dex = character.abilities['dex']
    pow_val = character.abilities['pow']
    str_val = character.abilities['str']
    con = character.abilities['con']
    siz = character.abilities['siz']
    
    calculation_methods = {
        'edu20': edu * 20,
        'edu10app10': edu * 10 + app * 10,
        'edu10dex10': edu * 10 + dex * 10,
        'edu10pow10': edu * 10 + pow_val * 10,
        'edu10str10': edu * 10 + str_val * 10,
        'edu10con10': edu * 10 + con * 10,
        'edu10siz10': edu * 10 + siz * 10,
        'fixed': 0  # 手動設定
    }
    
    return calculation_methods.get(method, edu * 20)

def calculate_interest_skill_points(character, method='int10'):
    """趣味技能ポイント計算"""
    int_val = character.abilities['int']
    
    calculation_methods = {
        'int10': int_val * 10,
        'int5': int_val * 5,
        'int15': int_val * 15,
        'fixed': 0  # 手動設定
    }
    
    return calculation_methods.get(method, int_val * 10)
```

### 7.3 職業適用ルール

```python
def apply_occupation(character, occupation_data, skill_choices):
    """職業を適用"""
    # 技能ポイント計算
    occupation_points = calculate_occupation_skill_points(character, occupation_data['skill_points_method'])
    interest_points = calculate_interest_skill_points(character, 'int10')
    
    # 必須技能のチェック
    required_skills = occupation_data['required_skills']
    
    # 選択技能の適用
    choice_skills = skill_choices
    
    # クレジットレーティングの設定
    credit_rating_range = occupation_data['credit_rating']
    
    return {
        'occupation_skill_points': occupation_points,
        'interest_skill_points': interest_points,
        'required_skills': required_skills,
        'chosen_skills': choice_skills,
        'credit_rating_range': credit_rating_range
    }
```

---

## 8. 計算ルール

### 8.1 キャラクター作成手順

```python
def create_character_6th():
    """6版キャラクター作成"""
    
    # 1. 能力値の決定
    abilities = {
        'str': roll_3d6(),
        'con': roll_3d6(),
        'pow': roll_3d6(),
        'dex': roll_3d6(),
        'app': roll_3d6(),
        'siz': roll_2d6() + 6,
        'int': roll_2d6() + 6,
        'edu': roll_3d6() + 3
    }
    
    # 2. 副次ステータスの計算
    derived = {
        'hit_points': (abilities['con'] + abilities['siz']) // 2,
        'magic_points': abilities['pow'],
        'sanity': abilities['pow'] * 5,
        'idea': abilities['int'] * 5,
        'luck': abilities['pow'] * 5,
        'know': abilities['edu'] * 5,
        'damage_bonus': calculate_damage_bonus_6th(abilities['str'], abilities['siz'])
    }
    
    # 3. 基本技能値の設定
    skills = set_basic_skills_6th(abilities)
    
    # 4. 職業技能の割り振り
    # （職業選択後に実行）
    
    # 5. 興味技能の割り振り
    # （INT × 10 ポイントを任意に配分）
    
    return {
        'abilities': abilities,
        'derived': derived,
        'skills': skills
    }
```

### 8.2 技能成長

```python
def skill_improvement_6th(current_value, roll_result):
    """6版技能成長判定"""
    # 現在の技能値より高い値を出せば成長
    if roll_result > current_value:
        improvement = roll_1d10()
        new_value = min(current_value + improvement, 90)
        return new_value
    return current_value

def experience_check_6th(skill_value):
    """経験チェック（セッション終了時）"""
    roll = roll_d100()
    if roll > skill_value:
        return True  # 成長可能
    return False
```

---

## 9. 実装仕様

### 9.1 データベーススキーマ（6版専用）

```sql
CREATE TABLE characters_6th (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    
    -- 基本情報
    name VARCHAR(100) NOT NULL,
    age INTEGER CHECK (age BETWEEN 15 AND 90),
    gender VARCHAR(50),
    occupation VARCHAR(100),
    birthplace VARCHAR(100),
    mental_disorder TEXT,
    
    -- 能力値
    str INTEGER CHECK (str BETWEEN 3 AND 18),
    con INTEGER CHECK (con BETWEEN 3 AND 18),
    pow INTEGER CHECK (pow BETWEEN 3 AND 18),
    dex INTEGER CHECK (dex BETWEEN 3 AND 18),
    app INTEGER CHECK (app BETWEEN 3 AND 18),
    siz INTEGER CHECK (siz BETWEEN 8 AND 18),
    int INTEGER CHECK (int BETWEEN 8 AND 18),
    edu INTEGER CHECK (edu BETWEEN 6 AND 21),
    
    -- 副次ステータス
    hit_points_max INTEGER,
    hit_points_current INTEGER,
    magic_points_max INTEGER,
    magic_points_current INTEGER,
    sanity_max INTEGER,
    sanity_current INTEGER,
    
    -- 6版固有
    idea_roll INTEGER,
    luck_roll INTEGER,
    know_roll INTEGER,
    damage_bonus VARCHAR(10),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 9.2 API設計（6版専用）

```python
# 6版キャラクター作成
POST /api/characters/6th/
{
    "name": "田中太郎",
    "age": 28,
    "occupation": "探偵",
    "abilities": {
        "str": 12,
        "con": 14,
        "pow": 11,
        "dex": 13,
        "app": 10,
        "siz": 12,
        "int": 15,
        "edu": 16
    }
}

# 6版能力値ロール
POST /api/characters/6th/roll-abilities/
{
    "method": "standard"
}

# 6版スキル成長
POST /api/characters/6th/{id}/skill-growth/
{
    "skill_name": "目星",
    "growth_roll": 45
}

# 6版判定支援
POST /api/characters/6th/{id}/check/
{
    "type": "skill", # skill, idea, luck, know
    "skill_name": "目星",
    "dice_roll": 34,
    "modifier": 0
}
```

### 9.3 バリデーションルール

```python
class Character6thValidator:
    @staticmethod
    def validate_abilities(abilities):
        """6版能力値検証"""
        rules = {
            'str': (3, 18),
            'con': (3, 18), 
            'pow': (3, 18),
            'dex': (3, 18),
            'app': (3, 18),
            'siz': (8, 18),
            'int': (8, 18),
            'edu': (6, 21)
        }
        
        for ability, value in abilities.items():
            min_val, max_val = rules[ability]
            if not min_val <= value <= max_val:
                raise ValidationError(f"{ability}は{min_val}-{max_val}の範囲で入力してください")
    
    @staticmethod  
    def validate_skills(skills):
        """6版スキル値検証"""
        for skill_name, value in skills.items():
            if value > 90:
                raise ValidationError(f"{skill_name}は90%を超えることはできません")
```

---

## 📋 6版の特徴まとめ

### ✅ 利点
- **シンプルな判定システム**: d100で技能値以下
- **直感的なルール**: 理解しやすい基本構造
- **豊富な実績**: 長年の運用によるバランス
- **アイデア・幸運・知識ロール**: 便利な副次判定

### ⚠️ 注意点
- **固定的なスキル基本値**: カスタマイズ性が低い
- **ダメージボーナス表参照**: 計算が複雑
- **技能上限90%**: 成長に限界がある
- **単純な成功/失敗**: 成功度の段階がない

---

*6版仕様書 - 最終更新日: 2025-06-14*