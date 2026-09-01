# ==============================================================================
# 🐍 PC Butler: main_window.py (GUI 인터페이스 및 쓰레딩 로직) - 최종 요구사항 통합 및 CRITICAL FIX
# [CRITICAL FIX] 1. 'theme_action' 객체 생성 전에 'apply_theme'이 호출되는 순서 오류 수정 (AttributeError 해결).
# [핵심 기능] 2. 로그 GUI 리디렉션 3. 3가지 모드(일반/고급/기타) 선택 복원 4. 긴급 작업 중지 기능 5. 밝은/어두운 테마 전환 기능
# ==============================================================================
import sys
import traceback
import json
import os
import subprocess 
import platform 
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QTextEdit, QProgressBar, QLabel, QDesktopWidget, QMessageBox, QFileDialog, 
    QComboBox, QToolBar, QAction, QScrollArea, QSizePolicy, QGroupBox 
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QCoreApplication, QSize 
from PyQt5.QtGui import QIcon, QTextCharFormat, QColor, QFont 
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional, Union 
from threading import Event 
import configparser

# ------------------------------------------------------------------------------
# 테마 정의 (Dark Theme / Light Theme)
# ------------------------------------------------------------------------------
DARK_THEME_QSS = """
    QMainWindow, QWidget { background-color: #2e2e2e; color: #f0f0f0; }
    QGroupBox { color: #ffffff; border: 1px solid #555555; margin-top: 10px; }
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px; }
    QTextEdit { background-color: #1e1e1e; color: #cccccc; border: 1px solid #333333; }
    QProgressBar { border: 2px solid #555555; background-color: #444444; color: #ffffff; text-align: center; }
    QProgressBar::chunk { background-color: #0078d4; } /* Windows Blue */
    QPushButton { background-color: #505050; color: #ffffff; border: 1px solid #404040; padding: 5px; }
    QPushButton:hover { background-color: #606060; }
    QPushButton:pressed { background-color: #404040; }
    QPushButton:disabled { background-color: #3e3e3e; color: #777777; }
    QComboBox { background-color: #404040; color: #ffffff; border: 1px solid #555555; }
    QToolBar { background-color: #3e3e3e; spacing: 5px; }
    QAction { color: #f0f0f0; }
"""

LIGHT_THEME_QSS = """
    QMainWindow, QWidget { background-color: #f0f0f0; color: #000000; }
    QGroupBox { color: #000000; border: 1px solid #aaaaaa; margin-top: 10px; }
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px; }
    QTextEdit { background-color: #ffffff; color: #000000; border: 1px solid #bbbbbb; }
    QProgressBar { border: 2px solid #aaaaaa; background-color: #eeeeee; color: #000000; text-align: center; }
    QProgressBar::chunk { background-color: #0078d4; } /* Windows Blue */
    QPushButton { background-color: #dddddd; color: #000000; border: 1px solid #cccccc; padding: 5px; }
    QPushButton:hover { background-color: #eeeeee; }
    QPushButton:pressed { background-color: #cccccc; }
    QPushButton:disabled { background-color: #f5f5f5; color: #aaaaaa; }
    QComboBox { background-color: #ffffff; color: #000000; border: 1px solid #cccccc; }
    QToolBar { background-color: #eeeeee; spacing: 5px; }
    QAction { color: #000000; }
"""

# ------------------------------------------------------------------------------
# 플러그인 임포트 및 Mock 정의
# ------------------------------------------------------------------------------
try:
    from plugin_base import PCButlerPlugin 
    
    AUTO_FIX_MAPPING_GUI = {
        "plugin_antiviruscheck.py": "plugin_antivirus_manager.py",
        "plugin_autoruncheck.py": "plugin_configlock.py",
        # ... 여기에 실제 매핑 정보를 추가하십시오.
    }
