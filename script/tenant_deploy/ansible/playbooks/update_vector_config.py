#!/usr/bin/env python3
import sys
import yaml
import copy

# --- 定数 ---
LOKI_SINKS_TEMPLATE = {
    "kubelet_loki_mgr": {
        "encoding": {"codec": "json"},
        "endpoint": "https://loki.local:8443",
        "tls": {"verify_certificate": False},
        "inputs": ["kubelet_journald"],
        "labels": {
            "host": "${VECTOR_SELF_NODE_NAME}",
            "job": "kubelet_journald",
            "tenant": "{tenant}"
        },
        "type": "loki"
    },
    "pod_loki_mgr": {
        "encoding": {"codec": "json"},
        "endpoint": "https://loki.local:8443",
        "tls": {"verify_certificate": False},
        "inputs": ["drop_unwanted"],
        "labels": {
            "container": "{{ kubernetes.container_name }}",
            "job": "kubernetes_logs",
            "namespace": "{{ kubernetes.pod_namespace }}",
            "node": "{{ kubernetes.pod_node_name }}",
            "tenant": "{tenant}"
        },
        "type": "loki"
    },
    "syslog_loki_mgr": {
        "encoding": {"codec": "json"},
        "endpoint": "https://loki.local:8443",
        "tls": {"verify_certificate": False},
        "inputs": ["syslog_file"],
        "labels": {
            "host": "${VECTOR_SELF_NODE_NAME}",
            "job": "syslog_file",
            "tenant": "{tenant}"
        },
        "type": "loki"
    },
    "auditd_loki_mgr": {
        "encoding": {"codec": "json"},
        "endpoint": "https://loki.local:8443",
        "tls": {"verify_certificate": False},
        "inputs": ["auditd_logs"],
        "labels": {
            "host": "${VECTOR_SELF_NODE_NAME}",
            "job": "auditd_file",
            "tenant": "{tenant}"
        },
        "type": "loki"
    }
}

AUDIT_LOKI_SINKS_TEMPLATE = {
    "k8s_audit_loki_mgr": {
        "encoding": {"codec": "json"},
        "endpoint": "https://loki.local:8443",
        "tls": {"verify_certificate": False},
        "inputs": ["kubernetes_audit"],
        "labels": {
            "host": "${VECTOR_SELF_NODE_NAME}",
            "job": "k8s_audit",
            "tenant": "{tenant}"
        },
        "type": "loki"
    }
}

DROP_UNWANTED_TRANSFORM = {
    "drop_unwanted": {
        "type": "remap",
        "inputs": ["kubernetes_logs"],
        "drop_on_abort": True,
        "source": """cont = to_string(.kubernetes.container_name) ?? ""
ns = to_string(.kubernetes.pod_namespace) ?? ""
allow = {
  \"argo-events\": true,
  \"calico-apiserver\": true,
  \"calico-system\": true,
  \"cert-manager\": true,
  \"dci\": true,
  \"dra-driver\": true,
  \"gateway-api\": true,
  \"gpu-operator\": true,
  \"harbor\": true,
  \"kube-node-lease\": true,
  \"kube-public\": true,
  \"kube-system\": true,
  \"kyverno\": true,
  \"loki\": true,
  \"nfs-subdir-external-provisioner\": true,
  \"nginx-gateway\": true,
  \"npd\": true,
  \"nvidia-dra-driver-gpu\": true,
  \"nvidia-network-operator\": true,
  \"policy-reporter\": true,
  \"prometheus\": true,
  \"sriov-device-settings\": true,
  \"temporal\": true,
  \"tigera-operator\": true,
  \"vector\": true,
  \"velero\": true,
  \"watch-gpu-status\": true,
}
is_allowed = (get(allow, path: [ns]) ?? false) == true
if !is_allowed && !(cont == \"app-conn-control-info-manager-dci\" || cont==\"vector\") {
  abort
}
"""
    }
}

# --- メイン処理 ---
def main():
    if len(sys.argv) not in (4, 5):
        print("Usage: update_vector_config.py <TENANT_NAMESPACE> <input_vector.yaml> <output_vector.yaml> [audit]", file=sys.stderr)
        sys.exit(2)
    tenant = sys.argv[1]
    input_file = sys.argv[2]
    output_file = sys.argv[3]
    mode = sys.argv[4] if len(sys.argv) == 5 else "vector"
    if mode == "audit":
        sink_template = AUDIT_LOKI_SINKS_TEMPLATE
        apply_transforms = False
    else:
        sink_template = LOKI_SINKS_TEMPLATE
        apply_transforms = True
    
    with open(input_file, 'r') as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        print("ERROR: vector.yamlが空または不正です", file=sys.stderr)
        sys.exit(2)

    # sinks 追加（冪等性: 既に1つでも存在すればスキップ）
    sinks = data.setdefault('sinks', {})
    already = any(k in sinks for k in sink_template)
    if already:
        print("[SKIP] sinksは既に存在します", file=sys.stderr)
        sys.exit(1)
    for k, v in sink_template.items():
        v2 = copy.deepcopy(v)
        if 'labels' in v2:
            for label_k, label_v in v2['labels'].items():
                if label_v == '{tenant}':
                    v2['labels'][label_k] = tenant
        sinks[k] = v2

    # transforms 追加（drop_unwantedがなければ追加、vectorモード時のみ）
    if apply_transforms:
        transforms = data.setdefault('transforms', {})
        if 'drop_unwanted' not in transforms:
            transforms.update(DROP_UNWANTED_TRANSFORM)

    def literal_str_representer(dumper, data):
        if '\n' in data:
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)
    yaml.add_representer(str, literal_str_representer)

    # 変更が必要な場合のみファイルに書き込む
    with open(output_file, 'w') as f:
        f.write(yaml.dump(data, allow_unicode=True, default_flow_style=False))
    
    msg = "sinks, transformsを追加しました" if apply_transforms else "sinksを追加しました"
    print(f"[OK] {msg}: tenant={tenant}", file=sys.stderr)
    sys.exit(0)

if __name__ == '__main__':
    main()
