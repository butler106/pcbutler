from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
import os
import shutil

class TempCleanPlugin(PCButlerPlugin):
    plugin_name = "TempClean"
    description = "시스템 임시 파일을 정리합니다."

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)

        status = "SUCCESS"
        cleaned_count = 0

        # 시스템 폴더 제외
        temp_dirs = [
            os.path.expandvars('%TEMP%')  # 사용자 임시 폴더만 대상
        ]

        excluded_dirs = [os.path.join(os.path.expandvars('%WINDIR%'), 'Temp')]
        self.logger(f"⚠️ 시스템 보호 폴더 제외됨: {excluded_dirs[0]}", "yellow")

        for temp_dir in temp_dirs:
            self.logger(f"🔍 임시 폴더 정리 시작: {temp_dir}")

            try:
                for item_name in os.listdir(temp_dir):
                    item_path = os.path.join(temp_dir, item_name)

                    try:
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                            cleaned_count += 1
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                            cleaned_count += 1
                    except PermissionError:
                        self.logger(f"❌ [권한 오류] 삭제 실패: {item_path}", "red")
                    except OSError as e:
                        self.logger(f"⚠️ [정리 오류] 삭제 실패: {item_path} ({e})", "yellow")
            except Exception as e:
                self.logger(f"❌ [예상치 못한 오류] TempClean 실행 중 오류 발생: {e}", "red")
                status = "ERROR"

        summary = f"총 {cleaned_count}개의 임시 파일/폴더 정리 완료. (최종 상태: {status})"
        self.logger(summary, "lime" if status == "SUCCESS" else "yellow" if status == "WARNING" else "red")

        self.progress(100)
        return {
            "status": status,
            "summary": summary,
            "details": {
                "deleted_count": cleaned_count,
                "excluded_paths": excluded_dirs
            }
        }
