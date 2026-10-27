#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
異常検出モジュール
収集したKubernetesリソースの状態から異常を検出します。
"""

import re
from typing import Dict, List, Optional
import logging


class AnomalyDetector:
    """異常検出を行うクラス"""
    
    def __init__(self, diagnosis_vars: Optional[Dict] = None):
        """
        Args:
            diagnosis_vars: 診断ツールの設定（config.yamlから読み込まれた値）
        """
        self.logger = logging.getLogger(__name__)
        self.issues = []
        
        # デフォルト設定
        self.diagnosis_vars = diagnosis_vars or {}
        self.pod_restart_threshold = self.diagnosis_vars.get('pod_restart_threshold', 50)
        self.collect_details_for_warnings = self.diagnosis_vars.get('collect_details_for_warnings', False)
        self.collect_details_for_critical = self.diagnosis_vars.get('collect_details_for_critical', True)
        self.pod_not_ready_severity = self.diagnosis_vars.get('pod_not_ready_severity', 'warning')
        self.high_restart_severity = self.diagnosis_vars.get('high_restart_severity', 'warning')
    
    def detect_node_issues(self, nodes: List[Dict]) -> List[Dict]:
        """
        ノードの異常を検出
        
        Args:
            nodes: ノード情報のリスト
        
        Returns:
            検出された問題のリスト
        """
        issues = []
        
        for node in nodes:
            node_name = node.get('name', 'Unknown')
            
            # NotReady状態のチェック
            if node.get('status') != 'Ready':
                issues.append({
                    'severity': 'critical',
                    'resource_type': 'Node',
                    'resource_name': node_name,
                    'issue_type': 'NotReady',
                    'message': f"Node '{node_name}' is not in Ready state",
                    'details': {
                        'status': node.get('status'),
                        'conditions': node.get('conditions', [])
                    }
                })
            
            # Conditionsのチェック
            for condition in node.get('conditions', []):
                if condition['type'] in ['MemoryPressure', 'DiskPressure', 'PIDPressure'] and condition['status'] == 'True':
                    issues.append({
                        'severity': 'warning',
                        'resource_type': 'Node',
                        'resource_name': node_name,
                        'issue_type': f'{condition["type"]}',
                        'message': f"Node '{node_name}' has {condition['type']}",
                        'details': {
                            'condition': condition
                        }
                    })
        
        return issues
    
    def detect_pod_issues(self, pods: List[Dict], expected_pattern: Optional[str] = None) -> List[Dict]:
        """
        Podの異常を検出
        
        Args:
            pods: Pod情報のリスト
            expected_pattern: 期待されるPod名のパターン（正規表現）
        
        Returns:
            検出された問題のリスト
        """
        issues = []
        
        for pod in pods:
            pod_name = pod.get('name', 'Unknown')
            namespace = pod.get('namespace', 'Unknown')
            pod_id = f"{namespace}/{pod_name}"
            
            # 異常なステータスのチェック
            abnormal_statuses = ['Failed', 'CrashLoopBackOff', 'ImagePullBackOff', 
                                'ErrImagePull', 'Pending']
            
            status = pod.get('status', 'Unknown')
            
            if status in abnormal_statuses:
                severity = 'critical' if status in ['Failed', 'CrashLoopBackOff'] else 'warning'
                
                issues.append({
                    'severity': severity,
                    'resource_type': 'Pod',
                    'resource_name': pod_id,
                    'issue_type': f'PodStatus{status}',
                    'message': f"Pod '{pod_id}' is in {status} state",
                    'details': {
                        'phase': pod.get('phase'),
                        'conditions': pod.get('conditions', []),
                        'container_statuses': pod.get('container_statuses', [])
                    },
                    'needs_detailed_collection': True  # 詳細情報収集が必要
                })
            
            # Readyでない場合のチェック（Running状態でも）
            elif status == 'Running':
                ready_str = pod.get('ready', '0/0')
                try:
                    ready, total = map(int, ready_str.split('/'))
                    if ready < total:
                        severity = self.pod_not_ready_severity
                        needs_collection = (
                            (severity == 'critical' and self.collect_details_for_critical) or
                            (severity == 'warning' and self.collect_details_for_warnings)
                        )
                        issues.append({
                            'severity': severity,
                            'resource_type': 'Pod',
                            'resource_name': pod_id,
                            'issue_type': 'PodNotReady',
                            'message': f"Pod '{pod_id}' is Running but not all containers are ready ({ready_str})",
                            'details': {
                                'ready': ready_str,
                                'container_statuses': pod.get('container_statuses', [])
                            },
                            'needs_detailed_collection': needs_collection
                        })
                except ValueError:
                    pass
            
            # 再起動回数が多い場合のチェック
            restarts = pod.get('restarts', 0)
            if self.high_restart_severity != 'ignore' and restarts > self.pod_restart_threshold:
                severity = self.high_restart_severity
                needs_collection = (
                    (severity == 'critical' and self.collect_details_for_critical) or
                    (severity == 'warning' and self.collect_details_for_warnings)
                )
                issues.append({
                    'severity': severity,
                    'resource_type': 'Pod',
                    'resource_name': pod_id,
                    'issue_type': 'HighRestartCount',
                    'message': f"Pod '{pod_id}' has high restart count ({restarts}, threshold: {self.pod_restart_threshold})",
                    'details': {
                        'restart_count': restarts,
                        'threshold': self.pod_restart_threshold,
                        'container_statuses': pod.get('container_statuses', [])
                    },
                    'needs_detailed_collection': needs_collection
                })
        
        # 期待されるパターンに一致するPodが存在するかチェック
        if expected_pattern:
            pattern = re.compile(expected_pattern)
            matching_pods = [p for p in pods if pattern.match(p.get('name', ''))]
            
            if not matching_pods:
                issues.append({
                    'severity': 'critical',
                    'resource_type': 'Pod',
                    'resource_name': f'Pattern: {expected_pattern}',
                    'issue_type': 'ExpectedPodNotFound',
                    'message': f"No pods found matching expected pattern: {expected_pattern}",
                    'details': {
                        'expected_pattern': expected_pattern,
                        'available_pods': [p.get('name') for p in pods]
                    }
                })
            else:
                # パターンに一致するPodの中で異常があるかチェック
                running_count = sum(1 for p in matching_pods if p.get('status') == 'Running')
                if running_count < len(matching_pods):
                    issues.append({
                        'severity': 'warning',
                        'resource_type': 'Pod',
                        'resource_name': f'Pattern: {expected_pattern}',
                        'issue_type': 'NotAllPodsRunning',
                        'message': f"Not all pods matching pattern '{expected_pattern}' are running ({running_count}/{len(matching_pods)})",
                        'details': {
                            'expected_pattern': expected_pattern,
                            'total_pods': len(matching_pods),
                            'running_pods': running_count,
                            'pod_statuses': [(p.get('name'), p.get('status')) for p in matching_pods]
                        }
                    })
        
        return issues
    
    def detect_namespace_issues(self, expected_namespaces: List[str], 
                                actual_namespaces: List[str]) -> List[Dict]:
        """
        Namespaceの存在チェック
        
        Args:
            expected_namespaces: 期待されるNamespaceのリスト
            actual_namespaces: 実際に存在するNamespaceのリスト
        
        Returns:
            検出された問題のリスト
        """
        issues = []
        
        for expected_ns in expected_namespaces:
            if expected_ns not in actual_namespaces:
                issues.append({
                    'severity': 'critical',
                    'resource_type': 'Namespace',
                    'resource_name': expected_ns,
                    'issue_type': 'NamespaceNotFound',
                    'message': f"Expected namespace '{expected_ns}' not found",
                    'details': {
                        'expected': expected_ns,
                        'actual_namespaces': actual_namespaces
                    }
                })
        
        return issues
    
    def categorize_issues(self, issues: List[Dict]) -> Dict:
        """
        問題を重要度別に分類
        
        Args:
            issues: 問題のリスト
        
        Returns:
            {
                'critical': [],
                'warning': [],
                'info': []
            }
        """
        categorized = {
            'critical': [],
            'warning': [],
            'info': []
        }
        
        for issue in issues:
            severity = issue.get('severity', 'info')
            if severity in categorized:
                categorized[severity].append(issue)
            else:
                categorized['info'].append(issue)
        
        return categorized
    
    def get_summary_stats(self, issues: List[Dict]) -> Dict:
        """
        問題の統計情報を取得
        
        Args:
            issues: 問題のリスト
        
        Returns:
            統計情報の辞書
        """
        categorized = self.categorize_issues(issues)
        
        return {
            'total_issues': len(issues),
            'critical_count': len(categorized['critical']),
            'warning_count': len(categorized['warning']),
            'info_count': len(categorized['info']),
            'issue_types': self._count_by_type(issues),
            'resources_affected': len(set(i.get('resource_name', '') for i in issues))
        }
    
    def _count_by_type(self, issues: List[Dict]) -> Dict[str, int]:
        """問題をタイプ別にカウント"""
        type_counts = {}
        
        for issue in issues:
            issue_type = issue.get('issue_type', 'Unknown')
            type_counts[issue_type] = type_counts.get(issue_type, 0) + 1
        
        return type_counts
    
    def detect_generic_resource_issues(
        self,
        resources: List[Dict],
        resource_spec: Dict
    ) -> List[Dict]:
        """
        汎用リソースの異常検出（Pod/Node/Namespace/ConfigMap/Secret/CRD等全対応）
        
        Args:
            resources: 正規化されたリソースリスト
            resource_spec: resource_mappingsからの定義
        
        Returns:
            検出された問題のリスト
        """
        issues = []
        kind = resource_spec.get('kind', '').lower()
        
        # kind毎の検出ロジック振り分け
        if kind == 'pod':
            issues.extend(self._detect_pod_issues(resources, resource_spec))
        elif kind == 'node':
            issues.extend(self._detect_node_issues(resources, resource_spec))
        elif kind == 'namespace':
            issues.extend(self._detect_namespace_issues(resources, resource_spec))
        else:
            # その他のリソース（ConfigMap, Secret, CRD等）
            issues.extend(self._detect_generic_existence(resources, resource_spec))
        
        return issues
    
    def _detect_pod_issues(self, pods: List[Dict], spec: Dict) -> List[Dict]:
        """Pod固有の異常検出（汎用版）"""
        issues = []
        name_pattern = spec.get('name_pattern')
        expected_status = spec.get('expected_status', 'Running')
        namespace = spec.get('namespace')
        
        # name_patternでフィルタ
        if name_pattern:
            pattern = re.compile(name_pattern)
            target_pods = [p for p in pods if pattern.match(p.get('name', ''))]
            
            # 期待パターンに一致するPodが存在しない
            if not target_pods:
                # optional=Trueの場合はスキップ
                if spec.get('optional', False):
                    return issues
                
                issues.append({
                    'severity': 'critical',
                    'resource_type': 'Pod',
                    'resource_name': f"{namespace}/{name_pattern}" if namespace else name_pattern,
                    'issue_type': 'ExpectedPodNotFound',
                    'message': f"No pods matching pattern '{name_pattern}' found",
                    'details': {'expected_pattern': name_pattern, 'namespace': namespace}
                })
                return issues
        else:
            target_pods = pods
        
        # 各Podの状態チェック
        for pod in target_pods:
            pod_name = pod.get('name')
            pod_ns = pod.get('namespace', namespace)
            pod_id = f"{pod_ns}/{pod_name}" if pod_ns else pod_name
            status = pod.get('status', 'Unknown')
            
            # 既知の異常状態チェック（expected_statusの有無に関わらず常に実行）
            if status in ['CrashLoopBackOff', 'Failed']:
                issues.append({
                    'severity': 'critical',
                    'resource_type': 'Pod',
                    'resource_name': pod_id,
                    'issue_type': f'PodStatus{status}',
                    'message': f"Pod '{pod_id}' is in {status} state",
                    'details': pod.get('container_statuses', []),
                    'needs_detailed_collection': True
                })
            elif status in ['ImagePullBackOff', 'ErrImagePull']:
                issues.append({
                    'severity': 'warning',
                    'resource_type': 'Pod',
                    'resource_name': pod_id,
                    'issue_type': f'PodStatus{status}',
                    'message': f"Pod '{pod_id}' is in {status} state",
                    'details': pod.get('container_statuses', []),
                    'needs_detailed_collection': self.collect_details_for_warnings
                })
            elif status == 'Pending':
                issues.append({
                    'severity': 'warning',
                    'resource_type': 'Pod',
                    'resource_name': pod_id,
                    'issue_type': 'PodStatusPending',
                    'message': f"Pod '{pod_id}' is in Pending state",
                    'details': pod.get('container_statuses', []),
                    'needs_detailed_collection': self.collect_details_for_warnings
                })
            elif status == 'Error':
                issues.append({
                    'severity': 'critical',
                    'resource_type': 'Pod',
                    'resource_name': pod_id,
                    'issue_type': 'PodStatusError',
                    'message': f"Pod '{pod_id}' is in Error state",
                    'details': pod.get('container_statuses', []),
                    'needs_detailed_collection': True
                })
            # expected_statusが指定されている場合、期待値との不一致を追加でチェック
            elif expected_status and status != expected_status:
                # 上記の既知状態以外で期待値と異なる場合
                issues.append({
                    'severity': 'critical',
                    'resource_type': 'Pod',
                    'resource_name': pod_id,
                    'issue_type': 'UnexpectedPodStatus',
                    'message': f"Pod '{pod_id}' status is '{status}' (expected: '{expected_status}')",
                    'details': {'actual': status, 'expected': expected_status},
                    'needs_detailed_collection': self.collect_details_for_critical
                })
            
            # Ready状態チェック（Running時のみ）
            if status == 'Running':
                ready_str = pod.get('ready', '0/0')
                try:
                    ready, total = map(int, ready_str.split('/'))
                    if ready < total:
                        severity = self.pod_not_ready_severity
                        issues.append({
                            'severity': severity,
                            'resource_type': 'Pod',
                            'resource_name': pod_id,
                            'issue_type': 'PodNotReady',
                            'message': f"Pod '{pod_id}' not all containers ready ({ready_str})",
                            'details': {'ready': ready_str},
                            'needs_detailed_collection': (
                                (severity == 'critical' and self.collect_details_for_critical) or
                                (severity == 'warning' and self.collect_details_for_warnings)
                            )
                        })
                except ValueError:
                    pass
            
            # 再起動回数チェック
            restarts = pod.get('restarts', 0)
            if self.high_restart_severity != 'ignore' and restarts > self.pod_restart_threshold:
                severity = self.high_restart_severity
                needs_collection = (
                    (severity == 'critical' and self.collect_details_for_critical) or
                    (severity == 'warning' and self.collect_details_for_warnings)
                )
                issues.append({
                    'severity': severity,
                    'resource_type': 'Pod',
                    'resource_name': pod_id,
                    'issue_type': 'HighRestartCount',
                    'message': f"Pod '{pod_id}' has {restarts} restarts (threshold: {self.pod_restart_threshold})",
                    'details': {'restarts': restarts, 'threshold': self.pod_restart_threshold},
                    'needs_detailed_collection': needs_collection
                })
        
        return issues
    
    def _detect_node_issues(self, nodes: List[Dict], spec: Dict) -> List[Dict]:
        """Node固有の異常検出（汎用版）"""
        issues = []
        expected_conditions = spec.get('expected_conditions', [])
        
        for node in nodes:
            node_name = node.get('name')
            status = node.get('status', 'Unknown')
            conditions = node.get('conditions', [])
            
            # Ready状態チェック
            if status != 'Ready':
                issues.append({
                    'severity': 'critical',
                    'resource_type': 'Node',
                    'resource_name': node_name,
                    'issue_type': 'NodeNotReady',
                    'message': f"Node '{node_name}' is {status}",
                    'details': {'status': status, 'conditions': conditions},
                    'needs_detailed_collection': self.collect_details_for_critical
                })
            
            # 期待されるConditionsチェック
            for expected_cond in expected_conditions:
                exp_type = expected_cond.get('condition')
                exp_status = expected_cond.get('status')
                
                actual_cond = next(
                    (c for c in conditions if c.get('type') == exp_type),
                    {}
                )
                actual_status = actual_cond.get('status')
                
                if actual_status != exp_status:
                    issues.append({
                        'severity': 'critical',
                        'resource_type': 'Node',
                        'resource_name': node_name,
                        'issue_type': f'NodeCondition{exp_type}',
                        'message': f"Node '{node_name}' condition {exp_type} is {actual_status} (expected: {exp_status})",
                        'details': {'condition': actual_cond},
                        'needs_detailed_collection': self.collect_details_for_critical
                    })
            
            # リソース圧迫チェック
            for condition in conditions:
                if condition['type'] in ['MemoryPressure', 'DiskPressure', 'PIDPressure']:
                    if condition.get('status') == 'True':
                        issues.append({
                            'severity': 'warning',
                            'resource_type': 'Node',
                            'resource_name': node_name,
                            'issue_type': condition['type'],
                            'message': f"Node '{node_name}' has {condition['type']}",
                            'details': {'condition': condition},
                            'needs_detailed_collection': self.collect_details_for_warnings
                        })
        
        return issues
    
    def _detect_namespace_issues(self, namespaces: List[Dict], spec: Dict) -> List[Dict]:
        """Namespace固有の異常検出（汎用版）"""
        issues = []
        name_pattern = spec.get('name_pattern')
        expected_exists = spec.get('expected_exists', True)
        
        if not name_pattern:
            return issues
        
        pattern = re.compile(name_pattern)
        matching_ns = [ns for ns in namespaces if pattern.match(ns.get('name', ''))]
        
        if expected_exists and not matching_ns:
            # optional=Trueの場合はスキップ
            if spec.get('optional', False):
                return issues
            
            issues.append({
                'severity': 'critical',
                'resource_type': 'Namespace',
                'resource_name': name_pattern,
                'issue_type': 'NamespaceNotFound',
                'message': f"Expected namespace matching '{name_pattern}' not found",
                'details': {'expected_pattern': name_pattern},
                'needs_detailed_collection': self.collect_details_for_critical
            })
        
        return issues
    
    def _detect_generic_existence(self, resources: List[Dict], spec: Dict) -> List[Dict]:
        """汎用リソース（ConfigMap, Secret, CRD, PVC等）の存在チェック"""
        issues = []
        kind = spec.get('kind', 'Resource')
        namespace = spec.get('namespace')
        name_pattern = spec.get('name_pattern')
        expected_exists = spec.get('expected_exists', True)
        expected_status = spec.get('expected_status')  # PVC等で使用
        description = spec.get('description', '')
        
        if not name_pattern:
            return issues
        
        pattern = re.compile(name_pattern)
        matching_resources = [r for r in resources if pattern.match(r.get('name', ''))]
        
        # 存在チェック
        if expected_exists and not matching_resources:
            # optional=Trueの場合はスキップ
            if spec.get('optional', False):
                return issues

            resource_id = f"{namespace}/{name_pattern}" if namespace else name_pattern
            issues.append({
                'severity': 'critical',
                'resource_type': kind,
                'resource_name': resource_id,
                'issue_type': 'ExpectedResourceNotFound',
                'message': f"Expected {kind} matching '{name_pattern}' not found",
                'details': {
                    'expected_pattern': name_pattern,
                    'namespace': namespace,
                    'description': description
                },
                'needs_detailed_collection': self.collect_details_for_critical
            })
        
        # ステータスチェック（PVC等）
        if expected_status:
            for resource in matching_resources:
                actual_status = resource.get('status', 'Unknown')
                if actual_status != expected_status:
                    resource_id = f"{namespace}/{resource.get('name')}" if namespace else resource.get('name')
                    issues.append({
                        'severity': 'critical',
                        'resource_type': kind,
                        'resource_name': resource_id,
                        'issue_type': f'{kind}StatusMismatch',
                        'message': f"{kind} '{resource_id}' status is '{actual_status}' (expected: '{expected_status}')",
                        'details': {'actual': actual_status, 'expected': expected_status},
                        'needs_detailed_collection': self.collect_details_for_critical
                    })
        
        return issues
