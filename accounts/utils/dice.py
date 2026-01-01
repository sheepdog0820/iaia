"""
クトゥルフ神話TRPG 6版 ユーティリティ関数
"""

import re
import random
from typing import List, Union, Dict, Optional
from ..character_models import CharacterDiceRollSetting


def parse_custom_formula(formula: str) -> List[str]:
    """
    カスタム式を構成要素にパース
    
    Args:
        formula: カスタム計算式（例: "(EDU + STR) × 10"）
    
    Returns:
        パースされたトークンのリスト
    """
    # 数式で使用される記号を認識するパターン
    pattern = r'(\(|\)|×|÷|\+|\-|[A-Z]+|\d+)'
    tokens = re.findall(pattern, formula)
    return tokens


def validate_custom_formula(formula: str) -> bool:
    """
    カスタム式のバリデーション
    
    Args:
        formula: 検証する計算式
    
    Returns:
        有効な式の場合True
    """
    # 許可される能力値
    valid_abilities = ['STR', 'CON', 'POW', 'DEX', 'APP', 'SIZ', 'INT', 'EDU']
    
    # 許可される演算子
    valid_operators = ['×', '÷', '+', '-', '(', ')']
    
    # 危険な文字列のチェック
    dangerous_patterns = [
        'eval', 'exec', '__', 'import', 'DROP', 'DELETE', 
        'UPDATE', 'INSERT', ';', '--', '/*', '*/', 'script'
    ]
    
    # 無効な演算子（*を使用してはいけない）
    if '*' in formula or '/' in formula and '÷' not in formula:
        return False
    
    formula_upper = formula.upper()
    for pattern in dangerous_patterns:
        if pattern.upper() in formula_upper:
            return False
    
    # パースしてトークンを検証
    try:
        tokens = parse_custom_formula(formula)
        
        for token in tokens:
            # 数値、能力値、演算子のいずれかであること
            if token.isdigit():
                continue
            elif token in valid_abilities:
                continue
            elif token in valid_operators:
                continue
            else:
                return False
        
        # 空の式は無効
        if not tokens:
            return False
        
        # 演算子の連続チェック
        prev_operator = False
        for token in tokens:
            if token in ['+', '-', '×', '÷']:
                if prev_operator:
                    return False
                prev_operator = True
            else:
                prev_operator = False
        
        return True
        
    except Exception:
        return False


def calculate_custom_formula(character, formula: str) -> int:
    """
    カスタム式を計算
    
    Args:
        character: CharacterSheetオブジェクト
        formula: 計算式
    
    Returns:
        計算結果（最小値0）
    
    Raises:
        ValueError: 無効な式やゼロ除算の場合
    """
    if not validate_custom_formula(formula):
        raise ValueError("無効な計算式です")
    
    # 長すぎる式のチェック
    if len(formula) > 200:
        raise ValueError("計算式が長すぎます")
    
    # 6版の値に変換（現在のモデルは7版仕様なので5で割る）
    ability_values = {
        'STR': character.str_value // 5,
        'CON': character.con_value // 5,
        'POW': character.pow_value // 5,
        'DEX': character.dex_value // 5,
        'APP': character.app_value // 5,
        'SIZ': character.siz_value // 5,
        'INT': character.int_value // 5,
        'EDU': character.edu_value // 5,
    }
    
    # 式の評価用に変換
    eval_formula = formula
    
    # 能力値を実際の値に置き換え
    for ability, value in ability_values.items():
        eval_formula = eval_formula.replace(ability, str(value))
    
    # 演算子を Python の演算子に変換
    eval_formula = eval_formula.replace('×', '*')
    eval_formula = eval_formula.replace('÷', '/')
    
    try:
        # 安全な評価のために許可された要素のみ使用
        result = eval(eval_formula, {"__builtins__": {}}, {})
        
        # 整数に変換（切り捨て）
        result = int(result)
        
        # 最小値は0
        return max(0, result)
        
    except ZeroDivisionError:
        raise ValueError("ゼロ除算エラー")
    except Exception as e:
        raise ValueError(f"計算エラー: {str(e)}")


def calculate_occupation_skill_points(character, formula_type: str, custom_formula: str = None) -> int:
    """
    職業技能ポイントを計算
    
    Args:
        character: CharacterSheetオブジェクト
        formula_type: 計算式のタイプ
        custom_formula: カスタム式（formula_type='custom'の場合）
    
    Returns:
        職業技能ポイント
    
    Raises:
        ValueError: 無効な計算式の場合
    """
    # 6版の値に変換
    edu = character.edu_value // 5
    app = character.app_value // 5
    dex = character.dex_value // 5
    pow_val = character.pow_value // 5
    str_val = character.str_value // 5
    con = character.con_value // 5
    siz = character.siz_value // 5
    int_val = character.int_value // 5
    
    calculation_methods = {
        'edu20': edu * 20,
        'edu10app10': edu * 10 + app * 10,
        'edu10dex10': edu * 10 + dex * 10,
        'edu10pow10': edu * 10 + pow_val * 10,
        'edu10str10': edu * 10 + str_val * 10,
        'edu10con10': edu * 10 + con * 10,
        'edu10siz10': edu * 10 + siz * 10,
        'edu10int10': edu * 10 + int_val * 10,
    }
    
    if formula_type == 'custom':
        if not custom_formula:
            raise ValueError("カスタム式が指定されていません")
        return calculate_custom_formula(character, custom_formula)
    
    if formula_type in calculation_methods:
        return calculation_methods[formula_type]
    
    raise ValueError(f"無効な計算式タイプ: {formula_type}")