except ImportError:
    class PCButlerPlugin:
        def __init__(self, analysis_id: str, settings: Any): pass
        def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
            return {"status": "error", "summary": "PCButlerPlugin 클래스 로드 실패 (Mock)"}
    
    AUTO_FIX_MAPPING_GUI = {}
    print("Warning: plugin_base.py could not be imported. Using Mock class.") 

# ==============================================================================
# Worker Thread 클래스
# ==============================================================================

class Worker(QThread):
    """백그라운드에서 플러그인 그룹 실행을 담당하는 쓰레드"""
    finished = pyqtSignal(dict) 
    progress_signal = pyqtSignal(str, int) 
    log_signal = pyqtSignal(str, str) 

    def __init__(self, plugin_group_executor: Callable, plugins_to_run: List[str], settings: Dict[str, Any], stop_event: Event, plugin_name_to_class: Dict[str, Any], is_follow_up_task: bool = False, parent=None):
        super().__init__(parent)
        self.plugin_group_executor = plugin_group_executor 
        self.plugins_to_run = plugins_to_run
        self.settings = settings
        self.stop_event = stop_event
        self.plugin_name_to_class = plugin_name_to_class 
        self.is_follow_up_task = is_follow_up_task

    def _stop_check(self) -> bool:
        return self.stop_event.is_set()

    def _logger_callback(self, message: str, color: str = 'white', end: str = '\n'):
        self.log_signal.emit(message, color)

    def run(self):
        try:
            task_type = "후속 조치" if self.is_follow_up_task else "진단 작업"
            self.log_signal.emit(f"🚀 {task_type} 쓰레드 시작... (총 {len(self.plugins_to_run)}개 플러그인)", "cyan")
            
            main_result = self.plugin_group_executor(
                self.plugins_to_run, 
                self.settings, 
                self._logger_callback, 
                self.progress_signal.emit, 
                self._stop_check, 
                self.plugin_name_to_class 
            )

            if main_result.get('status') == "ABORTED":
                self.finished.emit({"status": "ABORTED", "summary": f"사용자 요청으로 {task_type}이 중단됨."})
                return

            self.log_signal.emit(f"🎉 모든 {task_type}이 성공적으로 완료되었습니다.", "lime")
            self.finished.emit(main_result)
            
        except Exception as e:
            error_details = traceback.format_exc()
            self.log_signal.emit(f"🚨 치명적인 오류 발생: {type(e).__name__}: {str(e)}", "red")
            self.log_signal.emit(f"상세 정보:\n{error_details}", "gray")
            self.finished.emit({"status": "FATAL_ERROR", "summary": f"쓰레드 실행 중 치명적인 오류 발생."})


# ==============================================================================
# MainWindow 클래스
# ==============================================================================

