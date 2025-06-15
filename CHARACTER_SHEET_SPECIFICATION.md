# クトゥルフ神話TRPG キャラクターシート仕様書（統合版）

**Call of Cthulhu RPG Character Sheet Specifications (Combined Overview)**

## 📖 概要

本文書は、クトゥルフ神話TRPG 6版および7版のキャラクターシート機能に関する仕様書の統合インデックスです。詳細な仕様については、各版別の専用仕様書を参照してください。

## 📚 仕様書構成

### 個別仕様書

1. **[6版キャラクターシート仕様書](./CHARACTER_SHEET_6TH_EDITION.md)**
   - 6版固有の計算ルール（アイデア・幸運・知識ロール等）
   - 6版専用データベーススキーマ
   - 6版API仕様

2. **[7版キャラクターシート仕様書](./CHARACTER_SHEET_7TH_EDITION.md)**
   - 7版固有の機能（プッシュロール、ボーナス・ペナルティダイス等）
   - 7版専用データベーススキーマ  
   - 7版API仕様

3. **[技術実装仕様書](./CHARACTER_SHEET_TECHNICAL_SPEC.md)**
   - アーキテクチャ設計
   - 共通技術仕様
   - セキュリティ・パフォーマンス要件
   - テスト戦略

## 📑 クイックリファレンス

### 版別特徴比較

| 要素 | 6版 | 7版 |
|------|-----|-----|
| **判定システム** | d100 ≤ 技能値 | d100 ≤ 技能値（成功レベル有） |
| **特殊ロール** | アイデア・幸運・知識 | なし（幸運は技能化） |
| **プッシュロール** | なし | あり |
| **ボーナス・ペナルティダイス** | なし | あり |
| **ダメージボーナス** | 表参照 | ビルド値から算出 |
| **技能上限** | 90% | 99% |
| **背景設定** | 基本情報のみ | 詳細な背景要素 |

### 共通要素

- **能力値**: STR, CON, POW, DEX, APP, SIZ, INT, EDU（8種）
- **副次ステータス**: HP, MP, SAN
- **基本スキル**: 図書館、目星、聞き耳等の共通技能
- **職業システム**: 職業技能ポイント配分
- **装備・武器**: 武器データと防具システム

## 🎯 実装優先度

### Phase 1: 基本機能
- [ ] 6版キャラクターシート基本機能
- [ ] 能力値・副次ステータス計算
- [ ] 基本スキルシステム
- [ ] キャラクター作成・編集・保存

### Phase 2: 拡張機能  
- [ ] 7版キャラクターシート基本機能
- [ ] プッシュロール・ボーナスダイス
- [ ] 詳細な背景設定システム

### Phase 3: 高度な機能
- [ ] 判定支援システム
- [ ] 戦闘システム統合
- [ ] セッション連携機能

## 🔗 関連仕様書

- **[システム仕様書](./SPECIFICATION.md)**: Arkham Nexus全体仕様
- **[セッション管理仕様](./schedules/README.md)**: TRPGセッション管理
- **[ハンドアウト管理仕様](./scenarios/README.md)**: GMハンドアウト機能

---

*統合仕様書インデックス - 最終更新日: 2025-06-14*

---

## アーカイブ: 詳細仕様（参考用）

<details>
<summary>旧統合仕様書の詳細内容（クリックして展開）</summary>

## 1. 基本構造

### 1.1 共通要素

両版共通で存在する基本的な要素：

- **基本情報**: 名前、年齢、性別、職業、出身地
- **能力値**: STR, CON, POW, DEX, APP, SIZ, INT, EDU
- **副次ステータス**: HP, MP, SAN（正気度）
- **スキル**: 各種技能値
- **武器・装備**: 所持品とその効果
- **背景設定**: キャラクターの詳細設定

### 1.2 計算の基本原則

- **能力値**: 3D6 × 5（15-90の範囲）
- **副次ステータス**: 能力値から自動計算
- **スキル**: 基本値 + 職業技能 + 興味技能

