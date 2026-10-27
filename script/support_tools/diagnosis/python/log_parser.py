#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ansibleログパーサー
custom_logger.pyが出力するログファイルを解析し、
実行されたタスク、デプロイされたリソース、エラー情報を抽出します。
"""

import os
import re
import logging
import hashlib
from typing import Dict, List, Optional, Tuple


class AnsibleLogParser:
    """Ansibleログファイルを解析するクラス"""
    
    def __init__(self, log_dir: str, config: Dict = None):
        """
        Args:
            log_dir: ログディレクトリのパス
            config: 診断ツール設定（config.yaml の内容）
        """
        self.log_dir = log_dir
        self.log_files = []
        self.logger = logging.getLogger(__name__)
        
        # エラー検出設定（デフォルト値）
        default_error_config = {
            'critical_patterns': ['STATUS: FAILED'],
            'warning_patterns': [
                'ERROR:', 'error:', 'FAILED!', 'fatal:', r'failed=\d+',
                'WARNING:', 'warning:', r'\[WARN\]', 'deprecated'
            ],
            'stderr_error_detection': {
                'enabled': False,
                'patterns': ['Error:', 'ERROR:', 'Failed:', 'FAILED:']
            },
            'include_stderr_in_errors': True
        }
        
        # config から設定を取得（存在しない場合はデフォルト）
        if config and 'ansible_log_error_detection' in config:
            self.error_config = {**default_error_config, **config['ansible_log_error_detection']}
        else:
            self.error_config = default_error_config
        
        self._discover_log_files()
    
    def _discover_log_files(self):
        """ログディレクトリ内のログファイルを検索"""
        if not os.path.exists(self.log_dir):
            return
        
        for root, dirs, files in os.walk(self.log_dir):
            for file in files:
                if file.endswith('.log'):
                    self.log_files.append(os.path.join(root, file))
        
        # ファイル名でソート（順序を保証）
        self.log_files.sort()
    
    def parse_all_logs(self) -> Dict:
        """
        全ログファイルを解析
        
        Returns:
            解析結果の辞書
            {
                'playbooks_executed': [playbook名のリスト],
                'tasks_summary': {タスク情報},
                'deployed_resources': {デプロイされたリソース情報},
                'errors': [エラー情報のリスト],
                'warnings': [警告情報のリスト],
                'log_directory': ログディレクトリパス,
                'log_files': [ログファイル情報の辞書リスト]
            }
        """
        result = {
            'playbooks_executed': [],
            'tasks_summary': {},
            'deployed_resources': {
                'namespaces': set(),
                'helm_releases': [],
                'kubectl_applied': []
            },
            'errors': [],
            'warnings': [],
            'log_directory': self.log_dir,
            'log_files': []
        }
        
        for log_file in self.log_files:
            playbook_result = self._parse_log_file(log_file)
            
            # Playbookファイル名を抽出
            playbook_name = self._extract_playbook_name(log_file)
            if playbook_name and playbook_name not in result['playbooks_executed']:
                result['playbooks_executed'].append(playbook_name)
            
            # ログファイル情報を追加（ファイル名とタイミング情報）
            log_file_info = {
                'filename': os.path.basename(log_file),
                'start_time': playbook_result.get('timing', {}).get('start_time', 'N/A'),
                'end_time': playbook_result.get('timing', {}).get('end_time', 'N/A'),
                'duration': playbook_result.get('timing', {}).get('duration', 'N/A')
            }
            result['log_files'].append(log_file_info)
            
            # 結果をマージ
            result['tasks_summary'][playbook_name] = playbook_result['tasks']
            result['errors'].extend(playbook_result['errors'])
            result['warnings'].extend(playbook_result['warnings'])
            
            # デプロイリソース情報をマージ
            result['deployed_resources']['namespaces'].update(
                playbook_result['namespaces']
            )
            result['deployed_resources']['helm_releases'].extend(
                playbook_result['helm_releases']
            )
            result['deployed_resources']['kubectl_applied'].extend(
                playbook_result['kubectl_applied']
            )
        
        # setをlistに変換（JSON serializable）
        result['deployed_resources']['namespaces'] = list(
            result['deployed_resources']['namespaces']
        )
        
        # playbooks_executedをソート（Playbook番号順）
        result['playbooks_executed'].sort()
        
        return result
    
    def _parse_log_file(self, log_file_path: str) -> Dict:
        """
        単一のログファイルを解析
        
        Args:
            log_file_path: ログファイルのパス
        
        Returns:
            解析結果の辞書
        """
        result = {
            'tasks': [],
            'errors': [],
            'warnings': [],
            'namespaces': set(),
            'helm_releases': [],
            'kubectl_applied': [],
            'timing': {}
        }
        
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            error_msg = f'ログファイルが見つかりません: {log_file_path}'
            self.logger.warning(error_msg)
            result['errors'].append({
                'type': 'file_not_found',
                'message': error_msg,
                'file': log_file_path,
                'parse_step': 'file_read'
            })
            return result
        except Exception as e:
            error_msg = f'ログファイルの読み込みに失敗: {log_file_path}'
            self.logger.warning(f"{error_msg}: {e}")
            result['errors'].append({
                'type': 'file_read_error',
                'message': error_msg,
                'detail': str(e),
                'file': log_file_path,
                'parse_step': 'file_read'
            })
            return result
        
        # 各解析処理を個別にtry-exceptでラップ
        try:
            result['tasks'] = self._extract_tasks(content)
        except Exception as e:
            self.logger.warning(f"タスク抽出に失敗 ({log_file_path}): {e}")
            result['errors'].append({
                'type': 'task_extraction_error',
                'message': f'タスク情報の抽出に失敗',
                'detail': str(e),
                'file': log_file_path,
                'parse_step': 'task_extraction'
            })
        
        try:
            result['errors'] = self._extract_errors(content, log_file_path)
        except Exception as e:
            self.logger.warning(f"エラー抽出に失敗 ({log_file_path}): {e}")
            result['errors'].append({
                'type': 'error_extraction_error',
                'message': f'エラー情報の抽出に失敗',
                'detail': str(e),
                'file': log_file_path,
                'parse_step': 'error_extraction'
            })
        
        try:
            result['warnings'] = self._extract_warnings(content, log_file_path)
        except Exception as e:
            self.logger.warning(f"警告抽出に失敗 ({log_file_path}): {e}")
            result['errors'].append({
                'type': 'warning_extraction_error',
                'message': f'警告情報の抽出に失敗',
                'detail': str(e),
                'file': log_file_path,
                'parse_step': 'warning_extraction'
            })
        
        try:
            result['namespaces'] = self._extract_namespaces(content)
        except Exception as e:
            self.logger.warning(f"Namespace抽出に失敗 ({log_file_path}): {e}")
            result['errors'].append({
                'type': 'namespace_extraction_error',
                'message': f'Namespace情報の抽出に失敗',
                'detail': str(e),
                'file': log_file_path,
                'parse_step': 'namespace_extraction'
            })
            result['namespaces'] = set()
        
        try:
            result['helm_releases'] = self._extract_helm_releases(content)
        except Exception as e:
            self.logger.warning(f"Helmリリース抽出に失敗 ({log_file_path}): {e}")
            result['errors'].append({
                'type': 'helm_extraction_error',
                'message': f'Helmリリース情報の抽出に失敗',
                'detail': str(e),
                'file': log_file_path,
                'parse_step': 'helm_extraction'
            })
            result['helm_releases'] = []
        
        try:
            result['kubectl_applied'] = self._extract_kubectl_applied(content)
        except Exception as e:
            self.logger.warning(f"kubectl apply抽出に失敗 ({log_file_path}): {e}")
            result['errors'].append({
                'type': 'kubectl_extraction_error',
                'message': f'kubectl apply情報の抽出に失敗',
                'detail': str(e),
                'file': log_file_path,
                'parse_step': 'kubectl_extraction'
            })
            result['kubectl_applied'] = []
        
        try:
            result['timing'] = self._extract_playbook_timing(content)
        except Exception as e:
            self.logger.warning(f"タイミング情報抽出に失敗 ({log_file_path}): {e}")
            result['errors'].append({
                'type': 'timing_extraction_error',
                'message': f'タイミング情報の抽出に失敗',
                'detail': str(e),
                'file': log_file_path,
                'parse_step': 'timing_extraction'
            })
            result['timing'] = {}
        
        return result
    
    def _extract_playbook_name(self, log_file_path: str) -> Optional[str]:
        """ログファイル名からPlaybook名を抽出"""
        basename = os.path.basename(log_file_path)
        # パターン: YYYYMMDD_HHMMSS_XX_YY-playbook_name.log
        # XX_プレフィックスを削除して YY-playbook_name.yaml を返す
        match = re.search(r'\d{2}_(\d{2}-[a-zA-Z0-9_-]+)\.log', basename)
        if match:
            return match.group(1) + '.yaml'
        # フォールバック: 古い形式
        match = re.search(r'(\d{2}-[a-zA-Z0-9_-]+)\.log', basename)
        if match:
            return match.group(1) + '.yaml'
        return basename.replace('.log', '')
    
    def _extract_playbook_timing(self, content: str) -> Dict:
        """
        Playbook実行時間情報を抽出
        
        Args:
            content: ログファイルの内容
        
        Returns:
            タイミング情報の辞書 {'start_time': str, 'end_time': str, 'duration': str}
        """
        timing = {
            'start_time': 'N/A',
            'end_time': 'N/A',
            'duration': 'N/A'
        }
        
        # PLAY START の TIME を抽出
        start_pattern = r'PLAY START:.*?TIME:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})'
        start_match = re.search(start_pattern, content, re.DOTALL)
        if start_match:
            timing['start_time'] = start_match.group(1)
        
        # PLAYBOOK END の END TIME を抽出
        end_pattern = r'END TIME:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})'
        end_match = re.search(end_pattern, content)
        if end_match:
            timing['end_time'] = end_match.group(1)
        
        # TOTAL DURATION を抽出
        duration_pattern = r'TOTAL DURATION:\s*(\d{2}:\d{2}:\d{2})'
        duration_match = re.search(duration_pattern, content)
        if duration_match:
            timing['duration'] = duration_match.group(1)
        
        return timing
    
    def _extract_tasks(self, content: str) -> List[Dict]:
        """タスク情報を抽出"""
        tasks = []
        
        # タスク区切りパターン（custom_logger.pyの出力形式に基づく）
        task_pattern = r'={80}\nHOST: (.+?)\nTASK: (.+?)\n'
        
        for match in re.finditer(task_pattern, content):
            host = match.group(1).strip()
            task_name = match.group(2).strip()
            
            tasks.append({
                'host': host,
                'name': task_name
            })
        
        return tasks
    
    def _extract_errors(self, content: str, log_file_path: str = '') -> List[Dict]:
        """エラー情報を抽出（重大エラー：STATUS: FAILEDタスクとSTDERRエラー）"""
        errors = []
        log_file_name = os.path.basename(log_file_path) if log_file_path else ''
        
        # 設定から重大エラーパターンを取得
        critical_patterns = self.error_config.get('critical_patterns', ['STATUS: FAILED'])
        
        lines = content.split('\n')
        
        # STATUS: FAILED タスクを検出してブロック全体を解析
        if 'STATUS: FAILED' in critical_patterns:
            failed_tasks = self._extract_failed_task_details(content, log_file_name)
            errors.extend(failed_tasks)
        
        # STDERR内のエラー検出が有効な場合
        stderr_config = self.error_config.get('stderr_error_detection', {})
        if stderr_config.get('enabled', False):
            stderr_patterns = stderr_config.get('patterns', [])
            stderr_errors = self._extract_stderr_errors(content, log_file_name, stderr_patterns)
            errors.extend(stderr_errors)
        
        # その他の重大エラーパターンを検出
        other_patterns = [p for p in critical_patterns if p != 'STATUS: FAILED']
        for line_number, line in enumerate(lines, start=1):
            for pattern in other_patterns:
                try:
                    if re.search(pattern, line, re.IGNORECASE):
                        error_dict = {
                            'type': 'critical_pattern',
                            'message': line.strip()
                        }
                        if log_file_name:
                            error_dict['log_file'] = log_file_name
                            error_dict['line_number'] = line_number
                        errors.append(error_dict)
                        break
                except re.error as e:
                    self.logger.warning(f"Invalid regex pattern '{pattern}': {e}")
        
        return errors
    
    def _extract_warnings(self, content: str, log_file_path: str = '') -> List[Dict]:
        """警告情報を抽出（軽微なエラーを含む）"""
        warnings = []
        log_file_name = os.path.basename(log_file_path) if log_file_path else ''
        
        # 設定から警告パターンを取得
        warning_patterns = self.error_config.get('warning_patterns', [
            'ERROR:', 'error:', 'FAILED!', 'fatal:', r'failed=\d+',
            'WARNING:', 'warning:', r'\[WARN\]', 'deprecated'
        ])
        
        lines = content.split('\n')
        # 警告の一時リスト（STDERR抽出前）
        temp_warnings = []
        
        for line_number, line in enumerate(lines, start=1):
            for pattern in warning_patterns:
                try:
                    if re.search(pattern, line, re.IGNORECASE):
                        warning_dict = {
                            'type': 'warning',
                            'message': line.strip(),
                            'line_number': line_number
                        }
                        if log_file_name:
                            warning_dict['log_file'] = log_file_name
                        temp_warnings.append(warning_dict)
                        break  # 同じ行で複数パターンにマッチしても1回だけ記録
                except re.error as e:
                    self.logger.warning(f"Invalid regex pattern '{pattern}': {e}")
        
        # 各警告にSTDERR情報を追加
        for warning in temp_warnings:
            stderr_info = self._find_stderr_for_line(content, warning['line_number'])
            if stderr_info:
                warning['task_name'] = stderr_info['task_name']
                warning['stderr'] = stderr_info['stderr']
        
        # 同じSTDERRブロックの警告を統合
        warnings = self._consolidate_warnings_by_stderr(temp_warnings)
        
        return warnings
    
    def _extract_failed_task_details(self, content: str, log_file_name: str) -> List[Dict]:
        """
        STATUS: FAILED タスクの詳細情報を抽出
        タスクブロック全体（HOST、TASK、ERROR MESSAGE、STDERR等）を解析
        
        Args:
            content: ログファイルの内容
            log_file_name: ログファイル名
        
        Returns:
            エラー情報の辞書リスト
        """
        errors = []
        
        # タスクブロックを区切り線で分割
        # パターン: ====...==== で始まるブロックを抽出
        task_blocks = re.split(r'={80,}', content)
        
        lines = content.split('\n')
        current_line = 0
        
        for block in task_blocks:
            if not block.strip():
                continue
            
            # STATUS: FAILED を含むブロックのみ処理
            if 'STATUS: FAILED' not in block:
                current_line += block.count('\n') + 1
                continue
            
            # ブロック内の情報を抽出
            host_match = re.search(r'^HOST:\s*(.+)$', block, re.MULTILINE)
            task_match = re.search(r'^TASK:\s*(.+)$', block, re.MULTILINE)
            error_msg_match = re.search(r'^ERROR MESSAGE:\s*(.+)$', block, re.MULTILINE)
            
            host = host_match.group(1).strip() if host_match else 'Unknown'
            task_name = task_match.group(1).strip() if task_match else 'Unknown task'
            error_message = error_msg_match.group(1).strip() if error_msg_match else 'No error message'
            
            # STDERR内容を抽出（存在する場合）
            stderr_content = None
            if self.error_config.get('include_stderr_in_errors', True):
                stderr_match = re.search(
                    r'^STDERR:\s*\n(.*?)(?:^[-=]{80,}|\Z)',
                    block,
                    re.MULTILINE | re.DOTALL
                )
                if stderr_match:
                    stderr_content = stderr_match.group(1).strip()
            
            # エラー辞書を作成
            error_dict = {
                'type': 'task_failed',
                'message': task_name,
                'host': host,
                'error_message': error_message,
            }
            
            if stderr_content:
                error_dict['stderr'] = stderr_content
            
            if log_file_name:
                error_dict['log_file'] = log_file_name
                # ブロックの開始行番号を計算
                error_dict['line_number'] = current_line + 1
            
            errors.append(error_dict)
            current_line += block.count('\n') + 1
        
        return errors
    
    def _extract_stderr_errors(self, content: str, log_file_name: str, patterns: List[str]) -> List[Dict]:
        """
        STDERR内容からエラーパターンを検出
        
        Args:
            content: ログファイルの内容
            log_file_name: ログファイル名
            patterns: 検出するパターンのリスト
        
        Returns:
            エラー情報の辞書リスト
        """
        errors = []
        
        # STDERRブロックを抽出
        stderr_blocks = re.finditer(
            r'^STDERR:\s*\n(.*?)(?:^[-=]{80,}|\Z)',
            content,
            re.MULTILINE | re.DOTALL
        )
        
        lines = content.split('\n')
        
        for match in stderr_blocks:
            stderr_content = match.group(1).strip()
            if not stderr_content or stderr_content == '(empty)':
                continue
            
            # パターンに一致するか確認
            for pattern in patterns:
                try:
                    if re.search(pattern, stderr_content, re.IGNORECASE):
                        # STDERR全体を含むエラーとして記録
                        # このSTDERRがどのタスクのものか推測するため、前後のコンテキストを取得
                        start_pos = match.start()
                        line_number = content[:start_pos].count('\n') + 1
                        
                        # タスク名を逆方向検索
                        task_match = None
                        for i in range(line_number - 1, max(0, line_number - 20), -1):
                            if i < len(lines):
                                task_line_match = re.match(r'^TASK:\s*(.+)$', lines[i])
                                if task_line_match:
                                    task_match = task_line_match.group(1).strip()
                                    break
                        
                        error_dict = {
                            'type': 'stderr_error',
                            'message': task_match if task_match else 'Unknown task (STDERR error)',
                            'error_message': f'Error pattern "{pattern}" found in STDERR',
                            'stderr': stderr_content
                        }
                        
                        if log_file_name:
                            error_dict['log_file'] = log_file_name
                            error_dict['line_number'] = line_number
                        
                        errors.append(error_dict)
                        break  # 1つのSTDERRブロックで1つのエラーとして記録
                except re.error as e:
                    self.logger.warning(f"Invalid regex pattern '{pattern}': {e}")
        
        return errors
    
    def _parse_task_block_sections(self, lines: List[str], task_start_line: int, task_end_line: int) -> Dict[str, Tuple[int, int]]:
        """
        タスクブロック内のセクション(STDOUT, STDERR)の範囲を解析
        
        Args:
            lines: ログファイルの全行リスト
            task_start_line: タスクブロック開始行(0-indexed)
            task_end_line: タスクブロック終了行(0-indexed)
        
        Returns:
            セクション範囲の辞書 {'stdout': (start, end), 'stderr': (start, end)}
            範囲は1-indexed行番号で、start <= 行番号 < end
        """
        sections = {}
        
        # STDOUTセクションを探す
        stdout_start = None
        for i in range(task_start_line, task_end_line):
            if i < len(lines) and re.match(r'^STDOUT:\s*$', lines[i]):
                stdout_start = i + 1  # STDOUT:の次の行から開始
                break
        
        if stdout_start is not None:
            # STDOUTの終了を探す(次の区切り線またはSTDERR:)
            stdout_end = task_end_line
            for i in range(stdout_start, task_end_line):
                if i < len(lines):
                    if re.match(r'^[-=]{80,}', lines[i]):
                        stdout_end = i
                        break
                    if re.match(r'^STDERR:\s*$', lines[i]):
                        stdout_end = i
                        break
            
            # 0-indexed → 1-indexed変換
            sections['stdout'] = (stdout_start + 1, stdout_end + 1)
        
        # STDERRセクションを探す
        stderr_start = None
        for i in range(task_start_line, task_end_line):
            if i < len(lines) and re.match(r'^STDERR:\s*$', lines[i]):
                stderr_start = i + 1  # STDERR:の次の行から開始
                break
        
        if stderr_start is not None:
            # STDERRの終了を探す(次の区切り線)
            stderr_end = task_end_line
            for i in range(stderr_start, task_end_line):
                if i < len(lines) and re.match(r'^[-=]{80,}', lines[i]):
                    stderr_end = i
                    break
            
            # 0-indexed → 1-indexed変換
            sections['stderr'] = (stderr_start + 1, stderr_end + 1)
        
        return sections
    
    def _find_stderr_for_line(self, content: str, line_number: int) -> Optional[Dict]:
        """
        指定行番号のSTDERRを検索（改善版）
        
        推奨ロジック:
        1. タスクブロックを特定
        2. タスクブロック内のSTDERRセクション範囲を解析
        3. 警告行番号がSTDERRセクション内にあるかチェック
        4. STDERRセクション内にある場合のみSTDERR詳細を返す
        
        Args:
            content: ログファイルの内容
            line_number: 警告が検出された行番号(1-indexed)
        
        Returns:
            警告がSTDERRセクション内にある場合: {'task_name': str, 'stderr': str}
            STDOUTセクションまたはセクション外の場合: None
        """
        lines = content.split('\n')
        
        # ========================================
        # Step 1: タスクブロックを特定
        # ========================================
        task_start_line = None
        task_name = None
        
        # 警告行から前方に遡ってタスクブロック開始を探す
        for i in range(line_number - 1, max(0, line_number - 5000), -1):
            if i < len(lines) and re.match(r'^={80,}', lines[i]):
                task_start_line = i
                # タスク名を検索(区切り線の後)
                for j in range(i + 1, min(len(lines), i + 10)):
                    task_match = re.match(r'^TASK:\s*(.+)$', lines[j])
                    if task_match:
                        task_name = task_match.group(1).strip()
                        break
                break
        
        if task_start_line is None:
            return None
        
        # タスクブロックの終了を探す(次の区切り線)
        task_end_line = len(lines)
        for i in range(task_start_line + 1, min(len(lines), task_start_line + 5000)):
            if re.match(r'^={80,}', lines[i]):
                task_end_line = i
                break
        
        # ========================================
        # Step 2: タスクブロック内のセクション範囲を解析
        # ========================================
        sections = self._parse_task_block_sections(lines, task_start_line, task_end_line)
        
        # ========================================
        # Step 3: 警告行番号がSTDERRセクション内にあるかチェック
        # ========================================
        if 'stderr' in sections:
            stderr_start, stderr_end = sections['stderr']
            
            # 警告行がSTDERRセクション範囲内にあるかチェック
            if stderr_start <= line_number < stderr_end:
                # STDERRセクション内容を抽出
                stderr_lines = lines[stderr_start - 1:stderr_end - 1]  # 1-indexed → 0-indexed
                stderr_content = '\n'.join(stderr_lines).strip()
                
                # (empty) や空のSTDERRは無視
                if stderr_content and stderr_content != '(empty)':
                    return {
                        'task_name': task_name or 'Unknown task',
                        'stderr': stderr_content
                    }
        
        # STDERRセクション外の警告(STDOUTセクション内など)はNoneを返す
        return None
    
    def _consolidate_warnings_by_stderr(self, warnings: List[Dict]) -> List[Dict]:
        """
        同じSTDERRブロックを持つ警告を統合
        
        Args:
            warnings: 警告リスト
        
        Returns:
            統合された警告リスト
        """
        # STDERRがない警告はそのまま追加
        no_stderr_warnings = [w for w in warnings if 'stderr' not in w]
        
        # STDERRがある警告をグループ化
        stderr_groups = {}
        for warning in warnings:
            if 'stderr' not in warning:
                continue
            
            # グループ化キー: タスク名 + STDERR内容のハッシュ
            task_name = warning.get('task_name', 'Unknown')
            stderr_hash = hashlib.md5(warning['stderr'].encode()).hexdigest()
            group_key = f"{task_name}:{stderr_hash}"
            
            if group_key not in stderr_groups:
                stderr_groups[group_key] = []
            stderr_groups[group_key].append(warning)
        
        # グループを統合
        consolidated = []
        for group_key, group_warnings in stderr_groups.items():
            if len(group_warnings) == 1:
                # 1つだけの場合はそのまま追加
                consolidated.append(group_warnings[0])
            else:
                # 複数ある場合は統合
                first = group_warnings[0]
                warning_lines = [w['message'] for w in group_warnings]
                
                consolidated_warning = {
                    'type': 'warning',
                    'message': f"Multiple warnings in STDERR (タスク: {first.get('task_name', 'Unknown')})",
                    'task_name': first.get('task_name', 'Unknown'),
                    'stderr': first['stderr'],
                    'warning_lines': warning_lines,
                    'log_file': first.get('log_file', ''),
                    'line_number': group_warnings[0]['line_number']  # 最初の警告の行番号
                }
                consolidated.append(consolidated_warning)
        
        # STDERRなし + 統合済みを結合してソート
        all_warnings = no_stderr_warnings + consolidated
        # ログファイル名と行番号でソート
        all_warnings.sort(key=lambda w: (w.get('log_file', ''), w.get('line_number', 0)))
        
        return all_warnings
    
    def _extract_namespaces(self, content: str) -> set:
        """作成されたNamespaceを抽出"""
        namespaces = set()
        
        # "kubectl create namespace" パターン
        ns_patterns = [
            r'kubectl create namespace\s+(\S+)',
            r'--namespace\s+(\S+)',
            r'-n\s+(\S+)',
            # 厳格なYAMLコンテキストでのnamespace抽出（HelmコマンドやKubernetes YAMLマニフェスト用）
            r'^\s{2,8}NAMESPACE:\s+([a-z0-9][a-z0-9-]*[a-z0-9]|[a-z0-9])$',
        ]
        
        for pattern in ns_patterns:
            # 最後のパターンはMULTILINEモードで実行
            flags = re.MULTILINE if pattern.startswith('^') else 0
            
            for match in re.finditer(pattern, content, flags):
                ns = match.group(1).strip()
                
                # Kubernetes namespace命名規則に準拠した検証
                # - 小文字英数字とハイフンのみ
                # - 1-63文字
                # - 英数字で開始・終了
                if not self._is_valid_namespace(ns):
                    continue
                
                # 変数展開されていないものを除外
                if ns.startswith('{{'):
                    continue
                
                # デフォルトnamespaceは除外
                if ns in ['default', 'kube-system', 'kube-public', 'kube-node-lease']:
                    continue
                    
                namespaces.add(ns)
        
        return namespaces
    
    def _is_valid_namespace(self, ns: str) -> bool:
        """
        Kubernetes namespace命名規則に準拠しているか検証
        RFC 1123 DNS label規則:
        - 小文字英数字とハイフン(-)のみ
        - 1-63文字
        - 英数字で開始・終了
        """
        if not ns or len(ns) > 63:
            return False
        
        # 基本的な文字チェック: 小文字英数字とハイフンのみ
        if not re.match(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$', ns):
            return False
        
        # 無効なパターンを除外
        invalid_patterns = [
            r'://',  # URL
            r'^\$',  # シェル変数
            r'^".*"$',  # 引用符で囲まれた文字列
            r"^'.*'$",  # 単一引用符で囲まれた文字列
            r'@',  # メールアドレスやDB接続文字列
            r'\..*\.',  # FQDNやドメイン名（.が複数）
            r'^[A-Z]',  # 大文字で開始（Kubernetesでは無効）
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, ns):
                return False
        
        return True
    
    def _extract_helm_releases(self, content: str) -> List[Dict]:
        """Helmリリース情報を抽出"""
        releases = []
        
        # "helm upgrade --install" or "helm install" パターン
        helm_pattern = r'helm\s+(?:upgrade\s+--install|install)\s+(\S+)\s+(\S+)'
        
        for match in re.finditer(helm_pattern, content):
            release_name = match.group(1).strip()
            chart = match.group(2).strip()
            
            # namespaceも抽出を試みる
            namespace = None
            line = match.group(0)
            ns_match = re.search(r'(?:-n|--namespace)\s+(\S+)', line)
            if ns_match:
                namespace = ns_match.group(1)
            
            releases.append({
                'name': release_name,
                'chart': chart,
                'namespace': namespace
            })
        
        return releases
    
    def _extract_kubectl_applied(self, content: str) -> List[Dict]:
        """kubectl applyで適用されたリソースを抽出"""
        applied = []
        
        # "kubectl apply -f" パターン
        kubectl_pattern = r'kubectl\s+apply\s+-f\s+(\S+)'
        
        for match in re.finditer(kubectl_pattern, content):
            file_path = match.group(1).strip()
            applied.append({
                'file': file_path
            })
        
        return applied
