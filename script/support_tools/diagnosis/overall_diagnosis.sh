#!/bin/bash
set -u  # 未定義変数使用時にエラー終了

# DCI診断一括実行ツール - 4つの自動化スクリプトの診断を一括実行
# Usage: ./overall_diagnosis.sh [OPTIONS]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 共通ライブラリの読み込み
source "${SCRIPT_DIR}/common/diagnosis_common.sh"

DIAGNOSIS_TOOL="${SCRIPT_DIR}/diagnosis.sh"

# デフォルト設定（共通ライブラリから提供される値を使用）
SCRIPT_ROOT_ARG="${DIAGNOSIS_SCRIPT_ROOT_DEFAULT}"
OUTPUT_BASE_DIR="${DIAGNOSIS_OUTPUT_BASE_DIR_DEFAULT}"
START_TIME=$(date +%s)
TIMESTAMP=$(generate_timestamp)

# 診断対象スクリプトリスト（依存関係順に実行）
SCRIPTS=(
    "manager_cluster_setup"
    "manager_software_deploy"
    "tenant_provisioning"
    "tenant_deploy"
)

# 各診断結果の記録用配列
declare -A DIAGNOSIS_EXIT_CODES
declare -A DIAGNOSIS_REPORT_PATHS
declare -A DIAGNOSIS_LOG_DIRS

# Usage表示関数
usage() {
    cat << 'EOF'
Usage: ./overall_diagnosis.sh [OPTIONS]

DCI診断一括実行ツール - 4つの自動化スクリプトの診断を一括実行

このツールは以下の4つの自動化スクリプトの実行結果に対して診断ツールを順次実行します：
  1. manager_cluster_setup      - Kubernetesクラスタ基盤構築
  2. manager_software_deploy    - DCI管理基盤ソフトウェアコンポーネント配備
  3. tenant_provisioning        - テナント論理インフラ準備とプロビジョニング
  4. tenant_deploy              - テナントサービス配備

各診断は最新のログディレクトリを自動選択して実行されます。
いずれかの診断が失敗しても、全ての診断を続行します。

Options:
  --script-root PATH    : 自動化スクリプトの親ディレクトリパス
                          (デフォルト: ../../)
                          指定されたパスの下に4つのスクリプトディレクトリが存在する必要があります
  --output-dir DIR      : 統合レポートの出力ディレクトリを指定
                          (デフォルト: ./diagnosis_reports)
  --help, -h            : このヘルプメッセージを表示

Environment Variables:
  DIAGNOSIS_LOG_LEVEL   : 各診断ツールのログレベル (DEBUG|INFO|WARNING|ERROR, デフォルト: INFO)
  DIAGNOSIS_TIMEOUT     : 各診断ツールの処理タイムアウト(秒, デフォルト: 600)

Examples:
  # 基本的な使用方法（最新ログを自動選択、デフォルトパス使用）
  ./overall_diagnosis.sh

  # カスタムパス指定
  ./overall_diagnosis.sh --script-root /path/to/scripts

  # 出力ディレクトリを指定
  ./overall_diagnosis.sh --output-dir /tmp/diagnosis_output

  # デバッグモードで実行
  DIAGNOSIS_LOG_LEVEL=DEBUG ./overall_diagnosis.sh

Exit Codes:
  0 - 全診断完了（全てのリソース状態に問題なし）
  1 - 診断ツール自体のエラーが1つ以上発生
  2 - リソース状態の重大な問題が1つ以上検出
  3 - リソース状態の警告が1つ以上検出

Output:
  diagnosis_reports/YYYYMMDD_HHMMSS_overall/
    ├── overall_summary.md           # 統合サマリーレポート（Markdown形式）
    └── overall_console.log          # 実行時コンソール出力（生ログ）

  個別の診断レポートは各スクリプト用のディレクトリに格納されます：
    diagnosis_reports/YYYYMMDD_HHMMSS_manager_cluster_setup/
    diagnosis_reports/YYYYMMDD_HHMMSS_manager_software_deploy/
    diagnosis_reports/YYYYMMDD_HHMMSS_tenant_provisioning/
    diagnosis_reports/YYYYMMDD_HHMMSS_tenant_deploy/

Note: 
  - 各自動化スクリプトが既に実行済みで、ansible/logs/ ディレクトリに
    ログが存在していることが前提です。
  - 診断対象のログが1つもない場合は、該当スクリプトの診断はスキップされます。

EOF
}

