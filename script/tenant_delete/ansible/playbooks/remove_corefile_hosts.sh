#!/bin/bash
# CorefileのhostsブロックからPrometheus/Lokiエントリを冪等的に削除する
#
# 使い方:
#   echo "$COREFILE" | ./remove_corefile_hosts.sh <TARGET_HOST>
#
# 出力: 変更後のCorefileを標準出力（ログ・メッセージは標準エラー）
#       ※スキップ時も現在のCorefile内容をそのまま出力する（後続処理に使用）
#
# 終了コード:
#   0: エントリを削除した（変更あり）
#   1: エントリが存在しなかった（変更なし・スキップ）
#   2: エラー（引数不足、Corefile空など）

set -uo pipefail

if [ $# -lt 1 ]; then
  echo "ERROR: 引数が不足しています。使い方: echo \"\$COREFILE\" | $0 <TARGET_HOST>" >&2
  exit 2
fi

TARGET_HOST="$1"
COREFILE=$(cat)

if [ -z "$COREFILE" ]; then
  echo "ERROR: Corefileが空です" >&2
  exit 2
fi

# 冪等性チェック: エントリが存在しない場合はスキップ
if ! echo "$COREFILE" | grep -qF "${TARGET_HOST}"; then
  echo "[SKIP] エントリは存在しません: ${TARGET_HOST}" >&2
  # スキップでも現在のCorefileをそのまま出力（後続処理に使用）
  echo "$COREFILE"
  exit 1
fi

# hostsブロック内のTARGET_HOSTを含む行を削除
output=$(echo "$COREFILE" | awk -v host="$TARGET_HOST" '
{
  if (index($0, host) > 0) {
    next
  }
  print
}')

if [ $? -ne 0 ]; then
  echo "ERROR: awk処理に失敗しました" >&2
  exit 2
fi

echo "$output"
echo "[OK] エントリを削除しました: ${TARGET_HOST}" >&2
exit 0
