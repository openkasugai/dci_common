#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kubernetesリソース収集モジュール
外部Playbook テンプレート（Jinja2）を使用して、一度の実行で全リソースを取得します。
"""

import json
import re
from typing import Dict, List, Optional, Any
import os
import subprocess
import logging
import tempfile
import time
import yaml as yaml_lib
import base64
from jinja2 import Environment, FileSystemLoader
from exceptions import (
    TemplateRenderError, PlaybookExecutionError,
    ResourceCollectionError, ParseError, RemoteAccessError
)


def extract_json_from_ansible_output(ansible_output: str, context: str = "") -> Optional[str]:
    """
    Ansible出力から純粋なJSON部分を抽出する（正規表現ベース）
    
    Args:
        ansible_output: Ansibleコマンドの標準出力
        context: ログ用のコンテキスト情報
    
    Returns:
        抽出されたJSON文字列、または失敗時はNone
    
    Examples:
        >>> output = "d1-host | SUCCESS => {\\n  \"key\": \"value\"\\n}"
        >>> extract_json_from_ansible_output(output)
        '{"key": "value"}'
    """
    if not ansible_output:
        return None
    
    # パターン1: "=> " の後のJSON（slurpモジュールなど）
    # 非貪欲マッチでJSON全体を取得
    match = re.search(r'=>\s*(\{.*\})\s*$', ansible_output, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # パターン2: ">>" の後のJSON（raw/commandモジュール）
    match = re.search(r'>>\s*(\{.*\})', ansible_output, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # パターン3: 行頭から始まるJSON（Ansibleプロンプトなし）
    match = re.search(r'^\s*(\{.*\})\s*$', ansible_output, re.DOTALL | re.MULTILINE)
    if match:
        return match.group(1).strip()
    
    # どのパターンにもマッチしない場合
    logger = logging.getLogger(__name__)
    logger.debug(
        f"Failed to extract JSON from Ansible output{f' ({context})' if context else ''}. "
        f"Output preview: {ansible_output[:200]}"
    )
    return None


class KubernetesCollector:
    """Kubernetesリソースを収集するクラス（Ansible Playbook方式）"""
    
    def __init__(self, script_root: str, target_host: str = "dci_mgmt_k8s_control_plane[0]", output_dir: str = None, ansible_vars: Dict = None, kubeconfig_path: str = None):
        """
        Args:
            script_root: 自動化スクリプトのルートディレクトリ（例: ../manager_cluster_setup）
            target_host: Ansibleのターゲット指定（デフォルト: dci_mgmt_k8s_control_plane[0]）
            output_dir: 診断レポート出力ディレクトリ（エラーログ保存先、デフォルト: /tmp）
            ansible_vars: Ansible vars（テナント情報など）
            kubeconfig_path: kubeconfigファイルパス（テナントクラスタ用、デフォルト: $HOME/.kube/config）
        """
        self.script_root = os.path.abspath(script_root)
        self.inventory = os.path.abspath(os.path.join(script_root, 'ansible/inventory/hosts'))
        self.vault_pass = os.path.abspath(os.path.join(script_root, 'ansible/.vault_pass'))
        self.output_dir = output_dir if output_dir else '/tmp'
        self.ansible_vars = ansible_vars if ansible_vars else {}
        
        # ansible.cfgの選択: 診断ツール専用 > 自動化スクリプト
        diagnosis_tool_dir = os.path.dirname(os.path.dirname(__file__))
        diagnosis_ansible_cfg = os.path.join(diagnosis_tool_dir, 'ansible.cfg')
        script_ansible_cfg = os.path.abspath(os.path.join(script_root, 'ansible/ansible.cfg'))
        
        if os.path.exists(diagnosis_ansible_cfg):
            self.ansible_cfg = diagnosis_ansible_cfg
            self.ansible_cfg_source = 'diagnosis_tool'
        else:
            self.ansible_cfg = script_ansible_cfg
            self.ansible_cfg_source = 'automation_script'
        
        self.target_host = target_host
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Using ansible.cfg from {self.ansible_cfg_source}: {self.ansible_cfg}")
        # kubeconfigパスはリモートホストのHOMEディレクトリを使用
        self.kubeconfig = kubeconfig_path if kubeconfig_path else "$HOME/.kube/config"
        # Playbookテンプレートのパス
        self.playbook_template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'playbooks')
        self.playbook_template_file = 'k8s_collector.yaml.j2'
        # Playbookタイムアウト（環境変数から取得）
        self.playbook_timeout = int(os.environ.get('K8S_COLLECTOR_TIMEOUT'))
        # リソースキャッシュ
        self._cache = {
            'nodes': None,
            'namespaces': None,
            'pods': {},  # namespace -> pods
            'pods_wide': None,  # kubectl get pod -A -o wide のテキスト出力
            'namespaces_wide': None  # kubectl get namespace -o wide のテキスト出力
        }
        self._cache_loaded = False

    def _render_playbook_from_template(self, generic_resources: List[Dict], cluster_type: str = 'manager', 
                                       tenant_namespace: str = None, tenant_kubeconfig_file: str = None) -> str:
        """
        外部Playbookテンプレートをレンダリングして一時ファイルを生成（汎用リソース対応）
        Args:
            generic_resources: resource_mappingsからの汎用リソース定義リスト
            cluster_type: クラスタタイプ ('manager' or 'tenant')
            tenant_namespace: テナント名前空間 (cluster_type='tenant'の場合)
            tenant_kubeconfig_file: テナントkubeconfigファイル名 (cluster_type='tenant'の場合)
        Returns:
            生成したPlaybookファイルのパス
        """
        try:
            # Jinja2環境を設定
            self.logger.debug(f"Loading template from directory: {self.playbook_template_dir}")
            env = Environment(loader=FileSystemLoader(self.playbook_template_dir))
            template = env.get_template(self.playbook_template_file)
            
            # テンプレート変数を準備
            template_vars = {
                'target_host': self.target_host,
                'generic_resources': generic_resources,
                'cluster_type': cluster_type
            }
            
            # テナントクラスタの場合、追加情報を設定
            if cluster_type == 'tenant':
                template_vars['tenant_namespace'] = tenant_namespace
                template_vars['tenant_kubeconfig_file'] = tenant_kubeconfig_file
                self.logger.info(f"Rendering template for tenant cluster: {tenant_namespace}")
            else:
                self.logger.debug(f"Rendering template for manager cluster")
            
            self.logger.debug(f"Rendering template with {len(generic_resources)} generic resources")
            
            # テンプレートをレンダリング
            rendered_playbook = template.render(template_vars)
            
            # 一時ファイルに書き込み
            fd, playbook_path = tempfile.mkstemp(suffix='.yaml', prefix='diagnosis_k8s_collector_')
            try:
                with os.fdopen(fd, 'w') as f:
                    f.write(rendered_playbook)
                self.logger.debug(f"Rendered playbook to: {playbook_path}")
                return playbook_path
            except Exception as e:
                os.close(fd)
                raise TemplateRenderError(
                    f"Playbookテンプレートの一時ファイルへの書き込みに失敗しました",
                    template_file=os.path.join(self.playbook_template_dir, self.playbook_template_file),
                    template_vars=template_vars,
                    step="Playbookテンプレートレンダリング",
                    context={
                        'playbook_path': playbook_path,
                        'resources_count': len(generic_resources)
                    },
                    suggestion="一時ファイルの書き込み権限を確認してください",
                    original_error=e
                )
                
        except TemplateRenderError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to render playbook template: {e}")
            template_path = os.path.join(self.playbook_template_dir, self.playbook_template_file)
            raise TemplateRenderError(
                f"Playbookテンプレートのレンダリングに失敗しました",
                template_file=template_path,
                template_vars={'target_host': self.target_host, 'generic_resources_count': len(generic_resources)},
                step="Playbookテンプレートレンダリング",
                context={
                    'template_dir': self.playbook_template_dir,
                    'template_file': self.playbook_template_file,
                    'resources_count': len(generic_resources)
                },
                suggestion="以下を確認してください:\n"
                    f"  1. テンプレートファイルが存在するか: {template_path}\n"
                    "  2. Jinja2パッケージがインストールされているか\n"
                    "  3. テンプレートの文法が正しいか",
                original_error=e
            )

    def _execute_playbook(self, playbook_path: str) -> tuple:
        """
        Playbookを実行
        Args:
            playbook_path: Playbookファイルのパス
        Returns:
            (success: bool, error: str)
        """
        ansible_cmd = [
            'ansible-playbook',
            playbook_path,
            '-i', self.inventory
        ]
        if os.path.exists(self.vault_pass):
            ansible_cmd.extend(['--vault-password-file', self.vault_pass])
        
        env = os.environ.copy()
        env['ANSIBLE_CONFIG'] = self.ansible_cfg
        # カスタムコールバックプラグインを完全に無効化
        env.pop('ANSIBLE_CALLBACK_PLUGINS', None)
        env.pop('ANSIBLE_CALLBACKS_ENABLED', None)
        env['ANSIBLE_LOAD_CALLBACK_PLUGINS'] = '0'
        env['ANSIBLE_STDOUT_CALLBACK'] = 'default'
        
        try:
            self.logger.debug(f"Executing playbook: {' '.join(ansible_cmd)}")
            self.logger.debug(f"Using ansible.cfg: {self.ansible_cfg} (source: {self.ansible_cfg_source})")
            self.logger.debug(f"Timeout: {self.playbook_timeout} seconds")
            
            # 実行時間計測開始
            start_time = time.time()
            
            # タイムアウトは環境変数K8S_COLLECTOR_TIMEOUTで設定可能（デフォルト180秒）
            result = subprocess.run(ansible_cmd, env=env, capture_output=True, text=True, timeout=self.playbook_timeout)
            
            # 実行時間計測終了
            duration = time.time() - start_time
            
            if result.returncode != 0:
                error_msg = result.stderr
                
                # エラー種別を判定
                error_type = 'runtime'
                if 'UNREACHABLE' in error_msg or 'Failed to connect' in error_msg:
                    error_type = 'ssh'
                elif 'permission denied' in error_msg.lower() or 'authentication' in error_msg.lower():
                    error_type = 'auth'
                elif 'ERROR!' in error_msg or 'syntax' in error_msg.lower():
                    error_type = 'syntax'
                
                # デバッグ: stderrの全文をログ出力
                self.logger.error(f"Ansible stderr (full):\n{error_msg}")
                
                # デバッグ: playbookファイルを保存
                debug_playbook_path = os.path.join(self.output_dir, f"diagnosis_playbook_debug_{os.path.basename(playbook_path)}")
                try:
                    import shutil
                    shutil.copy(playbook_path, debug_playbook_path)
                    self.logger.error(f"Playbook saved for debugging: {debug_playbook_path}")
                except Exception as copy_err:
                    self.logger.warning(f"Failed to save debug playbook: {copy_err}")
                
                # ansible実行ログを保存
                ansible_error_log_path = os.path.join(self.output_dir, "ansible_error.log")
                try:
                    with open(ansible_error_log_path, 'w', encoding='utf-8') as f:
                        f.write("=" * 80 + "\n")
                        f.write("Ansible Playbook Execution Error Log\n")
                        f.write("=" * 80 + "\n\n")
                        f.write(f"Command: {' '.join(ansible_cmd)}\n")
                        f.write(f"Return Code: {result.returncode}\n")
                        f.write(f"Duration: {duration:.2f} seconds\n")
                        f.write("\n" + "=" * 80 + "\n")
                        f.write("STDOUT:\n")
                        f.write("=" * 80 + "\n")
                        f.write(result.stdout if result.stdout else "(empty)\n")
                        f.write("\n" + "=" * 80 + "\n")
                        f.write("STDERR:\n")
                        f.write("=" * 80 + "\n")
                        f.write(result.stderr if result.stderr else "(empty)\n")
                    self.logger.error(f"Ansible execution log saved to: {ansible_error_log_path}")
                except Exception as log_err:
                    self.logger.warning(f"Failed to save ansible error log: {log_err}")
                
                # stderrが長すぎる場合は先頭部分のみ保持（エラーメッセージ用）
                stderr_preview = error_msg[:5000] if len(error_msg) > 5000 else error_msg
                
                raise PlaybookExecutionError(
                    f"Ansible Playbookの実行に失敗しました (returncode: {result.returncode})",
                    playbook_path=playbook_path,
                    target_hosts=[self.target_host],
                    error_type=error_type,
                    ansible_stderr=stderr_preview,
                    step="Ansible Playbook実行",
                    context={
                        'inventory': self.inventory,
                        'vault_pass_exists': os.path.exists(self.vault_pass),
                        'ansible_config': self.ansible_cfg,
                        'timeout': self.playbook_timeout,
                        'debug_playbook_path': debug_playbook_path
                    },
                    suggestion=self._get_playbook_error_suggestion(error_type),
                    log_locations=['/tmp/k8s_diagnosis/errors.log']
                )
            
            self.logger.debug("Playbook execution succeeded")
            return (True, "")
            
        except subprocess.TimeoutExpired:
            raise PlaybookExecutionError(
                f"Ansible Playbookの実行がタイムアウトしました ({self.playbook_timeout}秒)",
                playbook_path=playbook_path,
                target_hosts=[self.target_host],
                error_type='runtime',
                step="Ansible Playbook実行",
                context={
                    'timeout': self.playbook_timeout
                },
                suggestion=f"タイムアウト値を増やすには K8S_COLLECTOR_TIMEOUT 環境変数を設定してください\n"
                    f"例: export K8S_COLLECTOR_TIMEOUT=600"
            )
        except PlaybookExecutionError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to execute playbook: {e}")
            raise PlaybookExecutionError(
                f"Playbook実行中に予期しないエラーが発生しました",
                playbook_path=playbook_path,
                target_hosts=[self.target_host],
                step="Ansible Playbook実行",
                suggestion="ansible-playbook コマンドがインストールされているか確認してください",
                original_error=e
            )
    
    def _get_playbook_error_suggestion(self, error_type: str) -> str:
        """エラー種別に応じた推奨アクションを返す"""
        suggestions = {
            'ssh': (
                "SSH接続エラーが発生しました。以下を確認してください:\n"
                "  1. ターゲットホストが起動しているか\n"
                "  2. SSHキーが正しく設定されているか\n"
                "  3. ホスト名またはIPアドレスが正しいか\n"
                "  4. ファイアウォールがSSHポート(22)をブロックしていないか"
            ),
            'auth': (
                "認証エラーが発生しました。以下を確認してください:\n"
                "  1. SSHキーのパーミッションが正しいか (600 または 400)\n"
                "  2. Ansible Vaultパスワードが正しいか\n"
                "  3. ユーザー名が正しいか\n"
                "  4. sudo権限があるか"
            ),
            'syntax': (
                "Playbookの文法エラーが発生しました。以下を確認してください:\n"
                "  1. PlaybookテンプレートのYAML文法が正しいか\n"
                "  2. Ansibleのバージョンが互換性があるか\n"
                "  3. テンプレート変数が正しく渡されているか"
            ),
            'runtime': (
                "Playbook実行時エラーが発生しました。以下を確認してください:\n"
                "  1. ターゲットホスト上kubectlがインストールされているか\n"
                "  2. kubeconfigが正しく設定されているか\n"
                "  3. Kubernetesクラスターが正常に動作しているか\n"
                "  4. 必要なRBAC権限があるか"
            )
        }
        return suggestions.get(error_type, "詳細はAnsibleのエラーメッセージを確認してください")

    def _fetch_results(self, namespaces: List[str]) -> Optional[Dict]:
        """
        リモートから結果ファイルを取得（個別ファイル方式）
        Args:
            namespaces: チェック対象のNamespaceリスト
        Returns:
            結果の辞書、または失敗時はNone
        """
        try:
            results = {
                'nodes': '{}',
                'namespaces': '{}',
                'pods': {},
                'pods_wide': '',
                'namespaces_wide': ''
            }
            
            failed_resources = []
            
            # 完了マーカーを確認
            completion_data = self._fetch_single_file('/tmp/k8s_diagnosis/.complete')
            if completion_data:
                try:
                    completion_info = json.loads(completion_data)
                    self.logger.debug(f"Completion info: {completion_info}")
                except json.JSONDecodeError:
                    # 旧形式（"success"文字列のみ）の場合は警告のみ
                    self.logger.debug("Old format completion marker detected")
            
            # ノード情報を取得
            nodes_data = self._fetch_single_file('/tmp/k8s_diagnosis/nodes.json')
            if nodes_data:
                results['nodes'] = nodes_data
            else:
                failed_resources.append('nodes')
                self.logger.warning("Failed to fetch nodes data")
            
            # Namespace情報を取得
            ns_data = self._fetch_single_file('/tmp/k8s_diagnosis/namespaces.json')
            if ns_data:
                results['namespaces'] = ns_data
            else:
                failed_resources.append('namespaces')
                self.logger.warning("Failed to fetch namespaces data")
            
            # 各NamespaceのPod情報を取得
            for ns in namespaces:
                pod_data = self._fetch_single_file(f'/tmp/k8s_diagnosis/pods_{ns}.json')
                if pod_data:
                    results['pods'][ns] = pod_data
                else:
                    failed_resources.append(f'pods_{ns}')
                    self.logger.warning(f"Failed to fetch pods data for namespace: {ns}")
            
            # -o wide 形式のテキスト出力を取得（オプショナル）
            pods_wide_data = self._fetch_single_file('/tmp/k8s_diagnosis/pods_wide.txt')
            if pods_wide_data:
                results['pods_wide'] = pods_wide_data
            else:
                self.logger.debug("Failed to fetch pods wide output (may not be generated by older playbook)")
            
            namespaces_wide_data = self._fetch_single_file('/tmp/k8s_diagnosis/namespaces_wide.txt')
            if namespaces_wide_data:
                results['namespaces_wide'] = namespaces_wide_data
            else:
                self.logger.debug("Failed to fetch namespaces wide output (may not be generated by older playbook)")
            
            # 必須リソース（nodes、namespaces）が取得できない場合は失敗とする
            if 'nodes' in failed_resources or 'namespaces' in failed_resources:
                self.logger.error(f"Failed to fetch critical resources: {failed_resources}")
                # エラーファイルの内容を確認
                error_log = self._fetch_single_file('/tmp/k8s_diagnosis/errors.log')
                error_detail = ""
                if error_log:
                    self.logger.error(f"Remote error log:\n{error_log}")
                    error_detail = error_log[:1000]  # 最初の1000文字のみ
                
                raise ResourceCollectionError(
                    f"重要なKubernetesリソースの取得に失敗しました: {', '.join(failed_resources)}",
                    failed_resources=failed_resources,
                    step="リモートリソース取得",
                    context={
                        'target_namespaces': namespaces,
                        'remote_error_log': error_detail if error_detail else "(取得できず)"
                    },
                    suggestion="以下を確認してください:\n"
                        "  1. リモートホスト上で kubectl が正しく動作するか\n"
                        "  2. kubeconfig が正しく設定されているか\n"
                        "  3. RBAC 権限が十分か\n"
                        "  4. リモートエラーログを確認: ssh <control-plane-node> cat /tmp/k8s_diagnosis/errors.log",
                    log_locations=['/tmp/k8s_diagnosis/errors.log']
                )
            
            if failed_resources:
                self.logger.warning(f"Some resources failed to fetch: {failed_resources}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to fetch results: {e}")
            return None
    
    def _fetch_single_file(self, remote_path: str) -> Optional[str]:
        """
        リモートから単一ファイルを取得
        Args:
            remote_path: リモートファイルのパス
        Returns:
            ファイル内容（文字列）、または失敗時はNone
        """
        # 一時的なansible.cfgを使用してカスタムコールバックを無効化
        # callback_pluginsディレクトリを参照しない設定にする
        # self.inventoryは__init__で絶対パスに変換済み
        temp_cfg_content = f"""[defaults]