class MainWindow(QMainWindow):
    def __init__(self, plugin_group_executor: Callable, plugin_name_to_class: Dict[str, Any], plugins_by_group: Dict[str, List[str]], config_obj: configparser.ConfigParser, parent=None):
        super().__init__(parent)
        
        self.plugin_group_executor = plugin_group_executor
        self.plugin_name_to_class = plugin_name_to_class
        self.plugins_by_group = plugins_by_group
        self.config = config_obj
        
        self.settings = {}
        for section in self.config.sections():
            self.settings[section.upper()] = {k.upper(): v for k, v in self.config.items(section)}
        self.settings['BASE_DIR'] = os.path.dirname(os.path.abspath(__file__))

        # 🚨 FIX: 콘솔 모드(main.py execute_console_plugins)에서만 주입되던
        #        REPORT_DIR_FINAL 이 GUI 모드에서는 빠져 있어, plugin_base.py의
        #        _save_result_to_file()가 매번 "보고서 저장 경로가 불명확합니다"를
        #        출력하며 결과 JSON을 저장하지 못하던 문제를 수정.
        raw_report_dir = self.settings.get('PATHS', {}).get('REPORT_DIR', 'reports')
        self.settings['REPORT_DIR_FINAL'] = os.path.join(self.settings['BASE_DIR'], raw_report_dir)
        try:
            os.makedirs(self.settings['REPORT_DIR_FINAL'], exist_ok=True)
        except Exception:
            pass

        self.stop_event = Event()
        self.worker = None 
        self.is_running = False
        self.current_theme = 'dark' # 기본 테마 설정

        self.setWindowTitle("PC Butler - 통합 진단 및 조치 시스템")
        self._init_ui()

    # --------------------------------------------------------------------------
    # UI 초기화 및 구성
    # --------------------------------------------------------------------------

    def _init_ui(self):
        """UI 구성 요소를 초기화하고 배치합니다."""
        self.setGeometry(0, 0, 1000, 700)
        self._center_window()
        
        # 🟢 애플리케이션 아이콘 설정
        icon_path = os.path.join(self.settings.get('BASE_DIR'), "butler.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # --- 1. 툴바 영역 ---
        self._create_toolbar() # 👈 [CRITICAL FIX] 1. 툴바를 먼저 생성하여 'theme_action' 객체를 정의합니다.
        main_layout.addWidget(self.toolbar)
        
        # 2. 테마 적용
        self.apply_theme(self.current_theme) # 👈 2. 툴바 생성 후 테마를 적용합니다.

        # --- 2. 메인 콘텐츠 영역 (로그 및 조치 패널) ---
        content_layout = QHBoxLayout()
        
        self.log_panel = self._create_log_panel()
        content_layout.addWidget(self.log_panel, 7) 

        self.action_panel = self._create_action_panel()
        content_layout.addWidget(self.action_panel, 3) 
        
        main_layout.addLayout(content_layout, 1)

    def _create_toolbar(self):
        """모드 선택 ComboBox와 실행/중지 버튼, 테마 버튼을 포함하는 툴바를 생성합니다."""
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setIconSize(QSize(24, 24))
        
        # 모드 선택 ComboBox (3가지 모드 복원)
        mode_label = QLabel("진단 모드:")
        self.toolbar.addWidget(mode_label)
        self.mode_combo = QComboBox(self)
        self.mode_combo.addItems(self.plugins_by_group.keys())
        # 🚨 FIX: plugins_by_group의 실제 키는 "일반 모드"/"고급 모드"/"기타 모드 (개발자/업데이트)"이며
        #        영문 'basic' 키는 존재하지 않아 이 기본값 설정이 항상 무시되고 있었음.
        default_mode = "일반 모드"
        if default_mode in self.plugins_by_group:
            self.mode_combo.setCurrentText(default_mode)
        self.toolbar.addWidget(self.mode_combo)
        
        self.toolbar.addSeparator()

        # 실행 버튼
        self.run_action = QAction(QIcon(), "진단 시작", self)
        self.run_action.triggered.connect(self._run_task)
        self.toolbar.addAction(self.run_action)

        # 🚨 FIX(2026-08-31): "원클릭 최적화" — 예전 초안 파일에서는 버튼만 있고
        #    "아직 개발 중인 기능입니다" 메시지만 출력하는 스텁이었다. 이미 검증된
        #    _run_task() 실행 경로를 그대로 재사용해, 모드를 직접 고를 필요 없이
        #    "일반 모드" 플러그인 그룹(진단→정리→복구에 해당하는 기본 항목들)을
        #    바로 실행하는 버튼으로 실제 동작하게 만들었다.
        self.one_click_action = QAction(QIcon(), "⚡ 원클릭 최적화", self)
        self.one_click_action.setToolTip("모드 선택 없이 '일반 모드'의 진단·정리·복구 플러그인을 바로 실행합니다.")
        self.one_click_action.triggered.connect(self._run_one_click_optimize)
        self.toolbar.addAction(self.one_click_action)

        # 긴급 중지 버튼
        self.stop_action = QAction(QIcon(), "긴급 중지", self)
        self.stop_action.triggered.connect(self._stop_task)
        self.stop_action.setEnabled(False)
        self.toolbar.addAction(self.stop_action)

        self.toolbar.addSeparator()
        
        # 보고서 폴더 열기 버튼
        self.report_folder_action = QAction(QIcon(), "보고서 폴더 열기", self)
        self.report_folder_action.triggered.connect(self._open_report_folder)
        self.toolbar.addAction(self.report_folder_action)

        self.toolbar.addSeparator()
        
        # 테마 전환 버튼 (theme_action 객체 생성)
        self.theme_action = QAction(QIcon(), "테마 전환", self) # 👈 객체 생성
        self.theme_action.triggered.connect(self._toggle_theme)
        self.toolbar.addAction(self.theme_action)

    def _create_log_panel(self):
        """진단 과정 및 결과를 표시하는 로그 패널을 생성합니다."""
        log_group = QGroupBox("진단 로그 및 진행 상황")
        log_layout = QVBoxLayout(log_group)

        # 로그 출력 영역
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Consolas", 10))
        log_layout.addWidget(self.log_area)

        # 진행률 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        log_layout.addWidget(self.progress_bar)
        
        # 현재 실행 상태 라벨
        self.status_label = QLabel("준비 완료.")
        log_layout.addWidget(self.status_label)
        
        return log_group

    def _create_action_panel(self):
        """자동 조치 버튼 등을 포함하는 Action 패널을 생성합니다."""
        action_group = QGroupBox("후속 조치 (자동화)")
        action_layout = QVBoxLayout(action_group)
        
        self.action_layout = QVBoxLayout() 
        self.action_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        content_widget.setLayout(self.action_layout)
        scroll.setWidget(content_widget)
        
        action_layout.addWidget(scroll)
        
        self._update_action_buttons()
        
        return action_group

    def _update_action_buttons(self):
        """사용 가능한 자동 조치 버튼을 동적으로 생성하고 레이아웃에 추가합니다."""
        for i in reversed(range(self.action_layout.count())): 
            widget = self.action_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

        if not AUTO_FIX_MAPPING_GUI:
            no_action_label = QLabel("자동 조치 매핑 정보가 없습니다.")
            no_action_label.setWordWrap(True)
            self.action_layout.addWidget(no_action_label)
            return

        for check_plugin_name, fix_plugin_name in AUTO_FIX_MAPPING_GUI.items():
            button_text = f"[{check_plugin_name.replace('.py', '')}] 문제 자동 조치"
            button = QPushButton(button_text)
            button.setObjectName(fix_plugin_name) 
            button.clicked.connect(lambda checked, name=fix_plugin_name: self._run_follow_up_task(name))
            button.setEnabled(False) # 초기에는 비활성화 (진단 후 활성화)
            self.action_layout.addWidget(button)
            
    # --------------------------------------------------------------------------
    # 테마 및 유틸리티
    # --------------------------------------------------------------------------

    def apply_theme(self, theme_name: str):
        """밝은/어두운 테마를 적용합니다. 이 함수 호출 시점에는 self.theme_action이 이미 정의되어 있어야 합니다."""
        if theme_name == 'dark':
            self.setStyleSheet(DARK_THEME_QSS)
            # self.theme_action은 _create_toolbar에서 이미 정의됨
            self.theme_action.setText("테마 전환 (밝게)") 
            self.current_theme = 'dark'
        else: # light
            self.setStyleSheet(LIGHT_THEME_QSS)
            self.theme_action.setText("테마 전환 (어둡게)")
            self.current_theme = 'light'

    def _toggle_theme(self):
        """테마를 밝은/어두운 테마로 전환합니다."""
        new_theme = 'light' if self.current_theme == 'dark' else 'dark'
        self.apply_theme(new_theme)
        self.log_message(f"✅ 테마가 '{new_theme.upper()}'로 변경되었습니다.", "gray")

    def _center_window(self):
        """화면 중앙에 윈도우를 배치합니다."""
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    # --------------------------------------------------------------------------
    # 작업 실행/중지 및 UI 콜백 메서드
    # --------------------------------------------------------------------------
    
    def _run_task(self, plugins_to_run: Optional[List[str]] = None, is_follow_up: bool = False):
        """진단 또는 후속 조치 작업을 실행합니다."""
        if self.is_running:
            QMessageBox.warning(self, "경고", "이미 작업이 실행 중입니다. 잠시 기다려 주십시오.")
            return

        if not is_follow_up:
            selected_mode = self.mode_combo.currentText()
            plugins_to_run = self.plugins_by_group.get(selected_mode, [])
            self.log_area.clear() 
            self.log_message(f"▶️ '{selected_mode}' 모드 진단 시작... (총 {len(plugins_to_run)}개 플러그인)", "blue")
            
            for button in self.action_panel.findChildren(QPushButton):
                 button.setEnabled(False)
        elif not plugins_to_run:
             self.log_message("❌ 후속 조치 플러그인 목록이 비어 있습니다.", "red")
             return
        else:
            self.log_message(f"▶️ 후속 조치 '{plugins_to_run[0]}' 실행...", "blue")

        if not plugins_to_run:
            self.log_message("❌ 실행할 플러그인이 없습니다. 모드 또는 인덱스 파일을 확인하십시오.", "red")
            return

        self.is_running = True
        self.run_action.setEnabled(False)
        self.one_click_action.setEnabled(False)
        self.stop_action.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("작업 실행 중...")
        self.stop_event.clear() 
        
        self.worker = Worker(
            self.plugin_group_executor,
            plugins_to_run,
            self.settings,
            self.stop_event,
            self.plugin_name_to_class, 
            is_follow_up_task=is_follow_up
        )
        self.worker.finished.connect(self._task_finished)
        self.worker.progress_signal.connect(self._update_progress)
        self.worker.log_signal.connect(self.log_message) 
        
        self.worker.start()

    def _run_follow_up_task(self, fix_plugin_name: str):
        """자동 조치 버튼 클릭 시 호출됩니다."""
        self._run_task(plugins_to_run=[fix_plugin_name], is_follow_up=True)

    def _run_one_click_optimize(self):
        """'원클릭 최적화' 버튼: 모드 선택 없이 '일반 모드' 플러그인 그룹을 바로 실행한다."""
        if self.is_running:
            QMessageBox.warning(self, "경고", "이미 작업이 실행 중입니다. 잠시 기다려 주십시오.")
            return
        target_mode = "일반 모드"
        if target_mode not in self.plugins_by_group:
            self.log_message(f"❌ '{target_mode}' 그룹을 찾을 수 없습니다. plugin_index_categorized.txt를 확인하십시오.", "red")
            return
        # 콤보박스도 함께 맞춰서 사용자가 지금 무엇이 실행되는지 화면에서 알 수 있게 한다.
        self.mode_combo.setCurrentText(target_mode)
        self._run_task()

    def _stop_task(self):
        """실행 중인 작업을 중지합니다."""
        if self.is_running:
            self.stop_event.set()
            self.log_message("🛑 긴급 중지 요청됨. 현재 작업이 완료될 때까지 대기 중...", "yellow")
        
    def _task_finished(self, result: Dict[str, Any]):
        """Worker 쓰레드 완료 시 호출됩니다."""
        
        self.is_running = False
        self.run_action.setEnabled(True)
        self.one_click_action.setEnabled(True)
        self.stop_action.setEnabled(False)
        self.progress_bar.setValue(100)
        
        status = result.get('status', 'UNKNOWN')
        summary = result.get('summary', '결과 요약 없음')
        self.status_label.setText(f"작업 완료: {status}")
        
        if status == "ABORTED":
            self.log_message(f"⚠️ 작업 중단 완료: {summary}", "yellow")
        elif status == "FATAL_ERROR":
            self.log_message(f"🚨 치명적인 오류 발생: {summary}", "red")
        else:
            self.log_message(f"✅ 작업 최종 상태: {status}", "lime")

        if not self.worker.is_follow_up_task:
            self.log_message("💡 진단 결과를 바탕으로 조치 패널 버튼을 활성화합니다.", "gray")
            self._update_action_button_states(result.get('results', {}))

        self.worker = None

    def _update_progress(self, plugin_name: str, percent: int):
        """Worker 쓰레드에서 진행률 업데이트 시 호출됩니다."""
        self.progress_bar.setValue(percent)
        self.status_label.setText(f"진행 중: {plugin_name} ({percent}%)")

    def log_message(self, message: str, color: str = 'white', new_line: bool = True):
        """로그 영역에 색상 메시지를 출력합니다."""
        color_map = {
            'red': QColor(255, 0, 0), 'lime': QColor(50, 205, 50), 'yellow': QColor(255, 255, 0),
            'blue': QColor(0, 100, 255), 'cyan': QColor(0, 255, 255), 'magenta': QColor(255, 0, 255),
            'gray': QColor(150, 150, 150), 'white': QColor(255, 255, 255),
        }
        
        text_color = color_map.get(color.lower(), QColor(200, 200, 200))
        
        format = QTextCharFormat()
        format.setForeground(text_color)
        
        cursor = self.log_area.textCursor()
        cursor.movePosition(cursor.End)
        
        timestamped_message = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        
        if self.log_area.toPlainText() and new_line:
             cursor.insertText('\n')

        cursor.insertText(timestamped_message, format)
        
        self.log_area.ensureCursorVisible()

    def _update_action_button_states(self, plugin_results: Dict[str, Any]):
        """진단 결과에 따라 조치 패널 버튼의 활성화 상태를 업데이트합니다."""
        
        for button in self.action_panel.findChildren(QPushButton):
            fix_plugin_name = button.objectName()
            
            check_plugin_name = next((k for k, v in AUTO_FIX_MAPPING_GUI.items() if v == fix_plugin_name), None)
            
            if check_plugin_name:
                # FIX (2026-09-01): plugin_results is keyed by plugin_class.plugin_name
                # (the display name, e.g. "🚨"-free display text), not by the AUTO_FIX_MAPPING_GUI
                # filename key (e.g. "plugin_antiviruscheck"). Looking it up by filename
                # always missed, so status defaulted to 'success' and the action button
                # was never enabled even when the check plugin reported a real problem --
                # this is why clicking felt like it did nothing (it was correctly disabled,
                # but never got enabled in the first place). Resolve via plugin_name_to_class
                # to get the actual display-name key used in plugin_results.
                check_plugin_class = self.plugin_name_to_class.get(check_plugin_name)
                lookup_key = check_plugin_class.plugin_name if check_plugin_class else check_plugin_name.replace('.py', '')

                result = plugin_results.get(lookup_key, {})
                status = result.get('status', 'success').lower()
                
                if status in ('warning', 'error', 'fatal_error'):
                    button.setEnabled(True)
                    self.log_message(f"⚠️ 진단 결과에 따라 '{button.text()}' 버튼 활성화.", "yellow")
                else:
                    button.setEnabled(False)
                    
    def _open_report_folder(self):
        """보고서 폴더를 파일 탐색기로 엽니다."""
        raw_report_dir = self.settings.get('PATHS', {}).get('REPORT_DIR', 'reports')
        report_dir = os.path.join(self.settings.get('BASE_DIR'), raw_report_dir)
        
        if not os.path.exists(report_dir):
            os.makedirs(report_dir, exist_ok=True)
        
        try:
            if platform.system() == "Windows":
                subprocess.Popen(['explorer', report_dir])
            elif platform.system() == "Darwin": 
                subprocess.Popen(['open', report_dir])
            else: 
                subprocess.Popen(['xdg-open', report_dir])
            
            self.log_message(f"✅ 보고서 폴더 열기 성공: {report_dir}", "gray")

        except Exception as e:
            QMessageBox.critical(self, "오류", f"보고서 폴더를 열 수 없습니다:\n{e}")
            self.log_message(f"❌ 보고서 폴더 열기 실패: {e}", "red")