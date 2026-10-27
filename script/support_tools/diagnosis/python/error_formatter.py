#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
エラーメッセージフォーマッター
DiagnosisError 例外を見やすい形式でフォーマットして表示します。
"""

import sys
from typing import TextIO, Optional
from exceptions import DiagnosisError


def format_error(error: DiagnosisError, file: TextIO = sys.stderr) -> None:
    """
    DiagnosisError を見やすい形式でフォーマットして出力
    
    Args:
        error: DiagnosisError インスタンス
        file: 出力先ファイルオブジェクト（デフォルト: stderr）
    """
    lines = []
    
    # エラーヘッダー
    error_type = error.get_error_type()
    lines.append(f"\n{'='*80}")
    lines.append(f"[エラー] {error_type}")
    lines.append(f"{'='*80}")
    
    # メインメッセージ
    lines.append(f"\n{error.message}")
    
    # 処理ステップ
    if error.step:
        lines.append(f"\n処理ステップ: {error.step}")
    
    # 詳細コンテキスト
    if error.context:
        lines.append("\n詳細:")
        for key, value in error.context.items():
            # 長い値は省略表示
            if isinstance(value, str) and len(value) > 200:
                value_str = value[:200] + "... (省略)"
            else:
                value_str = str(value)
            lines.append(f"  - {key}: {value_str}")
    
    # 特定のエラー種別ごとの追加情報
    _add_specific_error_details(error, lines)
    
    # 推奨される対処アクション
    if error.suggestion:
        lines.append("\n推奨される対処アクション:")
        # 複数行の場合は各行にインデントを付ける
        for line in error.suggestion.split('\n'):
            if line.strip():
                lines.append(f"  {line}")
    
    # 関連ログファイル
    if error.log_locations:
        lines.append("\n関連ログファイル:")
        for log_path in error.log_locations:
            lines.append(f"  - {log_path}")
    
    # 元の例外情報
    if error.original_error:
        lines.append(f"\n元のエラー: {type(error.original_error).__name__}: {error.original_error}")
    
    lines.append(f"\n{'='*80}\n")
    
    # 出力
    print('\n'.join(lines), file=file)


def _add_specific_error_details(error: DiagnosisError, lines: list) -> None:
    """
    特定のエラー種別ごとの追加詳細情報を追加
    
    Args:
        error: DiagnosisError インスタンス
        lines: 出力行のリスト（この関数で追加される）
    """
    from exceptions import (
        PrerequisiteError, TemplateRenderError, PlaybookExecutionError,
        ResourceCollectionError, ParseError, RemoteAccessError, ValidationError
    )
    
    if isinstance(error, PrerequisiteError):
        lines.append(f"\n不足している項目: {error.missing_item}")
    
    elif isinstance(error, TemplateRenderError):
        if error.template_file:
            lines.append(f"\nテンプレートファイル: {error.template_file}")
        if error.template_vars:
            lines.append("\nテンプレート変数:")
            for key, value in error.template_vars.items():
                lines.append(f"  - {key}: {value}")
    
    elif isinstance(error, PlaybookExecutionError):
        if error.playbook_path:
            lines.append(f"\nPlaybookパス: {error.playbook_path}")
        if error.target_hosts:
            lines.append(f"\n対象ホスト: {', '.join(error.target_hosts)}")
        if error.error_type:
            error_type_ja = {
                'ssh': 'SSH接続エラー',
                'auth': '認証エラー',
                'syntax': 'Playbook文法エラー',
                'runtime': '実行時エラー'
            }.get(error.error_type, error.error_type)
            lines.append(f"\nエラー種別: {error_type_ja}")
        if error.ansible_stderr:
            # stderr の先頭部分のみ表示（長すぎる場合）
            stderr_preview = error.ansible_stderr
            if len(stderr_preview) > 1000:
                stderr_preview = stderr_preview[:1000] + "\n... (以下省略、詳細はログファイルを確認してください)"
            lines.append(f"\nAnsible stderr 出力:")
            for line in stderr_preview.split('\n'):
                if line.strip():
                    lines.append(f"  {line}")
    
    elif isinstance(error, ResourceCollectionError):
        if error.resource_type:
            lines.append(f"\nリソース種別: {error.resource_type}")
        if error.namespace:
            lines.append(f"\nNamespace: {error.namespace}")
        if error.failed_resources:
            lines.append(f"\n取得失敗したリソース: {', '.join(error.failed_resources)}")
    
    elif isinstance(error, ParseError):
        if error.file_path:
            lines.append(f"\nパース対象ファイル: {error.file_path}")
        if error.parse_type:
            parse_type_ja = {
                'json': 'JSON',
                'yaml': 'YAML',
                'log': 'ログファイル'
            }.get(error.parse_type, error.parse_type)
            lines.append(f"\nパース種別: {parse_type_ja}")
        if error.raw_data_sample:
            lines.append("\n元データのサンプル:")
            for line in error.raw_data_sample.split('\n')[:10]:  # 最初の10行のみ
                if line.strip():
                    lines.append(f"  {line}")
            if len(error.raw_data_sample.split('\n')) > 10:
                lines.append("  ... (以下省略)")
    
    elif isinstance(error, RemoteAccessError):
        if error.remote_host:
            lines.append(f"\nリモートホスト: {error.remote_host}")
        if error.access_method:
            access_method_ja = {
                'ssh': 'SSH',
                'kubectl': 'kubectl',
                'ansible': 'Ansible'
            }.get(error.access_method, error.access_method)
            lines.append(f"\nアクセス方法: {access_method_ja}")
    
    elif isinstance(error, ValidationError):
        if error.validation_type:
            lines.append(f"\nバリデーション種別: {error.validation_type}")
        if error.expected_value:
            lines.append(f"\n期待される値: {error.expected_value}")
        if error.actual_value:
            lines.append(f"\n実際の値: {error.actual_value}")


def format_error_compact(error: DiagnosisError) -> str:
    """
    エラーを1行のコンパクトな形式でフォーマット（ログ出力用）
    
    Args:
        error: DiagnosisError インスタンス
    
    Returns:
        1行のエラーメッセージ
    """
    error_type = error.get_error_type()
    step_info = f" (ステップ: {error.step})" if error.step else ""
    return f"[{error_type}]{step_info} {error.message}"


def print_step_info(step_number: int, total_steps: int, description: str, file: TextIO = sys.stdout) -> None:
    """
    処理ステップの進捗情報を出力
    
    Args:
        step_number: 現在のステップ番号
        total_steps: 全体のステップ数
        description: ステップの説明
        file: 出力先ファイルオブジェクト（デフォルト: stdout）
    """
    print(f"\n[ステップ {step_number}/{total_steps}] {description}", file=file)
    print("-" * 80, file=file)