# 引数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        --script-root)
            if [ -z "$2" ]; then
                log_error "--script-root オプションには引数が必要です"
                exit 1
            fi
            SCRIPT_ROOT_ARG="$2"
            shift 2
            ;;
        --output-dir)
            if [ -z "$2" ]; then
                log_error "--output-dir オプションには引数が必要です"
                exit 1
            fi
            OUTPUT_BASE_DIR="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        -*)
            log_error "Unknown option: $1"
            echo "" >&2
            usage
            exit 1
            ;;
        *)
            log_error "Unknown argument: $1"
            echo "" >&2
            usage
            exit 1
            ;;
    esac
done

# 事前チェック
log_section "DCI診断一括実行ツール - 事前チェック"

# 1. diagnosis.sh の存在確認
if [ ! -f "$DIAGNOSIS_TOOL" ]; then
    log_error "診断ツールが見つかりません: $DIAGNOSIS_TOOL"
    exit 1
fi

if [ ! -x "$DIAGNOSIS_TOOL" ]; then
    log_error "診断ツールに実行権限がありません: $DIAGNOSIS_TOOL"
    exit 1
fi

log_success "診断ツールが見つかりました: $DIAGNOSIS_TOOL"

# 2. 4つのスクリプトディレクトリと ansible/logs/ の存在確認
WORK_DIR="$(cd "${SCRIPT_ROOT_ARG}" 2>/dev/null && pwd)" || {
    log_error "親ディレクトリが見つかりません: ${SCRIPT_ROOT_ARG}"
    log_error "--script-root オプションで正しいパスを指定してください。"
    exit 1
}
MISSING_SCRIPTS=()
MISSING_LOGS=()

for script_name in "${SCRIPTS[@]}"; do
    script_path="${WORK_DIR}/${script_name}"
    logs_path="${script_path}/ansible/logs"
    
    if [ ! -d "$script_path" ]; then
        MISSING_SCRIPTS+=("$script_name")
    elif [ ! -d "$logs_path" ]; then
        MISSING_LOGS+=("$script_name")
    fi
done