---

## 2. 6版キャラクターシート仕様

### 2.1 基本情報

```json
{
  "basic_info": {
    "name": "文字列",
    "age": "整数(15-90)",
    "gender": "文字列",
    "occupation": "文字列",
    "birthplace": "文字列",
    "mental_disorder": "文字列（精神的障害）"
  }
}
```

### 2.2 能力値（6版）

| 能力値 | 英名 | 説明 | 計算方法 |
|--------|------|------|----------|
| 筋力 | STR | 物理的な力 | 3D6×5 |
| 体力 | CON | 持久力・健康 | 3D6×5 |
| 意思力 | POW | 精神力・魔法 | 3D6×5 |
| 敏捷性 | DEX | 素早さ・器用さ | 3D6×5 |
| 外見 | APP | 容姿・魅力 | 3D6×5 |
| 体格 | SIZ | 身長・体重 | 2D6+6×5 |
| 知識 | INT | 知性・推理力 | 2D6+6×5 |
| 教育 | EDU | 学識・教養 | 3D6+3×5 |

### 2.3 副次ステータス（6版）

```json
{
  "derived_stats": {
    "hit_points": {
      "max": "計算式: (CON + SIZ) / 10",
      "current": "現在値",
      "temporary": "一時的増減"
    },
    "magic_points": {
      "max": "計算式: POW / 5",
      "current": "現在値"
    },
    "sanity": {
      "max": "計算式: POW（最大99）",
      "current": "現在値",
      "temporary_insanity": "一時的狂気フラグ",
      "indefinite_insanity": "不定の狂気フラグ"
    },
    "idea_roll": "計算式: INT × 5",
    "luck_roll": "計算式: POW × 5",
    "know_roll": "計算式: EDU × 5",
    "damage_bonus": "計算式: STR+SIZに基づく表参照",
    "build": "ビルド値（7版にはない概念）"
  }
}
```

### 2.4 スキル（6版）

#### 2.4.1 基本スキル