inventory = {self.inventory}
host_key_checking = False
stdout_callback = default
verbosity = 0
"""
        # callback_pluginsの設定は意図的に含めない
        # callbacks_enabled も設定しない（デフォルトで無効）
        
        # 一時的なansible.cfgファイルを作成
        import tempfile
        fd, temp_cfg_path = tempfile.mkstemp(suffix='.cfg', prefix='ansible_')
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(temp_cfg_content)
        except:
            os.close(fd)
            raise
        
        ansible_cmd = [
            'ansible', self.target_host,
            '-i', self.inventory,
            '-m', 'slurp',
            '-a', f'src={remote_path}'
        ]
        if os.path.exists(self.vault_pass):
            ansible_cmd.extend(['--vault-password-file', self.vault_pass])
        
        env = os.environ.copy()
        env['ANSIBLE_CONFIG'] = temp_cfg_path
        # 念のため環境変数でも明示的に無効化
        env['ANSIBLE_STDOUT_CALLBACK'] = 'default'
        # カスタムコールバックプラグインを完全に無効化
        env.pop('ANSIBLE_CALLBACK_PLUGINS', None)
        env.pop('ANSIBLE_CALLBACKS_ENABLED', None)
        
        try:
            result = subprocess.run(ansible_cmd, env=env, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                self.logger.debug(f"File not found or failed to fetch: {remote_path}, stderr: {result.stderr[:200]}")
                return None
            
            # デバッグ: stdout/stderr の内容を確認
            if not result.stdout or result.stdout.strip() == '':
                self.logger.warning(f"Empty stdout from Ansible for {remote_path}. stderr: {result.stderr[:500] if result.stderr else 'N/A'}")
                return None
            
            # Ansibleの標準出力からJSON部分を抽出（改善版：正規表現ベース）
            json_text = extract_json_from_ansible_output(
                result.stdout,
                context=f"slurp {remote_path}"
            )
            
            if not json_text:
                self.logger.warning(
                    f"No JSON output found in Ansible response for {remote_path}. "
                    f"Output preview: {result.stdout[:300]}"
                )
                return None
            
            # JSONをパース
            try:
                ansible_output = json.loads(json_text)
            except json.JSONDecodeError as e:
                self.logger.warning(
                    f"Failed to parse JSON from Ansible output for {remote_path}: {e}. "
                    f"JSON text preview: {json_text[:200]}"
                )
                return None
            
            # slurpモジュールはbase64エンコードされた内容を'content'キーで返す
            if 'content' in ansible_output:
                try:
                    content = base64.b64decode(ansible_output['content']).decode('utf-8')
                    return content
                except Exception as e:
                    self.logger.warning(f"Failed to decode base64 content for {remote_path}: {e}")
                    return None
            
            self.logger.warning(
                f"No 'content' key found in Ansible output for {remote_path}. "
                f"Keys: {list(ansible_output.keys())}"
            )
            return None
        except Exception as e:
            self.logger.warning(f"Failed to fetch single file {remote_path}: {e}")
            return None
        finally:
            # 一時ファイルを削除
            try:
                os.unlink(temp_cfg_path)
            except:
                pass

    def collect_all_resources(self, namespaces: List[str]) -> bool:
        """
        全リソースを一度に収集してキャッシュに格納
        Args:
            namespaces: チェック対象のNamespace リスト
        Returns:
            成功した場合True
        """
        if self._cache_loaded:
            self.logger.debug("Using cached resources")
            return True
        
        self.logger.info(f"Collecting all Kubernetes resources (namespaces: {namespaces})")
        
        playbook_path = None
        try:
            # Playbookをテンプレートからレンダリング
            playbook_path = self._render_playbook_from_template(namespaces)
            self.logger.debug(f"Rendered playbook template: {playbook_path}")
            
            # Playbookを実行
            success, error = self._execute_playbook(playbook_path)
            if not success:
                self.logger.error(f"Failed to execute playbook: {error}")
                return False
            
            # 結果を取得
            results = self._fetch_results(namespaces)
            if not results:
                self.logger.error("Failed to fetch results")
                return False
            
            # キャッシュに格納（データ検証付き）
            nodes_data = results.get('nodes', '{}')
            namespaces_data = results.get('namespaces', '{}')
            pods_data = results.get('pods', {})
            
            # データ検証: 空データや不正データの検出
            if not nodes_data or nodes_data == '{}':
                self.logger.error("Nodes data is empty or invalid")
                return False
            
            if not namespaces_data or namespaces_data == '{}':
                self.logger.error("Namespaces data is empty or invalid")
                return False
            
            # JSONとして解析可能か確認
            try:
                json.loads(nodes_data)
                json.loads(namespaces_data)
                for ns, pod_data in pods_data.items():
                    if pod_data and pod_data != '{}':
                        json.loads(pod_data)
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON in collected data: {e}")
                return False
            
            self._cache['nodes'] = nodes_data
            self._cache['namespaces'] = namespaces_data
            self._cache['pods'] = pods_data
            self._cache['pods_wide'] = results.get('pods_wide', '')
            self._cache['namespaces_wide'] = results.get('namespaces_wide', '')
            self._cache_loaded = True
            
            self.logger.info("Successfully collected all resources")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to collect resources: {e}")
            return False
        finally:
            # 一時Playbookファイルを削除
            if playbook_path and os.path.exists(playbook_path):
                try:
                    os.unlink(playbook_path)
                except Exception as e:
                    self.logger.warning(f"Failed to delete temporary playbook: {e}")
    
    def collect_generic_resources(self, generic_resources_specs: List[Dict]) -> Dict[str, Dict]:
        """
        汎用リソース定義に基づいて全リソースを収集（新方式）
        
        Args:
            generic_resources_specs: resource_mappingsからのgeneric_resources定義リスト
                                     各要素は_indexフィールドを含む必要がある
        
        Returns:
            収集結果の辞書 {resource_key: {'data': [正規化されたリソースリスト], 'wide_text': 'kubectl get -o wide出力', 'spec': spec}}
        """
        self.logger.info(f"Collecting {len(generic_resources_specs)} generic resources")
        
        # cluster_typeを判定（全リソースが同じcluster_typeを持つ前提）
        cluster_type = 'manager'
        tenant_namespace = None
        tenant_kubeconfig_file = None
        
        if generic_resources_specs:
            cluster_type = generic_resources_specs[0].get('_cluster_type', 'manager')
            self.logger.info(f"Detected cluster_type: {cluster_type}")
            
            # テナントクラスタの場合、テナント情報を取得
            if cluster_type == 'tenant':
                tenants = self.ansible_vars.get('tenants', [])
                if tenants and isinstance(tenants, list) and len(tenants) > 0:
                    first_tenant = tenants[0]
                    tenant_namespace = first_tenant.get('tenant_namespace')
                    tenant_kubeconfig_file = first_tenant.get('kubeconfig_file', f'{tenant_namespace}.kubeconfig')
                    self.logger.info(f"Using tenant: {tenant_namespace}, kubeconfig: {tenant_kubeconfig_file}")
                else:
                    self.logger.warning("cluster_type is 'tenant' but no tenant information found in ansible_vars")
                    # テナント情報がない場合はmanagerにフォールバック
                    cluster_type = 'manager'
        
        playbook_path = None
        try:
            # Playbookをテンプレートからレンダリング
            playbook_path = self._render_playbook_from_template(
                generic_resources_specs, 
                cluster_type=cluster_type,
                tenant_namespace=tenant_namespace,
                tenant_kubeconfig_file=tenant_kubeconfig_file
            )
            self.logger.debug(f"Rendered playbook template: {playbook_path}")
            
            # Playbookを実行
            success, error = self._execute_playbook(playbook_path)
            if not success:
                self.logger.error(f"Failed to execute playbook: {error}")
                return {}
            
            # 結果を収集
            results = {}
            for spec in generic_resources_specs:
                resource_key = self._make_resource_key(spec)
                resources = self._fetch_and_parse_resource(spec)
                wide_text = self._fetch_wide_output_for_resource(spec)
                
                if resources is not None:
                    results[resource_key] = {
                        'data': resources,
                        'wide_text': wide_text,
                        'spec': spec
                    }
                    self.logger.debug(f"Collected {len(resources)} {spec.get('kind')} resources")
                else:
                    self.logger.warning(f"Failed to collect {spec.get('kind')} resources")
                    results[resource_key] = {
                        'data': [],
                        'wide_text': wide_text,
                        'spec': spec
                    }
            
            self.logger.info(f"Successfully collected {len(results)} resource types")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to collect generic resources: {e}")
            raise
        finally:
            # 一時Playbookファイルを削除
            if playbook_path and os.path.exists(playbook_path):
                try:
                    os.unlink(playbook_path)
                except Exception as e:
                    self.logger.warning(f"Failed to delete temporary playbook: {e}")
    
    def _make_resource_key(self, spec: Dict) -> str:
        """
        リソースキーを生成（cluster_type識別子を含む）
        
        Args:
            spec: リソース定義辞書（_cluster_type, kind, namespace, _indexを含む）
        
        Returns:
            クラスタタイプで区別されたリソースキー（例: 'manager:pod_kube-system_1', 'tenant:pod_argo-events_3'）
        """
        cluster_type = spec.get('_cluster_type', 'manager')
        kind = spec.get('kind', '').lower()
        namespace = spec.get('namespace', '')
        index = spec.get('_index', 0)
        base_key = f"{kind}_{namespace}_{index}" if namespace else f"{kind}_{index}"
        resource_key = f"{cluster_type}:{base_key}"
        
        # デバッグ: キー生成の詳細を出力
        self.logger.debug(
            f"[KEY_GEN] Generated key: {resource_key} | "
            f"cluster_type={cluster_type} | kind={kind} | "
            f"namespace={namespace or 'N/A'} | index={index}"
        )
        
        return resource_key
    
    def _fetch_and_parse_resource(self, spec: Dict) -> Optional[List[Dict]]:
        """リモートホストからリソースJSONを取得して解析・正規化"""
        kind = spec.get('kind', '').lower()
        namespace = spec.get('namespace', '')
        index = spec.get('_index', 0)
        
        # ファイル名構築
        if namespace:
            filename = f"{kind}_{namespace}_{index}.json"
        else:
            filename = f"{kind}_{index}.json"
        
        remote_path = f"/tmp/k8s_diagnosis/{filename}"
        
        # SSH経由でファイル内容を取得
        try:
            json_content = self._fetch_single_file(remote_path)
            if not json_content:
                return None
            
            resource_data = json.loads(json_content)
            
            # Kubernetesリソースリストを正規化
            if 'items' in resource_data:
                return self._normalize_resources(resource_data['items'], spec)
            else:
                return [self._normalize_resource(resource_data, spec)]
        
        except Exception as e:
            self.logger.error(f"Error fetching {filename}: {e}")
            return None
    
    def _fetch_wide_output_for_resource(self, spec: Dict) -> str:
        """リモートホストからwide出力テキストを取得（kind別、namespace情報なし）"""
        kind = spec.get('kind', '').lower()
        
        # ファイル名構築（kindのみ、namespace/index情報なし）
        filename = f"{kind}_wide.txt"
        
        remote_path = f"/tmp/k8s_diagnosis/{filename}"
        
        # SSH経由でファイル内容を取得
        try:
            wide_text = self._fetch_single_file(remote_path)
            if not wide_text:
                self.logger.debug(f"Wide output not found: {filename}")
                return ''
            return wide_text
        except Exception as e:
            self.logger.debug(f"Error fetching wide output {filename}: {e}")
            return ''
    
    def _normalize_resources(self, items: List[Dict], spec: Dict) -> List[Dict]:
        """リソースリストを正規化"""
        return [self._normalize_resource(item, spec) for item in items]
    
    def _normalize_resource(self, item: Dict, spec: Dict) -> Dict:
        """
        個別リソースを正規化（kind毎の特別処理）
        
        Pod: status.phase, restarts等を抽出
        Node: status.conditions等を抽出
        その他: metadata.name等の基本情報のみ
        """
        kind = spec.get('kind', '').lower()
        
        normalized = {
            'name': item.get('metadata', {}).get('name', 'Unknown'),
            'kind': kind,
            'raw': item  # 元データ保持
        }
        
        # namespace（クラスタスコープリソースでは存在しない）
        if 'namespace' in item.get('metadata', {}):
            normalized['namespace'] = item['metadata']['namespace']
        
        # kind別の特別処理
        if kind == 'pod':
            self._normalize_pod(normalized, item)
        elif kind == 'node':
            self._normalize_node(normalized, item)
        elif kind == 'persistentvolumeclaim':
            self._normalize_pvc(normalized, item)
        
        return normalized
    
    def _normalize_pod(self, normalized: Dict, item: Dict):
        """Pod固有の正規化"""
        status = item.get('status', {})
        phase = status.get('phase', 'Unknown')
        normalized['status'] = phase  # デフォルトはphase
        
        # Ready状態の計算
        container_statuses = status.get('containerStatuses', [])
        ready_count = sum(1 for c in container_statuses if c.get('ready', False))
        total_count = len(container_statuses)
        normalized['ready'] = f"{ready_count}/{total_count}"
        
        # 再起動回数
        normalized['restarts'] = sum(
            c.get('restartCount', 0) for c in container_statuses
        )
        
        # コンテナステータスから詳細な状態を取得
        # waiting reason があれば、それを status として使用（CrashLoopBackOff, ImagePullBackOff など）
        for cs in container_statuses:
            state = cs.get('state', {})
            if 'waiting' in state:
                reason = state['waiting'].get('reason', '')
                if reason:
                    normalized['status'] = reason
                    break
        
        normalized['container_statuses'] = container_statuses
    
    def _normalize_node(self, normalized: Dict, item: Dict):
        """Node固有の正規化"""
        status = item.get('status', {})
        conditions = status.get('conditions', [])
        
        # Ready状態を判定
        ready_condition = next(
            (c for c in conditions if c.get('type') == 'Ready'),
            {}
        )
        normalized['status'] = 'Ready' if ready_condition.get('status') == 'True' else 'NotReady'
        normalized['conditions'] = conditions
    
    def _normalize_pvc(self, normalized: Dict, item: Dict):
        """PVC固有の正規化"""
        status = item.get('status', {})
        normalized['status'] = status.get('phase', 'Unknown')

    def _execute_kubectl(self, command: str) -> tuple:
        """
        Ansibleアドホックでkubectlコマンドを実行（フォールバック用）
        Args:
            command: kubectlコマンド（"kubectl"プレフィックスなし）
        Returns:
            (stdout, stderr, return_code)
        """
        ansible_cmd = [
            'ansible', self.target_host,
            '-i', self.inventory,
            '-m', 'shell',
            '-a', f'kubectl --kubeconfig={self.kubeconfig} {command}'
        ]
        if os.path.exists(self.vault_pass):
            ansible_cmd.extend(['--vault-password-file', self.vault_pass])
        
        env = os.environ.copy()
        env['ANSIBLE_CONFIG'] = self.ansible_cfg
        # カスタムコールバックプラグインを完全に無効化
        env.pop('ANSIBLE_CALLBACK_PLUGINS', None)
        env.pop('ANSIBLE_CALLBACKS_ENABLED', None)
        env['ANSIBLE_LOAD_CALLBACK_PLUGINS'] = '0'
        env['ANSIBLE_STDOUT_CALLBACK'] = 'default'
        self.logger.debug(f"Using ansible.cfg: {self.ansible_cfg} (source: {self.ansible_cfg_source})")
        
        try:
            result = subprocess.run(ansible_cmd, env=env, capture_output=True, text=True, timeout=30)
            
            # Ansible出力からkubectl結果を抽出（改善版：正規表現ベース）
            if result.returncode == 0 and result.stdout:
                # パターン1: ">>" の後のテキスト（shell/commandモジュール）
                match = re.search(r'>>\s*(.+)', result.stdout, re.DOTALL)
                if match:
                    kubectl_output = match.group(1).strip()
                    # JSON形式かどうかをチェック
                    if kubectl_output.startswith('{'):
                        # JSON出力の場合はそのまま返す
                        return (kubectl_output, '', 0)
                    else:
                        # テキスト出力の場合（describe、logs等）
                        return (kubectl_output, '', 0)
                
                # パターン2: "=> " の後のJSON（まれなケース）
                json_text = extract_json_from_ansible_output(result.stdout, context=f"kubectl {command}")
                if json_text:
                    return (json_text, '', 0)
                
                # どちらのパターンにもマッチしない場合
                self.logger.warning(
                    f"Could not extract kubectl output from Ansible response. "
                    f"Output preview: {result.stdout[:200]}"
                )
                return ("", "Failed to parse Ansible output", 1)
            else:
                # returncode が 0 以外、または出力が空の場合
                return (result.stdout, result.stderr, result.returncode)
            
            # ここには到達しない
            return (result.stdout, result.stderr, result.returncode)
            
        except Exception as e:
            self.logger.error(f"Failed to execute ansible kubectl command: {e}")
            return ("", str(e), -1)
    
    def get_nodes(self) -> List[Dict]:
        """ノード一覧と状態を取得"""
        # キャッシュから取得
        if self._cache_loaded and self._cache['nodes']:
            stdout = self._cache['nodes']
        else:
            # フォールバック: アドホック実行
            stdout, stderr, rc = self._execute_kubectl("get nodes -o json")
            if rc != 0:
                self.logger.error(f"Failed to get nodes: {stderr}")
                return []
        
        try:
            data = json.loads(stdout)
            nodes = []
            
            for item in data.get('items', []):
                node_info = {
                    'name': item['metadata']['name'],
                    'status': 'Unknown',
                    'roles': [],
                    'version': item['status'].get('nodeInfo', {}).get('kubeletVersion', 'Unknown'),
                    'conditions': []
                }
                
                # ロールを抽出
                labels = item['metadata'].get('labels', {})
                for key in labels:
                    if 'node-role.kubernetes.io/' in key:
                        role = key.replace('node-role.kubernetes.io/', '')
                        node_info['roles'].append(role)
                
                # 状態を抽出
                conditions = item['status'].get('conditions', [])
                for cond in conditions:
                    node_info['conditions'].append({
                        'type': cond['type'],
                        'status': cond['status'],
                        'reason': cond.get('reason', ''),
                        'message': cond.get('message', '')
                    })
                    
                    if cond['type'] == 'Ready':
                        node_info['status'] = 'Ready' if cond['status'] == 'True' else 'NotReady'
                
                nodes.append(node_info)
            
            return nodes
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse nodes JSON: {e}")
            # 元データのサンプルを取得
            data_sample = stdout[:500] if stdout else "(空)"
            raise ParseError(
                f"Node情報のJSONパースに失敗しました",
                parse_type='json',
                raw_data_sample=data_sample,
                step="Node情報の取得",
                context={
                    'data_length': len(stdout) if stdout else 0,
                    'cache_loaded': self._cache_loaded
                },
                suggestion="kubectl get nodes -o json を手動で実行して出力を確認してください",
                original_error=e
            )
    
    def get_pods(self, namespace: Optional[str] = None, 
                 label_selector: Optional[str] = None) -> List[Dict]:
        """
        Pod一覧と状態を取得
        
        Args:
            namespace: 対象Namespace（Noneの場合は全Namespace）
            label_selector: ラベルセレクタ
        
        Returns:
            Pod情報のリスト
        """
        # キャッシュから取得（label_selectorなしの場合のみ）
        if self._cache_loaded and namespace and not label_selector:
            if namespace in self._cache['pods']:
                stdout = self._cache['pods'][namespace]
                if stdout and stdout != '{}':
                    # キャッシュからパース
                    try:
                        data = json.loads(stdout)
                        return self._parse_pods(data)
                    except json.JSONDecodeError:
                        self.logger.warning(f"Failed to parse cached pods for {namespace}")
        
        # フォールバック: アドホック実行
        command = "get pods -o json"
        
        if namespace:
            command += f" -n {namespace}"
        else:
            command += " --all-namespaces"
        
        if label_selector:
            command += f" -l {label_selector}"
        
        stdout, stderr, rc = self._execute_kubectl(command)
        
        if rc != 0:
            self.logger.error(f"Failed to get pods: {stderr}")
            return []
        
        try:
            data = json.loads(stdout)
            return self._parse_pods(data)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse pods JSON: {e}")
            # 元データのサンプルを取得
            data_sample = stdout[:500] if stdout else "(空)"
            raise ParseError(
                f"Pod情報のJSONパースに失敗しました",
                parse_type='json',
                raw_data_sample=data_sample,
                step="Pod情報の取得",
                context={
                    'namespace': namespace,
                    'label_selector': label_selector,
                    'data_length': len(stdout) if stdout else 0,
                    'cache_loaded': self._cache_loaded
                },
                suggestion=f"kubectl get pods -n {namespace} -o json を手動で実行して出力を確認してください" if namespace else "kubectl get pods --all-namespaces -o json を手動で実行して出力を確認してください",
                original_error=e
            )
    
    def _parse_pods(self, data: Dict) -> List[Dict]:
        """Pod JSONデータをパース"""
        pods = []
        
        for item in data.get('items', []):
            pod_info = {
                'name': item['metadata']['name'],
                'namespace': item['metadata']['namespace'],
                'status': 'Unknown',
                'phase': item['status'].get('phase', 'Unknown'),
                'ready': '0/0',
                'restarts': 0,
                'node': item['spec'].get('nodeName', ''),
                'ip': item['status'].get('podIP', ''),
                'created': item['metadata'].get('creationTimestamp', 'N/A'),
                'conditions': [],
                'container_statuses': []
            }
            
            # Ready状態を計算
            container_statuses = item['status'].get('containerStatuses', [])
            ready_count = sum(1 for cs in container_statuses if cs.get('ready', False))
            total_count = len(container_statuses)
            pod_info['ready'] = f"{ready_count}/{total_count}"
            
            # 再起動回数を計算
            pod_info['restarts'] = sum(cs.get('restartCount', 0) for cs in container_statuses)
            
            # Pod全体のステータスを判定
            if pod_info['phase'] == 'Running' and ready_count == total_count:
                pod_info['status'] = 'Running'
            elif pod_info['phase'] == 'Pending':
                pod_info['status'] = 'Pending'
            elif pod_info['phase'] == 'Failed':
                pod_info['status'] = 'Failed'
            elif pod_info['phase'] == 'Succeeded':
                pod_info['status'] = 'Succeeded'
            else:
                # コンテナステータスから詳細を判定
                for cs in container_statuses:
                    state = cs.get('state', {})
                    if 'waiting' in state:
                        reason = state['waiting'].get('reason', '')
                        if reason in ['CrashLoopBackOff', 'ImagePullBackOff', 'ErrImagePull']:
                            pod_info['status'] = reason
                            break
            
            # Conditionsを抽出
            conditions = item['status'].get('conditions', [])
            for cond in conditions:
                pod_info['conditions'].append({
                    'type': cond['type'],
                    'status': cond['status'],
                    'reason': cond.get('reason', ''),
                    'message': cond.get('message', '')
                })
            
            # コンテナステータスを抽出
            for cs in container_statuses:
                container_info = {
                    'name': cs['name'],
                    'ready': cs.get('ready', False),
                    'restart_count': cs.get('restartCount', 0),
                    'state': {}
                }
                
                state = cs.get('state', {})
                if 'running' in state:
                    container_info['state'] = {'type': 'running'}
                elif 'waiting' in state:
                    container_info['state'] = {
                        'type': 'waiting',
                        'reason': state['waiting'].get('reason', ''),
                        'message': state['waiting'].get('message', '')
                    }
                elif 'terminated' in state:
                    container_info['state'] = {
                        'type': 'terminated',
                        'reason': state['terminated'].get('reason', ''),
                        'exit_code': state['terminated'].get('exitCode', 0)
                    }
                
                pod_info['container_statuses'].append(container_info)
            
            pods.append(pod_info)
        
        return pods
    
    def get_namespaces(self) -> List[Dict]:
        """Namespace一覧と詳細情報を取得"""
        # キャッシュから取得
        if self._cache_loaded and self._cache['namespaces']:
            stdout = self._cache['namespaces']
        else:
            # フォールバック: アドホック実行
            stdout, stderr, rc = self._execute_kubectl("get namespaces -o json")
            if rc != 0:
                self.logger.error(f"Failed to get namespaces: {stderr}")
                return []
        
        try:
            data = json.loads(stdout)
            namespaces = []
            for item in data.get('items', []):
                ns_info = {
                    'name': item['metadata']['name'],
                    'status': item['status'].get('phase', 'Unknown'),
                    'created': item['metadata'].get('creationTimestamp', 'N/A')
                }
                namespaces.append(ns_info)
            return namespaces
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse namespaces JSON: {e}")
            return []
    
    def check_resource_exists(self, resource_type: str, name: str, 
                             namespace: Optional[str] = None) -> bool:
        """
        指定されたリソースが存在するかチェック
        
        Args:
            resource_type: リソースタイプ（例: "deployment", "service"）
            name: リソース名
            namespace: Namespace（リソースがNamespace化されている場合）
        
        Returns:
            存在する場合True
        """
        command = f"get {resource_type} {name}"
        
        if namespace:
            command += f" -n {namespace}"
        
        stdout, stderr, rc = self._execute_kubectl(command)
        
        return rc == 0