# エラー報告（エラーがあっても全て報告してから終了）
if [ ${#MISSING_SCRIPTS[@]} -gt 0 ]; then
    log_error "以下のスクリプトディレクトリが見つかりません:"
    for script_name in "${MISSING_SCRIPTS[@]}"; do
        echo "  - ${WORK_DIR}/${script_name}"
    done
    exit 1
fi

if [ ${#MISSING_LOGS[@]} -gt 0 ]; then
    log_warning "以下のスクリプトの ansible/logs/ ディレクトリが見つかりません:"
    for script_name in "${MISSING_LOGS[@]}"; do
        echo "  - ${WORK_DIR}/${script_name}/ansible/logs"
    done
    log_warning "該当スクリプトの診断はスキップされます。"
fi

log_success "事前チェック完了"

# 統合レポートディレクトリの事前作成
OVERALL_OUTPUT_DIR="${OUTPUT_BASE_DIR}/${TIMESTAMP}_overall"
mkdir -p "$OVERALL_OUTPUT_DIR"

log_info "統合レポート出力先: $OVERALL_OUTPUT_DIR"

# コンソール出力をリアルタイムでログファイルに保存
OVERALL_CONSOLE_LOG="${OVERALL_OUTPUT_DIR}/overall_console.log"
exec > >(tee -a "$OVERALL_CONSOLE_LOG") 2>&1

# 診断実行ループ
log_section "診断実行 - 4つのスクリプトを順次処理"

TOTAL_SCRIPTS=${#SCRIPTS[@]}
CURRENT_INDEX=0

for script_name in "${SCRIPTS[@]}"; do
    CURRENT_INDEX=$((CURRENT_INDEX + 1))
    
    log_section "[$CURRENT_INDEX/$TOTAL_SCRIPTS] ${script_name} の診断実行"
    
    script_root="${WORK_DIR}/${script_name}"
    logs_dir="${script_root}/ansible/logs"
    
    # ログディレクトリが存在しない場合はスキップ
    if [ ! -d "$logs_dir" ]; then
        log_warning "${script_name}: ログディレクトリが存在しないためスキップします"
        DIAGNOSIS_EXIT_CODES["$script_name"]="SKIP"
        DIAGNOSIS_REPORT_PATHS["$script_name"]="N/A"
        DIAGNOSIS_LOG_DIRS["$script_name"]="N/A"
        continue
    fi
    
    # ログディレクトリが空の場合はスキップ
    log_count=$(find "$logs_dir" -maxdepth 1 -type d -name "*_${script_name}" | wc -l)
    if [ "$log_count" -eq 0 ]; then
        log_warning "${script_name}: ログファイルが見つからないためスキップします"
        DIAGNOSIS_EXIT_CODES["$script_name"]="SKIP"
        DIAGNOSIS_REPORT_PATHS["$script_name"]="N/A"
        DIAGNOSIS_LOG_DIRS["$script_name"]="N/A"
        continue
    fi
    
    # 診断ツール実行
    log_info "${script_name}: 診断ツールを実行中..."
    
    # 診断ツールの出力をキャプチャしながら実行
    # set +e で一時的にエラー終了を無効化
    set +e
    diagnosis_output=$("$DIAGNOSIS_TOOL" "$script_name" --script-root "$WORK_DIR" --output-dir "$OVERALL_OUTPUT_DIR" 2>&1)
    exit_code=$?
    set -e
    
    # 終了コードを記録
    DIAGNOSIS_EXIT_CODES["$script_name"]=$exit_code
    
    # レポートパスとログディレクトリを抽出
    # diagnosis.sh の出力から診断レポートディレクトリを抽出
    report_dir=$(echo "$diagnosis_output" | grep -oP "診断レポート出力先|Output Directory" | head -1)
    if [ -n "$report_dir" ]; then
        # 実際のパスを抽出（診断ツールの出力フォーマットに依存）
        report_path=$(echo "$diagnosis_output" | grep -oP "${OVERALL_OUTPUT_DIR}/[0-9_]+${script_name}" | head -1)
        if [ -n "$report_path" ]; then
            DIAGNOSIS_REPORT_PATHS["$script_name"]="$report_path"
        else
            # 最新のレポートディレクトリを検索（OVERALL_OUTPUT_DIR配下）
            latest_report=$(find "$OVERALL_OUTPUT_DIR" -maxdepth 1 -type d -name "*_${script_name}" | sort -r | head -1)
            DIAGNOSIS_REPORT_PATHS["$script_name"]="${latest_report:-N/A}"
        fi
    else
        # 最新のレポートディレクトリを検索（OVERALL_OUTPUT_DIR配下）
        latest_report=$(find "$OVERALL_OUTPUT_DIR" -maxdepth 1 -type d -name "*_${script_name}" | sort -r | head -1)
        DIAGNOSIS_REPORT_PATHS["$script_name"]="${latest_report:-N/A}"
    fi
    
    # ログディレクトリを抽出
    log_dir_line=$(echo "$diagnosis_output" | grep -oP "Log Directory\s*:\s*\K.*" | head -1)
    if [ -n "$log_dir_line" ]; then
        DIAGNOSIS_LOG_DIRS["$script_name"]="$log_dir_line"
    else
        # 最新のログディレクトリを検索
        latest_log=$(find "$logs_dir" -maxdepth 1 -type d -name "*_${script_name}" | sort -r | head -1)
        DIAGNOSIS_LOG_DIRS["$script_name"]="${latest_log:-N/A}"
    fi
    
    # 診断結果を表示
    case $exit_code in
        0)
            log_success "${script_name}: 診断完了 - リソース状態に問題なし"
            ;;
        1)
            log_error "${script_name}: 診断ツールエラー (終了コード: $exit_code)"
            ;;
        2)
            log_error "${script_name}: 重大な問題を検出 (終了コード: $exit_code)"
            ;;
        3)
            log_warning "${script_name}: 警告を検出 (終了コード: $exit_code)"
            ;;
        *)
            log_error "${script_name}: 不明な終了コード: $exit_code"
            ;;
    esac
    
    # 詳細ログを表示（オプション: 最後の数行のみ）
    # echo "$diagnosis_output" | tail -10
done

# 統合サマリーレポート生成
log_section "統合サマリーレポート生成"

OVERALL_SUMMARY="${OVERALL_OUTPUT_DIR}/overall_summary.md"

# 全体ステータスの決定
OVERALL_STATUS="SUCCESS"
OVERALL_EXIT_CODE=0