```json
{
  "skills": {
    "anthropology": {"base": 1, "occupation": 0, "interest": 0, "other": 0},
    "archaeology": {"base": 1, "occupation": 0, "interest": 0, "other": 0},
    "art": {"base": 5, "occupation": 0, "interest": 0, "other": 0},
    "astronomy": {"base": 1, "occupation": 0, "interest": 0, "other": 0},
    "bargain": {"base": 5, "occupation": 0, "interest": 0, "other": 0},
    "biology": {"base": 1, "occupation": 0, "interest": 0, "other": 0},
    "chemistry": {"base": 1, "occupation": 0, "interest": 0, "other": 0},
    "climb": {"base": 40, "occupation": 0, "interest": 0, "other": 0},
    "computer_use": {"base": 1, "occupation": 0, "interest": 0, "other": 0},
    "conceal": {"base": 15, "occupation": 0, "interest": 0, "other": 0},
    "credit_rating": {"base": 0, "occupation": 0, "interest": 0, "other": 0},
    "cthulhu_mythos": {"base": 0, "occupation": 0, "interest": 0, "other": 0},
    "dodge": {"base": "DEX×2", "occupation": 0, "interest": 0, "other": 0},
    "drive_auto": {"base": 20, "occupation": 0, "interest": 0, "other": 0},
    "electrical_repair": {"base": 10, "occupation": 0, "interest": 0, "other": 0},
    "electronics": {"base": 1, "occupation": 0, "interest": 0, "other": 0},
    "fast_talk": {"base": 5, "occupation": 0, "interest": 0, "other": 0},
    "first_aid": {"base": 30, "occupation": 0, "interest": 0, "other": 0},
    "geology": {"base": 1, "occupation": 0, "interest": 0, "other": 0},
    "hide": {"base": 10, "occupation": 0, "interest": 0, "other": 0},
    "history": {"base": 20, "occupation": 0, "interest": 0, "other": 0},
    "jump": {"base": 25, "occupation": 0, "interest": 0, "other": 0},
    "language_other": {"base": 1, "occupation": 0, "interest": 0, "other": 0},
    "language_own": {"base": "EDU×5", "occupation": 0, "interest": 0, "other": 0},
    "law": {"base": 5, "occupation": 0, "interest": 0, "other": 0},
    "library_use": {"base": 25, "occupation": 0, "interest": 0, "other": 0},
    "listen": {"base": 25, "occupation": 0, "interest": 0, "other": 0},
    "locksmith": {"base": 1, "occupation": 0, "interest": 0, "other": 0},
    "martial_arts": {"base": 1, "occupation": 0, "interest": 0, "other": 0},
    "mechanical_repair": {"base": 20, "occupation": 0, "interest": 0, "other": 0},
    "medicine": {"base": 5, "occupation": 0, "interest": 0, "other": 0},
    "natural_world": {"base": 10, "occupation": 0, "interest": 0, "other": 0},
    "navigate": {"base": 10, "occupation": 0, "interest": 0, "other": 0},
    "occult": {"base": 5, "occupation": 0, "interest": 0, "other": 0},
    "operate_heavy_machine": {"base": 1, "occupation": 0, "interest": 0, "other": 0},
    "persuade": {"base": 15, "occupation": 0, "interest": 0, "other": 0},
    "pharmacy": {"base": 1, "occupation": 0, "interest": 0, "other": 0},
    "photography": {"base": 10, "occupation": 0, "interest": 0, "other": 0},
    "physics": {"base": 1, "occupation": 0, "interest": 0, "other": 0},
    "pilot": {"base": 1, "occupation": 0, "interest": 0, "other": 0},
    "psychoanalysis": {"base": 1, "occupation": 0, "interest": 0, "other": 0},
    "psychology": {"base": 5, "occupation": 0, "interest": 0, "other": 0},
    "ride": {"base": 5, "occupation": 0, "interest": 0, "other": 0},
    "sneak": {"base": 10, "occupation": 0, "interest": 0, "other": 0},
    "spot_hidden": {"base": 25, "occupation": 0, "interest": 0, "other": 0},
    "swim": {"base": 25, "occupation": 0, "interest": 0, "other": 0},
    "throw": {"base": 25, "occupation": 0, "interest": 0, "other": 0},
    "track": {"base": 10, "occupation": 0, "interest": 0, "other": 0}
  }
}
```

### 2.5 戦闘関連（6版）

```json
{
  "combat": {
    "weapons": [
      {
        "name": "武器名",
        "skill": "使用技能",
        "damage": "ダメージ",
        "base_range": "基本射程",
        "uses_per_round": "ラウンド毎使用回数",
        "bullets_in_gun": "装弾数",
        "ammo": "弾薬"
      }
    ],
    "armor": {
      "type": "防具種別",
      "protection": "防護点"
    }
  }
}
```

---

## 3. 7版キャラクターシート仕様

### 3.1 基本情報

```json
{
  "basic_info": {
    "investigator_name": "文字列",
    "player_name": "文字列",
    "age": "整数(15-90)",
    "gender": "文字列",
    "residence": "居住地",
    "birthplace": "出身地",
    "occupation": "文字列"
  }
}
```

### 3.2 能力値（7版）

| 能力値 | 英名 | 説明 | 計算方法 |
|--------|------|------|----------|
| 筋力 | STR | 物理的な力 | 3D6×5 |
| 体力 | CON | 持久力・健康 | 3D6×5 |
| 意思力 | POW | 精神力・魔法 | 3D6×5 |
| 敏捷性 | DEX | 素早さ・器用さ | 3D6×5 |
| 外見 | APP | 容姿・魅力 | 3D6×5 |
| 体格 | SIZ | 身長・体重 | 2D6+6×5 |
| 知識 | INT | 知性・推理力 | 2D6+6×5 |
| 教育 | EDU | 学識・教養 | 2D6+6×5 |

**※ 7版では各能力値に「半分値」「1/5値」が追加**

