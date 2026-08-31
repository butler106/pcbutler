# ==============================================================================
# 🐍 PC Butler: main.py (메인 실행 파일) - 최종 오류 수정 및 진단 버전
# [핵심 수정] 1. GUI 임포트 실패 시 상세 Traceback 출력 (문제 진단용)
#            2. QApplication 임포트 위치 및 체크 로직 안정화
#            3. 🚨 FIX: UnboundLocalError: name 'QApplication_LOADED' is not defined 오류 수정
# ==============================================================================
import sys
import os
import traceback
import importlib.util
import inspect
import time
import csv # <--- CSV 임포트 추가 (플러그인 인덱스 파싱용)
import json 
import configparser
import shutil # 캐시 폴더 삭제를 위한 모듈
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional, Union
from threading import Event, Thread 
from queue import Queue 
import platform 
import ctypes 

# 🟢 PyQt5 임포트 (GUI 모드 사용 시 필요) - main_window.py와 MainWindow 클래스 정의가 필요
try:
    # 1단계: main_window 모듈 임포트 시도
    # 🚨 CRITICAL FIX: 'plugin_group_executor'는 main.py의 로컬 함수이므로 임포트 목록에서 제거했습니다.
    from main_window import MainWindow, Worker  
    # 2단계: QApplication 임포트 시도 (1단계가 성공하면)
    from PyQt5.QtWidgets import QApplication 
    # QApplication과 MainWindow 변수가 성공적으로 로드됨.
except ImportError:
    # 🚨 [오류 추적]: GUI 임포트 실패 시 상세 오류를 출력합니다.
    print("\n" + "="*80)
    print("🚨 CRITICAL ERROR: main_window.py 또는 PyQt5 모듈 임포트 실패.")
    # 오류의 정확한 원인(main_window.py 내부의 오류 포함)을 출력합니다.
    traceback.print_exc() 
    print("="*80 + "\n")
    # GUI 관련 모듈을 찾을 수 없는 경우 (콘솔 모드만 사용 가능)
    MainWindow = None 
    Worker = None
    plugin_group_executor = None 
    QApplication = None

# 🚨 [핵심 수정]: ModuleNotFoundError 및 경로 문제 해결을 위해 BASE_DIR 설정 최상단 배치
# 🚨 FIX (2026-08-31): PyInstaller로 패키징된 exe에서는 __file__ 기준 경로가
# 실제 exe가 있는 폴더가 아니라 내부 압축 해제 경로를 가리켜서, plugins/,
# config.ini, plugin_index_categorized.txt를 전혀 못 찾는 문제가 있었다.
# (plugin_dashboardgen.py는 이미 sys.frozen 체크로 이 문제를 우회하고 있었는데
#  main.py 자체에는 이 처리가 빠져 있었다.) sys.executable 기준으로 우회한다.
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
# --- 경로 설정 완료 ---

# 플러그인 폴더 경로
PLUGINS_DIR = os.path.join(BASE_DIR, "plugins")
INDEX_FILE = os.path.join(BASE_DIR, "plugin_index_categorized.txt") # <--- 인덱스 파일 경로

# ==============================================================================
# 로거 및 유틸리티 함수
# ==============================================================================

COLOR_MAP = {
    'red': '\033[91m', 'green': '\033[92m', 'yellow': '\033[93m', 'blue': '\033[94m',
    'magenta': '\033[95m', 'cyan': '\033[96m', 'white': '\033[97m', 'gray': '\033[90m',
    'end': '\033[0m'
}

def console_logger(msg: str, color: str = 'white', end: str = '\n'):
    """색상을 입혀 콘솔에 메시지를 출력합니다."""
    # 창 모드(console=False)로 빌드된 exe에서는 sys.stdout이 None이라
    # 그냥 write()하면 죽는다. 콘솔이 없으면 조용히 무시한다.
    if sys.stdout is None:
        return
    try:
        color_code = COLOR_MAP.get(color.lower(), COLOR_MAP['white'])
        sys.stdout.write(f"{color_code}{msg}{COLOR_MAP['end']}{end}")
        sys.stdout.flush()
    except Exception:
        pass
        
