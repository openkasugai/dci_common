#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Markdown要約レポート生成モジュール
人間が読みやすいMarkdown形式で診断結果の要約を生成します。
"""

import re
from datetime import datetime
from typing import Dict, List


class MarkdownReporter:
    """Markdown形式のレポートを生成するクラス"""
    
    def __init__(self):
        pass
    
    def _format_timestamp(self, iso_timestamp: str) -> str:
        """
        ISO形式のタイムスタンプを日本語形式に変換
        
        Args:
            iso_timestamp: ISO形式のタイムスタンプ (例: 2026-04-09T10:45:32.516598)
        
        Returns:
            日本語形式のタイムスタンプ (例: 2026年4月9日 10:45:32)
        """
        try:
            # ISO形式をパース
            dt = datetime.fromisoformat(iso_timestamp)
            # 日本語形式に変換（マイクロ秒は削除）
            return dt.strftime('%Y年%-m月%-d日 %H:%M:%S')
        except (ValueError, AttributeError):
            # パースエラーの場合は元の文字列をそのまま返す
            return iso_timestamp
    
    def _calculate_age(self, created_timestamp: str) -> str:
        """
        作成時刻からAGEを計算
        
        Args:
            created_timestamp: ISO形式のタイムスタンプ (例: 2026-04-10T01:58:51Z)
        
        Returns:
            AGE文字列 (例: "2d", "3h", "45m", "30s")
        """
        if not created_timestamp or created_timestamp == 'N/A':
            return 'N/A'
        
        try:
            # ISO形式をパース（Zタイムゾーン対応）
            created_timestamp = created_timestamp.replace('Z', '+00:00')
            created_dt = datetime.fromisoformat(created_timestamp)
            now = datetime.now(created_dt.tzinfo)
            
            # 差分を計算
            delta = now - created_dt
            total_seconds = int(delta.total_seconds())
            
            # 負の値の場合（将来の日付）
            if total_seconds < 0:
                return 'N/A'
            
            # 日・時・分・秒で表示
            days = total_seconds // 86400
            if days > 0:
                return f"{days}d"
            
            hours = total_seconds // 3600
            if hours > 0:
                return f"{hours}h"
            
            minutes = total_seconds // 60
            if minutes > 0:
                return f"{minutes}m"
            
            return f"{total_seconds}s"
            
        except (ValueError, AttributeError, TypeError):
            return 'N/A'
    
    def generate_summary_report(self, diagnosis_data: Dict) -> str:
        """
        診断結果の要約レポートを生成
        
        Args:
            diagnosis_data: format済みの診断データ
        
        Returns:
            Markdown形式のレポート文字列
        """
        lines = []
        
        # タイトルとメタデータ
        lines.append("# DCI 診断レポート")
        lines.append("")
        lines.append(f"**スクリプト名:** {diagnosis_data.get('metadata', {}).get('script_name', 'Unknown')}")
        
        # 診断開始時刻、終了時刻、稼働時間を表示
        metadata = diagnosis_data.get('metadata', {})
        start_time = metadata.get('diagnosis_start_time')
        end_time = metadata.get('diagnosis_end_time')
        duration = metadata.get('diagnosis_duration')
        
        formatted_start_time = self._format_timestamp(start_time) if start_time else 'N/A'
        formatted_end_time = self._format_timestamp(end_time) if end_time else 'N/A'
        lines.append(f"**診断開始時刻:** {formatted_start_time}")
        lines.append(f"**診断終了時刻:** {formatted_end_time}")
        lines.append(f"**診断稼働時間:** {duration if duration else 'N/A'}")
        
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 参照したログ情報（サマリーセクションで使用するため先に初期化）
        log_analysis = diagnosis_data.get('log_analysis', {})
        playbooks = log_analysis.get('playbooks_executed', [])
        log_directory = log_analysis.get('log_directory', '')
        log_files = log_analysis.get('log_files', [])
        
        # ログファイル合計稼働時間を計算（サマリーセクションで使用するため先に計算）
        total_duration_seconds = 0
        for log_file_info in log_files:
            if isinstance(log_file_info, dict):
                duration_str = log_file_info.get('duration', '00:00:00')
                if duration_str and duration_str != 'N/A':
                    # HH:MM:SS形式から秒数に変換
                    parts = duration_str.split(':')
                    if len(parts) == 3:
                        try:
                            hours, minutes, seconds = map(int, parts)
                            total_duration_seconds += hours * 3600 + minutes * 60 + seconds
                        except ValueError:
                            pass
        
        # 合計を HH:MM:SS 形式に変換
        hours, remainder = divmod(total_duration_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        total_duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # サマリーセクション
        summary = diagnosis_data.get('summary', {})
        overall_status = summary.get('overall_status', 'unknown')
        status_emoji = self._get_status_emoji(overall_status)
        status_ja = self._translate_status(overall_status)
        
        # 問題数のカウント（リソース異常 + ログエラー）
        resource_issues_count = diagnosis_data.get('issues_detected', {}).get('total_count', 0)
        log_errors = log_analysis.get('errors_from_logs', [])
        log_warnings = log_analysis.get('warnings_from_logs', [])
        
        # 重要度別の問題を取得
        issues_detected = diagnosis_data.get('issues_detected', {})
        by_severity = issues_detected.get('by_severity', {})
        critical_issues = by_severity.get('critical', [])
        warning_issues = by_severity.get('warning', [])
        
        total_issues_count = len(log_errors) + len(critical_issues)
        
        lines.append("♦ サマリー")
        lines.append("")
        lines.append(f"✏️ **総合ステータス:** {status_emoji} {status_ja}")
        lines.append("")
        lines.append(f"**検出された重大エラー:** {total_issues_count}件")
        lines.append(f"- ❌ ログから検出されたエラー: {len(log_errors)}件")
        lines.append(f"- ⚠️ ログからの警告: {len(log_warnings)}件")
        lines.append(f"- ❌ リソース状態の重大な問題: {len(critical_issues)}件")
        lines.append(f"- ⚠️ リソース状態の警告: {len(warning_issues)}件")
        lines.append("")
        lines.append("**参照したログ**")
        lines.append(f"- ログディレクトリ: `{log_directory}`")
        lines.append(f"- ログファイル: {len(log_files)}件")
        lines.append(f"- 合計Playbook稼働時間: {total_duration_str}")
        lines.append("")
        
        # 検出された問題
        all_issues = issues_detected.get('all_issues', [])
        
        # 検出された問題セクション（0件でも常に表示）
        lines.append("## 検出された問題")
        lines.append("")
        
        # ログから検出されたエラー（0件でも表示）
        lines.append(f"### ❌ ログから検出されたエラー: {len(log_errors)}件")
        if log_errors:
            for idx, error in enumerate(log_errors[:50], 1):  # 最大20件
                error_type = error.get('type', 'unknown')
                message = error.get('message', 'Unknown error')
                log_file = error.get('log_file', '')
                line_number = error.get('line_number', '')
                
                # タスク失敗の場合は詳細情報を表示
                if error_type in ['task_failed', 'stderr_error']:
                    host = error.get('host', '')
                    error_message = error.get('error_message', '')
                    stderr = error.get('stderr', '')
                    
                    # 基本情報の表示
                    lines.append(f"\n{idx}. **{message}**")
                    if host:
                        lines.append(f"   - ホスト: `{host}`")
                    if error_message:
                        lines.append(f"   - エラーメッセージ: {error_message}")
                    if log_file and line_number:
                        lines.append(f"   - ログファイル: `{log_file}:{line_number}`")
                    elif log_file:
                        lines.append(f"   - ログファイル: `{log_file}`")
                    
                    # STDERR内容がある場合は折りたたみ可能な形式で表示
                    if stderr:
                        lines.append(f"   - STDERR出力:")
                        lines.append("")
                        lines.append("   <details>")
                        lines.append("   <summary>詳細を表示</summary>")
                        lines.append("")
                        lines.append("   ```")
                        # STDERR内容を4スペースインデント
                        for stderr_line in stderr.split('\n'):
                            lines.append(f"   {stderr_line}")
                        lines.append("   ```")
                        lines.append("   </details>")
                else:
                    # その他のエラーは従来通り表示
                    if log_file and line_number:
                        lines.append(f"{idx}. {message} `({log_file}:{line_number})`")
                    else:
                        lines.append(f"{idx}. {message}")
            if len(log_errors) > 50:
                lines.append(f"\n... 他 {len(log_errors) - 50}件のエラー")
        lines.append("")
        
        # ログからの警告（0件でも表示）
        lines.append(f"### ⚠️ ログからの警告: {len(log_warnings)}件")
        if log_warnings:
            lines.append("")
            for idx, warning in enumerate(log_warnings[:50], 1):  # 最大20件
                message = warning.get('message', 'Unknown warning')
                log_file = warning.get('log_file', '')
                line_number = warning.get('line_number', '')
                stderr = warning.get('stderr', '')
                warning_lines = warning.get('warning_lines', [])
                task_name = warning.get('task_name', '')
                
                # STDERR情報がある場合は詳細表示
                if stderr:
                    lines.append(f"\n{idx}. **{message}**")
                    if task_name:
                        lines.append(f"   - タスク: {task_name}")
                    if log_file and line_number:
                        lines.append(f"   - ログファイル: `{log_file}:{line_number}`")
                    elif log_file:
                        lines.append(f"   - ログファイル: `{log_file}`")
                    
                    # 統合された警告の場合、警告行を表示
                    if warning_lines:
                        lines.append(f"   - 検出された警告パターン:")
                        for wline in warning_lines[:5]:  # 最大5行表示
                            lines.append(f"     - {wline}")
                        if len(warning_lines) > 5:
                            lines.append(f"     - ... 他 {len(warning_lines) - 5}件")
                    
                    # STDERR内容を折りたたみ可能な形式で表示
                    lines.append(f"   - STDERR出力:")
                    lines.append("")
                    lines.append("   <details>")
                    lines.append("   <summary>詳細を表示</summary>")
                    lines.append("")
                    lines.append("   ```")
                    # STDERR内容を4スペースインデント
                    for stderr_line in stderr.split('\n'):
                        lines.append(f"   {stderr_line}")
                    lines.append("   ```")
                    lines.append("   </details>")
                else:
                    # STDERR情報がない場合は従来通りの表示
                    if log_file and line_number:
                        lines.append(f"{idx}. {message} `({log_file}:{line_number})`")
                    else:
                        lines.append(f"{idx}. {message}")
            if len(log_warnings) > 50:
                lines.append(f"\n... 他 {len(log_warnings) - 50}件の警告")
        lines.append("")
                    
        # リソース状態の重大な問題（0件でも表示）
        lines.append(f"### ❌ リソース状態の重大な問題: {len(critical_issues)}件")
        if critical_issues:
            lines.append("")
            for idx, issue in enumerate(critical_issues, 1):
                lines.append(f"{idx}. **{issue.get('issue_type', 'Unknown')}**")
                lines.append(f"   - リソース: `{issue.get('resource_name', 'Unknown')}`")
                lines.append(f"   - タイプ: {issue.get('resource_type', 'Unknown')}")
                lines.append(f"   - メッセージ: {issue.get('message', 'No message')}")
                if issue.get('namespace'):
                    lines.append(f"   - Namespace: {issue.get('namespace')}")
                lines.append("")
        else:
            lines.append("")

        # リソース状態の警告（0件でも表示）
        lines.append(f"### ⚠️ リソース状態の警告: {len(warning_issues)}件")
        if warning_issues:
            lines.append("")
            for idx, issue in enumerate(warning_issues, 1):
                lines.append(f"{idx}. **{issue.get('issue_type', 'Unknown')}**")
                lines.append(f"   - リソース: `{issue.get('resource_name', 'Unknown')}`")
                lines.append(f"   - タイプ: {issue.get('resource_type', 'Unknown')}")
                lines.append(f"   - メッセージ: {issue.get('message', 'No message')}")
                if issue.get('namespace'):
                    lines.append(f"   - Namespace: {issue.get('namespace')}")
                lines.append("")
        else:
            lines.append("")
        
        # 詳細情報セクション（異常なPodのログとdescribe）
        detailed_logs = diagnosis_data.get('detailed_logs', [])
        if detailed_logs:
            lines.append("## 詳細情報")
            lines.append("")
            lines.append("異常が検出されたリソースの詳細情報（logs、describe、events）はログファイルをご覧ください。")
            lines.append("")
            
            for detail in detailed_logs:
                pod_name = detail.get('pod_name', 'Unknown')
                namespace = detail.get('namespace', 'Unknown')
                issue = detail.get('issue', {})
                saved_files = detail.get('saved_files', {})
                
                lines.append(f"### Pod: {namespace}/{pod_name}")
                lines.append("")
                
                # 問題の概要
                if issue:
                    lines.append(f"**問題タイプ:** {issue.get('issue_type', 'Unknown')}")
                    lines.append(f"**メッセージ:** {issue.get('message', 'No message')}")
                    lines.append("")
                
                # 保存されたファイルへのリンク
                if saved_files:
                    lines.append("**詳細ファイル:**")
                    lines.append("")
                    
                    if 'logs' in saved_files:
                        lines.append(f"- logs: [`{saved_files['logs']}`](resources/{saved_files['logs']})")
                    
                    if 'describe' in saved_files:
                        lines.append(f"- Describe: [`{saved_files['describe']}`](resources/{saved_files['describe']})")
                    
                    if 'events' in saved_files:
                        lines.append(f"- events: [`{saved_files['events']}`](resources/{saved_files['events']})")
                    
                    lines.append("")
                else:
                    lines.append("（詳細情報の取得に失敗しました）")
                    lines.append("")
                
                lines.append("---")
                lines.append("")

        # リソース状態
        resource_status = diagnosis_data.get('resource_status', {})
        
        # resources_by_cluster構造を優先使用（新形式）
        resources_by_cluster = resource_status.get('resources_by_cluster', {})
        
        if resources_by_cluster:
            # クラスタ別表示（新形式）
            # 管理クラスタ
            manager_resources = resources_by_cluster.get('manager', [])
            self._render_cluster_resources('manager', manager_resources, lines)
            
            # テナントクラスタ
            tenant_resources = resources_by_cluster.get('tenant', [])
            self._render_cluster_resources('tenant', tenant_resources, lines)
        else:
            # 後方互換性: resourcesフラットリストを使用（旧形式）
            lines.append("## リソース状態")
            lines.append("")
            
            resources = resource_status.get('resources', [])
            if resources:
                self._render_resources_list(resources, lines)
            else:
                lines.append("（このスクリプトではKubernetesリソースのチェックは行われませんでした）")
                lines.append("")

        if playbooks or log_directory or log_files:
            lines.append("## 参照したログ")
            lines.append("")
            
            # ログファイル情報を表示
            if log_files:
                lines.append(f"**ログファイル:** {len(log_files)}件")
                lines.append("")
                
                # ログファイルごとに開始時刻、終了時刻、稼働時間、Playbook名を表示
                for idx, log_file_info in enumerate(log_files):
                    # log_file_info が辞書の場合（新形式）
                    if isinstance(log_file_info, dict):
                        filename = log_file_info.get('filename', 'Unknown')
                        start_time = log_file_info.get('start_time', 'N/A')
                        end_time = log_file_info.get('end_time', 'N/A')
                        duration = log_file_info.get('duration', 'N/A')
                        
                        # Playbook名を取得（idxに対応）
                        playbook_name = playbooks[idx] if idx < len(playbooks) else 'Unknown'
                        
                        lines.append(f"- `{filename}`")
                        lines.append(f"  - Playbook: {playbook_name}")
                        if start_time != 'N/A':
                            lines.append(f"  - 開始時刻: {start_time}")
                        if end_time != 'N/A':
                            lines.append(f"  - 終了時刻: {end_time}")
                        if duration != 'N/A':
                            lines.append(f"  - 稼働時間: {duration}")
                        lines.append("")
                    else:
                        # 後方互換性: 文字列の場合（旧形式）
                        playbook_name = playbooks[idx] if idx < len(playbooks) else 'Unknown'
                        lines.append(f"- `{log_file_info}`")
                        lines.append(f"  - Playbook: {playbook_name}")
                        lines.append("")        
        return '\n'.join(lines)
    
    def _get_status_emoji(self, status: str) -> str:
        """ステータスに応じた絵文字を返す"""
        status_map = {
            'healthy': '✅',
            'warning': '⚠️',
            'critical': '❌',
            'unknown': '❓'
        }
        return status_map.get(status.lower(), '❓')
    
    def _translate_status(self, status: str) -> str:
        """ステータスを日本語に変換"""
        status_map = {
            'healthy': '正常',
            'warning': '警告',
            'critical': '重大',
            'unknown': '不明'
        }
        return status_map.get(status.lower(), '不明')
    
    def _render_cluster_resources(self, cluster_type: str, resources: List[Dict], lines: List[str]):
        """
        クラスタ別のリソースセクションをレンダリング
        
        Args:
            cluster_type: クラスタ種別 ('manager' or 'tenant')
            resources: リソースリスト
            lines: 出力先の行リスト
        """
        # クラスタ種別の日本語名
        cluster_name_map = {
            'manager': '管理クラスタ',
            'tenant': 'テナントクラスタ'
        }
        cluster_name = cluster_name_map.get(cluster_type, cluster_type)
        
        lines.append(f"## {cluster_name}のリソース状態")
        lines.append("")
        
        if resources:
            self._render_resources_list(resources, lines)
        else:
            # データがない場合のメッセージ
            if cluster_type == 'tenant':
                lines.append(f"（{cluster_name}のリソース収集は未対応のため、データがありません）")
            else:
                lines.append(f"（{cluster_name}のリソースは収集されませんでした）")
            lines.append("")
    
    def _render_resources_list(self, resources: List[Dict], lines: List[str]):
        """
        リソースリストをkind別にグループ化して表示
        
        Args:
            resources: リソースリスト
            lines: 出力先の行リスト
        """
        # kind別にグループ化（同じkindは1回のみ表示）
        displayed_kinds = set()
        
        for res in resources:
            kind = res.get('kind', 'Unknown')
            
            # 既に表示済みのkindはスキップ
            if kind in displayed_kinds:
                continue
            
            displayed_kinds.add(kind)
            
            wide_text = res.get('wide_text', '')
            
            # セクションタイトル
            lines.append(f"### {kind}")
            lines.append("")
            
            if wide_text:
                lines.append("```")
                lines.append(wide_text)
                lines.append("```")
            else:
                lines.append("（データなし）")
            lines.append("")
    
    def save_to_file(self, content: str, output_path: str):
        """
        Markdownファイルとして保存
        
        Args:
            content: Markdown content
            output_path: 出力ファイルパス
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