### 3.3 副次ステータス（7版）

```json
{
  "derived_stats": {
    "hit_points": {
      "max": "計算式: (CON + SIZ) / 10",
      "current": "現在値",
      "major_wound": "重傷フラグ"
    },
    "magic_points": {
      "max": "計算式: POW / 5",
      "current": "現在値"
    },
    "sanity": {
      "starting_maximum": "計算式: POW",
      "current_maximum": "現在最大値",
      "current": "現在値",
      "breaking_point": "ブレイキングポイント"
    },
    "luck": "3D6×5",
    "movement_rate": "計算式: 能力値ベース",
    "build": "計算式: STR+SIZから算出",
    "damage_bonus": "計算式: ビルドから算出"
  }
}
```

### 3.4 スキル（7版）

#### 3.4.1 基本スキル（難易度値付き）

```json
{
  "skills": {
    "accounting": {
      "base": 5,
      "occupation": 0,
      "interest": 0,
      "total": 5,
      "half": 2,
      "fifth": 1
    },
    "anthropology": {
      "base": 1,
      "occupation": 0,
      "interest": 0,
      "total": 1,
      "half": 0,
      "fifth": 0
    },
    "appraise": {
      "base": 5,
      "occupation": 0,
      "interest": 0,
      "total": 5,
      "half": 2,
      "fifth": 1
    },
    "archaeology": {
      "base": 1,
      "occupation": 0,
      "interest": 0,
      "total": 1,
      "half": 0,
      "fifth": 0
    },
    "art_craft": {
      "base": 5,
      "occupation": 0,
      "interest": 0,
      "total": 5,
      "half": 2,
      "fifth": 1
    },
    "charm": {
      "base": 15,
      "occupation": 0,
      "interest": 0,
      "total": 15,
      "half": 7,
      "fifth": 3
    },
    "climb": {
      "base": 20,
      "occupation": 0,
      "interest": 0,
      "total": 20,
      "half": 10,
      "fifth": 4
    },
    "computer_use": {
      "base": 5,
      "occupation": 0,
      "interest": 0,
      "total": 5,
      "half": 2,
      "fifth": 1
    },
    "credit_rating": {
      "base": 0,
      "occupation": 0,
      "interest": 0,
      "total": 0,
      "half": 0,
      "fifth": 0
    },
    "cthulhu_mythos": {
      "base": 0,
      "occupation": 0,
      "interest": 0,
      "total": 0,
      "half": 0,
      "fifth": 0
    },
    "disguise": {
      "base": 5,
      "occupation": 0,
      "interest": 0,
      "total": 5,
      "half": 2,
      "fifth": 1
    },
    "dodge": {
      "base": "DEX/2",
      "occupation": 0,
      "interest": 0,
      "total": "DEX/2",
      "half": "計算値",
      "fifth": "計算値"
    },
    "drive_auto": {
      "base": 20,
      "occupation": 0,
      "interest": 0,
      "total": 20,
      "half": 10,
      "fifth": 4
    },
    "electrical_repair": {
      "base": 10,
      "occupation": 0,
      "interest": 0,
      "total": 10,
      "half": 5,
      "fifth": 2
    },
    "electronics": {
      "base": 1,
      "occupation": 0,
      "interest": 0,
      "total": 1,
      "half": 0,
      "fifth": 0
    },
    "fast_talk": {
      "base": 5,
      "occupation": 0,
      "interest": 0,
      "total": 5,
      "half": 2,
      "fifth": 1
    },
    "fighting_brawl": {
      "base": 25,
      "occupation": 0,
      "interest": 0,
      "total": 25,
      "half": 12,
      "fifth": 5
    },
    "firearms_handgun": {
      "base": 20,
      "occupation": 0,
      "interest": 0,
      "total": 20,
      "half": 10,
      "fifth": 4
    },
    "firearms_rifle": {
      "base": 25,
      "occupation": 0,
      "interest": 0,
      "total": 25,
      "half": 12,
      "fifth": 5
    },
    "first_aid": {
      "base": 30,
      "occupation": 0,
      "interest": 0,
      "total": 30,
      "half": 15,
      "fifth": 6
    },
    "history": {
      "base": 5,
      "occupation": 0,
      "interest": 0,
      "total": 5,
      "half": 2,
      "fifth": 1
    },
    "intimidate": {
      "base": 15,
      "occupation": 0,
      "interest": 0,
      "total": 15,
      "half": 7,
      "fifth": 3
    },
    "jump": {
      "base": 20,
      "occupation": 0,
      "interest": 0,
      "total": 20,
      "half": 10,
      "fifth": 4
    },
    "language_other": {
      "base": 1,
      "occupation": 0,
      "interest": 0,
      "total": 1,
      "half": 0,
      "fifth": 0
    },
    "language_own": {
      "base": "EDU",
      "occupation": 0,
      "interest": 0,
      "total": "EDU",
      "half": "計算値",
      "fifth": "計算値"
    },
    "law": {
      "base": 5,
      "occupation": 0,
      "interest": 0,
      "total": 5,
      "half": 2,
      "fifth": 1
    },
    "library_use": {
      "base": 20,
      "occupation": 0,
      "interest": 0,
      "total": 20,
      "half": 10,
      "fifth": 4
    },
    "listen": {
      "base": 20,
      "occupation": 0,
      "interest": 0,
      "total": 20,
      "half": 10,
      "fifth": 4
    },
    "locksmith": {
      "base": 1,
      "occupation": 0,
      "interest": 0,
      "total": 1,
      "half": 0,
      "fifth": 0
    },
    "mechanical_repair": {
      "base": 10,
      "occupation": 0,
      "interest": 0,
      "total": 10,
      "half": 5,
      "fifth": 2
    },
    "medicine": {
      "base": 1,
      "occupation": 0,
      "interest": 0,
      "total": 1,
      "half": 0,
      "fifth": 0
    },
    "natural_world": {
      "base": 10,
      "occupation": 0,
      "interest": 0,
      "total": 10,
      "half": 5,
      "fifth": 2
    },
    "navigate": {
      "base": 10,
      "occupation": 0,
      "interest": 0,
      "total": 10,
      "half": 5,
      "fifth": 2
    },
    "occult": {
      "base": 5,
      "occupation": 0,
      "interest": 0,
      "total": 5,
      "half": 2,
      "fifth": 1
    },
    "operate_heavy_machinery": {
      "base": 1,
      "occupation": 0,
      "interest": 0,
      "total": 1,
      "half": 0,
      "fifth": 0
    },
    "persuade": {
      "base": 10,
      "occupation": 0,
      "interest": 0,
      "total": 10,
      "half": 5,
      "fifth": 2
    },
    "pilot": {
      "base": 1,
      "occupation": 0,
      "interest": 0,
      "total": 1,
      "half": 0,
      "fifth": 0
    },
    "psychoanalysis": {
      "base": 1,
      "occupation": 0,
      "interest": 0,
      "total": 1,
      "half": 0,
      "fifth": 0
    },
    "psychology": {
      "base": 10,
      "occupation": 0,
      "interest": 0,
      "total": 10,
      "half": 5,
      "fifth": 2
    },
    "ride": {
      "base": 5,
      "occupation": 0,
      "interest": 0,
      "total": 5,
      "half": 2,
      "fifth": 1
    },
    "science": {
      "base": 1,
      "occupation": 0,
      "interest": 0,
      "total": 1,
      "half": 0,
      "fifth": 0
    },
    "sleight_of_hand": {
      "base": 10,
      "occupation": 0,
      "interest": 0,
      "total": 10,
      "half": 5,
      "fifth": 2
    },
    "spot_hidden": {
      "base": 25,
      "occupation": 0,
      "interest": 0,
      "total": 25,
      "half": 12,
      "fifth": 5
    },
    "stealth": {
      "base": 20,
      "occupation": 0,
      "interest": 0,
      "total": 20,
      "half": 10,
      "fifth": 4
    },
    "survival": {
      "base": 10,
      "occupation": 0,
      "interest": 0,
      "total": 10,
      "half": 5,
      "fifth": 2
    },
    "swim": {
      "base": 20,
      "occupation": 0,
      "interest": 0,
      "total": 20,
      "half": 10,
      "fifth": 4
    },
    "throw": {
      "base": 20,
      "occupation": 0,
      "interest": 0,
      "total": 20,
      "half": 10,
      "fifth": 4
    },
    "track": {
      "base": 10,
      "occupation": 0,
      "interest": 0,
      "total": 10,
      "half": 5,
      "fifth": 2
    }
  }
}
```

