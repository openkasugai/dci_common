#!/bin/bash
# `set -e` は使用しない（診断ツールの終了コードを適切に処理するため）

# DCI構築診断ツール - メインエントリポイント
# Usage: ./diagnosis.sh <SCRIPT_NAME> [OPTIONS]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 共通ライブラリの読み込み
source "${SCRIPT_DIR}/common/diagnosis_common.sh"

PYTHON_ENGINE="${SCRIPT_DIR}/python/diagnosis_engine.py"

# Usage表示関数
show_usage() {
    cat << 'EOF'
Usage: ./diagnosis.sh <SCRIPT_NAME> [OPTIONS]

DCI構築診断ツール - AnsibleログとKubernetesリソースを解析するツール

Arguments:
  SCRIPT_NAME                 : 自動化スクリプト名（必須）
                                (例: manager_cluster_setup, manager_software_deploy,
                                     tenant_provisioning, tenant_deploy)

Options:
  --script-root PATH          : 自動化スクリプトの親ディレクトリパス
                                (デフォルト: ../../)
                                指定されたパスの下に <SCRIPT_NAME>/ が存在する必要があります
  --log-dir-name NAME         : 解析するログディレクトリ名（またはタイムスタンプ部分）
                                省略すると最新のログディレクトリを使用します
  --output-dir DIR            : 診断レポートの出力ディレクトリを指定
                                (デフォルト: ./diagnosis_reports)
  --help, -h                  : このヘルプメッセージを表示

Environment Variables:
  DIAGNOSIS_LOG_LEVEL         : ログレベル (DEBUG|INFO|WARNING|ERROR, デフォルト: INFO)
  DIAGNOSIS_TIMEOUT           : 処理タイムアウト(秒, デフォルト: 900)
  K8S_COLLECTOR_TIMEOUT       : Kubernetesリソース収集タイムアウト(秒, デフォルト: 600)

Examples:
  # 最新のログを解析（デフォルトパス使用）
  ./diagnosis.sh manager_cluster_setup

  # 特定のログディレクトリを解析
  ./diagnosis.sh manager_cluster_setup --log-dir-name 20260408_120000

  # カスタムパス指定
  ./diagnosis.sh manager_software_deploy --script-root /path/to/scripts

  # 出力ディレクトリを指定
  ./diagnosis.sh tenant_provisioning --output-dir /tmp/diagnosis_output

  # デバッグモードで実行
  DIAGNOSIS_LOG_LEVEL=DEBUG ./diagnosis.sh manager_cluster_setup

Exit Codes:
  0 - 診断完了（リソース状態の問題なし）
  1 - 診断ツール自体のエラー
  2 - リソース状態の重大な問題を検出
  3 - リソース状態の警告を検出

Note: ログエラーは終了コードに影響しません。
      診断結果の詳細はレポートで確認してください。

Required Directory Structure:
  <SCRIPT_ROOT>/
    <SCRIPT_NAME>/
      ansible/
        inventory/hosts
        logs/
          YYYYMMDD_HHMMSS_<SCRIPT_NAME>/
            *.log
EOF
}

# 引数チェック
if [ $# -lt 1 ]; then
    echo "Error: SCRIPT_NAME is required" >&2
    echo "" >&2
    show_usage
    exit 1
fi

# --helpオプションの処理
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    show_usage
    exit 0
fi

# 第1引数: SCRIPT_NAME（必須）
SCRIPT_NAME="$1"
shift

# デフォルト設定（共通ライブラリから提供される値を使用）
SCRIPT_ROOT_ARG="${DIAGNOSIS_SCRIPT_ROOT_DEFAULT}"
OUTPUT_BASE_DIR="${DIAGNOSIS_OUTPUT_BASE_DIR_DEFAULT}"
LOG_DIR_NAME=""

# オプション解析
while [[ $# -gt 0 ]]; do
    case $1 in
        --script-root)
            if [ -z "$2" ]; then
                echo "Error: --script-root requires an argument" >&2
                exit 1
            fi
            SCRIPT_ROOT_ARG="$2"
            shift 2
            ;;
        --log-dir-name)
            if [ -z "$2" ]; then
                echo "Error: --log-dir-name requires an argument" >&2
                exit 1
            fi
            LOG_DIR_NAME="$2"
            shift 2
            ;;
        --output-dir)
            if [ -z "$2" ]; then
                echo "Error: --output-dir requires an argument" >&2
                exit 1
            fi
            OUTPUT_BASE_DIR="$2"
            shift 2
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        -*)
            echo "Error: Unknown option: $1" >&2
            echo "" >&2
            show_usage
            exit 1
            ;;
        *)
            echo "Error: Unknown argument: $1" >&2
            echo "" >&2
            show_usage
            exit 1
            ;;
    esac
done

