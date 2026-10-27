#!/bin/bash
# CorefileのhostsブロックにPrometheusエントリを冪等的に追記する
#
# 使い方:
#   echo "$COREFILE" | ./update_corefile_hosts.sh <TARGET_HOST> <GATEWAY_VIP>
#
# 出力: 変更後のCorefileを標準出力（ログ・メッセージは標準エラー）
#
# 終了コード:
#   0: エントリを挿入した（変更あり）
#   1: エントリが既に存在した（変更なし・スキップ）
#   2: エラー（引数不足、ファイル未存在、Corefile空など）

set -uo pipefail

TARGET_HOST="$1"
GATEWAY_VIP="$2"
NEW_ENTRY="${GATEWAY_VIP} ${TARGET_HOST}"
COREFILE=$(cat)

if [ -z "$COREFILE" ]; then
  echo "ERROR: Corefileが空です" >&2
  exit 2
fi

# 冪等性チェック: エントリが既に存在する場合はスキップ
if echo "$COREFILE" | grep -qF "${TARGET_HOST}"; then
  echo "[SKIP] エントリは既に存在します: ${TARGET_HOST}" >&2
  exit 1
fi

# hostsブロック内の "fallthrough"（引数なし）の行の直前に新しいエントリを挿入
# ※ "fallthrough in-addr.arpa ip6.arpa" (kubernetes ブロック) とは区別する
#    → /^[[:space:]]*fallthrough[[:space:]]*$/ で引数なしの行のみマッチ
# 最初の1回だけ挿入（inserted フラグで制御）
output=$(echo "$COREFILE" | awk -v entry="$NEW_ENTRY" '
BEGIN { in_hosts=0; inserted=0 }
!inserted && /[[:space:]]+hosts[[:space:]]*\{/ { in_hosts=1 }
in_hosts && !inserted && /^[[:space:]]*fallthrough[[:space:]]*$/ {
  match($0, /^[[:space:]]*/); indent=substr($0, 1, RLENGTH)
  print indent entry
  inserted=1
  in_hosts=0
}
{ print }
')

if [ $? -ne 0 ]; then
  echo "ERROR: awk処理に失敗しました" >&2
  exit 2
fi

echo "$output"
echo "[OK] エントリを追加しました: ${NEW_ENTRY}" >&2
exit 0
