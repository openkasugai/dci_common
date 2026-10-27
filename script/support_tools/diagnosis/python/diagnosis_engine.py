#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DCI診断エンジン - メインロジック
各モジュールを統合し、診断処理全体を制御します。
"""

import argparse
import logging
import os
import sys
import yaml
import re
import copy
from datetime import datetime
from typing import Dict, List, Optional, Any

# 同ディレクトリのモジュールをインポート
from log_parser import AnsibleLogParser
from k8s_collector import KubernetesCollector
from anomaly_detector import AnomalyDetector
from detailed_collector import DetailedCollector
from markdown_reporter import MarkdownReporter
from exceptions import (
    DiagnosisError, PrerequisiteError, TemplateRenderError,
    PlaybookExecutionError, ResourceCollectionError, ParseError
)
from error_formatter import format_error, format_error_compact, print_step_info


class DiagnosisEngine:
    """診断エンジンのメインクラス"""
    
    def __init__(self, args):
        """
        Args:
            args: コマンドライン引数
        """
        self.args = args
        self.script_name = args.script_name
        self.log_dir = args.log_dir
        self.inventory_path = args.inventory_path
        self.output_dir = args.output_dir
        self.timeout = args.timeout
        
        # ログ設定
        self.logger = self._setup_logging(args.log_level)
        
        # 各モジュールの初期化
        self.log_parser = None
        self.k8s_collector = None
        self.anomaly_detector = None
        self.detailed_collector = None
        self.markdown_reporter = None
        
        # リソースマッピング
        self.resource_mappings = None
        
        # 診断ツール設定（config.yaml）
        self.diagnosis_vars = None
        
        # Ansible vars（テナント定義など）
        self.ansible_vars = None
        
        # 診断結果
        self.diagnosis_result = {
            'script_name': self.script_name,
            'timestamp': datetime.now().isoformat(),
            'log_analysis': {},
            'resource_checks': {},
            'collection_scope': {},
            'issues_found': [],
            'detailed_logs': [],
            'summary_stats': {},
            'environment': {}
        }
    
    def _setup_logging(self, log_level: str) -> logging.Logger:
        """ロギング設定"""
        level = getattr(logging, log_level.upper(), logging.INFO)
        
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        return logging.getLogger(__name__)
    
    def initialize(self):
        """各モジュールの初期化"""
        self.logger.info("Initializing diagnosis engine...")
        
        try:
            # 前提条件の検証
            self.logger.info("Validating prerequisites...")
            self.validate_prerequisites()
            
            # リソースマッピングをロード
            self._load_resource_mappings()
            
            # 診断ツール設定をロード
            self._load_diagnosis_vars()
            
            # Ansible vars.yamlをロード（テナント定義など）
            self._load_ansible_vars()
            
            # テンプレート変数を展開（{{ tenant_namespace }}など）
            self._expand_resource_mappings()
            
            # Ansibleログパーサー
            self.logger.info("Initializing log parser...")
            self.log_parser = AnsibleLogParser(self.log_dir, config=self.diagnosis_vars)
            
            # Anomaly Detector
            self.logger.info("Initializing anomaly detector...")
            self.anomaly_detector = AnomalyDetector(self.diagnosis_vars)
            
            # Markdown レポーター
            self.logger.info("Initializing markdown reporter...")
            self.markdown_reporter = MarkdownReporter()
            
            # SSH設定を取得
            # スクリプトルートからAnsible設定を再利用
            # inventory_path: /path/to/script_root/ansible/inventory/hosts
            # -> script_root: /path/to/script_root (3 levels up: hosts -> inventory -> ansible -> script_root)
            script_root = os.path.dirname(os.path.dirname(os.path.dirname(self.inventory_path)))
            self.logger.info(f"Script root detected: {script_root}")
            
            # Kubernetes collector初期化
            self.logger.info("Initializing Kubernetes collector...")
            try:
                self.k8s_collector = KubernetesCollector(
                    script_root, 
                    target_host="dci_mgmt_k8s_control_plane[0]", 
                    output_dir=self.output_dir,
                    ansible_vars=self.ansible_vars
                )
                self.detailed_collector = DetailedCollector(self.k8s_collector)
                
                # テナント情報がある場合、テナント用collectorを作成
                tenants = self.ansible_vars.get('tenants', [])
                if tenants and isinstance(tenants, list) and len(tenants) > 0:
                    first_tenant = tenants[0]
                    tenant_namespace = first_tenant.get('tenant_namespace')
                    
                    if not tenant_namespace:
                        self.logger.warning("Tenant information found but tenant_namespace is missing. Skipping tenant collector initialization.")
                        self.k8s_collector_tenant = None
                        self.detailed_collector_tenant = None
                    else:
                        tenant_kubeconfig_file = first_tenant.get('kubeconfig_file', f'{tenant_namespace}.kubeconfig')
                        tenant_kubeconfig_path = f"$HOME/auto_script_work/{tenant_namespace}/{tenant_kubeconfig_file}"
                        
                        self.logger.info(f"Creating tenant cluster collector for: {tenant_namespace}")
                        self.k8s_collector_tenant = KubernetesCollector(
                            script_root,
                            target_host="dci_mgmt_k8s_control_plane[0]",
                            output_dir=self.output_dir,
                            ansible_vars=self.ansible_vars,
                            kubeconfig_path=tenant_kubeconfig_path
                        )
                        self.detailed_collector_tenant = DetailedCollector(self.k8s_collector_tenant)
                else:
                    self.logger.debug("No tenant information found. Only manager cluster collector will be initialized.")
                    self.k8s_collector_tenant = None
                    self.detailed_collector_tenant = None
            except Exception as e:
                raise PrerequisiteError(
                    f"Kubernetesコレクターの初期化に失敗しました",
                    missing_item="Kubernetes collector",
                    step="モジュール初期化",
                    context={
                        'script_root': script_root,
                        'inventory_path': self.inventory_path
                    },
                    suggestion="以下を確認してください:\n"
                        "  1. Ansible inventory ファイルが正しいパスに存在するか\n"
                        "  2. スクリプトルートディレクトリの構造が正しいか\n"
                        "  3. 必要なPythonパッケージ (Jinja2, PyYAML) がインストールされているか",
                    original_error=e
                )
            
            self.logger.info("All modules initialized successfully")
            
        except DiagnosisError:
            # カスタム例外はそのまま再raise
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize modules: {e}")
            raise PrerequisiteError(
                f"診断ツールの初期化中に予期しないエラーが発生しました",
                missing_item="initialization",
                step="モジュール初期化",
                suggestion="エラーメッセージを確認し、必要なファイルとパッケージがすべて揃っているか確認してください",
                original_error=e
            )
    
    def validate_prerequisites(self):
        """前提条件のバリデーション
        
        注意: kubectl コマンドはリモートホスト（Control Plane ノード）上で実行されるため、
        ローカル環境でのチェックは不要です。
        """
        import shutil
        
        errors = []
        
        # 1. ansible-playbook コマンドの存在確認
        if not shutil.which('ansible-playbook'):
            errors.append("ansible-playbook コマンドが見つかりません")
        else:
            self.logger.debug(f"ansible-playbook found at: {shutil.which('ansible-playbook')}")
        
        # 2. Ansible inventory ファイルの存在確認
        if not os.path.isfile(self.inventory_path):
            errors.append(f"Ansible inventory ファイルが見つかりません: {self.inventory_path}")
        else:
            self.logger.debug(f"Inventory file found: {self.inventory_path}")
        
        # 3. ログディレクトリの存在確認
        if not os.path.isdir(self.log_dir):
            errors.append(f"ログディレクトリが見つかりません: {self.log_dir}")
        else:
            self.logger.debug(f"Log directory found: {self.log_dir}")
        
        # 4. 必須Pythonパッケージの確認
        required_packages = ['jinja2', 'yaml']
        for package in required_packages:
            try:
                if package == 'yaml':
                    import yaml
                elif package == 'jinja2':
                    import jinja2
                self.logger.debug(f"Python package '{package}' is available")
            except ImportError:
                errors.append(f"必須Pythonパッケージがインストールされていません: {package}")
        
        # エラーがあれば例外を発生
        if errors:
            error_list = "\n  - ".join(errors)
            raise PrerequisiteError(
                f"前提条件の検証に失敗しました。以下の問題が見つかりました:\n  - {error_list}",
                missing_item="multiple",
                step="前提条件チェック",
                context={
                    'inventory_path': self.inventory_path,
                    'log_dir': self.log_dir
                },
                suggestion="以下を実施してください:\n"
                    "  1. Ansible をインストール: pip install ansible\n"
                    "  2. 必須パッケージをインストール: pip install jinja2 PyYAML\n"
                    "  3. inventory ファイルとログディレクトリのパスを確認"
            )
        
        self.logger.info("All prerequisites validated successfully")
    
    def _load_diagnosis_vars(self):
        """診断ツール設定ファイル（config.yaml）をロード"""
        vars_file = os.path.join(
            os.path.dirname(__file__),
            'config',
            'config.yaml'
        )
        
        # デフォルト設定
        default_vars = {
            'pod_restart_threshold': 50,
            'collect_details_for_warnings': False,
            'collect_details_for_critical': True,
            'pod_not_ready_severity': 'warning',
            'high_restart_severity': 'warning'
        }
        
        try:
            with open(vars_file, 'r', encoding='utf-8') as f:
                loaded_vars = yaml.safe_load(f)
                # デフォルト値とマージ
                self.diagnosis_vars = {**default_vars, **(loaded_vars or {})}
            self.logger.info(f"Loaded diagnosis vars from {vars_file}")
            self.logger.debug(f"Diagnosis vars: {self.diagnosis_vars}")
        except FileNotFoundError:
            self.logger.warning(f"Diagnosis vars file not found: {vars_file}, using defaults")
            self.diagnosis_vars = default_vars
        except Exception as e:
            self.logger.error(f"Failed to load diagnosis vars: {e}, using defaults")
            self.diagnosis_vars = default_vars
    
    def _load_resource_mappings(self):
        """リソースマッピング定義ファイルをロード"""
        mapping_file = os.path.join(
            os.path.dirname(__file__),
            'config',
            'resource_mappings.yaml'
        )
        
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                self.resource_mappings = yaml.safe_load(f)
            self.logger.info(f"Loaded resource mappings from {mapping_file}")
        except FileNotFoundError:
            self.logger.warning(f"Resource mappings file not found: {mapping_file}")
            self.resource_mappings = {}
        except Exception as e:
            self.logger.error(f"Failed to load resource mappings: {e}")
            self.resource_mappings = {}
    
    def _load_ansible_vars(self):
        """
        Ansible vars.yamlをロード（テナント定義など）
        複数のgroup_varsディレクトリから変数を収集・マージする
        
        tenant_provisioning: group_vars/all/vars.yaml
        tenant_deploy: group_vars/dci_mgmt_k8s_control_plane/vars.yaml
        """
        inventory_dir = os.path.dirname(self.inventory_path)
        group_vars_dir = os.path.join(inventory_dir, 'group_vars')
        
        # 検索対象のgroup_varsサブディレクトリ
        search_paths = [
            os.path.join(group_vars_dir, 'all', 'vars.yaml'),
            os.path.join(group_vars_dir, 'dci_mgmt_k8s_control_plane', 'vars.yaml'),
        ]
        
        self.ansible_vars = {}
        all_tenants = []
        seen_tenant_namespaces = set()
        
        for vars_file in search_paths:
            if not os.path.exists(vars_file):
                self.logger.debug(f"Vars file not found (optional): {vars_file}")
                continue
                
            try:
                with open(vars_file, 'r', encoding='utf-8') as f:
                    vars_data = yaml.safe_load(f) or {}
                
                self.logger.info(f"Loaded Ansible vars from {vars_file}")
                
                # テナント定義を抽出（重複除去）
                tenants = vars_data.get('tenants', [])
                if tenants and isinstance(tenants, list):
                    for tenant in tenants:
                        if not isinstance(tenant, dict):
                            continue
                        ns = tenant.get('tenant_namespace')
                        if ns and ns not in seen_tenant_namespaces:
                            all_tenants.append(tenant)
                            seen_tenant_namespaces.add(ns)
                            self.logger.debug(f"  Found tenant: {ns}")
                        elif ns and ns in seen_tenant_namespaces:
                            self.logger.debug(f"  Skipping duplicate tenant: {ns}")
                
                # その他の変数をマージ（後勝ち、tenantsキーは除外）
                vars_without_tenants = {k: v for k, v in vars_data.items() if k != 'tenants'}
                self.ansible_vars.update(vars_without_tenants)
            
            except Exception as e:
                self.logger.warning(f"Failed to load {vars_file}: {e}")
                continue
        
        # マージしたテナントリストをセット
        if all_tenants:
            self.ansible_vars['tenants'] = all_tenants
            tenant_namespaces = [t.get('tenant_namespace') for t in all_tenants if t.get('tenant_namespace')]
            self.logger.info(f"Total {len(all_tenants)} tenant(s) found: {', '.join(tenant_namespaces)}")
        else:
            self.logger.info("No tenants defined in any vars.yaml")
    
    def _expand_resource_mappings(self):
        """
        リソースマッピング内のテンプレート変数を展開
        
        {{ tenant_namespace }}などのJinja2変数を実際の値に置換し、
        複数テナントの場合はリソース定義を複製します。
        """
        if not self.resource_mappings:
            self.logger.warning("No resource mappings to expand")
            return
        
        if not self.ansible_vars:
            self.logger.info("No Ansible vars loaded, skipping template expansion")
            return
        
        tenants = self.ansible_vars.get('tenants', [])
        if not tenants:
            self.logger.info("No tenants defined, skipping template expansion")
            return
        
        # 各スクリプトのリソース定義を展開
        for script_name, script_config in self.resource_mappings.items():
            if script_name == 'script_dependencies':
                continue
            
            if not isinstance(script_config, dict):
                continue
            
            # check_scope内のnamespacesを展開
            check_scope = script_config.get('check_scope', {})
            if check_scope and isinstance(check_scope, dict):
                namespaces = check_scope.get('namespaces', [])
                if namespaces and isinstance(namespaces, list):
                    expanded_namespaces = []
                    for ns in namespaces:
                        if isinstance(ns, str) and '{{ tenant_namespace }}' in ns:
                            # 各テナントのnamespaceを追加
                            for tenant in tenants:
                                tenant_namespace = tenant.get('tenant_namespace')
                                if tenant_namespace:
                                    expanded_ns = ns.replace('{{ tenant_namespace }}', tenant_namespace)
                                    expanded_namespaces.append(expanded_ns)
                        else:
                            # テンプレート変数なし、そのまま追加
                            expanded_namespaces.append(ns)
                    
                    if expanded_namespaces:
                        check_scope['namespaces'] = expanded_namespaces
                        self.logger.debug(f"Expanded namespaces in {script_name}: {len(namespaces)} -> {len(expanded_namespaces)}")
            
            # generic_resourcesを展開
            generic_resources = script_config.get('generic_resources', [])
            if not generic_resources:
                continue
            
            # 展開が必要なリソースと不要なリソースに分類
            expanded_resources = []
            
            for resource_spec in generic_resources:
                # テンプレート変数が含まれているか確認
                resource_str = yaml.dump(resource_spec)
                if '{{ tenant_namespace }}' in resource_str:
                    # 各テナントごとにリソース定義を複製
                    for tenant in tenants:
                        tenant_namespace = tenant.get('tenant_namespace')
                        if not tenant_namespace:
                            continue
                        
                        # リソース定義を複製
                        expanded_spec = copy.deepcopy(resource_spec)
                        
                        # すべての文字列フィールドでテンプレート変数を置換
                        self._replace_template_vars(expanded_spec, {'tenant_namespace': tenant_namespace})
                        
                        expanded_resources.append(expanded_spec)
                        
                    self.logger.debug(f"Expanded resource {resource_spec.get('kind')} for {len(tenants)} tenant(s)")
                else:
                    # テンプレート変数なし、そのまま追加
                    expanded_resources.append(resource_spec)
            
            # 展開後のリソース定義で置き換え
            if expanded_resources:
                script_config['generic_resources'] = expanded_resources
                self.logger.info(f"Expanded {script_name}: {len(generic_resources)} -> {len(expanded_resources)} resources")
    
    def _replace_template_vars(self, obj: Any, vars_dict: Dict[str, str]):
        """
        オブジェクト内のすべての文字列フィールドでテンプレート変数を置換（再帰的）
        
        Args:
            obj: 置換対象のオブジェクト（dict, list, str）
            vars_dict: 変数名と値のマッピング（例: {'tenant_namespace': 'tenant-1'}）
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, str):
                    # 文字列内のテンプレート変数を置換
                    for var_name, var_value in vars_dict.items():
                        value = value.replace(f'{{{{ {var_name} }}}}', var_value)
                    obj[key] = value
                elif isinstance(value, (dict, list)):
                    self._replace_template_vars(value, vars_dict)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, str):
                    for var_name, var_value in vars_dict.items():
                        item = item.replace(f'{{{{ {var_name} }}}}', var_value)
                    obj[i] = item
                elif isinstance(item, (dict, list)):
                    self._replace_template_vars(item, vars_dict)
    
    def _determine_collection_scope(self) -> Dict[str, Any]:
        """
        診断対象スクリプトに応じて収集範囲を決定
        
        Returns:
            {
                'target_scripts': ['manager_cluster_setup', 'manager_software_deploy'],
                'namespaces': ['kube-system', 'cert-manager', ...],
                'cluster_type': 'manager' or 'tenant',
                'check_filesystem': True/False
            }
        """
        scope = {
            'target_scripts': [],
            'namespaces': set(),
            'cluster_type': 'manager'
        }
        
        # 依存関係を解決
        dependencies = self.resource_mappings.get('script_dependencies', {})
        target_deps = dependencies.get(self.script_name, [])
        
        # 診断対象スクリプト + 依存スクリプトを収集対象に
        scope['target_scripts'] = target_deps + [self.script_name]
        
        self.logger.info(f"Collection target scripts: {scope['target_scripts']}")
        
        # 各スクリプトのNamespaceを収集
        for script in scope['target_scripts']:
            script_config = self.resource_mappings.get(script, {})
            check_scope = script_config.get('check_scope', {})
            
            # Namespaceリストを追加
            namespaces = check_scope.get('namespaces', [])
            scope['namespaces'].update(namespaces)
            
            # cluster_typeを更新（後勝ち: tenant_deployならtenant）
            if check_scope.get('cluster_type'):
                scope['cluster_type'] = check_scope['cluster_type']
        
        # setをlistに変換
        scope['namespaces'] = list(scope['namespaces'])
        
        self.logger.info(f"Collection scope: {len(scope['namespaces'])} namespaces, cluster_type={scope['cluster_type']}")
        self.logger.debug(f"Target namespaces: {scope['namespaces']}")
        
        return scope
    

    
    def run_diagnosis(self):
        """診断処理のメイン実行"""
        self.logger.info(f"Starting diagnosis for script: {self.script_name}")
        
        # 診断開始時刻を記録
        diagnosis_start_time = datetime.now()
        self.diagnosis_result['diagnosis_start_time'] = diagnosis_start_time.isoformat()
        
        try:
            # 0. 収集範囲決定
            print_step_info(0, 6, "収集範囲決定")
            self.logger.info("Step 0: Determining collection scope...")
            collection_scope = self._determine_collection_scope()
            self.diagnosis_result['collection_scope'] = collection_scope
            
            # 1. Ansibleログの解析
            print_step_info(1, 6, "Ansibleログの解析")
            self.logger.info("Step 1: Analyzing Ansible logs...")
            self._analyze_logs()
            
            # 2. Kubernetesリソースの状態チェック（収集範囲を絞り込み）
            if self.k8s_collector:
                print_step_info(2, 6, "Kubernetesリソースの状態チェック")
                self.logger.info("Step 2: Checking Kubernetes resources...")
                self._check_kubernetes_resources(collection_scope['namespaces'])
            else:
                self.logger.warning("Step 2: Skipping Kubernetes checks (no Ansible connection)")
            
            # 3. 異常検出
            print_step_info(3, 6, "異常検出")
            self.logger.info("Step 3: Detecting anomalies...")
            self._detect_anomalies()
            
            # 4. 詳細情報収集
            if self.detailed_collector:
                print_step_info(4, 6, "詳細情報収集")
                self.logger.info("Step 4: Collecting detailed information...")
                self._collect_detailed_info()
            
            # 5. 統計情報の生成
            print_step_info(5, 6, "統計情報の生成")
            self.logger.info("Step 5: Generating statistics...")
            self._generate_statistics()
            
            # 6. 結果の出力
            print_step_info(6, 6, "結果の出力")
            self.logger.info("Step 6: Outputting results...")
            
            # 診断終了時刻と稼働時間を記録（レポート出力前に設定）
            diagnosis_end_time = datetime.now()
            self.diagnosis_result['diagnosis_end_time'] = diagnosis_end_time.isoformat()
            
            # 診断稼働時間を計算
            duration = diagnosis_end_time - diagnosis_start_time
            total_seconds = duration.total_seconds()
            hours, remainder = divmod(int(total_seconds), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.diagnosis_result['diagnosis_duration'] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            self._output_results()
            
            self.logger.info("Diagnosis completed successfully")
            
        except DiagnosisError as e:
            # カスタム例外は詳細にフォーマットして表示
            self.logger.error(f"Diagnosis failed with DiagnosisError: {format_error_compact(e)}")
            format_error(e, sys.stderr)
            raise
        except Exception as e:
            self.logger.error(f"Diagnosis failed: {e}", exc_info=True)
            raise
        finally:
            # 診断終了時刻を記録（異常終了時も最終的な時刻を記録）
            # 正常終了時は既に記録されているが、再度更新する
            diagnosis_end_time = datetime.now()
            self.diagnosis_result['diagnosis_end_time'] = diagnosis_end_time.isoformat()
            
            # 診断稼働時間を計算
            duration = diagnosis_end_time - diagnosis_start_time
            total_seconds = duration.total_seconds()
            hours, remainder = divmod(int(total_seconds), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.diagnosis_result['diagnosis_duration'] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def _analyze_logs(self):
        """Ansibleログの解析"""
        if not self.log_parser:
            return
        
        log_result = self.log_parser.parse_all_logs()
        self.diagnosis_result['log_analysis'] = log_result
        
        self.logger.info(f"Parsed {len(log_result.get('playbooks_executed', []))} playbooks")
        self.logger.info(f"Found {len(log_result.get('errors', []))} errors in logs")
        self.logger.info(f"Found {len(log_result.get('warnings', []))} warnings in logs")
    
    def _check_kubernetes_resources(self, target_namespaces: List[str] = None):
        """
        Kubernetesリソースの状態チェック
        
        Args:
            target_namespaces: 収集対象のNamespaceリスト（非推奨、汎用リソース定義を使用してください）
        """
        if not self.k8s_collector:
            return
        
        resource_checks = {}
        
        try:
            # スクリプトマッピングからgeneric_resources定義を取得（依存スクリプト含む）
            self.logger.info("ステップ2a: 汎用リソース定義を読み込み...")
            collection_scope = self.diagnosis_result.get('collection_scope', {})
            target_scripts = collection_scope.get('target_scripts', [self.script_name])
            
            # 各スクリプトのリソースを収集
            generic_resources_specs = []
            for script in target_scripts:
                script_mapping = self.resource_mappings.get(script, {})
                specs = script_mapping.get('generic_resources', [])
                if specs:
                    self.logger.info(f"  - {script}: {len(specs)}種類のリソース定義")
                    # 各specにスクリプト名とcluster_typeを付与
                    check_scope = script_mapping.get('check_scope', {})
                    default_cluster_type = check_scope.get('cluster_type', 'manager')
                    for spec in specs:
                        spec['_source_script'] = script
                        # リソース個別のcluster_typeを優先、なければスクリプトレベルのデフォルトを使用
                        spec['_cluster_type'] = spec.get('cluster_type', default_cluster_type)
                    generic_resources_specs.extend(specs)
            
            # collect_all_pods フラグの処理
            # check_scope.collect_all_pods が true の場合、指定された namespace 内の全Podを収集
            for script in target_scripts:
                script_mapping = self.resource_mappings.get(script, {})
                check_scope = script_mapping.get('check_scope', {})
                
                if not check_scope.get('collect_all_pods', False):
                    continue
                
                namespaces = check_scope.get('namespaces', [])
                if not namespaces:
                    continue
                
                self.logger.info(f"  - {script}: collect_all_pods が有効、{len(namespaces)}個のnamespaceで全Pod収集")
                
                # 既存リソース定義から namespace ごとの cluster_type マッピングを構築
                ns_cluster_type_map = {}
                for spec in script_mapping.get('generic_resources', []):
                    ns = spec.get('namespace')
                    ct = spec.get('cluster_type')
                    if ns and ct:
                        ns_cluster_type_map[ns] = ct
                
                # デフォルトの cluster_type
                default_cluster_type = check_scope.get('cluster_type', 'manager')
                
                # 各namespace用の全Pod収集定義を生成
                for ns in namespaces:
                    # テンプレート変数（{{ tenant_namespace }}）が含まれていない場合のみ処理
                    # テンプレート変数は後で展開されるため、ここでは直接的な namespace 名のみ処理
                    if '{{' in ns:
                        # テンプレート namespace は既存定義から cluster_type を推測
                        # "{{ tenant_namespace }}" → manager
                        # "sa-{{ tenant_namespace }}" → manager
                        if ns.startswith('sa-'):
                            cluster_type = 'manager'
                        else:
                            cluster_type = ns_cluster_type_map.get(ns, default_cluster_type)
                    else:
                        # 通常の namespace: 既存定義から cluster_type を取得、なければデフォルト
                        cluster_type = ns_cluster_type_map.get(ns, default_cluster_type)
                    
                    # 全Pod収集用の定義を追加
                    all_pods_spec = {
                        'kind': 'Pod',
                        'namespace': ns,
                        'namespaced': True,
                        'cluster_type': cluster_type,
                        '_source_script': script,
                        '_cluster_type': cluster_type,
                        'collect_all': True,  # 全Pod収集フラグ
                        'description': f"All pods in {ns} namespace (collect_all_pods)"
                    }
                    generic_resources_specs.append(all_pods_spec)
                    self.logger.debug(f"    追加: {ns} namespace の全Pod (cluster_type={cluster_type})")
            
            if not generic_resources_specs:
                self.logger.warning(f"対象スクリプトには generic_resources 定義がありません")
                self.diagnosis_result['resource_checks'] = resource_checks
                return
            
            self.logger.info(f"合計 {len(generic_resources_specs)}種類のリソース定義を読み込みました")
            
            # cluster_type別にリソースをグループ化
            resources_by_cluster_type = {}
            for spec in generic_resources_specs:
                cluster_type = spec.get('_cluster_type', 'manager')
                if cluster_type not in resources_by_cluster_type:
                    resources_by_cluster_type[cluster_type] = []
                resources_by_cluster_type[cluster_type].append(spec)
            
            self.logger.info(f"Grouped resources by cluster_type: {list(resources_by_cluster_type.keys())}")
            for cluster_type, specs in resources_by_cluster_type.items():
                self.logger.info(f"  - {cluster_type}: {len(specs)}種類のリソース")
            
            # cluster_type別に収集
            all_collected_resources = {}
            for cluster_type, specs in resources_by_cluster_type.items():
                # インデックスを追加
                for idx, spec in enumerate(specs, start=1):
                    spec['_index'] = idx
                
                # cluster_typeに応じて適切なcollectorを選択
                if cluster_type == 'tenant':
                    if not self.k8s_collector_tenant:
                        self.logger.warning(f"Tenant resources defined but no tenant collector available. Skipping {len(specs)} tenant resources.")
                        continue
                    collector = self.k8s_collector_tenant
                    self.logger.info(f"Using tenant cluster collector for {len(specs)} resource types")
                else:
                    collector = self.k8s_collector
                    self.logger.info(f"Using manager cluster collector for {len(specs)} resource types")
                
                # リソース収集
                self.logger.info(f"ステップ2b-{cluster_type}: {len(specs)}種類のリソースを収集中...")
                
                collected_resources = collector.collect_generic_resources(specs)
                
                # 結果をマージ
                all_collected_resources.update(collected_resources)
            
            collected_resources = all_collected_resources
            
            if not collected_resources:
                self.logger.warning("No resources were collected")
            
            # 収集結果を診断結果に格納
            self.logger.info("ステップ2c: 収集したリソースを診断結果に格納...")
            for resource_key, resource_info in collected_resources.items():
                resource_checks[resource_key] = resource_info
                # resource_infoは {'data': [...], 'wide_text': '...', 'spec': ...} の構造
                resource_count = len(resource_info.get('data', [])) if isinstance(resource_info, dict) else 0
                self.logger.info(f"Collected {resource_count} {resource_key} resources")
                
                # デバッグ: 収集したリソースキーの詳細を出力
                if isinstance(resource_info, dict) and 'spec' in resource_info:
                    spec = resource_info['spec']
                    self.logger.debug(
                        f"[COLLECTION] Key={resource_key} | "
                        f"cluster_type={spec.get('_cluster_type')} | "
                        f"kind={spec.get('kind')} | "
                        f"namespace={spec.get('namespace', 'N/A')} | "
                        f"index={spec.get('_index')} | "
                        f"count={resource_count}"
                    )
            
            self.logger.info(f"Successfully collected {len(collected_resources)} resource types")
            
            # 診断結果に格納
            self.diagnosis_result['resource_checks'] = resource_checks
            self.logger.info("ステップ2: Kubernetesリソース収集完了")
            
        except DiagnosisError as e:
            # DiagnosisErrorが発生してもエラーを記録して処理を継続
            self.logger.warning(f"Resource collection encountered an error, continuing diagnosis: {e}")
            resource_checks['collection_failed'] = True
            self.diagnosis_result['resource_checks'] = resource_checks
            # リソース収集エラーを記録
            self.diagnosis_result['resource_collection_error'] = {
                'occurred': True,
                'message': 'リソース収集中にエラーが発生しました。詳細はコンソールログを確認してください。',
                'error_type': type(e).__name__
            }
            # 例外を投げずに継続
        except Exception as e:
            self.logger.warning(f"Unexpected error during Kubernetes resource check, continuing diagnosis: {e}")
            resource_checks['error'] = str(e)
            resource_checks['collection_failed'] = True
            self.diagnosis_result['resource_checks'] = resource_checks
            # 予期しないエラーも記録
            self.diagnosis_result['resource_collection_error'] = {
                'occurred': True,
                'message': f'予期しないエラー: {str(e)}'
            }
            # 例外を投げずに継続
        
        self.diagnosis_result['resource_checks'] = resource_checks
    
    def _format_issue_log(self, issue: Dict) -> str:
        """
        異常情報を1行形式にフォーマット
        
        Args:
            issue: 異常情報辞書
        
        Returns:
            1行形式の文字列
        """
        issue_type = issue.get('issue_type', 'Unknown')
        severity = issue.get('severity', 'unknown')
        cluster_type = issue.get('cluster_type', 'manager')
        resource_name = issue.get('resource_name', 'N/A')
        message = issue.get('message', '')
        needs_collection = issue.get('needs_detailed_collection', False)
        
        # 基本情報
        log_parts = [
            f"[ANOMALY] {issue_type}",
            severity,
            f"{cluster_type}:{resource_name}",
            message,
            f"details_collect={needs_collection}"
        ]
        
        # 期待値と実際の値（存在する場合）
        details = issue.get('details', {})
        if isinstance(details, dict):
            expected = details.get('expected')
            actual = details.get('actual')
            if expected is not None and actual is not None:
                log_parts.append(f"expected={expected}, actual={actual}")
        
        return ' | '.join(log_parts)
    
    def _detect_anomalies(self):
        """異常検出（汎用リソース統一処理）"""
        if not self.anomaly_detector:
            return
        
        issues_dict = {}
        
        # 収集済みリソースを取得
        collected_resources = self.diagnosis_result.get('resource_checks', {})
        
        # 収集時と同じ方法でリソース定義を取得（依存スクリプト含む）
        collection_scope = self.diagnosis_result.get('collection_scope', {})
        target_scripts = collection_scope.get('target_scripts', [self.script_name])
        
        # 各スクリプトのリソースを収集
        generic_resources_specs = []
        for script in target_scripts:
            script_mapping = self.resource_mappings.get(script, {})
            specs = script_mapping.get('generic_resources', [])
            if specs:
                # 各specにスクリプト名とcluster_typeを付与（収集時と同じ）
                check_scope = script_mapping.get('check_scope', {})
                default_cluster_type = check_scope.get('cluster_type', 'manager')
                for spec in specs:
                    spec['_source_script'] = script
                    # リソース個別のcluster_typeを優先、なければスクリプトレベルのデフォルトを使用
                    spec['_cluster_type'] = spec.get('cluster_type', default_cluster_type)
                generic_resources_specs.extend(specs)
        
        if not generic_resources_specs:
            self.logger.warning(f"対象スクリプトには generic_resources 定義がありません")
            self.diagnosis_result['issues_found'] = []
            return
        
        # インデックスを追加（収集時と同じ方法）
        resources_by_cluster_type = {}
        for spec in generic_resources_specs:
            cluster_type = spec.get('_cluster_type', 'manager')
            if cluster_type not in resources_by_cluster_type:
                resources_by_cluster_type[cluster_type] = []
            resources_by_cluster_type[cluster_type].append(spec)

        for cluster_type, specs in resources_by_cluster_type.items():
            for idx, spec in enumerate(specs, start=1):
                spec['_index'] = idx
        
        # 全リソースをループ処理
        for spec in generic_resources_specs:
            # cluster_typeに応じて適切なcollectorを選択
            cluster_type = spec.get('_cluster_type', 'manager')
            if cluster_type == 'tenant' and self.k8s_collector_tenant:
                collector = self.k8s_collector_tenant
            else:
                collector = self.k8s_collector
            
            resource_key = collector._make_resource_key(spec)
            resource_info = collected_resources.get(resource_key, {})
            
            # デバッグ: 異常検出時のリソースキーと存在チェック結果を出力
            found = resource_key in collected_resources
            resource_count = len(resource_info.get('data', [])) if isinstance(resource_info, dict) else 0
            self.logger.debug(
                f"[DETECTION] Key={resource_key} | "
                f"cluster_type={spec.get('_cluster_type')} | "
                f"kind={spec.get('kind')} | "
                f"namespace={spec.get('namespace', 'N/A')} | "
                f"index={spec.get('_index')} | "
                f"found={found} | "
                f"count={resource_count}"
            )
            
            # 新しい構造: {'data': [...], 'wide_text': '...', 'spec': ...}
            resources = resource_info.get('data', []) if isinstance(resource_info, dict) else []
            
            if resources is not None:
                # 汎用異常検出
                issues = self.anomaly_detector.detect_generic_resource_issues(resources, spec)
                
                # 重複排除してissues_dictに追加（cluster_type情報を追加）
                for issue in issues:
                    # cluster_type情報を追加（詳細情報収集時に必要）
                    issue['cluster_type'] = cluster_type
                    
                    # cluster_typeを含めてキーを生成（同じリソース名でもcluster_typeが異なれば別issue）
                    key = f"{cluster_type}:{spec['kind']}:{issue.get('resource_name')}:{issue.get('issue_type')}"
                    if key not in issues_dict:
                        issues_dict[key] = issue
                        # 異常検出時にINFOレベルでログ出力
                        self.logger.info(self._format_issue_log(issue))
        
        # 問題リストに変換
        self.diagnosis_result['issues_found'] = list(issues_dict.values())
        self.logger.info(f"Total issues detected: {len(issues_dict)}")
    
    def _collect_detailed_info(self):
        """詳細情報の収集（異常検知されたPodのみ）"""
        if not self.detailed_collector:
            return
        
        issues = self.diagnosis_result.get('issues_found', [])
        
        if not issues:
            self.logger.info("詳細情報収集対象の問題がありません")
            self.diagnosis_result['detailed_logs'] = []
            return
        
        # resourcesディレクトリを作成
        resources_dir = os.path.join(self.output_dir, 'resources')
        
        # cluster_type別にissuesをグループ化
        issues_by_cluster_type = {'manager': [], 'tenant': []}
        for issue in issues:
            # needs_detailed_collectionフラグをチェック
            if not issue.get('needs_detailed_collection', False):
                continue
            
            cluster_type = issue.get('cluster_type', 'manager')
            issues_by_cluster_type[cluster_type].append(issue)
        
        manager_count = len(issues_by_cluster_type['manager'])
        tenant_count = len(issues_by_cluster_type['tenant'])
        
        self.logger.info(f"詳細情報収集対象: Manager {manager_count}個, Tenant {tenant_count}個")
        
        # 詳細情報収集対象の異常を明示的に出力
        for issue in issues_by_cluster_type['manager']:
            self.logger.info(f"  [Manager] {issue.get('issue_type')} | {issue.get('resource_name')}")
        for issue in issues_by_cluster_type['tenant']:
            self.logger.info(f"  [Tenant] {issue.get('issue_type')} | {issue.get('resource_name')}")
        
        # 詳細情報を収集
        detailed_info = []
        
        # Manager cluster issues
        if manager_count > 0:
            self.logger.info(f"Collecting details for {manager_count} manager cluster issues...")
            manager_details = self.detailed_collector.collect_details_for_issues(
                issues_by_cluster_type['manager'], 
                resources_dir
            )
            detailed_info.extend(manager_details)
        
        # Tenant cluster issues
        if tenant_count > 0 and self.detailed_collector_tenant:
            self.logger.info(f"Collecting details for {tenant_count} tenant cluster issues...")
            tenant_details = self.detailed_collector_tenant.collect_details_for_issues(
                issues_by_cluster_type['tenant'], 
                resources_dir
            )
            detailed_info.extend(tenant_details)
        elif tenant_count > 0 and not self.detailed_collector_tenant:
            self.logger.warning(f"Tenant cluster issues found but no tenant collector available")
        
        # resourcesディレクトリは詳細情報収集時に作成される
        if any(d.get('saved_files') for d in detailed_info):
            os.makedirs(resources_dir, exist_ok=True)
            self.logger.info(f"Created resources directory: {resources_dir}")
        
        self.diagnosis_result['detailed_logs'] = detailed_info
        self.logger.info(f"Collected detailed information for {len(detailed_info)} resources")
    
    def _generate_statistics(self):
        """統計情報の生成"""
        issues = self.diagnosis_result.get('issues_found', [])
        
        if self.anomaly_detector:
            stats = self.anomaly_detector.get_summary_stats(issues)
            self.diagnosis_result['summary_stats'] = stats
    
    def _output_results(self):
        """結果の出力"""
        # 診断データをフォーマット（Markdown用）
        formatted_data = self._format_for_report()
        
        # Markdownサマリー生成
        markdown_content = self.markdown_reporter.generate_summary_report(formatted_data)
        md_output_path = os.path.join(self.output_dir, 'summary.md')
        self.markdown_reporter.save_to_file(markdown_content, md_output_path)
        self.logger.info(f"Diagnosis report saved to: {md_output_path}")
    
    def _format_for_report(self) -> Dict:
        """レポート生成用にデータをフォーマット"""
        issues = self.diagnosis_result.get('issues_found', [])
        
        # リソース収集エラーをチェック
        resource_collection_error = self.diagnosis_result.get('resource_collection_error', {})
        if resource_collection_error.get('occurred'):
            # リソース収集エラーをissueとして追加
            issues.append({
                'severity': 'critical',
                'issue_type': 'ResourceCollectionFailed',
                'resource_name': 'Kubernetes Cluster',
                'resource_type': 'Cluster',
                'message': resource_collection_error.get('message', 'リソース収集が失敗しました'),
                'namespace': 'N/A'
            })
        
        # severity別にissueを分類
        issues_by_severity = {
            'critical': [i for i in issues if i.get('severity') == 'critical'],
            'warning': [i for i in issues if i.get('severity') == 'warning']
        }
        
        return {
            'metadata': {
                'script_name': self.diagnosis_result.get('script_name', 'Unknown'),
                'diagnosis_timestamp': self.diagnosis_result.get('timestamp', datetime.now().isoformat()),
                'diagnosis_start_time': self.diagnosis_result.get('diagnosis_start_time'),
                'diagnosis_end_time': self.diagnosis_result.get('diagnosis_end_time'),
                'diagnosis_duration': self.diagnosis_result.get('diagnosis_duration'),
            },
            'log_analysis': {
                'playbooks_executed': self.diagnosis_result.get('log_analysis', {}).get('playbooks_executed', []),
                'log_directory': self.diagnosis_result.get('log_analysis', {}).get('log_directory', ''),
                'log_files': self.diagnosis_result.get('log_analysis', {}).get('log_files', []),
                'errors_from_logs': self.diagnosis_result.get('log_analysis', {}).get('errors', []),
                'warnings_from_logs': self.diagnosis_result.get('log_analysis', {}).get('warnings', []),
            },
            'resource_status': self._format_resource_status(),
            'issues_detected': {
                'total_count': len(issues),
                'all_issues': issues,
                'by_severity': issues_by_severity
            },
            'detailed_logs': self.diagnosis_result.get('detailed_logs', []),
            'summary': {
                'overall_status': self._determine_status(),
                'critical_issues_count': len(issues_by_severity['critical']),
                'warning_issues_count': len(issues_by_severity['warning']),
            },
        }
    
    def _format_resource_status(self) -> Dict:
        """リソース状態をレポート用にフォーマット"""
        resource_checks = self.diagnosis_result.get('resource_checks', {})
        resources = []
        resources_by_cluster = {
            'manager': [],
            'tenant': []
        }
        
        # resource_checksから各リソースの情報を抽出
        for resource_key, resource_info in resource_checks.items():
            if resource_key in ['collection_failed', 'error']:
                continue
            
            if isinstance(resource_info, dict) and 'spec' in resource_info:
                spec = resource_info['spec']
                resource_data = {
                    'kind': spec.get('kind', 'Unknown'),
                    'namespace': spec.get('namespace', ''),
                    'index': spec.get('_index', 0),
                    'description': spec.get('description', ''),
                    'wide_text': resource_info.get('wide_text', '')
                }
                
                # クラスタ別に分類
                cluster_type = spec.get('_cluster_type', 'manager')
                if cluster_type in resources_by_cluster:
                    resources_by_cluster[cluster_type].append(resource_data)
                
                # 後方互換性のためフラットリストにも追加
                resources.append(resource_data)
        
        return {
            'resources': resources,
            'resources_by_cluster': resources_by_cluster
        }
    
    def _determine_status(self) -> str:
        """全体ステータスを判定"""
        issues = self.diagnosis_result.get('issues_found', [])
        log_errors = self.diagnosis_result.get('log_analysis', {}).get('errors', [])
        
        # リソース異常の critical または ログエラーがある場合は critical
        if any(i.get('severity') == 'critical' for i in issues) or len(log_errors) > 0:
            return 'critical'
        elif any(i.get('severity') == 'warning' for i in issues):
            return 'warning'
        return 'healthy'
    
    def cleanup(self):
        """リソースのクリーンアップ（Ansible方式では不要）"""
        pass


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description='DCI Diagnosis Engine - Analyze automation script results'
    )
    
    parser.add_argument(
        '--script-name',
        required=True,
        help='Name of the automation script (e.g., manager_cluster_setup)'
    )
    
    parser.add_argument(
        '--log-dir',
        required=True,
        help='Path to the log directory'
    )
    
    parser.add_argument(
        '--inventory-path',
        required=True,
        help='Path to Ansible inventory file'
    )
    
    parser.add_argument(
        '--output-dir',
        required=True,
        help='Output directory for diagnosis reports'
    )
    
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=600,
        help='Timeout in seconds for operations'
    )
    
    args = parser.parse_args()
    
    # 診断エンジンの実行
    engine = DiagnosisEngine(args)
    
    try:
        engine.initialize()
        engine.run_diagnosis()
        
        # 診断結果に基づく終了コード判定
        issues = engine.diagnosis_result.get('issues_found', [])
        
        # リソース状態の問題のみをカウント（ログエラーは除外）
        resource_critical_count = len([i for i in issues if i.get('severity') == 'critical'])
        resource_warning_count = len([i for i in issues if i.get('severity') == 'warning'])
        
        # 終了コードの判定（リソース状態の問題に基づく）
        if resource_critical_count > 0:
            print(f"\n[WARNING] 終了コード2: リソース状態の重大な問題が{resource_critical_count}件見つかりました")
            exit_code = 2  # リソース状態の重大な問題あり
        elif resource_warning_count > 0:
            print(f"\n[WARNING] 終了コード3: リソース状態の警告が{resource_warning_count}件見つかりました")
            exit_code = 3  # リソース状態の警告あり
        else:
            print("\n[SUCCESS] 終了コード0: 診断が正常に完了しました")
            exit_code = 0  # 診断完了・リソース状態の問題なし
    
    except DiagnosisError as e:
        # カスタム例外は詳細にフォーマットして表示
        format_error(e, sys.stderr)
        print(f"\n[ERROR] 終了コード1: 診断処理が失敗しました: {e.message}", file=sys.stderr)
        exit_code = 1  # 診断自体が失敗
        
    except Exception as e:
        print(f"\n[ERROR] 終了コード1: 予期しないエラーが発生しました: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        exit_code = 1  # 診断自体が失敗
        
    finally:
        engine.cleanup()
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