# パス構築: 親ディレクトリ + スクリプト名
SCRIPT_ROOT="$(cd "${SCRIPT_ROOT_ARG}/${SCRIPT_NAME}" 2>/dev/null && pwd)" || {
    echo "[ERROR] スクリプトディレクトリが見つかりません: ${SCRIPT_ROOT_ARG}/${SCRIPT_NAME}" >&2
    echo "" >&2
    echo "指定された設定:" >&2
    echo "  親ディレクトリ: ${SCRIPT_ROOT_ARG}" >&2
    echo "  スクリプト名  : ${SCRIPT_NAME}" >&2
    echo "  期待されるパス: ${SCRIPT_ROOT_ARG}/${SCRIPT_NAME}" >&2
    echo "" >&2
    echo "--script-root オプションで親ディレクトリを指定してください。" >&2
    exit 1
}

# スクリプトルートから情報を自動推測
INVENTORY_PATH="${SCRIPT_ROOT}/ansible/inventory/hosts"
ANSIBLE_LOGS_DIR="${SCRIPT_ROOT}/ansible/logs"

# 入力検証
if [ ! -f "$INVENTORY_PATH" ]; then
    echo "[ERROR] Ansible inventory ファイルが見つかりません: $INVENTORY_PATH" >&2
    echo "" >&2
    echo "期待される場所: ${SCRIPT_ROOT}/ansible/inventory/hosts" >&2
    echo "" >&2
    echo "必須ディレクトリ構造:" >&2
    echo "  ${SCRIPT_ROOT_ARG}/${SCRIPT_NAME}/" >&2
    echo "    ansible/" >&2
    echo "      inventory/" >&2
    echo "        hosts  (← このファイルが必要)" >&2
    echo "      logs/" >&2
    exit 1
fi

if [ ! -d "$ANSIBLE_LOGS_DIR" ]; then
    echo "[ERROR] Ansible ログディレクトリが見つかりません: $ANSIBLE_LOGS_DIR" >&2
    echo "" >&2
    echo "期待される場所: ${SCRIPT_ROOT}/ansible/logs" >&2
    exit 1
fi

# ログディレクトリの決定
if [ -n "$LOG_DIR_NAME" ]; then
    # ディレクトリ名が指定されている場合: 該当するディレクトリを検索
    LOG_DIR=$(find "$ANSIBLE_LOGS_DIR" -maxdepth 1 -type d -name "*${LOG_DIR_NAME}*" | head -1)
    if [ -z "$LOG_DIR" ]; then
        echo "[ERROR] '$LOG_DIR_NAME' に一致するログディレクトリが $ANSIBLE_LOGS_DIR 内に見つかりません。" >&2
        exit 1
    fi
else
    # ログディレクトリ名が指定されていない場合: 最新のログディレクトリを自動選択
    LOG_DIR=$(find "$ANSIBLE_LOGS_DIR" -maxdepth 1 -type d -name "*_${SCRIPT_NAME}" | sort -r | head -1)
    if [ -z "$LOG_DIR" ]; then
        echo "[ERROR] $ANSIBLE_LOGS_DIR 内にログディレクトリが見つかりません。" >&2
        echo "        期待されるパターン: YYYYMMDD_HHMMSS_${SCRIPT_NAME}" >&2
        exit 1
    fi
    echo "[INFO] 最新のログを自動選択しました: $(basename "$LOG_DIR")"
fi

# Python仮想環境のアクティベート
VENV_DIR="${SCRIPT_DIR}/venv"
if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
    echo "[INFO] Python仮想環境をアクティベートします: $VENV_DIR"
    source "$VENV_DIR/bin/activate"
else
    echo "[WARNING] 仮想環境が $VENV_DIR に見つかりません。" >&2
    echo "          システムPythonを使用します。一部の依存関係が不足している可能性があります。" >&2
fi

# Python実行環境チェック
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 がインストールされていません。" >&2
    exit 1
fi

# Python依存関係チェック（簡易版）
python3 -c "import yaml, json" 2>/dev/null || {
    echo "[ERROR] 必要なPythonパッケージがインストールされていません。" >&2
    echo "次のコマンドを実行してください: pip install -r ${SCRIPT_DIR}/requirements.txt" >&2
    exit 1
}

# Ansible実行可能チェック
command -v ansible &> /dev/null || {
    echo "[ERROR] ansible コマンドが見つかりません。Ansibleをインストールしてください。" >&2
    exit 1
}

# 診断レポート出力ディレクトリ作成
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_DIR="${OUTPUT_BASE_DIR}/${TIMESTAMP}_${SCRIPT_NAME}"
mkdir -p "$OUTPUT_DIR"

# コンソールログの開始（この時点以降の全出力をログファイルとコンソールに出力）
CONSOLE_LOG="${OUTPUT_DIR}/diagnosis_console.log"
exec > >(tee "$CONSOLE_LOG") 2>&1

