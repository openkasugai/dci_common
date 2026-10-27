#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ansible Custom Logger Callback Plugin
Playbookの実行結果を詳細にログファイルに記録するカスタムコールバックプラグイン
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import logging
from datetime import datetime
from ansible.plugins.callback import CallbackBase

DOCUMENTATION = '''
    callback: custom_logger
    type: stdout
    short_description: カスタムログ出力プラグイン
    version_added: "2.0"
    description:
        - Ansibleタスクの実行結果を詳細にログファイルに記録します
        - 各タスクのホスト名、タスク名、実行時間、コマンド、モジュール、引数、標準出力/エラー出力を記録します
    requirements:
      - playbook_log_base_path変数が定義されていること
'''


class CallbackModule(CallbackBase):
    """
    Ansible Callback Plugin for custom logging
    """
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'notification'
    CALLBACK_NAME = 'custom_logger'
    CALLBACK_NEEDS_WHITELIST = False

    def __init__(self, display=None):
        super(CallbackModule, self).__init__(display)
        self.playbook_log_base_path = None
        self.log_file_path = None
        self.logger = None
        self.task_start_times = {}  # タスク開始時刻を記録する辞書 {(host, task_uuid): datetime}
        self.playbook_name = None
        self.current_play = None
        self.task_counter = 0  # タスク通番
        self._plugin_options = {}
        self.play_context_vars = None
        self.playbook_start_time = None  # Playbook開始時刻
    
    def set_options(self, task_keys=None, var_options=None, direct=None):
        """
        Ansibleからオプションを受け取る
        """
        super(CallbackModule, self).set_options(task_keys=task_keys, var_options=var_options, direct=direct)

    def _setup_logger(self, log_file_path):
        """
        Python loggerのセットアップ
        """
        self.log_file_path = log_file_path
        
        # ログディレクトリが存在しない場合は作成
        log_dir = os.path.dirname(self.log_file_path)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, mode=0o755)
        
        # Loggerの設定
        self.logger = logging.getLogger(f'custom_logger_{id(self)}')
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()  # 既存のハンドラをクリア
        
        # ファイルハンドラの設定
        file_handler = logging.FileHandler(self.log_file_path, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # フォーマッタは使用せず、直接メッセージを書き込む
        formatter = logging.Formatter('%(message)s')
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)

    def _write_log(self, message):
        """
        ログメッセージを書き込む
        """
        if self.logger:
            self.logger.info(message)

    def _format_dict(self, data, indent=4):
        """
        辞書データを見やすくフォーマット
        """
        if not isinstance(data, dict):
            return str(data)
        
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{' ' * indent}{key}:")
                for sub_key, sub_value in value.items():
                    lines.append(f"{' ' * (indent + 2)}{sub_key}: {sub_value}")
            elif isinstance(value, list):
                lines.append(f"{' ' * indent}{key}: {value}")
            else:
                lines.append(f"{' ' * indent}{key}: {value}")
        return '\n'.join(lines)

    def _format_multiline(self, text, indent=4):
        """
        複数行テキストを見やすくフォーマット（各行にインデントを追加）
        """
        if not text:
            return f"{' ' * indent}(empty)"
        
        lines = str(text).splitlines()
        formatted_lines = [f"{' ' * indent}{line}" for line in lines]
        return '\n'.join(formatted_lines)

    def _get_task_duration(self, host, task_uuid):
        """
        タスクの実行時間を計算
        """
        key = (host, task_uuid)
        if key in self.task_start_times:
            start_time = self.task_start_times[key]
            duration = datetime.now() - start_time
            del self.task_start_times[key]  # メモリ節約のため削除
            return duration.total_seconds()
        return None

    # ------------------------------------------------------------------
    # Loop タスク用ヘルパーメソッド
    # ------------------------------------------------------------------

    def _get_item_label(self, result):
        """
        ループアイテムの表示用ラベルを返す
        _ansible_item_label を優先し、なければ item を使用する
        """
        item = result._result.get('_ansible_item_label', result._result.get('item'))
        if item is None:
            return None
        if isinstance(item, (dict, list)):
            return str(item)
        return str(item)

    def _write_loop_item_ok_log(self, result):
        """
        ループアイテム成功時の詳細ログを出力
        """
        host = result._host.get_name()
        task_name = result._task.get_name()
        item_label = self._get_item_label(result)
        task_result = result._result

        log_lines = []
        log_lines.append("=" * 80)
        log_lines.append(f"HOST: {host}")
        log_lines.append(f"TASK: {task_name}")
        if item_label is not None:
            log_lines.append(f"LOOP ITEM: {item_label}")
        log_lines.append("STATUS: OK")
        log_lines.append("-" * 80)

        if 'cmd' in task_result:
            cmd = task_result.get('cmd')
            if isinstance(cmd, list):
                cmd = ' '.join(cmd)
            log_lines.append(f"COMMAND: {cmd}")
            log_lines.append("-" * 80)

            stdout = task_result.get('stdout', '')
            log_lines.append("STDOUT:")
            log_lines.append(self._format_multiline(stdout) if stdout else "    (empty)")
            log_lines.append("-" * 80)

            stderr = task_result.get('stderr', '')
            log_lines.append("STDERR:")
            log_lines.append(self._format_multiline(stderr) if stderr else "    (empty)")
        else:
            module_name = result._task.action
            log_lines.append(f"MODULE: {module_name}")

            if 'invocation' in task_result and 'module_args' in task_result['invocation']:
                task_args = task_result['invocation']['module_args'].copy()
            else:
                task_args = result._task.args.copy() if result._task.args else {}
            if task_args:
                log_lines.append("ARGS:")
                log_lines.append(self._format_dict(task_args))

            log_lines.append("-" * 80)
            msg = task_result.get('msg', '')
            log_lines.append("MESSAGE:")
            log_lines.append(self._format_multiline(msg) if msg else "    (no message)")
            log_lines.append("-" * 80)

            stdout = task_result.get('stdout', '')
            log_lines.append("STDOUT:")
            log_lines.append(self._format_multiline(stdout) if stdout else "    (empty)")
            log_lines.append("-" * 80)

            stderr = task_result.get('stderr', '')
            log_lines.append("STDERR:")
            log_lines.append(self._format_multiline(stderr) if stderr else "    (empty)")

        log_lines.append("=" * 80)
        log_lines.append("")
        self._write_log('\n'.join(log_lines))

    def _write_loop_item_failed_log(self, result):
        """
        ループアイテム失敗時の詳細ログを出力
        """
        host = result._host.get_name()
        task_name = result._task.get_name()
        item_label = self._get_item_label(result)
        task_result = result._result
        error_msg = task_result.get('msg', 'Unknown error')

        log_lines = []
        log_lines.append("=" * 80)
        log_lines.append(f"HOST: {host}")
        log_lines.append(f"TASK: {task_name}")
        if item_label is not None:
            log_lines.append(f"LOOP ITEM: {item_label}")
        log_lines.append("STATUS: FAILED")
        log_lines.append("-" * 80)

        if 'rc' in task_result:
            log_lines.append(f"RC: {task_result.get('rc')}")

        if 'cmd' in task_result:
            cmd = task_result.get('cmd')
            if isinstance(cmd, list):
                cmd = ' '.join(cmd)
            log_lines.append(f"COMMAND: {cmd}")
        else:
            module_name = result._task.action
            log_lines.append(f"MODULE: {module_name}")

            if 'invocation' in task_result and 'module_args' in task_result['invocation']:
                task_args = task_result['invocation']['module_args'].copy()
            else:
                task_args = result._task.args.copy() if result._task.args else {}
            if task_args:
                log_lines.append("ARGS:")
                log_lines.append(self._format_dict(task_args))

        log_lines.append("-" * 80)
        log_lines.append(f"ERROR MESSAGE: {error_msg}")

        exception = task_result.get('exception', '')
        if exception:
            log_lines.append("-" * 80)
            log_lines.append("EXCEPTION:")
            log_lines.append(self._format_multiline(exception))

        log_lines.append("-" * 80)
        stdout = task_result.get('stdout', '')
        log_lines.append("STDOUT:")
        log_lines.append(self._format_multiline(stdout) if stdout else "    (empty)")

        log_lines.append("-" * 80)
        stderr = task_result.get('stderr', '')
        log_lines.append("STDERR:")
        log_lines.append(self._format_multiline(stderr) if stderr else "    (empty)")

        log_lines.append("=" * 80)
        log_lines.append("")
        self._write_log('\n'.join(log_lines))

    def _write_loop_item_skipped_log(self, result):
        """
        ループアイテムスキップ時のログを出力
        """
        host = result._host.get_name()
        task_name = result._task.get_name()
        item_label = self._get_item_label(result)

        log_lines = []
        log_lines.append("-" * 80)
        log_lines.append(f"HOST: {host}")
        log_lines.append(f"TASK: {task_name}")
        if item_label is not None:
            log_lines.append(f"LOOP ITEM: {item_label}")
        log_lines.append("STATUS: SKIPPED")
        log_lines.append("-" * 80)
        log_lines.append("")
        self._write_log('\n'.join(log_lines))

    def _write_loop_summary_log(self, result, status):
        """
        ループタスク完了時のサマリーログを出力
        各アイテムの詳細は v2_runner_item_on_* で出力済み
        """
        host = result._host.get_name()
        task_name = result._task.get_name()
        task_uuid = result._task._uuid
        items = result._result.get('results', [])

        duration = self._get_task_duration(host, task_uuid)
        duration_str = f"{duration:.3f}s" if duration is not None else "N/A"

        ok_count      = sum(1 for r in items if not r.get('failed', False) and not r.get('skipped', False))
        failed_count  = sum(1 for r in items if r.get('failed', False))
        skipped_count = sum(1 for r in items if r.get('skipped', False))

        log_lines = []
        log_lines.append("=" * 80)
        log_lines.append(f"HOST: {host}")
        log_lines.append(f"TASK: {task_name}")
        log_lines.append("LOOP SUMMARY")
        log_lines.append(f"STATUS: {status}")
        log_lines.append(f"DURATION: {duration_str}")
        log_lines.append("-" * 80)
        log_lines.append(f"  ok      : {ok_count}")
        log_lines.append(f"  failed  : {failed_count}")
        log_lines.append(f"  skipped : {skipped_count}")
        log_lines.append("=" * 80)
        log_lines.append("")
        self._write_log('\n'.join(log_lines))

    # ------------------------------------------------------------------
    # 非 Loop タスク用ログメソッド
    # ------------------------------------------------------------------

    def _write_task_success_log(self, result):
        """
        成功したタスクの詳細ログを出力
        """
        host = result._host.get_name()
        task_name = result._task.get_name()
        task_uuid = result._task._uuid
        
        # タスク実行時間を計算
        duration = self._get_task_duration(host, task_uuid)
        duration_str = f"{duration:.3f}s" if duration is not None else "N/A"
        
        # ログメッセージの構築
        log_lines = []
        log_lines.append("=" * 80)
        log_lines.append(f"HOST: {host}")
        log_lines.append(f"TASK: {task_name}")
        log_lines.append(f"DURATION: {duration_str}")
        log_lines.append("-" * 80)
        
        # 結果データの取得
        task_result = result._result
        
        # CMDがある場合（command, shell, rawモジュールなど）
        if 'cmd' in task_result:
            cmd = task_result.get('cmd')
            if isinstance(cmd, list):
                cmd = ' '.join(cmd)
            log_lines.append(f"COMMAND: {cmd}")
            log_lines.append("-" * 80)
            
            # STDOUT
            stdout = task_result.get('stdout', '')
            if stdout:
                log_lines.append("STDOUT:")
                log_lines.append(self._format_multiline(stdout))
            else:
                log_lines.append("STDOUT:")
                log_lines.append("    (empty)")
            
            log_lines.append("-" * 80)
            
            # STDERR
            stderr = task_result.get('stderr', '')
            if stderr:
                log_lines.append("STDERR:")
                log_lines.append(self._format_multiline(stderr))
            else:
                log_lines.append("STDERR:")
                log_lines.append("    (empty)")
        else:
            # MODULEとARGSを出力
            module_name = result._task.action
            log_lines.append(f"MODULE: {module_name}")
            
            # タスクの引数を取得（展開済みの値を使用）
            # invocation.module_argsに展開済みの引数が入っている
            if 'invocation' in task_result and 'module_args' in task_result['invocation']:
                # 展開済みの引数を使用
                task_args = task_result['invocation']['module_args'].copy()
            else:
                # フォールバック: タスク定義の引数を使用
                task_args = result._task.args.copy() if result._task.args else {}
            
            if task_args:
                log_lines.append("ARGS:")
                log_lines.append(self._format_dict(task_args))
            
            log_lines.append("-" * 80)
            
            # MODULEの場合はmsgを出力
            msg = task_result.get('msg', '')
            if msg:
                log_lines.append("MESSAGE:")
                log_lines.append(self._format_multiline(msg))
            else:
                log_lines.append("MESSAGE:")
                log_lines.append("    (no message)")
            log_lines.append("-" * 80)
            
            # STDOUT
            stdout = task_result.get('stdout', '')
            if stdout:
                log_lines.append("STDOUT:")
                log_lines.append(self._format_multiline(stdout))
            else:
                log_lines.append("STDOUT:")
                log_lines.append("    (empty)")
            
            log_lines.append("-" * 80)
            
            # STDERR
            stderr = task_result.get('stderr', '')
            if stderr:
                log_lines.append("STDERR:")
                log_lines.append(self._format_multiline(stderr))
            else:
                log_lines.append("STDERR:")
                log_lines.append("    (empty)")
        
        log_lines.append("=" * 80)
        log_lines.append("")  # 空行
        
        self._write_log('\n'.join(log_lines))

    def _write_task_failed_log(self, result):
        """
        失敗したタスクの詳細ログを出力
        """
        host = result._host.get_name()
        task_name = result._task.get_name()
        task_uuid = result._task._uuid
        task_result = result._result

        # タスク実行時間を計算
        duration = self._get_task_duration(host, task_uuid)
        duration_str = f"{duration:.3f}s" if duration is not None else "N/A"
        
        # エラーメッセージの取得
        error_msg = task_result.get('msg', 'Unknown error')
        
        # ログメッセージの構築
        log_lines = []
        log_lines.append("=" * 80)
        log_lines.append(f"HOST: {host}")
        log_lines.append(f"TASK: {task_name}")
        log_lines.append(f"DURATION: {duration_str}")
        log_lines.append(f"STATUS: FAILED")
        log_lines.append("-" * 80)

        # RC
        if 'rc' in task_result:
            log_lines.append(f"RC: {task_result.get('rc')}")

        # command/shell/raw のように cmd を持つ場合
        if 'cmd' in task_result:
            cmd = task_result.get('cmd')
            if isinstance(cmd, list):
                cmd = ' '.join(cmd)
            log_lines.append(f"COMMAND: {cmd}")
        else:
            module_name = result._task.action
            log_lines.append(f"MODULE: {module_name}")

            if 'invocation' in task_result and 'module_args' in task_result['invocation']:
                task_args = task_result['invocation']['module_args'].copy()
            else:
                task_args = result._task.args.copy() if result._task.args else {}

            if task_args:
                log_lines.append("ARGS:")
                log_lines.append(self._format_dict(task_args))

        log_lines.append("-" * 80)
        log_lines.append(f"ERROR MESSAGE: {error_msg}")

        # 例外情報
        exception = task_result.get('exception', '')
        if exception:
            log_lines.append("-" * 80)
            log_lines.append("EXCEPTION:")
            log_lines.append(self._format_multiline(exception))

        # STDOUT
        log_lines.append("-" * 80)
        stdout = task_result.get('stdout', '')
        if stdout:
            log_lines.append("STDOUT:")
            log_lines.append(self._format_multiline(stdout))
        else:
            log_lines.append("STDOUT:")
            log_lines.append("    (empty)")

        # STDERR
        log_lines.append("-" * 80)
        stderr = task_result.get('stderr', '')
        if stderr:
            log_lines.append("STDERR:")
            log_lines.append(self._format_multiline(stderr))
        else:
            log_lines.append("STDERR:")
            log_lines.append("    (empty)")

        log_lines.append("=" * 80)
        log_lines.append("")  # 空行
        
        self._write_log('\n'.join(log_lines))

    def v2_playbook_on_start(self, playbook):
        """
        Playbook開始時に呼び出される
        """
        self.playbook_name = os.path.basename(playbook._file_name)
        self.playbook_start_time = datetime.now()  # Playbook開始時刻を記録

    def v2_playbook_on_play_start(self, play):
        """
        Play開始時に呼び出される
        """
        self.current_play = play
        
        # Playからvariable_managerを取得してplaybook_log_base_pathを設定（まだ設定されていない場合）
        if not self.playbook_log_base_path and hasattr(play, 'get_variable_manager'):
            vm = play.get_variable_manager()
            if vm and hasattr(vm, '_extra_vars'):
                self.playbook_log_base_path = vm._extra_vars.get('playbook_log_base_path')
        
        # Playのvarsから直接取得を試みる
        if not self.playbook_log_base_path and hasattr(play, '_variable_manager'):
            vm = play._variable_manager
            if hasattr(vm, '_extra_vars'):
                self.playbook_log_base_path = vm._extra_vars.get('playbook_log_base_path')
        
        # get_vars()を使う
        play_vars = None
        if not self.playbook_log_base_path and hasattr(play, 'get_vars'):
            try:
                play_vars = play.get_vars()
                self.playbook_log_base_path = play_vars.get('playbook_log_base_path')
            except Exception:
                pass
        
        # play_descriptionを取得（まだplay_varsを取得していない場合は取得）
        play_description = None
        if play_vars is None and hasattr(play, 'get_vars'):
            try:
                play_vars = play.get_vars()
            except Exception:
                pass
        if play_vars:
            play_description = play_vars.get('play_description')
        
        # ログファイルがまだセットアップされていない場合はここでセットアップ
        if not self.logger and self.playbook_name:
            if not self.playbook_log_base_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                playbook_basename = os.path.splitext(self.playbook_name)[0]
                self.playbook_log_base_path = f"./logs/{timestamp}_{playbook_basename}"
                if self._display:
                    self._display.warning(f"playbook_log_base_path not found in play, using default: {self.playbook_log_base_path}")
            
            playbook_basename = os.path.splitext(self.playbook_name)[0]
            log_file_name = f"{playbook_basename}.log"
            log_file_path = os.path.join(self.playbook_log_base_path, log_file_name)
            self._setup_logger(log_file_path)
            
            # Play開始ログを書き込む
            play_name = play.get_name()
            play_log = []
            play_log.append("-" * 80)
            play_log.append(f"PLAY START: {play_name}")
            
            # play_descriptionがある場合は出力
            if play_description:
                desc_lines = play_description.strip().splitlines()
                if len(desc_lines) == 1:
                    play_log.append(f"DESCRIPTION: {desc_lines[0]}")
                else:
                    play_log.append("DESCRIPTION:")
                    for line in desc_lines:
                        if line.strip():  # 空行をスキップ
                            play_log.append(f"    {line.strip()}")
            
            play_log.append(f"TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            play_log.append("-" * 80)
            play_log.append("")
            self._write_log('\n'.join(play_log))
        elif self.logger:
            # 既にロガーがセットアップされている場合はPlay開始ログのみ
            play_name = play.get_name()
            play_log = []
            play_log.append("-" * 80)
            play_log.append(f"PLAY START: {play_name}")
            
            # play_descriptionがある場合は出力
            if play_description:
                desc_lines = play_description.strip().splitlines()
                if len(desc_lines) == 1:
                    play_log.append(f"DESCRIPTION: {desc_lines[0]}")
                else:
                    play_log.append("DESCRIPTION:")
                    for line in desc_lines:
                        if line.strip():  # 空行をスキップ
                            play_log.append(f"    {line.strip()}")
            
            play_log.append(f"TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            play_log.append("-" * 80)
            play_log.append("")
            self._write_log('\n'.join(play_log))

    def v2_playbook_on_task_start(self, task, is_conditional):
        """
        タスク開始時に呼び出される
        """
        self.task_counter += 1
        
        # 全ホストに対してタスク開始時刻を記録
        # （どのホストで実行されるかわからないため、タスクUUIDをキーとして記録）
        task_uuid = task._uuid
        # 簡易的に現在時刻を記録（ホスト情報は結果受信時に判明）
        self._current_task_start = datetime.now()
        self._current_task_uuid = task_uuid

    def v2_runner_on_ok(self, result):
        """
        タスク成功時に呼び出される
        """
        host = result._host.get_name()
        task_uuid = result._task._uuid
        
        # タスク開始時刻を記録（v2_playbook_on_task_startで記録した時刻を使用）
        if hasattr(self, '_current_task_start') and hasattr(self, '_current_task_uuid'):
            if self._current_task_uuid == task_uuid:
                key = (host, task_uuid)
                self.task_start_times[key] = self._current_task_start
        
        # loopタスクはサマリーのみ出力（各アイテムは v2_runner_item_on_* で出力済み）
        if result._result.get('results') is not None:
            self._write_loop_summary_log(result, 'OK')
        else:
            self._write_task_success_log(result)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        """
        タスク失敗時に呼び出される
        """
        host = result._host.get_name()
        task_uuid = result._task._uuid

        # タスク開始時刻を記録（v2_playbook_on_task_startで記録した時刻を使用）
        if hasattr(self, '_current_task_start') and hasattr(self, '_current_task_uuid'):
            if self._current_task_uuid == task_uuid:
                key = (host, task_uuid)
                self.task_start_times[key] = self._current_task_start

        # loopタスクはサマリーのみ出力（各アイテムは v2_runner_item_on_* で出力済み）
        if result._result.get('results') is not None:
            self._write_loop_summary_log(result, 'FAILED')
        else:
            self._write_task_failed_log(result)

    def v2_runner_on_skipped(self, result):
        """
        タスクスキップ時に呼び出される（オプション）
        """
        host = result._host.get_name()
        task_name = result._task.get_name()
        
        skip_log = []
        skip_log.append("-" * 80)
        skip_log.append(f"HOST: {host}")
        skip_log.append(f"TASK: {task_name}")
        skip_log.append(f"STATUS: SKIPPED")
        skip_log.append("-" * 80)
        skip_log.append("")
        
        self._write_log('\n'.join(skip_log))

    # ------------------------------------------------------------------
    # Loop アイテム用コールバック
    # ------------------------------------------------------------------

    def v2_runner_item_on_ok(self, result):
        """
        ループアイテム成功時に呼び出される
        """
        self._write_loop_item_ok_log(result)

    def v2_runner_item_on_failed(self, result):
        """
        ループアイテム失敗時に呼び出される
        """
        self._write_loop_item_failed_log(result)

    def v2_runner_item_on_skipped(self, result):
        """
        ループアイテムスキップ時に呼び出される
        """
        self._write_loop_item_skipped_log(result)

    def v2_playbook_on_stats(self, stats):
        """
        Playbook終了時に統計情報を出力
        """
        # Playbook全体の実行時間を計算
        playbook_end_time = datetime.now()
        if self.playbook_start_time:
            total_duration = playbook_end_time - self.playbook_start_time
            total_seconds = total_duration.total_seconds()
            hours, remainder = divmod(int(total_seconds), 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            duration_str = "N/A"
        
        summary_log = []
        summary_log.append("")
        summary_log.append("=" * 80)
        summary_log.append(f"PLAYBOOK END: {self.playbook_name}")
        summary_log.append(f"END TIME: {playbook_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        summary_log.append(f"TOTAL DURATION: {duration_str}")
        summary_log.append("=" * 80)
        summary_log.append("")
        summary_log.append("SUMMARY:")
        summary_log.append("-" * 80)
        
        hosts = sorted(stats.processed.keys())
        for host in hosts:
            summary = stats.summarize(host)
            summary_log.append(f"  Host: {host}")
            summary_log.append(f"    ok          : {summary['ok']}")
            summary_log.append(f"    changed     : {summary['changed']}")
            summary_log.append(f"    unreachable : {summary['unreachable']}")
            summary_log.append(f"    failed      : {summary['failures']}")
            summary_log.append(f"    skipped     : {summary['skipped']}")
            summary_log.append("")
        
        summary_log.append("=" * 80)
        
        self._write_log('\n'.join(summary_log))
