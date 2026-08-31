from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 격리 파일 자동 압축 (QuarantineZip) - 최종 완벽 버전
# - quarantine 폴더 내 오염 파일을 압축하고 원본을 정리합니다.
# ==============================================================================
from plugin_base import PCButlerPlugin
import os
import zipfile
import shutil
from datetime import datetime
import sys
import glob

class QuarantineZipPlugin(PCButlerPlugin):
    """
    격리 폴더(quarantine) 내의 파일을 ZIP 파일로 압축하고, 압축된 원본을 정리합니다.
    """
    plugin_name = "격리 파일 압축 및 정리"
    description = "quarantine 폴더 내 오염 파일을 자동 압축하여 실행을 차단하고 원본을 정리합니다."
    version = "2.1.0" # 최종 버전

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        
        # BASE_DIR을 settings에서 가져와 격리 폴더 경로를 구성합니다.
        base_path = self.settings.get("BASE_DIR", os.path.dirname(os.path.abspath(__file__)))
        # 격리 폴더 경로: BASE_DIR/quarantine
        self.quarantine_dir = os.path.join(base_path, "quarantine")

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        # 표준 run 메서드 시작
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🔍 '{self.name}' 작업을 시작합니다. (격리 파일 압축)", "cyan")
        self.progress(10)

        # 1. 격리 폴더 존재 확인
        if not os.path.isdir(self.quarantine_dir):
            summary = f"⚠️ 격리 폴더({self.quarantine_dir})가 존재하지 않습니다. 압축 작업 건너뜀."
            log(summary, "yellow")
            self.progress(100)
            # 폴더가 없는 것은 오류가 아니므로 Warning 반환
            return {"status": "warning", "summary": summary}
            
        try:
            # 2. 압축 대상 파일 목록 확보 (ZIP 파일 제외)
            # os.listdir 대신 glob를 사용하여 .zip이 아닌 파일만 확실히 필터링
            file_list = [
                f for f in os.listdir(self.quarantine_dir) 
                if os.path.isfile(os.path.join(self.quarantine_dir, f)) and not f.lower().endswith(('.zip', '.tmp'))
            ]

            if not file_list:
                summary = "✅ 압축할 격리 대상 파일이 없습니다. (양호)"
                log(summary, "lime")
                self.progress(100)
                return {"status": "success", "summary": summary}

            log(f"📦 총 {len(file_list)}개의 격리 파일을 압축합니다.", "white")
            self.progress(30)

            # 3. ZIP 파일 경로 생성
            zip_name = f"quarantine_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            zip_path = os.path.join(self.quarantine_dir, zip_name)
            
            files_deleted = 0
            
            # 4. ZIP 압축 및 원본 파일 정리
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for i, fname in enumerate(file_list):
                    source_path = os.path.join(self.quarantine_dir, fname)
                    
                    # 4-a. 파일 압축
                    zipf.write(source_path, fname)
                    
                    # 4-b. 압축 성공 후 원본 파일 삭제 (정리)
                    try:
                        os.remove(source_path)
                        log(f"  -> ✅ 압축 및 원본 정리 완료: {fname}", "lime")
                        files_deleted += 1
                    except Exception as e:
                        log(f"  -> ❌ 압축된 원본 파일 삭제 실패: {source_path} ({e})", "red")
                    
                    self.progress(30 + int(60 * (i + 1) / len(file_list)))

            # 5. 최종 결과 보고
            total_files = len(file_list)
            
            if files_deleted == total_files:
                summary = f"✅ 격리 파일 **{total_files}개**를 성공적으로 압축하고 원본을 정리했습니다. (ZIP: {zip_name})"
                final_status = "success"
            elif files_deleted > 0:
                summary = f"⚠️ 격리 파일 **{files_deleted}/{total_files}개**를 압축하고 정리했습니다. 일부 파일 정리 실패."
                final_status = "warning"
            else:
                summary = f"❌ 격리 파일 압축은 완료했으나, 원본 정리 실패. (ZIP: {zip_name})"
                final_status = "error"

            details = {
                "total_files": total_files,
                "deleted_files": files_deleted,
                "zip_file": zip_path
            }
            
            self.progress(100)
            return {"status": final_status, "summary": summary, "details": details}
            
        except zipfile.BadZipFile as e:
            error_message = f"❌ ZIP 파일 생성 중 오류 발생 (BadZipFile): {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}
            
        except Exception as e:
            error_message = f"❌ 격리 파일 압축 작업 중 치명적인 오류 발생: {type(e).__name__}: {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}