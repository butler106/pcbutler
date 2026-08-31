from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# plugin_browsercache.py
# 플러그인: 브라우저 캐시 및 임시 파일 삭제 (v1.2 - NoneType 오류 및 표준 구조 적용)
import subprocess
import os
import shutil

class BrowserCachePlugin(PCButlerPlugin):
    plugin_name = "브라우저 캐시 정리"
    description = "Chrome, Edge 등 주요 브라우저의 캐시와 시스템 임시 파일을 정리합니다."

    # 🚨 [핵심 수정] execute_plugin 대신 run 메서드를 사용하고, 표준 인자를 받도록 변경
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🔍 '{self.plugin_name}' 작업을 시작합니다.", "cyan")
        self.progress(10)

        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에 최적화되어 있습니다."
            log(summary, "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}
            
        total_cleaned_size = 0
        cleaned_summary_list = []
        
        # 1. 시스템 임시 파일 경로
        temp_paths = [
            os.path.join(os.environ.get('TEMP', 'C:\\Windows\\Temp')),
            os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Temp'),
        ]
        
        # 2. 브라우저 캐시 경로 (Windows 기준)
        browser_paths = {
            "Chrome Cache": os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Google', 'Chrome', 'User Data', 'Default', 'Cache'),
            "Edge Cache": os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data', 'Default', 'Cache'),
        }

        # 모든 경로에 대한 정리 작업 수행
        paths_to_clean = temp_paths + list(browser_paths.values())
        
        for i, path in enumerate(paths_to_clean):
            if self.self.stop_event and self.self.stop_event.is_set():
                break
                
            self.progress(10 + int(70 * (i / len(paths_to_clean))))
            
            if not os.path.exists(path):
                continue
                
            log(f"🧹 폴더 정리 중: {os.path.basename(path)}", "white")
            size_before = 0
            
            try:
                # 폴더 전체 크기 계산
                for root, _, files in os.walk(path):
                    for name in files:
                        try:
                            size_before += os.path.getsize(os.path.join(root, name))
                        except:
                            pass
                
                # 폴더 내 파일 및 서브 디렉토리 삭제
                for item in os.listdir(path):
                    full_path = os.path.join(path, item)
                    try:
                        if os.path.isdir(full_path):
                            shutil.rmtree(full_path)
                        else:
                            os.remove(full_path)
                    except Exception:
                        pass # 사용 중인 파일은 무시

                # 정리 후 크기 계산 (삭제된 크기 = size_before)
                cleaned_size_mb = size_before / (1024 * 1024)
                total_cleaned_size += size_before
                
                if cleaned_size_mb > 0.01:
                    cleaned_summary_list.append(f"{os.path.basename(path)}: {cleaned_size_mb:.2f} MB")
                
            except Exception as e:
                log(f"  -> ⚠️ {os.path.basename(path)} 정리 실패: {e}", "yellow")

        self.progress(90)
        
        # 3. 최종 결과 요약
        if total_cleaned_size > 0:
            total_cleaned_mb = total_cleaned_size / (1024 * 1024)
            summary = f"✅ 캐시 및 임시 파일 {len(cleaned_summary_list)}개 항목에서 총 {total_cleaned_mb:.2f} MB 정리 완료."
            log(summary, "lime")
            for item in cleaned_summary_list:
                 log(f"  - {item}", "gray")
            final_status = "success"
        else:
            summary = "✅ 정리할 캐시/임시 파일이 없거나, 모두 사용 중인 파일이었습니다."
            log(summary, "lime")
            final_status = "success"

        self.progress(100)
        # 🚨 [필수] 최종 결과 반환
        return {"status": final_status, "summary": summary}
            
    # 🚨 [수정] plugin_stop은 정리 작업만 수행하도록 변경 (불필요한 return 제거)
    def plugin_stop(self):
        self.logger("🛑 브라우저 캐시 정리 플러그인 종료됨", "gray")
        pass