# ========== 動的ダイス設定機能 ==========

def get_current_dice_settings(user) -> Optional[CharacterDiceRollSetting]:
    """
    ユーザーの現在のダイス設定を取得
    
    Args:
        user: ユーザーオブジェクト
    
    Returns:
        CharacterDiceRollSetting: デフォルト設定、または None
    """
    try:
        return CharacterDiceRollSetting.get_default_setting(user)
    except Exception:
        return None


def get_dice_count(ability_name: str, setting: CharacterDiceRollSetting) -> int:
    """
    指定能力値のダイス数を取得
    
    Args:
        ability_name: 能力値名 ('str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu')
        setting: ダイス設定オブジェクト
    
    Returns:
        int: ダイス数
    
    Raises:
        ValueError: 無効な能力値名
        AttributeError: 設定オブジェクトが不正
    """
    ability_mapping = {
        'str': 'str_dice_count',
        'con': 'con_dice_count',
        'pow': 'pow_dice_count',
        'dex': 'dex_dice_count',
        'app': 'app_dice_count',
        'siz': 'siz_dice_count',
        'int': 'int_dice_count',
        'edu': 'edu_dice_count'
    }
    
    if ability_name not in ability_mapping:
        raise ValueError(f"Invalid ability name: {ability_name}")
    
    if not setting:
        raise AttributeError("Setting object is None")
    
    field_name = ability_mapping[ability_name]
    return getattr(setting, field_name)


def get_dice_sides(ability_name: str, setting: CharacterDiceRollSetting) -> int:
    """
    指定能力値のダイス面数を取得
    
    Args:
        ability_name: 能力値名
        setting: ダイス設定オブジェクト
    
    Returns:
        int: ダイス面数
    """
    ability_mapping = {
        'str': 'str_dice_sides',
        'con': 'con_dice_sides',
        'pow': 'pow_dice_sides',
        'dex': 'dex_dice_sides',
        'app': 'app_dice_sides',
        'siz': 'siz_dice_sides',
        'int': 'int_dice_sides',
        'edu': 'edu_dice_sides'
    }
    
    if ability_name not in ability_mapping:
        raise ValueError(f"Invalid ability name: {ability_name}")
    
    if not setting:
        raise AttributeError("Setting object is None")
    
    field_name = ability_mapping[ability_name]
    return getattr(setting, field_name)


def get_dice_bonus(ability_name: str, setting: CharacterDiceRollSetting) -> int:
    """
    指定能力値のダイスボーナスを取得
    
    Args:
        ability_name: 能力値名
        setting: ダイス設定オブジェクト
    
    Returns:
        int: ダイスボーナス
    """
    ability_mapping = {
        'str': 'str_bonus',
        'con': 'con_bonus',
        'pow': 'pow_bonus',
        'dex': 'dex_bonus',
        'app': 'app_bonus',
        'siz': 'siz_bonus',
        'int': 'int_bonus',
        'edu': 'edu_bonus'
    }
    
    if ability_name not in ability_mapping:
        raise ValueError(f"Invalid ability name: {ability_name}")
    
    if not setting:
        raise AttributeError("Setting object is None")
    
    field_name = ability_mapping[ability_name]
    return getattr(setting, field_name)


def roll_ability_with_setting(ability_name: str, setting: CharacterDiceRollSetting) -> int:
    """
    ダイス設定を使用して能力値をロール
    
    Args:
        ability_name: 能力値名
        setting: ダイス設定オブジェクト
    
    Returns:
        int: ロール結果
    
    Examples:
        >>> setting = CharacterDiceRollSetting(str_dice_count=3, str_dice_sides=6, str_bonus=0)
        >>> result = roll_ability_with_setting('str', setting)
        >>> 3 <= result <= 18
        True
    """
    if not setting:
        raise AttributeError("Setting object is None")
    
    dice_count = get_dice_count(ability_name, setting)
    dice_sides = get_dice_sides(ability_name, setting)
    dice_bonus = get_dice_bonus(ability_name, setting)
    
    # ダイスロール実行
    total = 0
    for _ in range(dice_count):
        total += random.randint(1, dice_sides)
    
    return total + dice_bonus


