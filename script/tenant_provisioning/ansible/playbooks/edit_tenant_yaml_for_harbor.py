import sys
import yaml
import base64

# 入力データ
manifest_b64 = sys.argv[1]
ca_cert_b64 = sys.argv[2]
output_path = sys.argv[3]

# デコード
manifest_yaml = base64.b64decode(manifest_b64).decode('utf-8')
ca_cert_content = base64.b64decode(ca_cert_b64).decode('utf-8')

# YAMLパース
docs = list(yaml.safe_load_all(manifest_yaml))

# CA証明書の更新または追加
def update_or_add_ca_cert(files, ca_file_entry):
    target_path = ca_file_entry['path']
    
    # 既存エントリを検索して更新
    for f in files:
        if isinstance(f, dict) and f.get('path') == target_path:
            f['content'] = ca_file_entry['content']
            f['owner'] = ca_file_entry['owner']
            f['permissions'] = ca_file_entry['permissions']
            return
    
    files.append(ca_file_entry)

# CA証明書エントリ
ca_file_entry = {
    'content': ca_cert_content,
    'owner': 'root:root',
    'path': '/etc/pki/ca-trust/source/anchors/harbor-root-ca.crt',
    'permissions': '0644'
}

# 各ドキュメントを処理
for doc in docs:
    if not doc:
        continue
    
    # KubeadmControlPlaneの処理
    if doc.get('kind') == 'KubeadmControlPlane':
        spec = doc.setdefault('spec', {})
        kubeadm_config = spec.setdefault('kubeadmConfigSpec', {})
        
        # files配下に更新または追加
        files = kubeadm_config.setdefault('files', [])
        update_or_add_ca_cert(files, ca_file_entry)
        
        # preKubeadmCommandsの先頭に追加
        commands = kubeadm_config.get('preKubeadmCommands', [])
        commands.insert(0, 'update-ca-trust extract')
        kubeadm_config['preKubeadmCommands'] = commands
    
    # KubeadmConfigTemplateの処理
    elif doc.get('kind') == 'KubeadmConfigTemplate' :
        spec = doc.setdefault('spec', {}).setdefault('template', {}).setdefault('spec', {})
        
        # files配下に更新または追加
        files = spec.setdefault('files', [])
        update_or_add_ca_cert(files, ca_file_entry)
        
        # preKubeadmCommandsの先頭に追加
        commands = spec.get('preKubeadmCommands', [])
        commands.insert(0, 'update-ca-trust extract')
        spec['preKubeadmCommands'] = commands

# 出力
with open(output_path, 'w') as f:
    yaml.dump_all(docs, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

print("✓ マニフェストファイルを生成しました: " + output_path)
