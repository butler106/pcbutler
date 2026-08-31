from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# plugin_versioninfo.py
# 플러그인: Butler 버전 정보 및 변경 이력 표시 (v2.0 - 상세 정보 포함 수정)
import os

class VersionInfoPlugin(PCButlerPlugin):
    plugin_name = "Butler 버전 정보 표시"
    description = "현재 Butler 버전과 최근 변경 이력을 자세히 표시합니다."

    # 🚨 [핵심 수정] execute_plugin 대신 run 메서드를 사용하고, 표준 인자를 받도록 변경
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        """플러그인의 메인 실행 로직"""
        # 표준 run 메서드 시작
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        
        # logger 사용을 간편하게 하기 위해 정의
        log = self.logger
        log(f"🔍 '{self.plugin_name}' 작업을 시작합니다.", "cyan")
        self.progress(10)

        # BASE_DIR 설정 (settings에서 전달받아 사용)
        base_path = self.settings.get(
            "BASE_DIR", 
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # 폴백 경로
        )
        
        try:
            log("📦 Butler 버전 정보 확인 중...", "white")
            self.progress(30)
            
            # config 폴더 경로를 BASE_DIR 기준으로 변경
            version_path = os.path.join(base_path, "config", "version_info.txt")
            
            if not os.path.exists(version_path):
                summary = "⚠️ 버전 정보 파일이 존재하지 않습니다 → 초기 버전으로 간주"
                log(summary, "yellow")
                self.progress(100)
                # 🚨 [필수] Warning 반환 및 details에 빈 리스트 반환
                return {"status": "warning", "summary": summary, "details": []} 

            version_info = []
            with open(version_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            log("✅ 현재 Butler 버전 및 변경 이력 상세:", "lime")
            
            # 텍스트 파일 내용을 상세 정보 리스트로 변환
            for i, line in enumerate(lines):
                stripped_line = line.strip()
                if stripped_line:
                    # 콘솔에도 상세 로그 출력
                    log(f"📌 {stripped_line}", "gray")
                    version_info.append(stripped_line)
                
                # 진행률 업데이트 추가
                self.progress(30 + int(60 * (i + 1) / len(lines)))
                
            self.progress(100)

            summary = "✅ Butler 버전 정보 및 변경 이력 상세 확인 완료."
            
            # 🚨 [핵심 수정] 상세 정보를 'details' 키에 담아 반환
            return {
                "status": "SUCCESS", 
                "summary": summary, 
                "details": version_info
            }
            
        except Exception as e:
            error_message = f"❌ 버전 정보 표시 실패: {type(e).__name__} - {e}"
            log(error_message, "red")
            self.progress(100)
            # 🚨 [필수] Error 반환 및 details에 빈 리스트 반환
            return {"status": "ERROR", "summary": error_message, "details": []}