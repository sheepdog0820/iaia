#!/bin/bash

# タブレノ サーバー管理スクリプト
# 使用方法: ./server.sh [start|stop|restart|status|logs]

# 設定
SERVER_PORT=8080
SERVER_HOST="0.0.0.0"
MANAGE_PY="python3 manage.py"
PID_FILE=".server.pid"
LOG_FILE="server.log"

# 色付きログ出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# サーバー起動
start_server() {
    # 既存セッション・プロセスの強制終了
    log_info "🔍 既存のサーバープロセスをチェック中..."
    
    # PIDファイルからのチェック
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        if ps -p $PID > /dev/null 2>&1; then
            log_warning "⚠️  既存サーバーを停止中 (PID: $PID)"
            kill $PID 2>/dev/null
            sleep 2
            kill -9 $PID 2>/dev/null
        fi
        rm -f $PID_FILE
    fi
    
    # Django関連プロセスの強制終了
    log_info "🧹 Django関連プロセスをクリーンアップ中..."
    pkill -f "python.*manage.py runserver" 2>/dev/null
    pkill -f "python3.*manage.py runserver" 2>/dev/null
    
    # ポート使用プロセスの強制終了
    PORT_PID=$(lsof -ti :$SERVER_PORT 2>/dev/null)
    if [ -n "$PORT_PID" ]; then
        log_warning "⚠️  ポート$SERVER_PORT を使用中のプロセスを終了: $PORT_PID"
        kill -9 $PORT_PID 2>/dev/null
    fi
    
    # セッション終了の待機
    sleep 2
    
    # データベースマイグレーション確認
    log_info "📊 データベースマイグレーションを確認中..."
    $MANAGE_PY migrate --check >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        log_info "🔧 マイグレーションを実行中..."
        $MANAGE_PY migrate
    fi
    
    # サーバー起動
    log_info "🚀 Djangoサーバーを起動中..."
    nohup $MANAGE_PY runserver $SERVER_HOST:$SERVER_PORT > $LOG_FILE 2>&1 & 
    SERVER_PID=$!
    echo $SERVER_PID > $PID_FILE
    
    # 起動確認
    sleep 3
    if ps -p $SERVER_PID > /dev/null 2>&1; then
        log_success "✅ サーバーが正常に起動しました!"
        log_info "🆔 PID: $SERVER_PID"
        log_info "🌐 URL: http://localhost:$SERVER_PORT"
        log_info "📊 管理画面: http://localhost:$SERVER_PORT/admin/"
        log_info "🔧 API: http://localhost:$SERVER_PORT/api/"
        log_info "📝 ログファイル: $LOG_FILE"
        
        # 管理者アカウント情報
        log_info "👤 管理者: admin / arkham_admin_2024"
        log_info "🎮 デモ: http://localhost:$SERVER_PORT/accounts/demo/"
        
        # 完了音
        echo -e "\a"
    else
        log_error "❌ サーバーの起動に失敗しました"
        rm -f $PID_FILE
        if [ -f "$LOG_FILE" ]; then
            log_error "エラーログ:"
            tail -10 $LOG_FILE
        fi
        return 1
    fi
}

# サーバー停止
stop_server() {
    log_info "🛑 サーバーを停止中..."
    
    # PIDファイルからの停止
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        if ps -p $PID > /dev/null 2>&1; then
            log_info "📍 PIDファイルからサーバーを停止中 (PID: $PID)"
            kill $PID
            
            # プロセス終了待機
            for i in {1..10}; do
                if ! ps -p $PID > /dev/null 2>&1; then
                    break
                fi
                sleep 1
            done
            
            # 強制終了
            if ps -p $PID > /dev/null 2>&1; then
                log_warning "⚠️  強制終了を実行中..."
                kill -9 $PID
            fi
        fi
        rm -f $PID_FILE
    fi
    
    # 全Django関連プロセスの強制終了
    log_info "🧹 残存プロセスをクリーンアップ中..."
    pkill -f "python.*manage.py runserver" 2>/dev/null
    pkill -f "python3.*manage.py runserver" 2>/dev/null
    
    # ポート使用プロセスの終了
    PORT_PID=$(lsof -ti :$SERVER_PORT 2>/dev/null)
    if [ -n "$PORT_PID" ]; then
        log_info "🔌 ポート$SERVER_PORT のプロセスを終了: $PORT_PID"
        kill -9 $PORT_PID 2>/dev/null
    fi
    
    log_success "✅ サーバー停止完了"
}

# サーバー再起動
restart_server() {
    log_info "🔄 サーバーを再起動中..."
    stop_server
    sleep 2
    start_server
}

# ステータス確認
show_status() {
    log_info "📊 サーバー状態を確認中..."
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        if ps -p $PID > /dev/null 2>&1; then
            log_success "✅ サーバーは起動中です"
            log_info "🆔 PID: $PID"
            log_info "🌐 URL: http://localhost:$SERVER_PORT"
            
            # ポート確認
            if lsof -i :$SERVER_PORT >/dev/null 2>&1; then
                log_info "📡 ポート$SERVER_PORT でリスニング中"
            else
                log_warning "⚠️  ポート$SERVER_PORT でリスニングしていません"
            fi
            
            # メモリ使用量
            MEMORY=$(ps -p $PID -o rss= 2>/dev/null)
            if [ -n "$MEMORY" ]; then
                MEMORY_MB=$(($MEMORY / 1024))
                log_info "💾 メモリ使用量: ${MEMORY_MB}MB"
            fi
            
            # 最新ログ
            if [ -f "$LOG_FILE" ]; then
                log_info "📝 最新ログ (最新5行):"
                tail -n 5 $LOG_FILE | sed 's/^/    /'
            fi
        else
            log_warning "⚠️  サーバーは停止中 (古いPIDファイル)"
            rm -f $PID_FILE
        fi
    else
        log_info "🛑 サーバーは停止中です"
        
        # ポート使用確認
        PORT_PID=$(lsof -ti :$SERVER_PORT 2>/dev/null)
        if [ -n "$PORT_PID" ]; then
            log_warning "⚠️  ポート$SERVER_PORT は他のプロセスが使用中: $PORT_PID"
        fi
    fi
}

# ログ表示
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        log_info "📝 サーバーログをリアルタイム表示中... (Ctrl+Cで終了)"
        echo "────────────────────────────────────────"
        tail -f $LOG_FILE
    else
        log_warning "⚠️  ログファイルが見つかりません: $LOG_FILE"
    fi
}

# 使用方法表示
show_usage() {
    echo "🎮 タブレノ サーバー管理スクリプト"
    echo ""
    echo "使用方法: $0 [コマンド]"
    echo ""
    echo "コマンド:"
    echo "  start   - サーバーを起動 (既存セッションを自動終了)"
    echo "  stop    - サーバーを停止"
    echo "  restart - サーバーを再起動 (デフォルト)"
    echo "  status  - サーバーの状態を確認"
    echo "  logs    - サーバーログをリアルタイム表示"
    echo "  help    - この使用方法を表示"
    echo ""
    echo "設定:"
    echo "  ポート: $SERVER_PORT"
    echo "  ホスト: $SERVER_HOST"
    echo "  ログ: $LOG_FILE"
    echo ""
    echo "例:"
    echo "  $0 start    # サーバー起動"
    echo "  $0 status   # 状態確認"
    echo "  $0 logs     # ログ監視"
}

# メイン処理
case "${1:-restart}" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        log_error "❌ 不正なコマンド: $1"
        show_usage
        exit 1
        ;;
esac