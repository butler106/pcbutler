from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 임시 폴더 사용량 (TempFolderUsage) - 필수 속성 추가
# ==============================================================================
from plugin_base import PCButlerPlugin
import os

class TempFolderUsagePlugin(PCButlerPlugin):
    """
    시스템 임시 폴더의 현재 사용량을 확인합니다.
    """
    # 🚨 [수정] 필수 속성 추가
    plugin_name = "TempFolderUsage"
    description = "Windows 임시 폴더 (Temp)의 총 사용량을 확인합니다."
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description
        self.temp_dirs = [os.environ.get('TEMP')]
        if os.name == 'nt':
            self.temp_dirs.append(os.path.join(os.environ.get('WINDIR'), 'Temp'))

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        self.logger(f"🔍 '{self.name}' 작업을 시작합니다.", "cyan")

        total_size_mb = 0
        
        for i, temp_dir in enumerate(filter(None, self.temp_dirs)):
            if not os.path.isdir(temp_dir):
                continue

            self.logger(f"  -> 🔍 폴더 크기 측정 시작: {temp_dir}", "yellow")

            # 폴더 크기 재귀적으로 계산 (느릴 수 있음)
            for dirpath, dirnames, filenames in os.walk(temp_dir):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.exists(fp):
                        try:
                            total_size_mb += os.path.getsize(fp) / (1024**2)
                        except:
                            pass
            
            self.progress(10 + int(80 * (i + 1) / len(self.temp_dirs)))

        self.progress(100)
        
        if total_size_mb > 1024: # 1GB 이상
            summary = f"❌ 임시 폴더 사용량: {total_size_mb:.2f} MB. 1GB를 초과했습니다. 정리가 필요합니다."
            status = "error"
            self.logger(f"\n❌ '{self.name}' 작업을 완료했습니다. ({summary})", "red")
        elif total_size_mb > 500: # 500MB 이상
            summary = f"⚠️ 임시 폴더 사용량: {total_size_mb:.2f} MB. 다소 많습니다. 정리를 고려하십시오."
            status = "warning"
            self.logger(f"\n⚠️ '{self.name}' 작업을 완료했습니다. ({summary})", "yellow")
        else:
            summary = f"✅ 임시 폴더 사용량: {total_size_mb:.2f} MB. (양호)"
            status = "success"
            self.logger(f"\n✅ '{self.name}' 작업을 완료했습니다. ({summary})", "lime")
            
        return {"status": status, "summary": summary, "total_size_mb": total_size_mb}