### 3.5 戦闘関連（7版）

```json
{
  "combat": {
    "weapons": [
      {
        "name": "武器名",
        "skill_value": "技能値",
        "damage": "ダメージ",
        "base_range": "基本射程",
        "attacks_per_round": "ラウンド毎攻撃回数",
        "ammo": "弾薬",
        "malfunction_number": "故障ナンバー"
      }
    ],
    "armor": {
      "type": "防具種別",
      "armor_points": "防護点"
    }
  }
}
```

---

## 4. 版間の主要な違い

### 4.1 難易度システム

| 項目 | 6版 | 7版 |
|------|-----|-----|
| 判定方式 | 技能値以下でロール | Regular/Hard/Extreme判定 |
| 技能値表示 | 技能値のみ | 技能値/半分値/1/5値 |
| 成功度 | 成功/失敗 | 成功度レベル（Regular/Hard/Extreme/Critical） |

### 4.2 能力値・ステータス

| 項目 | 6版 | 7版 |
|------|-----|-----|
| 副次ステータス | アイデア、幸運、知識ロール | 廃止（能力値直接使用） |
| 正気度 | POW値（最大99） | POW値（開始時最大値・現在最大値） |
| 移動力 | 記載なし | 詳細な移動力ルール |
| ビルド | 概念なし | STR+SIZから算出 |

