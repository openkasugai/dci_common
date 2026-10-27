#!/bin/bash
# DCI診断ツール - 共通ライブラリ
# このスクリプトは diagnosis.sh および overall_diagnosis.sh から source される共通関数群を提供します。
#
# Usage: source diagnosis_common.sh

# =============================================================================
# 終了コード定数
# =============================================================================
readonly EXIT_CODE_SUCCESS=0         # 診断完了（リソース状態の問題なし）
readonly EXIT_CODE_TOOL_ERROR=1      # 診断ツール自体のエラー
readonly EXIT_CODE_CRITICAL=2        # リソース状態の重大な問題を検出
readonly EXIT_CODE_WARNING=3         # リソース状態の警告を検出

# =============================================================================
# デフォルト設定
# =============================================================================
# 親ディレクトリ（自動化スクリプトの親ディレクトリ）のデフォルト
# 診断ツールディレクトリ（support_tools/diagnosis/）から2階層上（script/work/）を想定
DIAGNOSIS_SCRIPT_ROOT_DEFAULT="../../"

# 出力ディレクトリのデフォルト（呼び出し元で上書き可能）
DIAGNOSIS_OUTPUT_BASE_DIR_DEFAULT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../diagnosis_reports"

# ログレベルのデフォルト
DIAGNOSIS_LOG_LEVEL_DEFAULT="INFO"

# タイムアウトのデフォルト（秒）
DIAGNOSIS_TIMEOUT_DEFAULT=900

# Kubernetesリソース収集タイムアウトのデフォルト（秒）
K8S_COLLECTOR_TIMEOUT_DEFAULT=600

# =============================================================================
# ログ出力関数（色なし、シンプルなプレーンテキスト形式）
# =============================================================================

# [INFO] レベルのログ出力
# Arguments:
#   $@ - ログメッセージ
log_info() {
    echo "[INFO] $*"
}

# [SUCCESS] レベルのログ出力
# Arguments:
#   $@ - ログメッセージ
log_success() {
    echo "[SUCCESS] $*"
}

# [WARNING] レベルのログ出力（標準エラー出力）
# Arguments:
#   $@ - ログメッセージ
log_warning() {
    echo "[WARNING] $*" >&2
}

# [ERROR] レベルのログ出力（標準エラー出力）
# Arguments:
#   $@ - ログメッセージ
log_error() {
    echo "[ERROR] $*" >&2
}

# セクション区切りのログ出力
# Arguments:
#   $@ - セクションタイトル
log_section() {
    echo ""
    echo "========================================"
    echo "$*"
    echo "========================================"
}

# =============================================================================
# 引数解析ヘルパー関数
# =============================================================================

# --output-dir オプションの解析
# Arguments:
#   $1 - 次の引数（ディレクトリパス）
# Returns:
#   出力ディレクトリパスを変数 PARSED_OUTPUT_DIR に設定
#   消費した引数の数を返却（成功時: 2, 失敗時: 0）
parse_output_dir_option() {
    if [ $# -lt 2 ]; then
        log_error "--output-dir オプションには引数が必要です"
        return 0
    fi
    PARSED_OUTPUT_DIR="$2"
    return 2  # 2つの引数を消費（--output-dir DIR）
}

# --help/-h オプションの検出
# Arguments:
#   $1 - 引数
# Returns:
#   0 (true) if help option, 1 (false) otherwise
is_help_option() {
    [[ "$1" == "--help" || "$1" == "-h" ]]
}

# =============================================================================
# 環境変数の初期化
# =============================================================================

# 診断ツール用の環境変数をデフォルト値で初期化
# 既に設定されている場合は上書きしない
init_diagnosis_env_vars() {
    : "${DIAGNOSIS_LOG_LEVEL:=$DIAGNOSIS_LOG_LEVEL_DEFAULT}"
    : "${DIAGNOSIS_TIMEOUT:=$DIAGNOSIS_TIMEOUT_DEFAULT}"
    : "${K8S_COLLECTOR_TIMEOUT:=$K8S_COLLECTOR_TIMEOUT_DEFAULT}"
    
    # 呼び出し元にエクスポート（サブプロセスで使用できるように）
    export DIAGNOSIS_LOG_LEVEL
    export DIAGNOSIS_TIMEOUT
    export K8S_COLLECTOR_TIMEOUT
}

# =============================================================================
# タイムスタンプ生成
# =============================================================================

# 診断レポート用のタイムスタンプ文字列を生成
# Format: YYYYMMDD_HHMMSS
# Returns:
#   タイムスタンプ文字列を標準出力
generate_timestamp() {
    date +"%Y%m%d_%H%M%S"
}

# =============================================================================
# 時間計測ユーティリティ
# =============================================================================

# 経過時間を計算して人間が読みやすい形式で出力
# Arguments:
#   $1 - 開始時刻（Unix秒）
#   $2 - 終了時刻（Unix秒、省略時は現在時刻）
# Returns:
#   "Xm Ys" 形式の文字列を標準出力
format_elapsed_time() {
    local start_time=$1
    local end_time=${2:-$(date +%s)}
    local elapsed=$((end_time - start_time))
    local minutes=$((elapsed / 60))
    local seconds=$((elapsed % 60))
    echo "${minutes}分${seconds}秒"
}

# =============================================================================
# 終了コードの説明テキスト
# =============================================================================

# 終了コードに対応する説明文を返す
# Arguments:
#   $1 - 終了コード（0, 1, 2, 3）
# Returns:
#   説明文を標準出力
get_exit_code_description() {
    local code=$1
    case $code in
        0) echo "SUCCESS (診断完了 - リソース状態の問題なし)" ;;
        1) echo "TOOL ERROR (診断ツール自体のエラー)" ;;
        2) echo "CRITICAL ISSUES (リソース状態の重大な問題を検出)" ;;
        3) echo "WARNINGS (リソース状態の警告を検出)" ;;
        *) echo "UNKNOWN (不明な終了コード: $code)" ;;
    esac
}

# 終了コードに対応するステータス文字列を返す（簡易版）
# Arguments:
#   $1 - 終了コード（0, 1, 2, 3）
# Returns:
#   ステータス文字列を標準出力（例: "SUCCESS", "CRITICAL", "WARNING", "ERROR"）
get_exit_code_status() {
    local code=$1
    case $code in
        0) echo "SUCCESS" ;;
        1) echo "TOOL_ERROR" ;;
        2) echo "CRITICAL" ;;
        3) echo "WARNING" ;;
        *) echo "UNKNOWN" ;;
    esac
}

# =============================================================================
# 初期化処理
# =============================================================================

# このライブラリが source されたときに自動的に環境変数を初期化
init_diagnosis_env_vars