def get_plugin_class(file_path: str) -> Any:
    """주어진 파일 경로에서 PCButlerPlugin을 상속받은 클래스를 로드합니다."""
    spec = importlib.util.spec_from_file_location("module.name", file_path)
    if spec is None:
        raise ImportError(f"모듈 사양을 찾을 수 없습니다: {file_path}")
    
    module = importlib.util.module_from_spec(spec)
    sys.modules["module.name"] = module
    
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        console_logger(f"❌ 플러그인 모듈 실행 중 오류 발생 ({os.path.basename(file_path)}): {e}", 'red')
        return None
        
    try:
        from plugin_base import PCButlerPlugin
    except ImportError:
        console_logger("❌ plugin_base.py를 임포트할 수 없습니다. 경로를 확인하십시오.", 'red')
        return None

    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, PCButlerPlugin) and obj is not PCButlerPlugin:
            return obj
    
    return None

def is_admin() -> bool:
    """Windows에서 현재 프로세스가 관리자 권한으로 실행되었는지 확인합니다."""
    try:
        if platform.system() == "Windows":
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        return True 
    except Exception:
        return False

# ==============================================================================
# 플러그인 모드 분류 로직 (기존 코드 유지)
# ==============================================================================

def _parse_plugin_index(file_path: str) -> Dict[str, Dict[str, str]]:
    """plugin_index_categorized.txt 파일의 내용을 파싱하여 메타데이터를 추출합니다."""
    metadata = {}
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f, delimiter='\t')
            header = next(reader)
            
            try:
                filename_idx = header.index('Filename')
                usermode_idx = header.index('UserMode')
            except ValueError:
                console_logger("❌ plugin_index_categorized.txt의 헤더가 유효하지 않습니다.", 'red')
                return {}
            
            for row in reader:
                if len(row) > usermode_idx:
                    filename = row[filename_idx].strip()
                    usermode = row[usermode_idx].strip()
                    if filename.endswith('.py'):
                        metadata[filename] = {"UserMode": usermode}
    except FileNotFoundError:
        console_logger(f"❌ 플러그인 인덱스 파일 '{file_path}'을 찾을 수 없습니다.", 'red')
    except Exception as e:
        console_logger(f"❌ 플러그인 인덱스 파일 파싱 중 오류 발생: {e}", 'red')
        
    return metadata

def load_plugin_metadata() -> Dict[str, Dict[str, str]]:
    """plugin_index_categorized.txt 파일에서 메타데이터를 로드합니다."""
    return _parse_plugin_index(INDEX_FILE)

def categorize_plugins(metadata: Dict[str, Dict[str, str]]) -> Dict[str, List[str]]:
    """메타데이터를 기반으로 일반, 고급, 기타 모드 그룹을 분류합니다."""
    
    FINALIZATION_PLUGINS = ["plugin_stat_summary.py", "plugin_reportmerge.py", "plugin_pdfexport.py"]
    ADMIN_MAINTENANCE_PLUGINS = ["plugin_updatecheck.py", "plugin_selfupdate.py", "plugin_wingetupgrade.py"]
    
    core_basic_plugins = []
    expert_plugins = []

    for filename, info in metadata.items():
        if filename in FINALIZATION_PLUGINS:
            continue
        
        usermode = info.get("UserMode", "Basic")
        
        if usermode == "Basic":
            core_basic_plugins.append(filename)
        elif usermode == "Expert":
            expert_plugins.append(filename)

    core_basic_plugins.sort()
    expert_plugins.sort()

    PLUGINS_BASIC_MODE = core_basic_plugins + FINALIZATION_PLUGINS
    PLUGINS_EXPERT_MODE = core_basic_plugins + expert_plugins + FINALIZATION_PLUGINS
    PLUGINS_OTHER_MODE = sorted(list(set(expert_plugins + ADMIN_MAINTENANCE_PLUGINS)))
    
    plugins_by_group = {
        "일반 모드": PLUGINS_BASIC_MODE,
        "고급 모드": PLUGINS_EXPERT_MODE,
        "기타 모드 (개발자/업데이트)": PLUGINS_OTHER_MODE
    }
    
    return plugins_by_group

# ==============================================================================
# 플러그인 실행 함수 (Console/GUI Worker 공통 사용) (기존 코드 유지)
# ==============================================================================