### 4.3 スキル

| 項目 | 6版 | 7版 |
|------|-----|-----|
| 基本値 | 固定値 | 一部変更 |
| 戦闘技能 | 個別管理 | 分類整理（Fighting, Firearms） |
| 社交技能 | 基本的 | 細分化（Charm, Fast Talk, Intimidate, Persuade） |

### 4.4 戦闘システム

| 項目 | 6版 | 7版 |
|------|-----|-----|
| ダメージボーナス | 表参照 | ビルドから自動計算 |
| 防具 | 防護点 | 防護点（より詳細） |
| 重傷 | HP 1/2以下 | 重傷ルール |

---

## 5. データベース設計案

### 5.1 キャラクターベーステーブル

```sql
CREATE TABLE characters (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    session_id BIGINT NULL,
    game_version ENUM('6th', '7th') NOT NULL,
    
    -- 基本情報
    investigator_name VARCHAR(100) NOT NULL,
    player_name VARCHAR(100),
    age INTEGER CHECK (age BETWEEN 15 AND 90),
    gender VARCHAR(50),
    occupation VARCHAR(100),
    birthplace VARCHAR(100),
    residence VARCHAR(100),
    
    -- 6版固有
    mental_disorder TEXT NULL,
    
    -- 能力値
    str INTEGER CHECK (str BETWEEN 15 AND 90),
    con INTEGER CHECK (con BETWEEN 15 AND 90),
    pow INTEGER CHECK (pow BETWEEN 15 AND 90),
    dex INTEGER CHECK (dex BETWEEN 15 AND 90),
    app INTEGER CHECK (app BETWEEN 15 AND 90),
    siz INTEGER CHECK (siz BETWEEN 30 AND 90),
    int INTEGER CHECK (int BETWEEN 40 AND 90),
    edu INTEGER CHECK (edu BETWEEN 30 AND 90),
    
    -- 7版固有
    luck INTEGER NULL CHECK (luck BETWEEN 15 AND 90),
    
    -- 副次ステータス
    hit_points_max INTEGER,
    hit_points_current INTEGER,
    magic_points_max INTEGER,
    magic_points_current INTEGER,
    sanity_max INTEGER,
    sanity_current INTEGER,
    sanity_starting_max INTEGER NULL, -- 7版
    breaking_point INTEGER NULL, -- 7版
    
    -- 計算値
    damage_bonus VARCHAR(10),
    build INTEGER NULL, -- 7版
    movement_rate INTEGER NULL, -- 7版
    
    -- メタデータ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES custom_users(id),
    FOREIGN KEY (session_id) REFERENCES trpg_sessions(id)
);
```