def calculate_abilities_with_setting(setting: CharacterDiceRollSetting) -> Dict[str, int]:
    """
    ダイス設定を使用して全能力値を計算
    
    Args:
        setting: ダイス設定オブジェクト
    
    Returns:
        Dict[str, int]: 全能力値の辞書
    
    Examples:
        >>> setting = CharacterDiceRollSetting.create_standard_6th_preset(user)
        >>> abilities = calculate_abilities_with_setting(setting)
        >>> sorted(abilities.keys())
        ['app', 'con', 'dex', 'edu', 'int', 'pow', 'siz', 'str']
    """
    if not setting:
        raise AttributeError("Setting object is None")
    
    abilities = {}
    ability_names = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']
    
    for ability_name in ability_names:
        abilities[ability_name] = roll_ability_with_setting(ability_name, setting)
    
    return abilities


def validate_dice_settings(settings: Dict[str, Union[int, float]]) -> bool:
    """
    ダイス設定の妥当性を検証
    
    Args:
        settings: 検証する設定辞書 {'count': int, 'sides': int, 'bonus': int}
    
    Returns:
        bool: 設定が有効かどうか
    
    Examples:
        >>> validate_dice_settings({'count': 3, 'sides': 6, 'bonus': 0})
        True
        >>> validate_dice_settings({'count': 0, 'sides': 6, 'bonus': 0})
        False
    """
    try:
        count = int(settings.get('count', 0))
        sides = int(settings.get('sides', 0))
        bonus = int(settings.get('bonus', 0))
        
        # 範囲チェック
        if not (1 <= count <= 10):
            return False
        
        if not (2 <= sides <= 100):
            return False
        
        if not (-50 <= bonus <= 50):
            return False
        
        return True
        
    except (ValueError, TypeError, AttributeError):
        return False


def get_dice_formula_string(ability_name: str, setting: CharacterDiceRollSetting) -> str:
    """
    ダイス設定から式文字列を生成
    
    Args:
        ability_name: 能力値名
        setting: ダイス設定オブジェクト
    
    Returns:
        str: ダイス式文字列 (例: "3D6", "2D6+6", "4D6-2")
    
    Examples:
        >>> setting = CharacterDiceRollSetting(str_dice_count=3, str_dice_sides=6, str_bonus=0)
        >>> get_dice_formula_string('str', setting)
        '3D6'
        >>> setting.str_bonus = 6
        >>> get_dice_formula_string('str', setting)
        '3D6+6'
    """
    if not setting:
        raise AttributeError("Setting object is None")
    
    dice_count = get_dice_count(ability_name, setting)
    dice_sides = get_dice_sides(ability_name, setting)
    dice_bonus = get_dice_bonus(ability_name, setting)
    
    formula = f"{dice_count}D{dice_sides}"
    
    if dice_bonus > 0:
        formula += f"+{dice_bonus}"
    elif dice_bonus < 0:
        formula += str(dice_bonus)  # 負の場合は自動的に-がつく
    
    return formula


def get_all_dice_formulas(setting: CharacterDiceRollSetting) -> Dict[str, str]:
    """
    全能力値のダイス式文字列を取得
    
    Args:
        setting: ダイス設定オブジェクト
    
    Returns:
        Dict[str, str]: 能力値名とダイス式の辞書
    
    Examples:
        >>> setting = CharacterDiceRollSetting.create_standard_6th_preset(user)
        >>> formulas = get_all_dice_formulas(setting)
        >>> formulas['str']
        '3D6'
        >>> formulas['siz']
        '2D6+6'
    """
    if not setting:
        raise AttributeError("Setting object is None")
    
    formulas = {}
    ability_names = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']
    
    for ability_name in ability_names:
        formulas[ability_name] = get_dice_formula_string(ability_name, setting)
    
    return formulas


def calculate_ability_range(ability_name: str, setting: CharacterDiceRollSetting) -> Dict[str, int]:
    """
    能力値の理論的な範囲を計算
    
    Args:
        ability_name: 能力値名
        setting: ダイス設定オブジェクト
    
    Returns:
        Dict[str, int]: {'min': 最小値, 'max': 最大値}
    
    Examples:
        >>> setting = CharacterDiceRollSetting(str_dice_count=3, str_dice_sides=6, str_bonus=0)
        >>> calculate_ability_range('str', setting)
        {'min': 3, 'max': 18}
    """
    if not setting:
        raise AttributeError("Setting object is None")
    
    dice_count = get_dice_count(ability_name, setting)
    dice_sides = get_dice_sides(ability_name, setting)
    dice_bonus = get_dice_bonus(ability_name, setting)
    
    min_roll = dice_count * 1 + dice_bonus  # 全て1の目
    max_roll = dice_count * dice_sides + dice_bonus  # 全て最大の目
    
    return {
        'min': min_roll,
        'max': max_roll
    }