def run_plugin(plugin_class: Any, analysis_id: str, settings: Dict[str, Any], 
               result_queue: Queue, stop_event: Event, progress_bar: Dict[str, int]):
    """개별 플러그인을 실행하고 결과를 큐에 넣습니다."""
    plugin_name = plugin_class.plugin_name
    
    def check_stop() -> bool:
        """플러그인이 실행을 중단해야 하는지 확인하는 함수"""
        return stop_event.is_set()

    try:
        start_time = time.time()
        settings_copy = {k: v for k, v in settings.items()}
        plugin_instance = plugin_class(analysis_id, settings_copy)
        
        def update_progress(percentage: int) -> None:
            progress_bar[plugin_name] = min(100, max(0, percentage))

        result = plugin_instance.run(
            logger=lambda msg, color='white', end='\n': console_logger(f"  [{plugin_name}]  {msg}", color, end),
            progress=update_progress,
            stop_check=check_stop
        )
        
        end_time = time.time()
        result['execution_time'] = f"{end_time - start_time:.2f}s"
        result_queue.put({plugin_name: result})
        
    except Exception:
        error_msg = traceback.format_exc()
        console_logger(f"❌ '{plugin_name}' 실행 중 치명적인 오류 발생:\n{error_msg}", 'red')
        
        result_queue.put({plugin_name: {
            "status": "FATAL_ERROR",
            "summary": f"플러그인 실행 중 치명적인 오류 발생.",
            "details": {"traceback": error_msg.splitlines()},
            "execution_time": f"{time.time() - start_time:.2f}s"
        }})

def plugin_group_executor(plugins_to_run: List[str], settings: Dict[str, Any], logger_cb: Callable, 
                          progress_cb: Callable, stop_check: Callable, plugin_name_to_class: Dict[str, Any]) -> Dict[str, Any]:
    """
    플러그인 목록을 받아 쓰레드를 사용하며, 순차적으로 하나씩 실행하는 통합 실행기입니다.
    """
    analysis_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. 초기화
    final_results = {}
    thread_list = []
    result_queue = Queue()
    stop_event = Event()
    if stop_check is not None:
        pass # GUI Worker의 stop_check를 여기에 연결하는 로직은 Worker 클래스에서 처리됨

    progress_data = {}

    # 2. 실행 (순차 실행으로 수정됨)
    for plugin_filename in plugins_to_run:
        # stop_check를 직접 호출하여 중단 확인
        if stop_check is not None and stop_check():
            logger_cb("⚠️ 그룹 실행 중단 요청 수신.", "yellow")
            return {"status": "ABORTED", "summary": "사용자 요청으로 그룹 실행 중단."}

        plugin_class = plugin_name_to_class.get(plugin_filename)
        if plugin_class is None:
            logger_cb(f"❌ 플러그인 클래스를 찾을 수 없습니다: {plugin_filename}", 'red')
            continue
            
        logger_cb(f"▶️ '{plugin_filename}' 작업을 순차적으로 실행 중...", "magenta")
        
        t = Thread(target=run_plugin, args=(
            plugin_class, 
            analysis_id, 
            settings, 
            result_queue, 
            stop_event, 
            progress_data
        ))
        thread_list.append(t)
        t.start()
        
        # 🚨 핵심 수정: 스레드가 완료될 때까지 대기 (순차 실행 보장)
        t.join()

    # 3. 완료 대기 (순차 실행 로직에 의해 이 시점에서 모든 스레드가 완료되었음)
    # 기존의 전체 대기 루프는 제거되었습니다.

    # 4. 결과 취합
    while not result_queue.empty():
        result = result_queue.get()
        final_results.update(result)
        
    # 5. 최종 보고서 생성
    final_report = {
        "analysis_id": analysis_id,
        "timestamp": datetime.now().isoformat(),
        "status": "SUCCESS",
        "summary": "모든 진단/조치 작업 완료.",
        "results": final_results
    }
    
    if stop_check is not None and stop_check():
        final_report['status'] = "ABORTED"
        final_report['summary'] = "사용자 요청으로 진단이 중단됨."
        
    return final_report