### 5.2 スキルテーブル

```sql
CREATE TABLE character_skills (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    character_id BIGINT NOT NULL,
    skill_name VARCHAR(100) NOT NULL,
    base_value INTEGER DEFAULT 0,
    occupation_points INTEGER DEFAULT 0,
    interest_points INTEGER DEFAULT 0,
    other_points INTEGER DEFAULT 0,
    total_value INTEGER GENERATED ALWAYS AS (
        base_value + occupation_points + interest_points + other_points
    ) STORED,
    half_value INTEGER GENERATED ALWAYS AS (
        FLOOR(total_value / 2)
    ) STORED,
    fifth_value INTEGER GENERATED ALWAYS AS (
        FLOOR(total_value / 5)
    ) STORED,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
    UNIQUE KEY unique_character_skill (character_id, skill_name)
);
```

### 5.3 装備・武器テーブル

```sql
CREATE TABLE character_equipment (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    character_id BIGINT NOT NULL,
    item_type ENUM('weapon', 'armor', 'item') NOT NULL,
    name VARCHAR(100) NOT NULL,
    
    -- 武器用フィールド
    skill_name VARCHAR(100) NULL,
    damage VARCHAR(20) NULL,
    base_range VARCHAR(20) NULL,
    attacks_per_round INTEGER NULL,
    ammo INTEGER NULL,
    malfunction_number INTEGER NULL,
    
    -- 防具用フィールド
    armor_points INTEGER NULL,
    
    -- 一般アイテム
    description TEXT,
    quantity INTEGER DEFAULT 1,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
```

### 5.4 職業テンプレートテーブル

```sql
CREATE TABLE occupation_templates (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    game_version ENUM('6th', '7th') NOT NULL,
    description TEXT,
    credit_rating_range VARCHAR(20),
    
    -- 技能ポイント計算式
    skill_points_formula VARCHAR(100), -- 例: "EDU*4", "APP+EDU*2"
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_occupation_version (name, game_version)
);

CREATE TABLE occupation_skills (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    occupation_id BIGINT NOT NULL,
    skill_name VARCHAR(100) NOT NULL,
    is_required BOOLEAN DEFAULT FALSE,
    choice_group INTEGER NULL, -- 選択制スキルのグループ
    
    FOREIGN KEY (occupation_id) REFERENCES occupation_templates(id) ON DELETE CASCADE
);
```

---

## 6. API設計案

### 6.1 キャラクター管理API

```python
# キャラクター作成
POST /api/characters/
{
    "game_version": "7th",
    "investigator_name": "田中一郎",
    "occupation": "探偵",
    "age": 35,
    "abilities": {
        "str": 70,
        "con": 60,
        "pow": 55,
        "dex": 65,
        "app": 50,
        "siz": 60,
        "int": 80,
        "edu": 75,
        "luck": 60
    }
}

# キャラクター取得
GET /api/characters/{id}/

# キャラクター更新
PATCH /api/characters/{id}/

# スキル更新
PATCH /api/characters/{id}/skills/
{
    "skills": {
        "spot_hidden": {
            "occupation_points": 40,
            "interest_points": 20
        }
    }
}
```

</details>

---

*このファイルは統合インデックスとして機能します。実装時は各個別仕様書を参照してください。*