for script_name in "${SCRIPTS[@]}"; do
    exit_code="${DIAGNOSIS_EXIT_CODES[$script_name]}"
    
    if [ "$exit_code" = "SKIP" ]; then
        continue
    fi
    
    # 終了コードの優先順位: 2(重大) > 3(警告) > 1(ツールエラー) > 0(成功)
    if [ "$exit_code" -eq 2 ]; then
        OVERALL_STATUS="CRITICAL_ISSUES"
        if [ "$OVERALL_EXIT_CODE" -lt 2 ]; then
            OVERALL_EXIT_CODE=2
        fi
    elif [ "$exit_code" -eq 3 ]; then
        if [ "$OVERALL_STATUS" != "CRITICAL_ISSUES" ]; then
            OVERALL_STATUS="WARNINGS"
        fi
        if [ "$OVERALL_EXIT_CODE" -lt 3 ] && [ "$OVERALL_EXIT_CODE" -ne 2 ]; then
            OVERALL_EXIT_CODE=3
        fi
    elif [ "$exit_code" -eq 1 ]; then
        if [ "$OVERALL_STATUS" != "CRITICAL_ISSUES" ] && [ "$OVERALL_STATUS" != "WARNINGS" ]; then
            OVERALL_STATUS="TOOL_ERROR"
        fi
        if [ "$OVERALL_EXIT_CODE" -eq 0 ]; then
            OVERALL_EXIT_CODE=1
        fi
    fi
done

# Markdownレポート生成
END_TIME=$(date +%s)
ELAPSED_TIME=$((END_TIME - START_TIME))
ELAPSED_MIN=$((ELAPSED_TIME / 60))
ELAPSED_SEC=$((ELAPSED_TIME % 60))

cat > "$OVERALL_SUMMARY" << EOF
# DCI診断一括実行レポート

**実行日時:** $(date '+%Y年%m月%d日 %H:%M:%S')  
**総実行時間:** ${ELAPSED_MIN}分${ELAPSED_SEC}秒

---

## 全体ステータス

EOF

case $OVERALL_STATUS in
    SUCCESS)
        echo "✅ **全診断成功** - 全てのリソース状態に問題はありません" >> "$OVERALL_SUMMARY"
        ;;
    WARNINGS)
        echo "⚠️ **警告あり** - 一部のリソースに警告が検出されました" >> "$OVERALL_SUMMARY"
        ;;
    CRITICAL_ISSUES)
        echo "❌ **重大な問題あり** - 一部のリソースに重大な問題が検出されました" >> "$OVERALL_SUMMARY"
        ;;
    TOOL_ERROR)
        echo "🔧 **診断ツールエラー** - 一部の診断でツールエラーが発生しました" >> "$OVERALL_SUMMARY"
        ;;
esac

cat >> "$OVERALL_SUMMARY" << EOF

**全体終了コード:** $OVERALL_EXIT_CODE

---

## 各スクリプトの診断結果

| # | スクリプト名 | ステータス | 終了コード | レポート | ログディレクトリ |
|---|-------------|-----------|-----------|---------|----------------|
EOF

INDEX=1
for script_name in "${SCRIPTS[@]}"; do
    exit_code="${DIAGNOSIS_EXIT_CODES[$script_name]}"
    report_path="${DIAGNOSIS_REPORT_PATHS[$script_name]}"
    log_dir="${DIAGNOSIS_LOG_DIRS[$script_name]}"
    
    # ステータス表示
    if [ "$exit_code" = "SKIP" ]; then
        status="⏭️ スキップ"
        exit_code_display="N/A"
    else
        case $exit_code in
            0) status="✅ 成功" ;;
            1) status="🔧 ツールエラー" ;;
            2) status="❌ 重大な問題" ;;
            3) status="⚠️ 警告" ;;
            *) status="❓ 不明" ;;
        esac
        exit_code_display="$exit_code"
    fi
    
    # レポートリンク
    if [ "$report_path" != "N/A" ] && [ -d "$report_path" ]; then
        report_basename=$(basename "$report_path")
        report_link="[📄 レポート](./${report_basename}/summary.md)"
    else
        report_link="N/A"
    fi
    
    # ログディレクトリ表示（パスが長い場合は省略）
    if [ "$log_dir" != "N/A" ]; then
        log_dir_basename=$(basename "$log_dir")
        log_dir_display="\`${log_dir_basename}\`"
    else
        log_dir_display="N/A"
    fi
    
    echo "| $INDEX | \`$script_name\` | $status | $exit_code_display | $report_link | $log_dir_display |" >> "$OVERALL_SUMMARY"
    INDEX=$((INDEX + 1))
done

cat >> "$OVERALL_SUMMARY" << EOF

---

## 診断の詳細

各スクリプトの詳細な診断結果は、上記の「レポート」リンクから確認できます。

### レポートファイル構成

各診断レポートディレクトリには以下のファイルが含まれます：

