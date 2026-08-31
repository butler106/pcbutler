from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
import os
import json
from datetime import datetime
import sys

# --- get_base_path function (for plugins) ---
# main.py에서 BASE_DIR을 설정했지만, 플러그인 파일 자체에서 BASE_DIR을
# 안전하게 가져올 수 있도록 함수를 유지합니다.
def get_base_path_for_plugin():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        # plugins 폴더의 상위 디렉토리 (BASE_DIR)
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# --- get_base_path function end ---

class DashboardgenPlugin(PCButlerPlugin):
    plugin_name = "대시보드 생성"
    description = "승인 상태를 요약한 HTML 대시보드를 생성합니다."

    def __init__(self, analysis_id, settings):
        # PCButlerPlugin의 필수 인자를 전달합니다.
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    # 🚨 [수정 사항 1] run 메서드 추가: main.py의 run_diagnosis에서 호출됨
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        """메인 실행기에 의해 호출되는 기본 실행 메서드."""
        # settings에서 BASE_DIR을 가져오거나, 없다면 안전 경로를 사용
        base_path = self.settings.get("BASE_DIR", get_base_path_for_plugin())
        return self.execute_plugin(base_path)


    def _load_json(self, path):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                self.logger(f"❌ JSON 파일 로드 오류 ({path}): {e}", "red")
                return {}
        return {}
    
    def _generate_html(self, status_data, approval_data, version_data, report_dir):
        """핵심 데이터를 기반으로 HTML 문자열을 생성합니다."""
        
        # 1. 상태 요약 정보 추출
        system_status = status_data.get("status", "진단 미실행")
        recommendation = status_data.get("recommendation", "진단을 실행하세요.")
        issue_count = status_data.get("issue_count", 0)
        last_checked = status_data.get("generated_at", "N/A")
        
        # 2. 버전 정보 추출
        current_version = version_data.get("current_version", "N/A")
        
        # 3. 업데이트 승인 정보 추출
        approved_by = approval_data.get("approved_by", "미확인 사용자")
        # approved_upgrades 키가 없거나 딕셔너리가 아닐 수 있으므로 안전하게 처리
        approved_plugins = approval_data.get("approved_upgrades", {}) if isinstance(approval_data.get("approved_upgrades"), dict) else {}
        
        # 4. 시각화 상태 결정
        status_color = "#3498db" # INFO: blue
        status_icon = "🔵"
        if "경고" in system_status or "주의" in system_status:
            status_color = "#f39c12" # WARNING: orange
            status_icon = "🟠"
        elif "오류" in system_status or "심각" in system_status:
            status_color = "#e74c3c" # ERROR: red
            status_icon = "🔴"
        elif "정상" in system_status or "양호" in system_status:
            status_color = "#2ecc71" # SUCCESS: green
            status_icon = "🟢"

        # 5. HTML 템플릿 작성
        html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PC Butler 진단 대시보드</title>
    <style>
        body {{ font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; background-color: #f4f7f6; color: #333; margin: 0; padding: 20px; }}
        .dashboard-container {{ max-width: 900px; margin: 0 auto; background: #fff; border-radius: 12px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1); padding: 30px; }}
        .header {{ text-align: center; margin-bottom: 30px; border-bottom: 3px solid {status_color}; padding-bottom: 15px; }}
        .header h1 {{ color: #2c3e50; font-size: 28px; margin: 0; }}
        .status-box {{ background: {status_color}; color: #fff; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 30px; }}
        .status-box h2 {{ margin: 0; font-size: 24px; font-weight: 600; }}
        .card-container {{ display: flex; flex-wrap: wrap; gap: 20px; }}
        .card {{ background: #f9f9f9; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05); flex: 1 1 calc(50% - 20px); min-width: 300px; }}
        .card h3 {{ color: #34495e; margin-top: 0; border-bottom: 1px dashed #ccc; padding-bottom: 10px; margin-bottom: 15px; font-size: 18px; }}
        .version-info {{ font-weight: bold; color: #7f8c8d; }}
        .recommendation {{ background: #ecf0f1; padding: 15px; border-left: 5px solid {status_color}; border-radius: 4px; margin-top: 15px; white-space: pre-wrap; }}
        .list-item {{ margin-bottom: 8px; font-size: 14px; }}
        .list-item .icon {{ margin-right: 8px; }}
        .list-item.approved {{ color: #2ecc71; font-weight: 600; }}
        .list-item.denied {{ color: #e74c3c; }}
        .list-item.pending {{ color: #f39c12; }}
    </style>
</head>
<body>
    <div class="dashboard-container">
        <div class="header">
            <h1>PC Butler 시스템 진단 대시보드</h1>
            <p class="version-info">현재 버전: {current_version} | 최종 확인: {last_checked}</p>
        </div>

        <div class="status-box">
            <h2>{status_icon} 시스템 최종 상태: {system_status}</h2>
            <p>발견된 주요 문제/경고: <strong>{issue_count}건</strong></p>
        </div>

        <div class="card-container">
            <div class="card">
                <h3>주요 권장 사항</h3>
                <div class="recommendation">
                    {recommendation if recommendation else '특별한 권장 사항이 없습니다.'}
                </div>
            </div>

            <div class="card">
                <h3>업데이트 승인 현황</h3>
                <p><strong>최종 승인자:</strong> {approved_by}</p>
                <ul>
                    {''.join([
                        f"""<li class="list-item {'approved' if is_approved else 'denied'}">
                            <span class="icon">{ '✅' if is_approved else '❌'}</span>
                            {plugin_name}: { '승인 완료' if is_approved else '승인 거부/보류'}
                        </li>"""
                        for plugin_name, is_approved in approved_plugins.items()
                    ]) if approved_plugins else '<li class="list-item pending"><span class="icon">ℹ️</span> 대기 중인 업데이트 제안 없음</li>'}
                </ul>
            </div>
        </div>
    </div>
</body>
</html>"""
        return html_template

    # 🚨 [수정 사항 2] base_path 인자를 run에서 받아오도록 수정
    def execute_plugin(self, base_path):
        self.logger(f"🔍 '{self.plugin_name}' 작업을 시작합니다.", "cyan")
        self.progress(10)

        # 1. 경로 설정
        report_dir = os.path.join(base_path, "reports")
        config_dir = os.path.join(base_path, "config")
        dashboard_path = os.path.join(report_dir, "dashboard.html")

        # 2. JSON 데이터 로드
        # 로드 실패 시 빈 딕셔너리를 반환하므로 안전합니다.
        status_data = self._load_json(os.path.join(report_dir, "status_latest.json"))
        approval_data = self._load_json(os.path.join(config_dir, "approval_flags.json"))
        version_data = self._load_json(os.path.join(config_dir, "versioninfo.json"))

        self.progress(30)
        
        # 3. HTML 생성
        try:
            # 필수 데이터(status_latest.json)가 없으면 경고 반환
            if not status_data:
                 self.progress(100)
                 summary = "⚠️ 필수 진단 결과 파일(status_latest.json)이 없어 대시보드 생성을 건너뜁니다."
                 self.logger(summary, "yellow")
                 return {"status": "WARNING", "summary": summary}
                 
            html_content = self._generate_html(status_data, approval_data, version_data, report_dir)
            
            # 4. 파일 저장
            os.makedirs(report_dir, exist_ok=True)
            with open(dashboard_path, "w", encoding="utf-8") as f:
                f.write(html_content)
                
            self.logger(f"✅ 대시보드 생성 완료: {dashboard_path}", "lime")
            self.progress(100)
            
            return {"status": "SUCCESS", "summary": f"HTML 대시보드가 {dashboard_path}에 생성되었습니다."}

        except Exception as e:
            self.logger(f"❌ 대시보드 생성 중 치명적 오류 발생: {e}", "red")
            self.progress(100)
            return {"status": "ERROR", "summary": f"대시보드 생성 중 치명적 오류 발생: {e}"}
        
    def plugin_stop(self):
        # run 메서드를 추가했으므로, 이 함수는 사용되지 않을 가능성이 높습니다.
        pass