echo "=============================================="
echo "DCI診断ツール"
echo "=============================================="
echo "スクリプト名        : $SCRIPT_NAME"
echo "ログディレクトリ    : $LOG_DIR"
echo "インベントリパス    : $INVENTORY_PATH"
echo "出力ディレクトリ    : $OUTPUT_DIR"
echo "ログレベル          : $DIAGNOSIS_LOG_LEVEL"
echo "タイムアウト        : ${DIAGNOSIS_TIMEOUT}秒"
echo "=============================================="
echo ""

# Python診断エンジンを実行
python3 "$PYTHON_ENGINE" \
    --script-name "$SCRIPT_NAME" \
    --log-dir "$LOG_DIR" \
    --inventory-path "$INVENTORY_PATH" \
    --output-dir "$OUTPUT_DIR" \
    --log-level "$DIAGNOSIS_LOG_LEVEL" \
    --timeout "$DIAGNOSIS_TIMEOUT"

EXIT_CODE=$?

# 終了コードをログ出力（必要に応じてコメントアウト）
#echo "Python script exit code: $EXIT_CODE" >&2

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "=============================================="
    echo "✅ 診断が正常に完了しました - リソース状態の問題は見つかりませんでした"
    echo "=============================================="
    echo "結果:"
    echo "  - サマリーレポート : ${OUTPUT_DIR}/summary.md"
    echo "  - コンソールログ    : ${OUTPUT_DIR}/diagnosis_console.log"
    echo "=============================================="
elif [ $EXIT_CODE -eq 2 ]; then
    echo ""
    echo "=============================================="
    echo "⚠️ 診断完了 - リソース状態の重大な問題が検出されました"
    echo "=============================================="
    echo "結果:"
    echo "  - サマリーレポート : ${OUTPUT_DIR}/summary.md"
    echo "  - コンソールログ    : ${OUTPUT_DIR}/diagnosis_console.log"
    echo ""
    echo "リソース状態の重大な問題が検出されました。"
    echo "詳細はサマリーレポートをご確認ください。"
    echo "=============================================="
elif [ $EXIT_CODE -eq 3 ]; then
    echo ""
    echo "=============================================="
    echo "⚠️ 診断完了 - リソース状態の警告が検出されました"
    echo "=============================================="
    echo "結果:"
    echo "  - サマリーレポート : ${OUTPUT_DIR}/summary.md"
    echo "  - コンソールログ    : ${OUTPUT_DIR}/diagnosis_console.log"
    echo ""
    echo "リソース状態の警告が検出されました。"
    echo "詳細はサマリーレポートをご確認ください。"
    echo "=============================================="
elif [ $EXIT_CODE -eq 1 ]; then
    echo ""
    echo "=============================================="
    echo "❌ 診断プロセスが失敗しました"
    echo "=============================================="
    echo "エラー: 診断ツール自体がエラーに遭遇しました" >&2
    echo ""
    echo "出力結果:"
    echo "  - コンソールログ: ${OUTPUT_DIR}/diagnosis_console.log"
    echo ""
    echo "考えられる原因:"
    echo "  - Control Plane ノードへの SSH 接続ができない"
    echo "  - Kubernetes クラスターにアクセスできない"
    echo "  - クラスターリソースへのアクセス権限が不足"
    echo "  - ネットワーク接続の問題"
    echo "  - 必須Pythonパッケージがインストールされていない"
    echo "  - Ansibleがインストールされていない"
    echo ""
    echo "推奨される対応:"
    echo "  1. 前提条件チェック:"
    echo "     - Ansible のインストール確認: which ansible-playbook"
    echo "     - Pythonパッケージ: pip install -r ${SCRIPT_DIR}/python/requirements.txt"
    echo ""
    echo "  2. Control PlaneノードへのAnsible接続確認:"
    echo "     ansible -i ${INVENTORY_PATH} dci_mgmt_k8s_control_plane -m ping"
    echo ""
    echo "  3. 詳細エラーログを確認:"
    echo "     - ローカル: ${OUTPUT_DIR}/diagnosis_console.log"
    echo "     - リモート (利用可能な場合):"
    echo "       ssh <control-plane-node> cat /tmp/k8s_diagnosis/errors.log"
    echo ""
    echo "  4. デバッグモードで再実行:"
    echo "     DIAGNOSIS_LOG_LEVEL=DEBUG $0 $SCRIPT_NAME"
    if [ "$SCRIPT_ROOT_ARG" != "${DIAGNOSIS_SCRIPT_ROOT_DEFAULT}" ]; then
        echo "     (--script-root ${SCRIPT_ROOT_ARG} を忘れずに指定)"
    fi
    echo "=============================================="
else
    echo ""
    echo "=============================================="
    echo "予期せぬエラーで診断が完了しました (終了コード: $EXIT_CODE)"
    echo "=============================================="
    echo "${OUTPUT_DIR}内の出力をご確認ください"
    echo "=============================================="
fi

exit $EXIT_CODE
