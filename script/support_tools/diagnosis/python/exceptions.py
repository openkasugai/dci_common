#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
診断ツールのカスタム例外クラス
エラー種別ごとに詳細なコンテキスト情報を持つ例外を定義します。
"""

from typing import Dict, List, Optional, Any


class DiagnosisError(Exception):
    """診断ツールのベース例外クラス"""
    
    def __init__(
        self,
        message: str,
        step: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
        log_locations: Optional[List[str]] = None,
        original_error: Optional[Exception] = None
    ):
        """
        Args:
            message: エラーメッセージ
            step: エラーが発生した処理ステップ名
            context: コンテキスト情報（ファイルパス、設定値など）
            suggestion: 推奨される対処アクション
            log_locations: 関連するログファイルのパス一覧
            original_error: 元の例外（ある場合）
        """
        super().__init__(message)
        self.message = message
        self.step = step
        self.context = context or {}
        self.suggestion = suggestion
        self.log_locations = log_locations or []
        self.original_error = original_error
    
    def get_error_type(self) -> str:
        """エラー種別名を取得"""
        return self.__class__.__name__


class PrerequisiteError(DiagnosisError):
    """前提条件エラー（必須ツール、ファイル、権限などの不足）"""
    
    def __init__(
        self,
        message: str,
        missing_item: str,
        **kwargs
    ):
        """
        Args:
            message: エラーメッセージ
            missing_item: 不足している項目（kubectl, kubeconfig, etc.）
            **kwargs: DiagnosisError の他の引数
        """
        super().__init__(message, **kwargs)
        self.missing_item = missing_item


class TemplateRenderError(DiagnosisError):
    """テンプレートレンダリングエラー（Jinja2テンプレートの問題）"""
    
    def __init__(
        self,
        message: str,
        template_file: Optional[str] = None,
        template_vars: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Args:
            message: エラーメッセージ
            template_file: テンプレートファイルパス
            template_vars: テンプレート変数
            **kwargs: DiagnosisError の他の引数
        """
        super().__init__(message, **kwargs)
        self.template_file = template_file
        self.template_vars = template_vars


class PlaybookExecutionError(DiagnosisError):
    """Ansible Playbook実行エラー"""
    
    def __init__(
        self,
        message: str,
        playbook_path: Optional[str] = None,
        target_hosts: Optional[List[str]] = None,
        error_type: Optional[str] = None,  # 'ssh', 'auth', 'syntax', 'runtime'
        ansible_stderr: Optional[str] = None,
        **kwargs
    ):
        """
        Args:
            message: エラーメッセージ
            playbook_path: 実行したPlaybookのパス
            target_hosts: 対象ホスト一覧
            error_type: エラー種別 ('ssh', 'auth', 'syntax', 'runtime')
            ansible_stderr: Ansible の stderr 出力
            **kwargs: DiagnosisError の他の引数
        """
        super().__init__(message, **kwargs)
        self.playbook_path = playbook_path
        self.target_hosts = target_hosts
        self.error_type = error_type
        self.ansible_stderr = ansible_stderr


class ResourceCollectionError(DiagnosisError):
    """Kubernetesリソース収集エラー"""
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        namespace: Optional[str] = None,
        failed_resources: Optional[List[str]] = None,
        **kwargs
    ):
        """
        Args:
            message: エラーメッセージ
            resource_type: リソース種別 ('pods', 'deployments', 'nodes', etc.)
            namespace: 対象Namespace
            failed_resources: 取得に失敗したリソースのリスト
            **kwargs: DiagnosisError の他の引数
        """
        super().__init__(message, **kwargs)
        self.resource_type = resource_type
        self.namespace = namespace
        self.failed_resources = failed_resources or []


class ParseError(DiagnosisError):
    """パースエラー（JSON、YAML、ログファイルなどの解析失敗）"""
    
    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        parse_type: Optional[str] = None,  # 'json', 'yaml', 'log'
        raw_data_sample: Optional[str] = None,
        **kwargs
    ):
        """
        Args:
            message: エラーメッセージ
            file_path: パース対象のファイルパス
            parse_type: パース種別 ('json', 'yaml', 'log')
            raw_data_sample: 元データのサンプル（最初の200文字など）
            **kwargs: DiagnosisError の他の引数
        """
        super().__init__(message, **kwargs)
        self.file_path = file_path
        self.parse_type = parse_type
        self.raw_data_sample = raw_data_sample


class RemoteAccessError(DiagnosisError):
    """リモートアクセスエラー（SSH接続、kubectl実行などの失敗）"""
    
    def __init__(
        self,
        message: str,
        remote_host: Optional[str] = None,
        access_method: Optional[str] = None,  # 'ssh', 'kubectl', 'ansible'
        **kwargs
    ):
        """
        Args:
            message: エラーメッセージ
            remote_host: リモートホスト名またはIP
            access_method: アクセス方法 ('ssh', 'kubectl', 'ansible')
            **kwargs: DiagnosisError の他の引数
        """
        super().__init__(message, **kwargs)
        self.remote_host = remote_host
        self.access_method = access_method


class ValidationError(DiagnosisError):
    """バリデーションエラー（設定値、引数などの検証失敗）"""
    
    def __init__(
        self,
        message: str,
        validation_type: Optional[str] = None,
        expected_value: Optional[str] = None,
        actual_value: Optional[str] = None,
        **kwargs
    ):
        """
        Args:
            message: エラーメッセージ
            validation_type: バリデーション種別
            expected_value: 期待される値
            actual_value: 実際の値
            **kwargs: DiagnosisError の他の引数
        """
        super().__init__(message, **kwargs)
        self.validation_type = validation_type
        self.expected_value = expected_value
        self.actual_value = actual_value
