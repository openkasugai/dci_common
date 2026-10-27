#!/usr/bin/env python3
"""
product-mappings-configmap.yamlのmappings.jsonに追加プロダクト情報をマージするスクリプト
既存のproduct情報を保持し、重複しない追加product情報のみをマージします。
"""

import sys
import json
import re
from typing import List, Dict, Any


def load_configmap_file(file_path: str) -> tuple[str, Dict[str, Any]]:
    """
    ConfigMapファイルを読み込み、mappings.jsonをJSON解析して返す
    
    Returns:
        tuple: (元ファイル内容文字列, mappings.jsonのdict)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # data.mappings.json部分を抽出
    # "mappings.json: |" の後ろから次のキーまたはファイル末尾までを抽出
    pattern = r'mappings\.json:\s*\|\s*\n((?:[ ]{4,}.*\n?)*)'
    match = re.search(pattern, content)
    
    if not match:
        raise ValueError("mappings.json セクションが見つかりません")
    
    # インデントを除去してJSON文字列を取得
    json_lines = match.group(1)
    json_str = re.sub(r'^[ ]{4}', '', json_lines, flags=re.MULTILINE)
    
    try:
        mappings_data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"mappings.json のJSON解析に失敗しました: {e}")
    
    return content, mappings_data


def get_product_key(product: Dict[str, Any], category: str) -> str:
    """
    product情報から一意キーを生成（重複チェック用）
    vendor、product_name、version、osの全てが一致する場合に重複と判断
    
    Args:
        product: product情報のdict
        category: カテゴリ名 (nw_products, server_products, etc.)
    
    Returns:
        一意キー文字列
    """
    vendor = product.get('vendor', '').lower()
    product_name = product.get('product_name', '').lower()
    version = product.get('version', '').lower()
    os_name = product.get('os', '').lower()
    
    # すべてのフィールドを使用して一意キーを生成
    return f"{vendor}|{product_name}|{version}|{os_name}"


def merge_products(existing: List[Dict[str, Any]], 
                   additional: List[Dict[str, Any]], 
                   category: str) -> tuple[List[Dict[str, Any]], int, int]:
    """
    既存product情報に追加product情報をマージ
    
    Args:
        existing: 既存のproductリスト
        additional: 追加するproductリスト
        category: カテゴリ名
    
    Returns:
        tuple: (マージ後のリスト, 追加数, スキップ数)
    """
    # 既存productのキーセットを作成
    existing_keys = {get_product_key(p, category) for p in existing}
    
    added_count = 0
    skipped_count = 0
    result = list(existing)
    
    for product in additional:
        key = get_product_key(product, category)
        if key in existing_keys:
            # 既存に同じproductが存在する場合はスキップ
            skipped_count += 1
            print(f"  [SKIP] {category}: {product.get('vendor', '')} {product.get('product_name', '')} (既存に存在)", 
                  file=sys.stderr)
        else:
            # 新規追加
            result.append(product)
            existing_keys.add(key)
            added_count += 1
            print(f"  [ADD]  {category}: {product.get('vendor', '')} {product.get('product_name', '')} {product.get('version', product.get('os', ''))}")
    
    return result, added_count, skipped_count


def save_configmap_file(file_path: str, original_content: str, 
                        updated_mappings: Dict[str, Any]) -> None:
    """
    更新後のmappings.jsonをConfigMapファイルに書き込む
    
    Args:
        file_path: 保存先ファイルパス
        original_content: 元のファイル内容
        updated_mappings: 更新後のmappingsデータ
    """
    # JSON文字列を生成（整形、インデント2スペース）
    json_str = json.dumps(updated_mappings, indent=2, ensure_ascii=False)
    
    # 各行に4スペースのインデントを追加（ConfigMap内のインデントに合わせる）
    indented_json = '\n'.join('    ' + line if line.strip() else '' 
                               for line in json_str.split('\n'))
    
    # 元のファイル内容のmappings.json部分を置換
    pattern = r'(mappings\.json:\s*\|\s*\n)((?:[ ]{4,}.*\n?)*)'
    
    def replacement(match):
        return match.group(1) + indented_json + '\n'
    
    updated_content = re.sub(pattern, replacement, original_content)
    
    # ファイルに書き込み
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)


def main():
    if len(sys.argv) != 6:
        print("Usage: merge_product_mappings.py <configmap_file> <nw_products_json> <server_products_json> <cdi_products_json> <maas_products_json>", 
              file=sys.stderr)
        print("  各product情報はJSON配列文字列として渡してください（空の場合は '[]'）", file=sys.stderr)
        sys.exit(1)
    
    configmap_file = sys.argv[1]
    
    # 各カテゴリの追加product情報をJSON解析
    try:
        additional_nw = json.loads(sys.argv[2]) if sys.argv[2] != '[]' else []
        additional_server = json.loads(sys.argv[3]) if sys.argv[3] != '[]' else []
        additional_cdi = json.loads(sys.argv[4]) if sys.argv[4] != '[]' else []
        additional_maas = json.loads(sys.argv[5]) if sys.argv[5] != '[]' else []
    except json.JSONDecodeError as e:
        print(f"ERROR: 追加product情報のJSON解析に失敗: {e}", file=sys.stderr)
        sys.exit(1)
    
    # すべての追加リストが空の場合は処理スキップ
    total_additional = len(additional_nw) + len(additional_server) + len(additional_cdi) + len(additional_maas)
    if total_additional == 0:
        print("追加するproduct情報がありません。処理をスキップします。")
        sys.exit(0)
    
    print(f"ConfigMapファイル: {configmap_file}")
    print(f"追加対象product数: nw={len(additional_nw)}, server={len(additional_server)}, cdi={len(additional_cdi)}, maas={len(additional_maas)}")
    
    # ConfigMapファイルを読み込み
    try:
        original_content, mappings_data = load_configmap_file(configmap_file)
    except Exception as e:
        print(f"ERROR: ConfigMapファイルの読み込みに失敗: {e}", file=sys.stderr)
        sys.exit(1)
    
    # 各カテゴリをマージ
    total_added = 0
    total_skipped = 0
    
    if 'nw_products' in mappings_data and additional_nw:
        mappings_data['nw_products'], added, skipped = merge_products(
            mappings_data['nw_products'], additional_nw, 'nw_products')
        total_added += added
        total_skipped += skipped
    
    if 'server_products' in mappings_data and additional_server:
        mappings_data['server_products'], added, skipped = merge_products(
            mappings_data['server_products'], additional_server, 'server_products')
        total_added += added
        total_skipped += skipped
    
    if 'cdi_products' in mappings_data and additional_cdi:
        mappings_data['cdi_products'], added, skipped = merge_products(
            mappings_data['cdi_products'], additional_cdi, 'cdi_products')
        total_added += added
        total_skipped += skipped
    
    if 'maas_products' in mappings_data and additional_maas:
        mappings_data['maas_products'], added, skipped = merge_products(
            mappings_data['maas_products'], additional_maas, 'maas_products')
        total_added += added
        total_skipped += skipped
    
    # 結果をファイルに保存
    try:
        save_configmap_file(configmap_file, original_content, mappings_data)
    except Exception as e:
        print(f"ERROR: ConfigMapファイルの保存に失敗: {e}", file=sys.stderr)
        sys.exit(1)
    
    print(f"\n完了: {total_added}個のproduct情報を追加しました（{total_skipped}個はスキップ）")
    
    # 変更がなかった場合は終了コード2を返す（changed_when判定用）
    if total_added == 0:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
