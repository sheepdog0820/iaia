# クトゥルフ神話TRPG キャラクターシート 技術仕様書

**Call of Cthulhu RPG Character Sheet Technical Implementation Specification**

## 📖 概要

本文書は、クトゥルフ神話TRPG 6版・7版キャラクターシートのシステム実装における共通技術仕様を定義します。Arkham Nexusプラットフォームでのキャラクターシート機能実装の技術的ガイドラインとなります。

---

## 📑 目次

1. [アーキテクチャ設計](#1-アーキテクチャ設計)
2. [データベース設計](#2-データベース設計)
3. [API仕様](#3-api仕様)
4. [フロントエンド設計](#4-フロントエンド設計)
5. [計算エンジン](#5-計算エンジン)
6. [バリデーション](#6-バリデーション)
7. [セキュリティ](#7-セキュリティ)
8. [パフォーマンス](#8-パフォーマンス)
9. [テスト戦略](#9-テスト戦略)

---

## 1. アーキテクチャ設計

### 1.1 全体アーキテクチャ

```
┌─────────────────────────────────────┐
│           フロントエンド            │
│     (React/Vue.js + TypeScript)     │
├─────────────────────────────────────┤
│            API Gateway              │
│        (Django REST Framework)      │
├─────────────────────────────────────┤
│          ビジネスロジック           │
│      (Character Service Layer)      │
├─────────────────────────────────────┤
│          データアクセス層           │
│         (Django ORM/Models)         │
├─────────────────────────────────────┤
│           データベース              │
│           (PostgreSQL)              │
└─────────────────────────────────────┘
```

### 1.2 モジュール構成

```python
# プロジェクト構造
characters/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── base.py          # 共通ベースモデル
│   ├── character_6th.py # 6版専用モデル
│   ├── character_7th.py # 7版専用モデル
│   └── common.py        # 共通モデル
├── serializers/
│   ├── __init__.py
│   ├── character_6th.py
│   ├── character_7th.py
│   └── common.py
├── views/
│   ├── __init__.py
│   ├── character_6th.py
│   ├── character_7th.py
│   └── common.py
├── services/
│   ├── __init__.py
│   ├── calculation_engine.py
│   ├── dice_roller.py
│   ├── character_creator.py
│   └── validators.py
├── tests/
│   ├── test_models.py
│   ├── test_api.py
│   ├── test_calculations.py
│   └── test_integration.py
└── urls.py
```

### 1.3 デザインパターン

```python
# Factory Pattern for Character Creation
class CharacterFactory:
    @staticmethod
    def create_character(edition, **kwargs):
        if edition == '6th':
            return Character6th.objects.create(**kwargs)
        elif edition == '7th':
            return Character7th.objects.create(**kwargs)
        else:
            raise ValueError(f"Unsupported edition: {edition}")

# Strategy Pattern for Calculation Rules
class CalculationStrategy:
    def calculate_derived_stats(self, character):
        raise NotImplementedError

class Calculation6thStrategy(CalculationStrategy):
    def calculate_derived_stats(self, character):
        # 6版固有の計算ロジック
        pass

class Calculation7thStrategy(CalculationStrategy):
    def calculate_derived_stats(self, character):
        # 7版固有の計算ロジック
        pass

# Observer Pattern for Character Updates
class CharacterObserver:
    def update(self, character, field_name, old_value, new_value):
        # 能力値変更時の自動再計算等
        pass
```

---

## 2. データベース設計

### 2.1 共通ベーステーブル

```sql
-- 共通キャラクター情報
CREATE TABLE characters_base (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    edition ENUM('6th', '7th') NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 共通能力値
    str INTEGER CHECK (str BETWEEN 15 AND 90),
    con INTEGER CHECK (con BETWEEN 15 AND 90),
    pow INTEGER CHECK (pow BETWEEN 15 AND 90),
    dex INTEGER CHECK (dex BETWEEN 15 AND 90),
    app INTEGER CHECK (app BETWEEN 15 AND 90),
    siz INTEGER CHECK (siz BETWEEN 30 AND 90),
    int INTEGER CHECK (int BETWEEN 40 AND 90),
    edu INTEGER CHECK (edu BETWEEN 30 AND 90),
    
    -- インデックス
    INDEX idx_user_edition (user_id, edition),
    INDEX idx_created_at (created_at),
    
    FOREIGN KEY (user_id) REFERENCES accounts_customuser(id) ON DELETE CASCADE
);

-- 6版専用拡張テーブル
CREATE TABLE characters_6th_extended (
    character_id BIGINT PRIMARY KEY,
    
    -- 6版固有フィールド
    idea_roll INTEGER,
    luck_roll INTEGER,
    know_roll INTEGER,
    damage_bonus VARCHAR(10),
    
    FOREIGN KEY (character_id) REFERENCES characters_base(id) ON DELETE CASCADE
);

-- 7版専用拡張テーブル
CREATE TABLE characters_7th_extended (
    character_id BIGINT PRIMARY KEY,
    
    -- 7版固有フィールド
    luck_points INTEGER,
    build_value INTEGER CHECK (build_value BETWEEN -2 AND 4),
    move_rate INTEGER,
    
    -- 7版背景情報
    personal_description TEXT,
    ideology_beliefs TEXT,
    significant_people TEXT,
    meaningful_locations TEXT,
    treasured_possessions TEXT,
    traits TEXT,
    injuries_scars TEXT,
    phobias_manias TEXT,
    
    FOREIGN KEY (character_id) REFERENCES characters_base(id) ON DELETE CASCADE
);

-- スキルテーブル（版共通）
CREATE TABLE character_skills (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    character_id BIGINT NOT NULL,
    skill_name VARCHAR(100) NOT NULL,
    base_value INTEGER DEFAULT 0,
    occupation_points INTEGER DEFAULT 0,
    interest_points INTEGER DEFAULT 0,
    other_points INTEGER DEFAULT 0,
    current_value INTEGER NOT NULL,
    
    -- 7版用追加フィールド
    half_value INTEGER GENERATED ALWAYS AS (current_value DIV 2) STORED,
    fifth_value INTEGER GENERATED ALWAYS AS (current_value DIV 5) STORED,
    
    UNIQUE KEY unique_character_skill (character_id, skill_name),
    FOREIGN KEY (character_id) REFERENCES characters_base(id) ON DELETE CASCADE
);
```

### 2.2 インデックス戦略

```sql
-- パフォーマンス向上のためのインデックス
CREATE INDEX idx_characters_user_edition ON characters_base(user_id, edition);
CREATE INDEX idx_skills_character_skill ON character_skills(character_id, skill_name);
CREATE INDEX idx_characters_updated_at ON characters_base(updated_at);

-- フルテキスト検索用インデックス
ALTER TABLE characters_base ADD FULLTEXT(name);
ALTER TABLE characters_7th_extended ADD FULLTEXT(personal_description, ideology_beliefs);
```

### 2.3 データ制約と整合性

```sql
-- トリガーによる整合性保証
DELIMITER //
CREATE TRIGGER tr_character_skills_validation
BEFORE INSERT ON character_skills
FOR EACH ROW
BEGIN
    -- スキル値上限チェック（版に応じて）
    DECLARE edition_type ENUM('6th', '7th');
    SELECT edition INTO edition_type FROM characters_base WHERE id = NEW.character_id;
    
    IF edition_type = '6th' AND NEW.current_value > 90 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '6版では技能値は90が上限です';
    END IF;
    
    IF edition_type = '7th' AND NEW.current_value > 99 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '7版では技能値は99が上限です';
    END IF;
END//
DELIMITER ;
```

---

## 3. API仕様

### 3.1 RESTful API設計

```python
# URLパターン
urlpatterns = [
    # 共通エンドポイント
    path('api/characters/', include([
        path('', CharacterListCreateView.as_view(), name='character-list-create'),
        path('<int:pk>/', CharacterDetailView.as_view(), name='character-detail'),
        path('<int:pk>/duplicate/', CharacterDuplicateView.as_view(), name='character-duplicate'),
        
        # 版別エンドポイント
        path('6th/', include([
            path('', Character6thListCreateView.as_view()),
            path('<int:pk>/', Character6thDetailView.as_view()),
            path('<int:pk>/roll-abilities/', Character6thAbilityRollView.as_view()),
            path('<int:pk>/calculate-derived/', Character6thCalculateView.as_view()),
        ])),
        
        path('7th/', include([
            path('', Character7thListCreateView.as_view()),
            path('<int:pk>/', Character7thDetailView.as_view()),
            path('<int:pk>/roll-abilities/', Character7thAbilityRollView.as_view()),
            path('<int:pk>/push-roll/', Character7thPushRollView.as_view()),
            path('<int:pk>/bonus-penalty-roll/', Character7thBonusPenaltyRollView.as_view()),
        ])),
        
        # スキル関連
        path('<int:pk>/skills/', CharacterSkillsView.as_view()),
        path('<int:pk>/skills/<str:skill_name>/', CharacterSkillDetailView.as_view()),
        path('<int:pk>/skills/improve/', SkillImprovementView.as_view()),
        
        # 計算・判定支援
        path('<int:pk>/dice-roll/', DiceRollView.as_view()),
        path('<int:pk>/skill-check/', SkillCheckView.as_view()),
        path('<int:pk>/combat-action/', CombatActionView.as_view()),
    ])),
]
```

### 3.2 API レスポンス形式

```python
# 統一レスポンス形式
class APIResponse:
    @staticmethod
    def success(data=None, message="", status_code=200):
        return Response({
            'success': True,
            'data': data,
            'message': message,
            'timestamp': timezone.now().isoformat()
        }, status=status_code)
    
    @staticmethod
    def error(errors=None, message="", status_code=400):
        return Response({
            'success': False,
            'errors': errors,
            'message': message,
            'timestamp': timezone.now().isoformat()
        }, status=status_code)

# キャラクター詳細レスポンス例
{
    "success": true,
    "data": {
        "id": 123,
        "edition": "7th",
        "name": "田中花子",
        "abilities": {
            "str": 60,
            "con": 70,
            "pow": 65,
            "dex": 75,
            "app": 60,
            "siz": 55,
            "int": 80,
            "edu": 75
        },
        "derived_stats": {
            "hit_points": {
                "max": 12,
                "current": 12
            },
            "magic_points": {
                "max": 13,
                "current": 13
            },
            "sanity": {
                "starting": 65,
                "maximum": 99,
                "current": 65
            },
            "build": 0,
            "move_rate": 8,
            "dodge": 37
        },
        "skills": [
            {
                "name": "図書館",
                "current_value": 45,
                "half_value": 22,
                "fifth_value": 9,
                "base_value": 20,
                "occupation_points": 25,
                "interest_points": 0
            }
        ],
        "last_calculated": "2025-06-14T10:30:00Z"
    },
    "message": "",
    "timestamp": "2025-06-14T10:30:00Z"
}
```

### 3.3 エラーハンドリング

```python
class CharacterAPIException(Exception):
    """キャラクターシート関連例外"""
    pass

class InvalidEditionException(CharacterAPIException):
    """無効な版指定例外"""
    pass

class CalculationException(CharacterAPIException):
    """計算エラー例外"""
    pass

# エラーハンドラー
@api_view(['POST'])
def character_create_view(request):
    try:
        serializer = CharacterSerializer(data=request.data)
        if serializer.is_valid():
            character = serializer.save()
            return APIResponse.success(
                data=CharacterSerializer(character).data,
                message="キャラクターが作成されました",
                status_code=201
            )
        else:
            return APIResponse.error(
                errors=serializer.errors,
                message="入力データに誤りがあります",
                status_code=400
            )
    except InvalidEditionException as e:
        return APIResponse.error(
            message=str(e),
            status_code=400
        )
    except Exception as e:
        logger.error(f"Character creation error: {e}")
        return APIResponse.error(
            message="サーバーエラーが発生しました",
            status_code=500
        )
```

---

## 4. フロントエンド設計

### 4.1 コンポーネント設計

```typescript
// TypeScript型定義
interface BaseCharacter {
  id: number;
  edition: '6th' | '7th';
  name: string;
  abilities: Abilities;
  derivedStats: DerivedStats;
  skills: Skill[];
}

interface Character6th extends BaseCharacter {
  edition: '6th';
  ideaRoll: number;
  luckRoll: number;
  knowRoll: number;
  damageBonus: string;
}

interface Character7th extends BaseCharacter {
  edition: '7th';
  luckPoints: number;
  buildValue: number;
  moveRate: number;
  background: Character7thBackground;
}

// React コンポーネント例
const CharacterSheet: React.FC<{characterId: number}> = ({ characterId }) => {
  const [character, setCharacter] = useState<BaseCharacter | null>(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchCharacter(characterId).then(setCharacter).finally(() => setLoading(false));
  }, [characterId]);
  
  if (loading) return <LoadingSpinner />;
  if (!character) return <ErrorMessage message="キャラクターが見つかりません" />;
  
  return (
    <div className="character-sheet">
      <CharacterHeader character={character} />
      <CharacterAbilities character={character} />
      <CharacterDerivedStats character={character} />
      <CharacterSkills character={character} />
      {character.edition === '7th' && (
        <Character7thBackground character={character as Character7th} />
      )}
    </div>
  );
};
```

### 4.2 状態管理（Redux Toolkit）

```typescript
// Character Slice
const characterSlice = createSlice({
  name: 'character',
  initialState: {
    current: null as BaseCharacter | null,
    list: [] as BaseCharacter[],
    loading: false,
    error: null as string | null,
  },
  reducers: {
    setCurrentCharacter: (state, action) => {
      state.current = action.payload;
    },
    updateAbility: (state, action) => {
      if (state.current) {
        const { ability, value } = action.payload;
        state.current.abilities[ability] = value;
        // 派生ステータスの自動再計算
        state.current.derivedStats = calculateDerivedStats(
          state.current.abilities,
          state.current.edition
        );
      }
    },
    updateSkill: (state, action) => {
      if (state.current) {
        const { skillName, points, type } = action.payload;
        const skill = state.current.skills.find(s => s.name === skillName);
        if (skill) {
          skill[type] = points;
          skill.currentValue = calculateSkillTotal(skill);
        }
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchCharacter.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchCharacter.fulfilled, (state, action) => {
        state.loading = false;
        state.current = action.payload;
      })
      .addCase(fetchCharacter.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'エラーが発生しました';
      });
  },
});
```

### 4.3 リアルタイム計算

```typescript
// カスタムフック：リアルタイム計算
const useCharacterCalculation = (character: BaseCharacter) => {
  const [calculatedStats, setCalculatedStats] = useState(character.derivedStats);
  
  useEffect(() => {
    if (character.edition === '6th') {
      setCalculatedStats(calculate6thDerivedStats(character.abilities));
    } else if (character.edition === '7th') {
      setCalculatedStats(calculate7thDerivedStats(character.abilities));
    }
  }, [character.abilities, character.edition]);
  
  return calculatedStats;
};

// 計算関数
const calculate6thDerivedStats = (abilities: Abilities): DerivedStats => {
  return {
    hitPoints: {
      max: Math.floor((abilities.con + abilities.siz) / 10),
      current: Math.floor((abilities.con + abilities.siz) / 10),
    },
    magicPoints: {
      max: Math.floor(abilities.pow / 5),
      current: Math.floor(abilities.pow / 5),
    },
    sanity: {
      starting: abilities.pow,
      maximum: 99,
      current: abilities.pow,
    },
    // 6版固有の計算
    ideaRoll: abilities.int * 5,
    luckRoll: abilities.pow * 5,
    knowRoll: abilities.edu * 5,
    damageBonus: calculateDamageBonus6th(abilities.str, abilities.siz),
  };
};
```

---

## 5. 計算エンジン

### 5.1 ダイスシステム

```python
import random
from typing import List, Dict, Any

class DiceRoller:
    @staticmethod
    def roll_d100() -> int:
        """d100ロール"""
        return random.randint(1, 100)
    
    @staticmethod
    def roll_3d6() -> int:
        """3d6ロール"""
        return sum(random.randint(1, 6) for _ in range(3))
    
    @staticmethod
    def roll_2d6() -> int:
        """2d6ロール"""
        return sum(random.randint(1, 6) for _ in range(2))
    
    @staticmethod
    def roll_dice(dice_expression: str) -> Dict[str, Any]:
        """汎用ダイスロール (例: "2d6+3", "1d10")"""
        import re
        
        pattern = r'(\d+)d(\d+)(?:([+-])(\d+))?'
        match = re.match(pattern, dice_expression.lower())
        
        if not match:
            raise ValueError(f"Invalid dice expression: {dice_expression}")
        
        num_dice = int(match.group(1))
        die_size = int(match.group(2))
        modifier_sign = match.group(3)
        modifier_value = int(match.group(4)) if match.group(4) else 0
        
        # ダイスロール
        rolls = [random.randint(1, die_size) for _ in range(num_dice)]
        total = sum(rolls)
        
        # 修正値適用
        if modifier_sign == '+':
            total += modifier_value
        elif modifier_sign == '-':
            total -= modifier_value
        
        return {
            'expression': dice_expression,
            'rolls': rolls,
            'modifier': f"{modifier_sign}{modifier_value}" if modifier_sign else None,
            'total': total,
            'timestamp': timezone.now().isoformat()
        }

class AdvancedDiceRoller(DiceRoller):
    """7版用高度なダイスシステム"""
    
    @staticmethod
    def bonus_penalty_roll(bonus_dice: int = 0, penalty_dice: int = 0) -> Dict[str, Any]:
        """ボーナス・ペナルティダイス"""
        # 相殺処理
        net_bonus = bonus_dice - penalty_dice
        if net_bonus > 0:
            bonus_dice = net_bonus
            penalty_dice = 0
        elif net_bonus < 0:
            bonus_dice = 0
            penalty_dice = abs(net_bonus)
        else:
            bonus_dice = 0
            penalty_dice = 0
        
        # 基本ダイス
        ones = random.randint(0, 9)
        tens_rolls = [random.randint(0, 9) * 10]
        
        # 追加ダイス
        additional_count = max(bonus_dice, penalty_dice)
        for _ in range(additional_count):
            tens_rolls.append(random.randint(0, 9) * 10)
        
        # 最適な十の位選択
        if bonus_dice > 0:
            chosen_tens = min(tens_rolls)  # 最小値
        elif penalty_dice > 0:
            chosen_tens = max(tens_rolls)  # 最大値
        else:
            chosen_tens = tens_rolls[0]
        
        final_result = chosen_tens + ones
        if final_result == 0:
            final_result = 100
        
        return {
            'final_result': final_result,
            'ones_digit': ones,
            'tens_rolls': tens_rolls,
            'chosen_tens': chosen_tens,
            'bonus_dice': bonus_dice,
            'penalty_dice': penalty_dice,
            'all_combinations': [tens + ones or 100 for tens in tens_rolls]
        }
```

### 5.2 キャラクター計算エンジン

```python
class CharacterCalculationEngine:
    """キャラクター計算の中央エンジン"""
    
    def __init__(self, edition: str):
        self.edition = edition
        self.calculator = self._get_calculator()
    
    def _get_calculator(self):
        if self.edition == '6th':
            return Character6thCalculator()
        elif self.edition == '7th':
            return Character7thCalculator()
        else:
            raise ValueError(f"Unsupported edition: {self.edition}")
    
    def calculate_all(self, character_data: Dict) -> Dict:
        """全ての計算を実行"""
        return {
            'derived_stats': self.calculator.calculate_derived_stats(character_data),
            'skill_totals': self.calculator.calculate_skill_totals(character_data),
            'combat_stats': self.calculator.calculate_combat_stats(character_data),
        }

class Character6thCalculator:
    def calculate_derived_stats(self, character_data: Dict) -> Dict:
        abilities = character_data['abilities']
        
        return {
            'hit_points': {
                'max': (abilities['con'] + abilities['siz']) // 10,
                'current': character_data.get('current_hp', (abilities['con'] + abilities['siz']) // 10)
            },
            'magic_points': {
                'max': abilities['pow'] // 5,
                'current': character_data.get('current_mp', abilities['pow'] // 5)
            },
            'sanity': {
                'starting': abilities['pow'],
                'maximum': 99,
                'current': character_data.get('current_sanity', abilities['pow'])
            },
            'idea_roll': abilities['int'] * 5,
            'luck_roll': abilities['pow'] * 5,
            'know_roll': abilities['edu'] * 5,
            'damage_bonus': self.calculate_damage_bonus_6th(abilities['str'], abilities['siz'])
        }
    
    def calculate_damage_bonus_6th(self, str_val: int, siz_val: int) -> str:
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

class Character7thCalculator:
    def calculate_derived_stats(self, character_data: Dict) -> Dict:
        abilities = character_data['abilities']
        age = character_data.get('age', 25)
        
        build = self.calculate_build_7th(abilities['str'], abilities['siz'])
        move_rate = self.calculate_move_rate_7th(age, abilities['str'], abilities['dex'], abilities['siz'])
        
        return {
            'hit_points': {
                'max': (abilities['con'] + abilities['siz']) // 10,
                'current': character_data.get('current_hp', (abilities['con'] + abilities['siz']) // 10)
            },
            'magic_points': {
                'max': abilities['pow'] // 5,
                'current': character_data.get('current_mp', abilities['pow'] // 5)
            },
            'sanity': {
                'starting': abilities['pow'],
                'maximum': 99,
                'current': character_data.get('current_sanity', abilities['pow'])
            },
            'luck': character_data.get('luck_points', 50),
            'build': build,
            'move_rate': move_rate,
            'dodge': abilities['dex'] // 2,
            'damage_bonus': self.get_damage_bonus_from_build(build)
        }
    
    def calculate_build_7th(self, str_val: int, siz_val: int) -> int:
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
    
    def calculate_move_rate_7th(self, age: int, str_val: int, dex_val: int, siz_val: int) -> int:
        base_move = 8
        
        # 年齢修正
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
        
        # 能力値修正
        if str_val < siz_val and dex_val < siz_val:
            base_move -= 1
        elif str_val > siz_val or dex_val > siz_val:
            base_move += 1
        
        return max(base_move, 1)
```

---

## 6. バリデーション

### 6.1 サーバーサイドバリデーション

```python
from django.core.exceptions import ValidationError
from rest_framework import serializers

class CharacterBaseValidator:
    """キャラクター基本バリデーター"""
    
    @staticmethod
    def validate_abilities(abilities: Dict[str, int], edition: str) -> None:
        """能力値バリデーション"""
        rules = {
            '6th': {
                'str': (15, 90), 'con': (15, 90), 'pow': (15, 90), 'dex': (15, 90),
                'app': (15, 90), 'siz': (30, 90), 'int': (40, 90), 'edu': (30, 90)
            },
            '7th': {
                'str': (15, 90), 'con': (15, 90), 'pow': (15, 90), 'dex': (15, 90),
                'app': (15, 90), 'siz': (30, 90), 'int': (40, 90), 'edu': (40, 90)
            }
        }
        
        edition_rules = rules.get(edition)
        if not edition_rules:
            raise ValidationError(f"Unsupported edition: {edition}")
        
        for ability, value in abilities.items():
            if ability not in edition_rules:
                raise ValidationError(f"Unknown ability: {ability}")
            
            min_val, max_val = edition_rules[ability]
            if not min_val <= value <= max_val:
                raise ValidationError(
                    f"{ability} must be between {min_val} and {max_val}, got {value}"
                )
    
    @staticmethod
    def validate_skill_points(character_data: Dict, occupation_data: Dict) -> None:
        """技能ポイント配分バリデーション"""
        total_used = sum(
            skill.get('occupation_points', 0) + skill.get('interest_points', 0)
            for skill in character_data.get('skills', [])
        )
        
        available_points = CharacterCalculationEngine(
            character_data['edition']
        ).calculator.calculate_available_skill_points(
            character_data, occupation_data
        )
        
        if total_used > available_points:
            raise ValidationError(
                f"Skill points exceeded: used {total_used}, available {available_points}"
            )

class CharacterSerializer(serializers.ModelSerializer):
    """キャラクターシリアライザー（バリデーション含む）"""
    
    def validate(self, data):
        # 能力値バリデーション
        CharacterBaseValidator.validate_abilities(
            data.get('abilities', {}),
            data.get('edition')
        )
        
        # カスタムビジネスルールバリデーション
        if data.get('edition') == '7th' and 'luck_points' in data:
            if not 15 <= data['luck_points'] <= 90:
                raise serializers.ValidationError(
                    "Luck points must be between 15 and 90"
                )
        
        return data
    
    def create(self, validated_data):
        # 作成時の自動計算
        edition = validated_data['edition']
        calculator = CharacterCalculationEngine(edition)
        
        # 派生ステータス自動計算
        derived_stats = calculator.calculate_all(validated_data)
        validated_data.update(derived_stats)
        
        return super().create(validated_data)
```

### 6.2 クライアントサイドバリデーション

```typescript
// TypeScript バリデーション
interface ValidationRule {
  required?: boolean;
  min?: number;
  max?: number;
  pattern?: RegExp;
  custom?: (value: any) => string | null;
}

interface ValidationSchema {
  [key: string]: ValidationRule;
}

class CharacterValidator {
  private static get6thSchema(): ValidationSchema {
    return {
      name: { required: true },
      'abilities.str': { required: true, min: 15, max: 90 },
      'abilities.con': { required: true, min: 15, max: 90 },
      'abilities.pow': { required: true, min: 15, max: 90 },
      'abilities.dex': { required: true, min: 15, max: 90 },
      'abilities.app': { required: true, min: 15, max: 90 },
      'abilities.siz': { required: true, min: 30, max: 90 },
      'abilities.int': { required: true, min: 40, max: 90 },
      'abilities.edu': { required: true, min: 30, max: 90 },
    };
  }
  
  private static get7thSchema(): ValidationSchema {
    return {
      ...this.get6thSchema(),
      'abilities.edu': { required: true, min: 40, max: 90 }, // 7版はEDU最低40
      luckPoints: { required: true, min: 15, max: 90 },
      buildValue: { required: true, min: -2, max: 4 },
    };
  }
  
  static validate(character: Partial<BaseCharacter>): ValidationErrors {
    const schema = character.edition === '6th' 
      ? this.get6thSchema() 
      : this.get7thSchema();
    
    const errors: ValidationErrors = {};
    
    for (const [fieldPath, rule] of Object.entries(schema)) {
      const value = this.getNestedValue(character, fieldPath);
      const error = this.validateField(value, rule, fieldPath);
      
      if (error) {
        errors[fieldPath] = error;
      }
    }
    
    return errors;
  }
  
  private static validateField(value: any, rule: ValidationRule, fieldPath: string): string | null {
    if (rule.required && (value === undefined || value === null || value === '')) {
      return `${fieldPath} is required`;
    }
    
    if (value !== undefined && value !== null) {
      if (rule.min !== undefined && value < rule.min) {
        return `${fieldPath} must be at least ${rule.min}`;
      }
      
      if (rule.max !== undefined && value > rule.max) {
        return `${fieldPath} must be at most ${rule.max}`;
      }
      
      if (rule.pattern && !rule.pattern.test(value)) {
        return `${fieldPath} format is invalid`;
      }
      
      if (rule.custom) {
        return rule.custom(value);
      }
    }
    
    return null;
  }
}

// リアルタイムバリデーション Hook
const useCharacterValidation = (character: Partial<BaseCharacter>) => {
  const [errors, setErrors] = useState<ValidationErrors>({});
  
  useEffect(() => {
    const validationErrors = CharacterValidator.validate(character);
    setErrors(validationErrors);
  }, [character]);
  
  const isValid = Object.keys(errors).length === 0;
  
  return { errors, isValid };
};
```

---

## 7. セキュリティ

### 7.1 認証・認可

```python
from rest_framework.permissions import BasePermission

class CharacterOwnerPermission(BasePermission):
    """キャラクター所有者のみアクセス可能"""
    
    def has_object_permission(self, request, view, obj):
        # キャラクターの所有者またはスーパーユーザーのみ
        return obj.user == request.user or request.user.is_superuser

class CharacterViewPermission(BasePermission):
    """キャラクター閲覧権限"""
    
    def has_object_permission(self, request, view, obj):
        # 所有者、セッション参加者、またはGMがアクセス可能
        if obj.user == request.user:
            return True
        
        # セッション参加中の場合は閲覧可能
        from schedules.models import TRPGSession, SessionParticipant
        user_sessions = TRPGSession.objects.filter(
            participants=request.user,
            status__in=['planned', 'in_progress']
        )
        
        character_sessions = TRPGSession.objects.filter(
            participants=obj.user,
            status__in=['planned', 'in_progress']
        )
        
        return user_sessions.intersection(character_sessions).exists()

# セキュリティ検証用デコレーター
def security_check(func):
    """セキュリティ検証デコレーター"""
    def wrapper(request, *args, **kwargs):
        # レート制限
        if not check_rate_limit(request.user):
            raise PermissionDenied("Rate limit exceeded")
        
        # CSRF保護
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            if not request.META.get('HTTP_X_CSRFTOKEN'):
                raise PermissionDenied("CSRF token required")
        
        return func(request, *args, **kwargs)
    return wrapper
```

### 7.2 データ暗号化

```python
from cryptography.fernet import Fernet
from django.conf import settings

class SensitiveDataEncryption:
    """機密データ暗号化"""
    
    def __init__(self):
        self.cipher = Fernet(settings.CHARACTER_ENCRYPTION_KEY.encode())
    
    def encrypt_character_notes(self, notes: str) -> str:
        """キャラクターメモの暗号化"""
        if not notes:
            return notes
        
        encrypted = self.cipher.encrypt(notes.encode())
        return encrypted.decode()
    
    def decrypt_character_notes(self, encrypted_notes: str) -> str:
        """キャラクターメモの復号化"""
        if not encrypted_notes:
            return encrypted_notes
        
        decrypted = self.cipher.decrypt(encrypted_notes.encode())
        return decrypted.decode()

# モデルフィールドでの暗号化
class EncryptedCharacterNotes(models.TextField):
    """暗号化キャラクターメモフィールド"""
    
    def __init__(self, *args, **kwargs):
        self.encryption = SensitiveDataEncryption()
        super().__init__(*args, **kwargs)
    
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return self.encryption.decrypt_character_notes(value)
    
    def to_python(self, value):
        if isinstance(value, str) or value is None:
            return value
        return str(value)
    
    def get_prep_value(self, value):
        if value is None:
            return value
        return self.encryption.encrypt_character_notes(str(value))
```

---

## 8. パフォーマンス

### 8.1 キャッシュ戦略

```python
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
import hashlib

class CharacterCacheManager:
    """キャラクター関連キャッシュ管理"""
    
    @staticmethod
    def get_character_cache_key(character_id: int, user_id: int) -> str:
        """キャラクターキャッシュキー生成"""
        return f"character:{character_id}:user:{user_id}"
    
    @staticmethod
    def get_calculated_stats_cache_key(character_id: int, abilities_hash: str) -> str:
        """計算済み統計キャッシュキー生成"""
        return f"calc_stats:{character_id}:{abilities_hash}"
    
    @staticmethod
    def invalidate_character_cache(character_id: int, user_id: int):
        """キャラクターキャッシュ無効化"""
        cache_key = CharacterCacheManager.get_character_cache_key(character_id, user_id)
        cache.delete(cache_key)
        
        # 関連キャッシュも削除
        pattern = f"calc_stats:{character_id}:*"
        cache.delete_pattern(pattern)

def cached_calculation(timeout: int = 3600):
    """計算結果キャッシュデコレーター"""
    def decorator(func):
        def wrapper(self, character_data, *args, **kwargs):
            # 能力値のハッシュ値生成
            abilities_str = str(sorted(character_data.get('abilities', {}).items()))
            abilities_hash = hashlib.md5(abilities_str.encode()).hexdigest()
            
            cache_key = CharacterCacheManager.get_calculated_stats_cache_key(
                character_data.get('id', 0), abilities_hash
            )
            
            # キャッシュから取得試行
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 計算実行
            result = func(self, character_data, *args, **kwargs)
            
            # キャッシュに保存
            cache.set(cache_key, result, timeout)
            return result
        
        return wrapper
    return decorator

# 使用例
class Character7thCalculator:
    @cached_calculation(timeout=1800)  # 30分キャッシュ
    def calculate_derived_stats(self, character_data: Dict) -> Dict:
        # 重い計算処理
        pass
```

### 8.2 データベース最適化

```python
# 効率的なクエリ
class CharacterQuerySet(models.QuerySet):
    def with_skills(self):
        """スキル情報を含む効率的なクエリ"""
        return self.prefetch_related('characterskill_set')
    
    def with_sessions(self):
        """セッション情報を含む効率的なクエリ"""
        return self.prefetch_related(
            'user__sessionparticipant_set__session'
        )
    
    def for_user_dashboard(self, user):
        """ユーザーダッシュボード用最適化クエリ"""
        return self.filter(user=user).select_related('user').with_skills()

class CharacterManager(models.Manager):
    def get_queryset(self):
        return CharacterQuerySet(self.model, using=self._db)
    
    def with_skills(self):
        return self.get_queryset().with_skills()

# バッチ更新
class BulkCharacterUpdater:
    """キャラクター一括更新"""
    
    @staticmethod
    def bulk_update_derived_stats(character_ids: List[int]):
        """派生ステータス一括更新"""
        characters = Character.objects.filter(id__in=character_ids)
        
        updates = []
        for character in characters:
            calculator = CharacterCalculationEngine(character.edition)
            derived_stats = calculator.calculate_derived_stats(character.to_dict())
            
            character.hit_points_max = derived_stats['hit_points']['max']
            character.magic_points_max = derived_stats['magic_points']['max']
            # その他の更新...
            
            updates.append(character)
        
        # 一括更新実行
        Character.objects.bulk_update(
            updates,
            ['hit_points_max', 'magic_points_max', 'sanity_starting']
        )
```

### 8.3 フロントエンド最適化

```typescript
// React.memo による再レンダリング最適化
const CharacterAbilities = React.memo<{abilities: Abilities, onChange: (abilities: Abilities) => void}>(
  ({ abilities, onChange }) => {
    const handleAbilityChange = useCallback((ability: string, value: number) => {
      onChange({
        ...abilities,
        [ability]: value
      });
    }, [abilities, onChange]);
    
    return (
      <div className="abilities-grid">
        {Object.entries(abilities).map(([ability, value]) => (
          <AbilityInput
            key={ability}
            ability={ability}
            value={value}
            onChange={handleAbilityChange}
          />
        ))}
      </div>
    );
  }
);

// 仮想化による大量データ表示最適化
import { FixedSizeList as List } from 'react-window';

const SkillList: React.FC<{skills: Skill[]}> = ({ skills }) => {
  const Row = ({ index, style }: {index: number, style: React.CSSProperties}) => (
    <div style={style}>
      <SkillItem skill={skills[index]} />
    </div>
  );
  
  return (
    <List
      height={400}
      itemCount={skills.length}
      itemSize={50}
      width="100%"
    >
      {Row}
    </List>
  );
};

// データフェッチング最適化
const useCharacterData = (characterId: number) => {
  return useQuery({
    queryKey: ['character', characterId],
    queryFn: () => fetchCharacter(characterId),
    staleTime: 5 * 60 * 1000, // 5分間はフレッシュとみなす
    cacheTime: 10 * 60 * 1000, // 10分間キャッシュ保持
    refetchOnWindowFocus: false,
  });
};
```

---

## 9. テスト戦略

### 9.1 単体テスト

```python
import pytest
from django.test import TestCase
from characters.services.calculation_engine import Character7thCalculator

class TestCharacter7thCalculator(TestCase):
    def setUp(self):
        self.calculator = Character7thCalculator()
        self.test_abilities = {
            'str': 60, 'con': 70, 'pow': 65, 'dex': 75,
            'app': 60, 'siz': 55, 'int': 80, 'edu': 75
        }
    
    def test_build_calculation(self):
        """ビルド値計算テスト"""
        # STR 60 + SIZ 55 = 115 -> Build 0
        build = self.calculator.calculate_build_7th(60, 55)
        self.assertEqual(build, 0)
        
        # STR 90 + SIZ 90 = 180 -> Build 2
        build = self.calculator.calculate_build_7th(90, 90)
        self.assertEqual(build, 2)
        
        # 境界値テスト
        build = self.calculator.calculate_build_7th(32, 32)  # 64
        self.assertEqual(build, -2)
        
        build = self.calculator.calculate_build_7th(33, 32)  # 65
        self.assertEqual(build, -1)
    
    def test_move_rate_calculation(self):
        """移動力計算テスト"""
        # 若いキャラクター、通常の能力値
        move_rate = self.calculator.calculate_move_rate_7th(25, 60, 75, 55)
        self.assertEqual(move_rate, 9)  # DEX > SIZ なので +1
        
        # 年齢による減少
        move_rate = self.calculator.calculate_move_rate_7th(45, 60, 75, 55)
        self.assertEqual(move_rate, 8)  # 40代なので -1, DEXボーナス +1
        
        # 複数条件
        move_rate = self.calculator.calculate_move_rate_7th(75, 30, 30, 80)
        self.assertEqual(move_rate, 2)  # 70代 -4, STR&DEX < SIZ -1
    
    def test_derived_stats_calculation(self):
        """派生ステータス計算テスト"""
        character_data = {
            'abilities': self.test_abilities,
            'age': 28
        }
        
        derived = self.calculator.calculate_derived_stats(character_data)
        
        # HP = (CON + SIZ) / 10 = (70 + 55) / 10 = 12
        self.assertEqual(derived['hit_points']['max'], 12)
        
        # MP = POW / 5 = 65 / 5 = 13
        self.assertEqual(derived['magic_points']['max'], 13)
        
        # SAN = POW = 65
        self.assertEqual(derived['sanity']['starting'], 65)
        
        # Build = 0 (STR 60 + SIZ 55 = 115)
        self.assertEqual(derived['build'], 0)
        
        # Dodge = DEX / 2 = 75 / 2 = 37
        self.assertEqual(derived['dodge'], 37)

@pytest.mark.django_db
class TestCharacterAPI:
    def test_character_creation(self, api_client, user):
        """キャラクター作成APIテスト"""
        character_data = {
            'edition': '7th',
            'name': 'テストキャラクター',
            'abilities': {
                'str': 60, 'con': 70, 'pow': 65, 'dex': 75,
                'app': 60, 'siz': 55, 'int': 80, 'edu': 75
            }
        }
        
        api_client.force_authenticate(user=user)
        response = api_client.post('/api/characters/', character_data, format='json')
        
        assert response.status_code == 201
        assert response.data['name'] == 'テストキャラクター'
        assert response.data['edition'] == '7th'
        
        # 派生ステータスが自動計算されていることを確認
        assert 'derived_stats' in response.data
        assert response.data['derived_stats']['build'] == 0
    
    def test_character_update_recalculation(self, api_client, user, character_7th):
        """キャラクター更新時の再計算テスト"""
        api_client.force_authenticate(user=user)
        
        # STRを変更
        update_data = {
            'abilities': {
                **character_7th.abilities,
                'str': 90  # 60 -> 90に変更
            }
        }
        
        response = api_client.patch(
            f'/api/characters/{character_7th.id}/',
            update_data,
            format='json'
        )
        
        assert response.status_code == 200
        
        # ビルド値が再計算されていることを確認
        # STR 90 + SIZ 55 = 145 -> Build 1
        assert response.data['derived_stats']['build'] == 1
```

### 9.2 統合テスト

```python
class CharacterIntegrationTestCase(TransactionTestCase):
    """キャラクター機能統合テスト"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.client.force_authenticate(user=self.user)
    
    def test_complete_character_creation_workflow(self):
        """完全なキャラクター作成ワークフローテスト"""
        
        # 1. 能力値ロール
        response = self.client.post('/api/characters/7th/roll-abilities/', {
            'method': 'standard'
        })
        self.assertEqual(response.status_code, 200)
        rolled_abilities = response.data['abilities']
        
        # 2. キャラクター基本情報作成
        character_data = {
            'edition': '7th',
            'name': '統合テストキャラクター',
            'age': 28,
            'occupation': 'ジャーナリスト',
            'abilities': rolled_abilities
        }
        
        response = self.client.post('/api/characters/', character_data, format='json')
        self.assertEqual(response.status_code, 201)
        character_id = response.data['id']
        
        # 3. スキル振り分け
        skill_data = {
            'skills': [
                {'name': '図書館', 'occupation_points': 40, 'interest_points': 10},
                {'name': '心理学', 'occupation_points': 30, 'interest_points': 0},
                {'name': '説得', 'occupation_points': 35, 'interest_points': 5},
            ]
        }
        
        response = self.client.patch(
            f'/api/characters/{character_id}/skills/',
            skill_data,
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        
        # 4. 最終確認
        response = self.client.get(f'/api/characters/{character_id}/')
        self.assertEqual(response.status_code, 200)
        
        character = response.data
        self.assertEqual(character['name'], '統合テストキャラクター')
        self.assertIn('derived_stats', character)
        self.assertIn('skills', character)
        
        # スキル計算が正しいことを確認
        library_skill = next(
            (s for s in character['skills'] if s['name'] == '図書館'),
            None
        )
        self.assertIsNotNone(library_skill)
        self.assertEqual(library_skill['current_value'], 70)  # 20(基本) + 40(職業) + 10(興味)
    
    def test_push_roll_workflow(self):
        """プッシュロールワークフローテスト"""
        # キャラクター作成
        character = self.create_test_character_7th()
        
        # 通常判定（失敗）
        response = self.client.post(f'/api/characters/{character.id}/skill-check/', {
            'skill_name': '図書館',
            'dice_roll': 85,  # 失敗想定
            'modifier': 0
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['result'], 'failure')
        
        # プッシュロール実行
        response = self.client.post(f'/api/characters/{character.id}/push-roll/', {
            'skill_name': '図書館',
            'original_roll': 85,
            'gm_approval': True
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('result', response.data)
        self.assertEqual(response.data['pushed'], True)
```

### 9.3 E2Eテスト

```typescript
// Playwright E2Eテスト
import { test, expect } from '@playwright/test';

test.describe('Character Sheet E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // ログイン
    await page.goto('/login');
    await page.fill('[data-testid="username"]', 'testuser');
    await page.fill('[data-testid="password"]', 'testpass123');
    await page.click('[data-testid="login-button"]');
    
    // ダッシュボードに移動することを確認
    await expect(page).toHaveURL('/dashboard');
  });
  
  test('should create a new 7th edition character', async ({ page }) => {
    // キャラクター作成ページに移動
    await page.click('[data-testid="create-character-button"]');
    await expect(page).toHaveURL('/characters/create');
    
    // 7版を選択
    await page.click('[data-testid="edition-7th"]');
    
    // 基本情報入力
    await page.fill('[data-testid="character-name"]', 'E2Eテストキャラクター');
    await page.fill('[data-testid="character-age"]', '28');
    await page.selectOption('[data-testid="occupation"]', 'ジャーナリスト');
    
    // 能力値ロール
    await page.click('[data-testid="roll-abilities-button"]');
    
    // ロール結果が表示されることを確認
    await expect(page.locator('[data-testid="str-value"]')).not.toBeEmpty();
    await expect(page.locator('[data-testid="con-value"]')).not.toBeEmpty();
    
    // 派生ステータスが自動計算されることを確認
    await expect(page.locator('[data-testid="hit-points"]')).not.toBeEmpty();
    await expect(page.locator('[data-testid="build-value"]')).not.toBeEmpty();
    
    // スキル振り分け
    await page.click('[data-testid="next-to-skills"]');
    
    // 職業技能に振り分け
    await page.fill('[data-testid="skill-library-occupation"]', '40');
    await page.fill('[data-testid="skill-psychology-occupation"]', '30');
    
    // 興味技能に振り分け  
    await page.fill('[data-testid="skill-library-interest"]', '10');
    
    // 保存
    await page.click('[data-testid="save-character"]');
    
    // 成功メッセージを確認
    await expect(page.locator('[data-testid="success-message"]')).toContainText('キャラクターが作成されました');
    
    // キャラクター詳細ページに移動することを確認
    await expect(page).toHaveURL(/\/characters\/\d+/);
    
    // 作成されたキャラクターの詳細を確認
    await expect(page.locator('[data-testid="character-name-display"]')).toContainText('E2Eテストキャラクター');
    await expect(page.locator('[data-testid="edition-display"]')).toContainText('7版');
  });
  
  test('should perform skill check with push roll', async ({ page }) => {
    // 既存のキャラクターページに移動
    await page.goto('/characters/1');
    
    // スキルチェック実行
    await page.click('[data-testid="skill-check-button"]');
    await page.selectOption('[data-testid="skill-select"]', '図書館');
    await page.click('[data-testid="roll-dice"]');
    
    // 結果表示を確認
    await expect(page.locator('[data-testid="dice-result"]')).toBeVisible();
    
    // 失敗の場合、プッシュロールボタンが表示されることを確認
    const result = await page.locator('[data-testid="check-result"]').textContent();
    if (result?.includes('失敗')) {
      await expect(page.locator('[data-testid="push-roll-button"]')).toBeVisible();
      
      // プッシュロール実行
      await page.click('[data-testid="push-roll-button"]');
      
      // プッシュロール結果表示
      await expect(page.locator('[data-testid="push-roll-result"]')).toBeVisible();
    }
  });
});
```

---

## 📋 実装チェックリスト

### ✅ バックエンド
- [ ] データベースマイグレーション作成
- [ ] モデル実装（6版・7版）
- [ ] シリアライザー実装
- [ ] API エンドポイント実装
- [ ] 計算エンジン実装
- [ ] バリデーション実装
- [ ] テスト作成
- [ ] セキュリティ対策実装

### ✅ フロントエンド
- [ ] TypeScript型定義
- [ ] Reactコンポーネント実装
- [ ] 状態管理（Redux）実装
- [ ] バリデーション実装
- [ ] レスポンシブデザイン
- [ ] アクセシビリティ対応
- [ ] E2Eテスト作成

### ✅ DevOps・その他
- [ ] 開発環境構築
- [ ] CI/CDパイプライン設定
- [ ] パフォーマンス監視設定
- [ ] ログ監視設定
- [ ] ドキュメント整備

---

*技術仕様書 - 最終更新日: 2025-06-14*