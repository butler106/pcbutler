from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 보고서 백업 (ReportBackup) - 최종 완벽 버전
# - 최종 보고서 파일(ZIP)을 지정된 로컬 백업 위치로 복사합니다.
# ==============================================================================
from plugin_base import PCButlerPlugin
import os
import shutil
import time

class ReportBackupPlugin(PCButlerPlugin):
    """
    최종 진단 보고서 파일(ZIP)을 지정된 로컬 백업 위치로 복사합니다.
    """
    plugin_name = "보고서 백업"
    description = "최종 진단 보고서 파일(ZIP)을 지정된 로컬 백업 위치로 안정적으로 복사합니다."
    version = "2.0.0" # 최종 버전

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description
        
        # 기본 경로 설정
        self.base_path = self.settings.get("BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.report_dir = os.path.join(self.base_path, 'reports')

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        # 표준 run 메서드 시작
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        self.progress(10)

        log(f"💾 '{self.name}' 작업을 시작합니다.", "cyan")
        final_status = "error"
        final_summary = ""
        
        try:
            # 1. 필수 설정 확인 (백업 경로)
            backup_path_setting = self.settings.get("BACKUP_PATH")
            if not backup_path_setting or backup_path_setting == "DUMMY_PATH":
                summary = "⚠️ 백업 경로 설정(BACKUP_PATH)이 누락되었습니다. 백업 작업을 건너뜁니다."
                log(summary, "yellow")
                self.progress(100)
                return {"status": "warning", "summary": summary}

            backup_dir = backup_path_setting # 사용자 설정 경로
            
            # 백업 디렉토리 생성 (없을 경우)
            os.makedirs(backup_dir, exist_ok=True)
            log(f"  -> 📂 백업 대상 경로: {backup_dir}", "white")
            self.progress(20)

            # 2. 전송 대상 파일 확인 (압축된 ZIP 파일을 가정)
            report_filename = self.settings.get('report_filename', f"Analysis_Report_{self.analysis_id}")
            source_file = f"{report_filename}.zip"
            source_file_path = os.path.join(self.report_dir, source_file)
            destination_file_path = os.path.join(backup_dir, source_file)

            if not os.path.exists(source_file_path):
                summary = f"❌ 백업할 보고서 파일({source_file})을 찾을 수 없습니다. (ReportCompress 플러그인이 먼저 실행되어야 합니다)"
                log(summary, "red")
                self.progress(100)
                return {"status": "error", "summary": summary}
            
            log(f"  -> 🗄️ 소스 파일: {source_file}", "white")
            self.progress(50)
            
            # 3. 파일 복사 실행
            log("  -> 🔄 보고서 파일 백업 복사 중...", "yellow")
            
            # shutil.copy2는 파일의 메타데이터(수정 시간 등)까지 복사합니다.
            shutil.copy2(source_file_path, destination_file_path)
            
            log("  -> ✅ 복사 완료.", "gray")
            self.progress(90)

            # 4. 최종 결과
            final_summary = f"✅ 보고서 파일({source_file})이 백업 경로({backup_dir})로 성공적으로 백업되었습니다."
            log(f"\n{final_summary}", "lime")
            final_status = "success"
            
            return {"status": final_status, "summary": final_summary}

        except PermissionError:
            final_summary = f"❌ 백업 실패: 접근 권한이 없습니다. (경로: {backup_dir}). 관리자 권한을 확인하십시오."
            log(final_summary, "red")
            final_status = "error"
        except FileNotFoundError as e:
            final_summary = f"❌ 백업 실패: 대상 파일 또는 경로를 찾을 수 없습니다. ({e})"
            log(final_summary, "red")
            final_status = "error"
        except Exception as e:
            final_summary = f"❌ 보고서 백업 중 치명적인 오류 발생: {type(e).__name__}: {e}"
            log(final_summary, "red")
            final_status = "error"

        self.progress(100)
        # 🚨 [필수] 최종 결과 반환
        return {"status": final_status, "summary": final_summary}