#!/usr/bin/env python3
"""
values.yamlのconfigYaml内のphy2インフラストラクチャを削除するスクリプト
コメントとフォーマットを保持します
"""

import sys
import yaml

def remove_phy2_from_configyaml(values_yaml_path):
    """
    values.yamlファイルのconfigYaml内からphy2要素を削除
    """
    with open(values_yaml_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # YAMLをロード（コメントは保持しない標準的な方法）
    data = yaml.safe_load(content)
    
    # config.configYamlの文字列部分を取得
    if 'config' not in data or 'configYaml' not in data['config']:
        print("config.configYamlが見つかりません", file=sys.stderr)
        return False
    
    config_yaml_str = data['config']['configYaml']
    config_data = yaml.safe_load(config_yaml_str)
    
    # infrastructures配列からphy2を削除
    if 'infrastructures' in config_data and isinstance(config_data['infrastructures'], list):
        original_count = len(config_data['infrastructures'])
        config_data['infrastructures'] = [
            infra for infra in config_data['infrastructures']
            if not (isinstance(infra, dict) and infra.get('name') == 'phy2')
        ]
        
        if len(config_data['infrastructures']) == original_count:
            print("phy2要素が見つかりませんでした")
            return False
        
        print(f"phy2要素を削除しました（{original_count} -> {len(config_data['infrastructures'])}）")
    else:
        print("infrastructures配列が見つかりません", file=sys.stderr)
        return False
    
    # configYamlを再構築（リテラルブロックスタイルを保持）
    # インデント2スペース、phy2削除後のYAML文字列を生成
    new_config_yaml_str = yaml.dump(
        config_data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=1000,
        indent=2
    )
    
    # 元のファイル内容からconfigYaml部分を置換
    # "configYaml: |-" から次のトップレベルキーまでを抽出して置換
    import re
    
    # configYaml配下の内容を特定（インデントされた行が続く範囲）
    pattern = r'(  configYaml: \|-\n)((?:    .*\n)*)'
    
    def create_replacement(match):
        # インデントを4スペースに調整
        indented_lines = []
        for line in new_config_yaml_str.rstrip('\n').split('\n'):
            indented_lines.append('    ' + line)
        return match.group(1) + '\n'.join(indented_lines) + '\n'
    
    new_content = re.sub(pattern, create_replacement, content)
    
    # ファイルに書き戻す
    with open(values_yaml_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <values.yaml path>", file=sys.stderr)
        sys.exit(1)
    
    yaml_path = sys.argv[1]
    
    try:
        if remove_phy2_from_configyaml(yaml_path):
            print(f"✓ {yaml_path} を更新しました")
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
