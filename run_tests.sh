#!/bin/bash

# タブレノ 自動テスト実行スクリプト
# 使用方法: ./run_tests.sh [オプション]

set -e  # エラー時に停止

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ヘルプ表示
show_help() {
    echo "タブレノ 自動テストスイート"
    echo ""
    echo "使用方法: $0 [オプション]"
    echo ""
    echo "オプション:"
    echo "  -h, --help      このヘルプを表示"
    echo "  -f, --fast      高速テスト（failfast有効）"
    echo "  -c, --coverage  カバレッジレポート付きテスト"
    echo "  -l, --lint      コード品質チェック"
    echo "  -s, --security  セキュリティチェック"
    echo "  -a, --all       全チェック実行"
    echo "  --keepdb        テストDB保持"
    echo ""
    echo "例:"
    echo "  $0                     # 基本テスト実行"
    echo "  $0 --all              # 全チェック実行"
    echo "  $0 --fast --coverage  # 高速テスト+カバレッジ"
}

# ログ出力
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Python環境チェック
check_python_env() {
    log_info "Python環境をチェック中..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python3が見つかりません"
        exit 1
    fi
    
    # 仮想環境の確認
    if [[ -n "$VIRTUAL_ENV" ]]; then
        log_info "仮想環境が有効: $VIRTUAL_ENV"
    else
        log_warning "仮想環境が有効になっていません"
    fi
    
    # 必要なパッケージのチェック
    python3 -c "import django" 2>/dev/null || {
        log_error "Django がインストールされていません"
        exit 1
    }
    
    log_success "Python環境OK"
}

# データベース準備
prepare_database() {
    log_info "テスト用データベースを準備中..."
    
    # マイグレーション実行
    python3 manage.py migrate --run-syncdb 2>/dev/null || {
        log_error "マイグレーションに失敗しました"
        exit 1
    }
    
    log_success "データベース準備完了"
}

# テスト実行
run_tests() {
    local args=()
    
    if [[ "$FAST_MODE" == "true" ]]; then
        args+=(--fast)
    fi
    
    if [[ "$COVERAGE_MODE" == "true" ]]; then
        args+=(--coverage)
    fi
    
    if [[ "$LINT_MODE" == "true" ]]; then
        args+=(--lint)
    fi
    
    if [[ "$SECURITY_MODE" == "true" ]]; then
        args+=(--security)
    fi
    
    if [[ "$ALL_MODE" == "true" ]]; then
        args+=(--all)
    fi
    
    if [[ "$KEEP_DB" == "true" ]]; then
        args+=(--keepdb)
    fi
    
    log_info "テストを実行中..."
    python3 test_runner.py "${args[@]}"
}

# テスト前の準備
pre_test_setup() {
    log_info "テスト前の準備を実行中..."
    
    # 静的ファイル収集（テスト用）
    python3 manage.py collectstatic --noinput --clear 2>/dev/null || true
    
    # キャッシュクリア
    if [[ -d "__pycache__" ]]; then
        find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    fi
    
    log_success "準備完了"
}

# テスト後のクリーンアップ
post_test_cleanup() {
    log_info "テスト後のクリーンアップを実行中..."
    
    # テンポラリファイル削除
    find . -name "*.pyc" -delete 2>/dev/null || true
    
    log_success "クリーンアップ完了"
}

# メイン処理
main() {
    # デフォルト値
    FAST_MODE="false"
    COVERAGE_MODE="false"
    LINT_MODE="false"
    SECURITY_MODE="false"
    ALL_MODE="false"
    KEEP_DB="false"
    
    # 引数解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -f|--fast)
                FAST_MODE="true"
                shift
                ;;
            -c|--coverage)
                COVERAGE_MODE="true"
                shift
                ;;
            -l|--lint)
                LINT_MODE="true"
                shift
                ;;
            -s|--security)
                SECURITY_MODE="true"
                shift
                ;;
            -a|--all)
                ALL_MODE="true"
                shift
                ;;
            --keepdb)
                KEEP_DB="true"
                shift
                ;;
            *)
                log_error "不明なオプション: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # バナー表示
    echo "========================================"
    echo "    ARKHAM NEXUS テストスイート"
    echo "========================================"
    echo ""
    
    # 実行
    check_python_env
    prepare_database
    pre_test_setup
    
    # テスト実行（エラーハンドリング付き）
    if run_tests; then
        log_success "すべてのテストが正常に完了しました！"
        post_test_cleanup
        exit 0
    else
        log_error "テストが失敗しました"
        post_test_cleanup
        exit 1
    fi
}

# スクリプト実行
main "$@"