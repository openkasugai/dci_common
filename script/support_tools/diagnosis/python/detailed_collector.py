#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
詳細情報収集モジュール
異常が検出されたリソースの詳細情報（logs, describe, events）を収集します。
"""

import logging
import os
from typing import Dict, List, Optional


class DetailedCollector:
    """詳細情報を収集するクラス"""
    
    def __init__(self, k8s_collector):
        """
        Args:
            k8s_collector: K8sCollectorのインスタンス
        """
        self.k8s_collector = k8s_collector
        self.logger = logging.getLogger(__name__)
    
    def _save_to_file(self, content: str, filepath: str) -> bool:
        """
        コンテンツをファイルに保存
        
        Args:
            content: 保存する内容
            filepath: 保存先ファイルパス
        
        Returns:
            保存成功時True、失敗時False
        """
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            self.logger.debug(f"Successfully saved to {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save to {filepath}: {e}")
            return False
    
    def collect_pod_logs(self, pod_name: str, namespace: str, 
                        tail_lines: int = 100) -> Dict:
        """
        Podのログを収集
        
        Args:
            pod_name: Pod名
            namespace: Namespace
            tail_lines: 取得する行数
        
        Returns:
            ログ情報の辞書
        """
        result = {
            'pod_name': pod_name,
            'namespace': namespace,
            'logs': {},
            'errors': [],
            'summary': {
                'total_containers': 0,
                'logs_collected': 0,
                'logs_failed': 0
            }
        }
        
        # 全コンテナのログを取得
        command = f"get pod {pod_name} -n {namespace} -o jsonpath='{{.spec.containers[*].name}}'"
        stdout, stderr, rc = self.k8s_collector._execute_kubectl(command)
        
        if rc != 0:
            error_msg = f"コンテナ名の取得に失敗: {stderr}"
            self.logger.warning(f"Pod {pod_name} ({namespace}): {error_msg}")
            result['errors'].append(error_msg)
            return result
        
        if not stdout or not stdout.strip():
            error_msg = "コンテナ名の取得結果が空です"
            self.logger.warning(f"Pod {pod_name} ({namespace}): {error_msg}")
            result['errors'].append(error_msg)
            return result
        
        container_names = stdout.strip().split()
        
        # コンテナ名の妥当性チェック（不正な文字列をフィルタリング）
        # Kubernetes のコンテナ名は英数字、ハイフン、アンダースコア、ドットのみ許可
        invalid_names = []
        valid_names = []
        for name in container_names:
            # 明らかにコンテナ名ではない文字列を除外
            if name in ['ansible', 'config', 'file', 'module', 'search', 'path', 
                       'location', 'executable', 'python', 'version', 'collection',
                       'configured', '[core', '=', '[GCC'] or \
               '/' in name or name.endswith(']') or name.startswith('['):
                invalid_names.append(name)
            elif name and all(c.isalnum() or c in '-_.' for c in name):
                valid_names.append(name)
            else:
                invalid_names.append(name)
        
        if invalid_names:
            self.logger.warning(
                f"Pod {pod_name} ({namespace}): 不正なコンテナ名をスキップしました: {', '.join(invalid_names[:5])}{'...' if len(invalid_names) > 5 else ''}"
            )
        
        if not valid_names:
            error_msg = f"有効なコンテナ名が見つかりませんでした。取得結果: {stdout[:200]}"
            self.logger.error(f"Pod {pod_name} ({namespace}): {error_msg}")
            result['errors'].append(error_msg)
            return result
        
        container_names = valid_names
        result['summary']['total_containers'] = len(container_names)
        
        for container_name in container_names:
            log_command = f"logs {pod_name} -n {namespace} -c {container_name} --tail={tail_lines}"
            stdout, stderr, rc = self.k8s_collector._execute_kubectl(log_command)
            
            if rc == 0:
                result['logs'][container_name] = stdout
                result['summary']['logs_collected'] += 1
                self.logger.debug(f"Successfully collected logs for container {container_name} in pod {pod_name}")
            else:
                # 前回のコンテナログも取得を試みる（再起動している場合）
                prev_log_command = f"logs {pod_name} -n {namespace} -c {container_name} --previous --tail={tail_lines}"
                prev_stdout, prev_stderr, prev_rc = self.k8s_collector._execute_kubectl(prev_log_command)
                
                if prev_rc == 0:
                    result['logs'][f"{container_name}_previous"] = prev_stdout
                    result['summary']['logs_collected'] += 1
                    self.logger.info(f"Collected previous logs for container {container_name} in pod {pod_name} (container was restarted)")
                else:
                    error_msg = f"コンテナ {container_name} のログ取得に失敗: {stderr}"
                    result['errors'].append(error_msg)
                    result['summary']['logs_failed'] += 1
                    self.logger.warning(f"Pod {pod_name} ({namespace}): {error_msg}")
        
        # サマリーをログ出力
        if result['summary']['logs_failed'] > 0:
            self.logger.warning(
                f"Pod {pod_name} ({namespace}): "
                f"{result['summary']['logs_collected']}/{result['summary']['total_containers']} コンテナのログを収集しました "
                f"({result['summary']['logs_failed']}個失敗)"
            )
        else:
            self.logger.info(
                f"Pod {pod_name} ({namespace}): "
                f"全{result['summary']['total_containers']}コンテナのログを収集しました"
            )
        
        return result
    
    def collect_pod_describe(self, pod_name: str, namespace: str) -> Dict:
        """
        Podのdescribe情報を収集
        
        Args:
            pod_name: Pod名
            namespace: Namespace
        
        Returns:
            describe情報の辞書
        """
        result = {
            'pod_name': pod_name,
            'namespace': namespace,
            'describe': '',
            'error': None
        }
        
        command = f"describe pod {pod_name} -n {namespace}"
        stdout, stderr, rc = self.k8s_collector._execute_kubectl(command)
        
        if rc == 0:
            result['describe'] = stdout
        else:
            result['error'] = stderr
        
        return result
    
    def collect_pod_events(self, pod_name: str, namespace: str) -> Dict:
        """
        Pod関連のイベントを収集
        
        Args:
            pod_name: Pod名
            namespace: Namespace
        
        Returns:
            イベント情報の辞書
        """
        result = {
            'pod_name': pod_name,
            'namespace': namespace,
            'events': [],
            'error': None
        }
        
        command = f"get events -n {namespace} --field-selector involvedObject.name={pod_name} -o json"
        stdout, stderr, rc = self.k8s_collector._execute_kubectl(command)
        
        if rc == 0:
            try:
                import json
                data = json.loads(stdout)
                events = []
                
                for item in data.get('items', []):
                    events.append({
                        'type': item.get('type', ''),
                        'reason': item.get('reason', ''),
                        'message': item.get('message', ''),
                        'count': item.get('count', 0),
                        'first_timestamp': item.get('firstTimestamp', ''),
                        'last_timestamp': item.get('lastTimestamp', '')
                    })
                
                result['events'] = events
                
            except json.JSONDecodeError as e:
                result['error'] = f"Failed to parse events JSON: {e}"
        else:
            result['error'] = stderr
        
        return result
    
    def collect_all_pod_details(self, pod_name: str, namespace: str, output_dir: Optional[str] = None) -> Dict:
        """
        Podの全詳細情報を収集
        
        Args:
            pod_name: Pod名
            namespace: Namespace
            output_dir: 詳細情報を保存するディレクトリ（指定時はファイルに保存）
        
        Returns:
            全詳細情報の辞書
        """
        self.logger.info(f"Collecting detailed information for pod {namespace}/{pod_name}")
        
        result = {
            'pod_name': pod_name,
            'namespace': namespace,
            'logs': self.collect_pod_logs(pod_name, namespace),
            'describe': self.collect_pod_describe(pod_name, namespace),
            'events': self.collect_pod_events(pod_name, namespace),
            'saved_files': {}  # 保存されたファイルのパス情報
        }
        
        # output_dirが指定されている場合、ファイルに保存
        if output_dir:
            # ファイル名に使用する安全な文字列（namespace_podname形式）
            safe_name = f"{namespace}_{pod_name}"
            
            # ログの保存
            logs_info = result['logs']
            if logs_info and logs_info.get('logs') and not logs_info.get('errors'):
                logs_content = ""
                for container_name, log_content in logs_info['logs'].items():
                    logs_content += f"=== Container: {container_name} ===\n"
                    logs_content += log_content
                    logs_content += "\n\n"
                
                if logs_content.strip():  # 空でない場合のみ保存
                    logs_filepath = os.path.join(output_dir, f"{safe_name}_logs.txt")
                    if self._save_to_file(logs_content, logs_filepath):
                        result['saved_files']['logs'] = os.path.basename(logs_filepath)
            
            # describeの保存
            describe_info = result['describe']
            if describe_info and describe_info.get('describe') and not describe_info.get('error'):
                describe_filepath = os.path.join(output_dir, f"{safe_name}_describe.txt")
                if self._save_to_file(describe_info['describe'], describe_filepath):
                    result['saved_files']['describe'] = os.path.basename(describe_filepath)
            
            # eventsの保存
            events_info = result['events']
            if events_info and events_info.get('events') and not events_info.get('error'):
                events_content = ""
                events_content += f"Events for Pod: {namespace}/{pod_name}\n"
                events_content += "=" * 80 + "\n\n"
                
                for event in events_info['events']:
                    events_content += f"Type:           {event.get('type', 'Unknown')}\n"
                    events_content += f"Reason:         {event.get('reason', 'Unknown')}\n"
                    events_content += f"Message:        {event.get('message', '')}\n"
                    events_content += f"Count:          {event.get('count', 0)}\n"
                    events_content += f"First Seen:     {event.get('first_timestamp', 'N/A')}\n"
                    events_content += f"Last Seen:      {event.get('last_timestamp', 'N/A')}\n"
                    events_content += "-" * 80 + "\n"
                
                if events_content.strip():  # 空でない場合のみ保存
                    events_filepath = os.path.join(output_dir, f"{safe_name}_events.txt")
                    if self._save_to_file(events_content, events_filepath):
                        result['saved_files']['events'] = os.path.basename(events_filepath)
        
        return result
    
    def collect_details_for_issues(self, issues: List[Dict], output_dir: Optional[str] = None) -> List[Dict]:
        """
        問題が検出されたリソースの詳細情報を収集
        
        Args:
            issues: 問題のリスト
            output_dir: 詳細情報を保存するディレクトリ（指定時はファイルに保存）
        
        Returns:
            詳細情報のリスト
        """
        detailed_info = []
        collected_resources = set()  # 重複排除用
        
        self.logger.info(f"[DEBUG] Processing {len(issues)} issues for detailed collection")
        
        for idx, issue in enumerate(issues):
            # 詳細収集が必要なものだけ処理
            needs_collection = issue.get('needs_detailed_collection', False)
            resource_type = issue.get('resource_type', '')
            resource_name = issue.get('resource_name', '')
            issue_type = issue.get('issue_type', '')
            
            self.logger.debug(
                f"[DEBUG] Issue #{idx+1}: "
                f"type={issue_type}, "
                f"resource_type={resource_type}, "
                f"resource_name={resource_name}, "
                f"needs_collection={needs_collection}"
            )
            
            if not needs_collection:
                self.logger.debug(f"[SKIP] Issue skipped: needs_detailed_collection=False")
                continue
            
            if resource_type == 'Pod':
                # resource_nameは "namespace/pod-name" 形式
                parts = resource_name.split('/')
                if len(parts) == 2:
                    namespace, pod_name = parts
                    resource_key = f"Pod:{namespace}/{pod_name}"
                    
                    # 重複チェック
                    if resource_key in collected_resources:
                        self.logger.debug(f"[SKIP] Pod already collected: {resource_name}")
                        continue
                    
                    self.logger.info(f"[COLLECT] Processing Pod: {namespace}/{pod_name}")
                    details = self.collect_all_pod_details(pod_name, namespace, output_dir)
                    details['issue'] = issue
                    detailed_info.append(details)
                    collected_resources.add(resource_key)
                else:
                    self.logger.debug(f"[SKIP] Invalid resource_name format: {resource_name}")
            else:
                self.logger.debug(f"[SKIP] Resource type '{resource_type}' not supported for detailed collection (only Pod is currently supported)")
        
        return detailed_info
    
    def summarize_logs(self, log_text: str, max_lines: int = 50) -> str:
        """
        ログを要約（エラー行を優先的に抽出）
        
        Args:
            log_text: ログテキスト
            max_lines: 最大行数
        
        Returns:
            要約されたログ
        """
        lines = log_text.split('\n')
        
        # エラー関連の行を抽出
        error_keywords = ['error', 'fail', 'exception', 'fatal', 'panic', 'warn']
        error_lines = []
        other_lines = []
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in error_keywords):
                error_lines.append(line)
            else:
                other_lines.append(line)
        
        # エラー行を優先し、残りは末尾から取得
        result_lines = error_lines[:max_lines]
        
        if len(result_lines) < max_lines:
            remaining = max_lines - len(result_lines)
            result_lines.extend(other_lines[-remaining:])
        
        return '\n'.join(result_lines)
