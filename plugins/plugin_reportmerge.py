from typing import Dict, Any, Callable, Optional, Union, List
from plugin_base import PCButlerPlugin
import os
import json
from datetime import datetime
import glob
import re

class ReportMergePlugin(PCButlerPlugin):
    plugin_name = "ReportMerge"
    description = "개별 플러그인 결과를 JSON 및 TXT 형식의 최종 보고서로 병합합니다."
    version = "1.1.1" 

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        
        # ✅ FIX: main.py에서 전달받은 REPORT_DIR_FINAL 절대 경로를 사용합니다.
        self.report_dir = self.settings.get('REPORT_DIR_FINAL', os.path.join(os.getcwd(), 'reports'))
        
        # main.py의 최종 보고서 파일명 (병합 대상에서 제외)
        self.main_report_file = f"report_{self.analysis_id}.json"
        
        self.final_report_name = "status_latest.json"
        self.final_report_path = os.path.join(self.report_dir, self.final_report_name)
        self.target_pattern = os.path.join(self.report_dir, '*.json')

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        log(f"🔍 '{self.name}' 작업을 시작합니다. (분석 ID: {self.analysis_id})", "cyan")
        log(f"  -> 보고서 검색 경로: {self.report_dir}", "gray")
        self.progress(10)

        # 1. 병합 대상 수집
        all_json_files = glob.glob(self.target_pattern)
        plugin_result_files = []

        for file_path in all_json_files:
            file_name = os.path.basename(file_path)
            
            # 제외 규칙 1: ReportMerge 자체가 만들 최종 파일
            if file_name == self.final_report_name: continue
            # 제외 규칙 2: AI 추천 파일 (존재한다면)
            if re.match(r'AI_Recommendation_\d{8}_\d{6}\.json$', file_name): continue
            # 제외 규칙 3: main.py가 최종적으로 만드는 보고서 파일
            if file_name == self.main_report_file: continue
            
            # 포함 규칙: PluginName_<AnalysisID>.json 형식으로 저장된 파일만 포함
            if self.analysis_id in file_name:
                plugin_result_files.append(file_path)

        total_files = len(plugin_result_files)
        log(f"  -> 총 {total_files}개의 플러그인 결과 파일을 병합합니다.", "gray")

        if total_files == 0:
            final_summary = "⚠️ 병합할 플러그인 결과 파일이 없습니다. (1단계 진단 파일 미생성 확인)"
            self.progress(100)
            return {"status": "warning", "summary": final_summary}

        self.progress(30)

        # 2. 병합 처리 (기존 로직 유지)
        merged_data = {
            "analysis_id": self.analysis_id,
            "timestamp": datetime.now().isoformat(),
            "status": "INCOMPLETE",
            "summary": "Report merge process initiated.",
            "plugin_results": {}
        }

        for i, file_path in enumerate(plugin_result_files):
            file_name = os.path.basename(file_path)
            plugin_id = file_name.replace(f"_{self.analysis_id}.json", "")

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                merged_data["plugin_results"][plugin_id] = data
            except Exception as e:
                log(f"  -> ❌ 병합 실패: {file_name} ({e})", "red")
                merged_data["plugin_results"][plugin_id] = {
                    "status": "ERROR",
                    "summary": f"파일 처리 오류: {e}",
                    "details": None
                }

            self.progress(30 + int(50 * (i + 1) / total_files))
            if stop_check and stop_check():
                return {"status": "warning", "summary": "⚠️ 사용자 요청으로 병합 중단됨."}

        # 3. 최종 보고서 저장 (JSON)
        merged_data["status"] = "SUCCESS"
        merged_data["summary"] = f"총 {len(merged_data['plugin_results'])}개 플러그인 결과를 성공적으로 병합하고 TXT 보고서를 생성했습니다."

        try:
            os.makedirs(self.report_dir, exist_ok=True)
            with open(self.final_report_path, 'w', encoding='utf-8') as f:
                json.dump(merged_data, f, indent=4, ensure_ascii=False)
            log(f"✅ JSON 병합 보고서 저장 완료: {self.final_report_path}", "gray")
        except Exception as e:
            log(f"❌ JSON 저장 실패: {e}", "red")

        # 4. TXT 보고서 저장 (PDFExport를 위한 필수 파일)
        txt_path = os.path.join(self.report_dir, f"Analysis_Report_{self.analysis_id}.txt")
        try:
            with open(txt_path, 'w', encoding='utf-8') as f:
                for plugin_id, result in merged_data["plugin_results"].items():
                    status = result.get("status", "unknown")
                    summary = result.get("summary", "")
                    f.write(f"[{plugin_id}] ({status}) {summary}\n")
            log(f"✅ TXT 보고서 저장 완료: {txt_path}", "gray")
        except Exception as e:
            log(f"❌ TXT 저장 실패: {e}", "red")

        self.progress(100)
        return {"status": "success", "summary": merged_data["summary"]}