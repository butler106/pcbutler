from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 보고서 압축 (ReportCompress) - 최종 완벽 버전
# - 최종 진단 보고서 파일(HTML/PDF)을 ZIP으로 압축합니다.
# ==============================================================================
from plugin_base import PCButlerPlugin
import os
import zipfile

class ReportCompressPlugin(PCButlerPlugin):
    """
    최종 진단 보고서 파일을 ZIP으로 압축합니다.
    """
    plugin_name = "보고서 압축"
    description = "최종 진단 보고서 파일(.html, .pdf 등)을 ZIP 형식으로 압축합니다."
    version = "2.0.0" # 최종 버전

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description
        
        # BASE_DIR을 settings에서 가져와 reports 경로를 구성 (표준 구조)
        # 기본값은 이 플러그인 파일의 상위 폴더의 상위 폴더 (PCButler_v106/)로 가정
        base_path = self.settings.get("BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.report_dir = os.path.join(base_path, 'reports') 

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        # 표준 run 메서드 시작
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        self.progress(10)

        log(f"🔍 '{self.name}' 작업을 시작합니다.", "cyan")

        # 1. 파일 경로 설정
        report_filename = self.settings.get('report_filename', f"Analysis_Report_{self.analysis_id}")
        source_path = os.path.join(self.report_dir, f"{report_filename}.html")
        zip_path = os.path.join(self.report_dir, f"{report_filename}.zip")
        
        # 2. 압축 대상 파일 존재 여부 확인
        if not os.path.exists(source_path):
            summary = f"⚠️ 압축할 보고서 파일({os.path.basename(source_path)})을 찾을 수 없어 건너뜁니다."
            log(f"  -> {summary}", "yellow")
            self.progress(100)
            # 🌟 파일 누락은 치명적 오류가 아니므로 'warning' 반환
            return {"status": "warning", "summary": summary} 
            
        self.progress(30)
        
        try:
            # 3. 압축 실행
            log(f"  -> 💾 보고서 파일 압축 시작: {os.path.basename(source_path)}", "yellow")
            
            # zipfile.ZIP_DEFLATED (압축) 또는 zipfile.ZIP_STORED (압축 없이 저장) 사용
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 아카이브 내에서 파일 경로가 복잡해지지 않도록 파일 이름만 저장
                # (예: reports/Analysis_Report_123.html -> Analysis_Report_123.html)
                zipf.write(source_path, os.path.basename(source_path))
            
            # 4. 최종 결과
            summary = f"✅ 보고서가 성공적으로 압축되었습니다: {os.path.basename(zip_path)}"
            log(f"\n✅ '{self.name}' 작업을 완료했습니다. ({summary})", "lime")
            
            self.progress(100)
            
            return {"status": "success", "summary": summary}

        except PermissionError:
            error_message = f"❌ 압축 실패: {self.report_dir}에 쓰기 권한이 없습니다. (관리자 권한 확인)"
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}
            
        except Exception as e:
            error_message = f"❌ 보고서 압축 중 치명적인 오류 발생: {type(e).__name__}: {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}