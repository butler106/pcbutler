from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# plugin_usbcheck.py
# 플러그인: USB 저장장치 사전 점검 (최종 구조적 수정 및 경로 안정화 버전)
import os
import shutil
from datetime import datetime
import sys

# psutil을 사용하여 크로스 플랫폼 호환성 확보 시도
try:
    if sys.platform != "win32":
        import psutil
    else:
        # Windows에서도 psutil 사용 가능. 없으면 예외 처리
        import psutil
except ImportError:
    pass # psutil이 없는 경우 로직에서 처리

class USBCheckPlugin(PCButlerPlugin):
    plugin_name = "USB 저장장치 사전 점검"
    description = "USB의 쓰기 가능 여부, 저장 공간, 오염 가능성 등을 진단 시작 전에 점검합니다. (시뮬레이션 포함)"

    # --- 보조 함수: 디스크 여유 공간 확인 ---
    def _get_free_space(self, path, log):
        """지정된 경로가 포함된 디스크의 여유 공간을 MB 단위로 반환합니다."""
        free_mb = 1024 # psutil 실패 시 기본값 (1GB 시뮬레이션)
        
        try:
            # psutil이 로드되었을 경우 사용
            if 'psutil' in sys.modules:
                disk = psutil.disk_usage(path)
                free_mb = disk.free / (1024**2) # 바이트를 MB로 변환
                log(f"  -> 💾 디스크 여유 공간 (psutil): {free_mb:.2f} MB", "gray")
                return free_mb
            
            # Unix-like 시스템에서 os.statvfs 사용 시도 (fallback)
            elif sys.platform != "win32":
                st = os.statvfs(path)
                free_bytes = st.f_bfree * st.f_frsize
                free_mb = free_bytes / (1024**2)
                log(f"  -> 💾 디스크 여유 공간 (statvfs): {free_mb:.2f} MB", "gray")
                return free_mb

        except Exception as e:
            log(f"  -> ❌ 디스크 공간 확인 실패 (오류: {e}). 시뮬레이션 기본값(1024MB) 사용.", "red")
            return free_mb # 기본값 반환
        
        return free_mb # 기본값 반환
    # ----------------------------------------
    
    # 🚨 [핵심 수정] run 메서드 시그니처 통일 및 로직 통합
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        """플러그인의 메인 실행 로직"""
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs) 
        log = self.logger # 로거 함수 재정의
        
        status = "SUCCESS"
        summary = "USB 사전 점검 완료."
        free_mb = 0 # 로그 기록용 변수 초기화
        
        log("🔍 USB 저장장치 사전 점검 시작...", "cyan")
        self.progress(5) 

        try:
            # 1. 경로 설정 및 표준화 (BASE_DIR 사용)
            # settings에서 BASE_DIR을 가져와 절대 경로 구성
            base_path = self.settings.get("BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            report_dir = os.path.join(base_path, "reports") 
            quarantine_dir = os.path.join(base_path, "quarantine")
            
            # 테스트/시뮬레이션을 위한 USB 경로
            TEST_USB_PATH = os.path.join(base_path, "test_usb") 

            # 2. 필수 디렉토리 생성
            os.makedirs(report_dir, exist_ok=True)
            os.makedirs(quarantine_dir, exist_ok=True)
            os.makedirs(TEST_USB_PATH, exist_ok=True)
            log(f"  -> 📂 테스트 USB 경로 설정됨: {TEST_USB_PATH}", "gray")
            self.progress(20)

            # 3. 쓰기 가능 여부 확인
            test_file = os.path.join(TEST_USB_PATH, ".write_test")
            try:
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
                log("  -> ✅ 쓰기 가능 여부: 통과", "lime")
            except Exception:
                status = "ERROR"
                summary = "❌ USB 쓰기 가능 여부 확인 실패: 해당 경로에 쓰기 권한이 없거나 경로가 잘못되었습니다."
                log(summary, "red")
                self.progress(100)
                return {"status": status, "summary": summary}
                
            self.progress(40)

            # 4. 저장 공간 확인
            free_mb = self._get_free_space(TEST_USB_PATH, log)
            
            # 5. 오염 파일 체크 (시뮬레이션)
            contaminated_files = ["virus_a.exe", "malware_b.dll"]
            
            # 시뮬레이션을 위해 TEST_USB_PATH에 파일 생성
            for f in contaminated_files:
                open(os.path.join(TEST_USB_PATH, f), 'a').close()

            suspicious_files = [f for f in os.listdir(TEST_USB_PATH) if f in contaminated_files]
            
            if suspicious_files:
                log(f"⚠️ 오염 가능성이 있는 파일 {len(suspicious_files)}개 발견. 격리를 시도합니다.", "yellow")
                
                status = "WARNING"
                summary = f"⚠️ 오염 가능 파일 {len(suspicious_files)}개 발견됨."

                # 6. 격리 시도 (quarantine_dir로 이동)
                for s in suspicious_files:
                    src = os.path.join(TEST_USB_PATH, s)
                    dst_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{s}"
                    dst = os.path.join(quarantine_dir, dst_name)
                    
                    try:
                        shutil.move(src, dst)
                        log(f"  -> 🧼 격리 완료: {s} → {dst_name}", "green")
                    except Exception as e:
                        log(f"  -> ❌ 격리 실패: {s} ({e})", "red")
                        if status != "ERROR": 
                            status = "WARNING"
                            summary = "오염 파일 격리에 실패했습니다."
            else:
                log("✅ 오염 파일 없음", "lime")

            self.progress(90)
            
            # 7. 로그 기록 (리포트 폴더 내부에 파일 기록)
            log_path = os.path.join(report_dir, "usb_check_log.txt")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] USB 점검 완료 - Free: {free_mb:.2f}MB, Contaminated: {len(suspicious_files)}\n")
            
            log("✅ USB 사전 점검 완료", "lime")
            
            # 🚨 [필수] 최종 결과 반환
            return {"status": status, "summary": summary}

        except Exception as e:
            error_message = f"❌ USB 사전 점검 실행 중 치명적 오류 발생: {type(e).__name__} - {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "ERROR", "summary": error_message}