- \`summary.md\` - Markdown形式の診断サマリーレポート
- \`diagnosis_console.log\` - 診断ツールのコンソール出力ログ
- \`k8s_resources/\` - 収集したKubernetesリソース情報（JSON形式）
- \`detailed_info/\` - 異常が検出された場合の詳細情報（ログ、describe、イベント等）

### 終了コードの意味

- **0**: 診断完了（リソース状態の問題なし）
- **1**: 診断ツール自体のエラー
- **2**: リソース状態の重大な問題を検出
- **3**: リソース状態の警告を検出

---

## 推奨アクション

EOF

if [ "$OVERALL_STATUS" = "SUCCESS" ]; then
    cat >> "$OVERALL_SUMMARY" << EOF
全ての診断が正常に完了し、リソース状態に問題は検出されませんでした。
DCI構築自動化スクリプトは正常に実行されています。
EOF
elif [ "$OVERALL_STATUS" = "WARNINGS" ]; then
    cat >> "$OVERALL_SUMMARY" << EOF
一部のリソースに警告が検出されました。

1. 警告が検出されたスクリプトの個別診断レポートを確認してください。
2. 警告の内容を確認し、必要に応じて対処してください。
3. 警告が想定内の場合は、そのまま運用を継続できます。
EOF
elif [ "$OVERALL_STATUS" = "CRITICAL_ISSUES" ]; then
    cat >> "$OVERALL_SUMMARY" << EOF
重大な問題が検出されました。

1. 問題が検出されたスクリプトの個別診断レポートを確認してください。
2. 詳細情報（Pod ログ、describe、イベント等）を確認し、根本原因を特定してください。
3. 問題を解決した後、該当スクリプトを再実行してください。
4. 再実行後、診断ツールを再度実行して問題が解消されたことを確認してください。
EOF
else
    cat >> "$OVERALL_SUMMARY" << EOF
診断ツールの実行でエラーが発生しました。

1. エラーが発生したスクリプトの個別診断レポートを確認してください。
2. 診断ツールのログ（diagnosis_console.log）を確認し、エラーの原因を特定してください。
3. 必要に応じて、診断ツールの前提条件を確認してください（Python環境、kubectl、Ansible等）。
EOF
fi

cat >> "$OVERALL_SUMMARY" << EOF

---

## 関連ドキュメント

- [診断ツールREADME](../../README.md) - 診断ツールの詳細な使用方法
- [manager_cluster_setup/README.md](../../../../manager_cluster_setup/README.md) - Kubernetesクラスタ構築
- [manager_software_deploy/README.md](../../../../manager_software_deploy/README.md) - ソフトウェアコンポーネント配備
- [tenant_provisioning/README.md](../../../../tenant_provisioning/README.md) - テナント論理インフラ準備
- [tenant_deploy/README.md](../../../../tenant_deploy/README.md) - テナントサービス配備

---

**レポート生成日時:** $(date '+%Y年%m月%d日 %H:%M:%S')
EOF

log_success "統合サマリーレポートを生成しました: $OVERALL_SUMMARY"

# 最終結果表示
log_section "診断完了"

echo ""
echo "========================================="
echo "診断結果サマリー"
echo "========================================="
echo ""

for script_name in "${SCRIPTS[@]}"; do
    exit_code="${DIAGNOSIS_EXIT_CODES[$script_name]}"
    
    printf "  %-30s : " "$script_name"
    
    if [ "$exit_code" = "SKIP" ]; then
        echo "SKIP"
    else
        case $exit_code in
            0) echo "SUCCESS (exit code: $exit_code)" ;;
            1) echo "TOOL ERROR (exit code: $exit_code)" ;;
            2) echo "CRITICAL ISSUES (exit code: $exit_code)" ;;
            3) echo "WARNINGS (exit code: $exit_code)" ;;
            *) echo "UNKNOWN (exit code: $exit_code)" ;;
        esac
    fi
done

echo ""
echo "========================================="
echo ""

case $OVERALL_STATUS in
    SUCCESS)
        log_success "全診断成功 - 全てのリソース状態に問題はありません"
        ;;
    WARNINGS)
        log_warning "警告あり - 一部のリソースに警告が検出されました"
        ;;
    CRITICAL_ISSUES)
        log_error "重大な問題あり - 一部のリソースに重大な問題が検出されました"
        ;;
    TOOL_ERROR)
        log_error "診断ツールエラー - 一部の診断でツールエラーが発生しました"
        ;;
esac

echo ""
log_info "統合レポート: $OVERALL_SUMMARY"
log_info "コンソールログ: $OVERALL_CONSOLE_LOG"
echo ""

# 終了
exit $OVERALL_EXIT_CODE