def execute_console_plugins(plugins_to_run: List[str], plugin_name_to_class: Dict[str, Any], config: configparser.ConfigParser):
    """콘솔 모드에서 플러그인 목록을 순차적으로 실행합니다."""
    settings = {}
    for section in config.sections():
        settings[section.upper()] = {k.upper(): v for k, v in config.items(section)}
        
    # 최종 보고서 경로 주입
    raw_report_dir = settings.get('PATHS', {}).get('REPORT_DIR', 'reports')
    FINAL_REPORT_DIR = os.path.join(BASE_DIR, raw_report_dir)
    settings['REPORT_DIR_FINAL'] = FINAL_REPORT_DIR
    settings['BASE_DIR'] = BASE_DIR
    
    console_logger(f"\n✨ PC Butler 진단 시작. (기본 모드)", 'cyan')
    
    final_report = plugin_group_executor(
        plugins_to_run, 
        settings, 
        console_logger, 
        lambda p, pct: None,
        lambda: False, # 콘솔에서는 중단 기능 없음 (항상 False 반환)
        plugin_name_to_class
    )
            
    if final_report['status'] == 'ABORTED':
        console_logger("\n🛑 콘솔 진단이 중단되었습니다.", 'red')
    else:
        console_logger("\n🎉 모든 진단/조치 작업 완료.", 'cyan')


def load_plugins() -> Dict[str, Any]:
    """plugins 디렉토리에서 모든 플러그인을 로드합니다."""
    plugin_name_to_class = {}
    if not os.path.exists(PLUGINS_DIR):
        console_logger(f"❌ 플러그인 디렉토리 '{PLUGINS_DIR}'를 찾을 수 없습니다.", 'red')
        return plugin_name_to_class
        
    for filename in os.listdir(PLUGINS_DIR):
        if filename.endswith(".py") and filename != "__init__.py":
            filepath = os.path.join(PLUGINS_DIR, filename)
            plugin_class = get_plugin_class(filepath)
            if plugin_class:
                plugin_name_to_class[filename] = plugin_class
                
    return plugin_name_to_class

# ==============================================================================
if __name__ == "__main__":
    # 1. 경로 및 설정 파일 정의
    CONFIG_FILE = os.path.join(BASE_DIR, "config.ini")
    
    # 2. 콘솔 모드 여부 확인
    is_console_mode = len(sys.argv) > 1 and sys.argv[1].lower() == "--console"
    
    # 3. 플러그인 메타데이터 로드 및 그룹 분류
    plugin_metadata = load_plugin_metadata()
    plugins_by_group = categorize_plugins(plugin_metadata)
    
    # 4. 모든 플러그인 클래스 로드 (GUI/Console 공통)
    plugin_name_to_class = load_plugins()

    # 5. 설정 파일 로드
    # 🚨 FIX: config.ini 파싱 오류(예: 파일 내용 오염, 잘못된 INI 문법) 시
    #        프로그램 전체가 죽지 않고 기본 설정으로 안전하게 대체되도록 예외 처리.
    config_obj = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        try:
            config_obj.read(CONFIG_FILE, encoding='utf-8')
        except configparser.Error as e:
            console_logger(f"❌ config.ini 파일 로드 중 오류 발생: {e}\n   기본 설정으로 대체합니다.", 'red')
            config_obj = configparser.ConfigParser()
    else:
        console_logger(f"⚠️ 설정 파일을 찾을 수 없습니다 ({CONFIG_FILE}). 기본 설정으로 진행합니다.", 'yellow')
    
    # 6. GUI 모드 실행
    # 🚨 FIX: MainWindow와 QApplication이 모두 성공적으로 임포트되었는지 확인합니다.
    if not is_console_mode and MainWindow is not None and QApplication is not None:
        try:
            # QApplication 객체 생성은 main_window.py의 임포트 성공 이후에만 시도
            app = QApplication(sys.argv)
            main_window = MainWindow(
                plugin_group_executor, 
                plugin_name_to_class, 
                plugins_by_group,
                config_obj
            )
            main_window.show()
            sys.exit(app.exec_())
        except Exception as e:
            console_logger(f"🚨 GUI 실행 중 런타임 오류 발생: {type(e).__name__}: {str(e)}", "red")
            traceback.print_exc()
            
    # 7. 콘솔 모드 실행 (또는 GUI 모드 실패 시)
    else:
        if not is_console_mode:
            # main.py 최상단 임포트 오류 메시지가 이미 출력되었을 것입니다.
            console_logger("❌ GUI 모듈 임포트 실패로 인해 콘솔 모드로 전환합니다. 위에 출력된 Traceback을 확인하십시오.", 'red')
            
        plugins_to_run = plugins_by_group.get("일반 모드", [])
        
        if not plugins_to_run:
            console_logger("❌ 실행할 플러그인(일반 모드)을 찾을 수 없습니다.", 'red')
            sys.exit(1)
            
        execute_console_plugins(plugins_to_run, plugin_name_to_class, config_obj)
