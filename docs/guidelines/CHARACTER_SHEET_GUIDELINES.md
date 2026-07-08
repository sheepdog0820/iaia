# キャラクターシート開発ガイドライン

## 🚨 重要な制限事項

### キャラクターシート機能の対象システム

**このプロジェクトのキャラクターシート機能は、クトゥルフ神話TRPG 6版・7版専用です。**

- ✅ **対応システム**: クトゥルフ神話TRPG 6版、7版のみ
- ❌ **非対応システム**: D&D、ソード・ワールド、インセイン、その他のTRPGシステム

### 実装制限の理由
1. **システム固有の複雑性**: 各TRPGシステムには独自のルール、能力値計算、技能体系があり、汎用的な実装は困難
2. **6版・7版の特化設計**: 現在のモデル構造は6版・7版の仕様に最適化されている
3. **開発効率**: 特定システムに集中することで、高品質な機能を提供

### 新しいTRPGシステムの要求について
他のTRPGシステム（D&D、ソード・ワールド等）のキャラクターシート機能を要求された場合：
- **理由を説明**: 上記の制限事項を伝える
- **代替案の提示**: シナリオ管理機能での対応を提案
- **実装拒否**: 「申し訳ございませんが、キャラクターシート機能はクトゥルフ神話TRPG専用です」と回答

### クトゥルフ神話TRPG 7版の開発について
**重要**: 7版は正式サポート対象です。
- **正式仕様**: `docs/character_sheet/CHARACTER_SHEET_7TH_EDITION_SPECIFICATION.md` を参照
- **6版互換性**: 7版修正時も6版の既存挙動を変更しない
- **版別テスト**: 7版の能力値、派生値、技能ポイント、APIレスポンスを必ずテストする

### 許可される作業範囲
- クトゥルフ神話TRPG 6版のキャラクターシート機能の改善・修正
- 6版のキャラクターシート関連のバグ修正
- プレイ履歴・統計機能の改善（クトゥルフ以外のシステムも対象）
- クトゥルフ神話TRPG 7版のキャラクターシート機能の改善・修正

## 📋 正式な仕様書

### メイン仕様書
```
docs/character_sheet/
├── CHARACTER_SHEET_6TH_EDITION_SPECIFICATION.md  # ✅ 6版完全仕様書（正式版）
├── CHARACTER_SHEET_7TH_EDITION_SPECIFICATION.md  # ✅ 7版仕様書（正式版）
├── README.md                                     # 仕様書の説明
└── archive/                                      # 過去バージョン（参照のみ）
```

### 関連仕様書
- **[docs/character_sheet/CHARACTER_SHEET_FEATURES.md](../../docs/character_sheet/CHARACTER_SHEET_FEATURES.md)** - 実装済み機能の完全リスト
  - 基本情報、能力値、スキル管理、戦闘・装備、インベントリなど全機能の詳細
  - 各機能の実装状態（✅完了/❌未実装）を確認可能
- **[docs/character_sheet/SKILL_TAB_SPECIFICATION.md](../../docs/character_sheet/SKILL_TAB_SPECIFICATION.md)** - 技能タブUI仕様
  - 技能分類（戦闘/探索/行動/交渉/知識）の定義
  - タブ切り替えとフィルタリング機能の実装仕様
  - 3列レイアウトとレスポンシブデザインの詳細

**重要**: キャラクターシート開発は該当版の正式仕様書を参照してください。

## 実装ファイル

```
templates/accounts/character_sheet_6th.html       # 6版テンプレート
static/js/character_sheet_6th.js                  # 6版JavaScript
static/js/character_sheet_6th_optimized.js        # 最適化版
```

## その他の仕様書

```
CHARACTER_SHEET_SPECIFICATION.md                  # 共通仕様
CHARACTER_SHEET_TECHNICAL_SPEC.md                 # 技術仕様
docs/character_sheet/CHARACTER_SHEET_7TH_EDITION_SPECIFICATION.md  # 7版正式仕様書
```

**注意**: これらのファイルはすべてクトゥルフ神話TRPG 6版・7版の仕様に基づいています。
他のTRPGシステム用のキャラクターシート機能は実装しません。

## 🎯 キャラクターシート作業時のTDD手順

### クトゥルフ神話TRPG専用開発プロセス
1. **📋 仕様確認**: 該当版の仕様書を必ず確認
   - 6版: `CHARACTER_SHEET_6TH_EDITION.md`
   - 7版: `docs/character_sheet/CHARACTER_SHEET_7TH_EDITION_SPECIFICATION.md`

2. **🔴 ルール準拠テスト**: 版別ルールのテストを作成
   - 能力値範囲テスト
   - 計算式テスト
   - バリデーションテスト

3. **🟢 ルール実装**: クトゥルフルールの正確な実装
   - 6版: 3D6（3-18）、×5計算なし
   - 7版: 3D6×5（15-90）、パーセンテージベース

4. **🔵 精度向上**: 計算精度とユーザビリティの改善

5. **🔍 ルール検証**: 公式ルールとの整合性確認
