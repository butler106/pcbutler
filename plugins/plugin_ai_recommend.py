from plugin_base import PCButlerPlugin
# plugin_ai_recommend.py
# 플러그인: AI 진단 추천 결과 저장 (v1.3 - run 메서드 시그니처 표준화)

# -*- coding: utf-8 -*-
import sys
import io
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Union, List # 표준 타입 힌트 추가

# 콘솔 인코딩 문제 방지
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding = 'utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding = 'utf-8')
except:
    pass

# AI 진단 결과의 심각도 매핑
STATUS_MAP = {
    "심각": {"css": "high", "icon": "🔴"},
    "경고": {"css": "medium", "icon": "🟠"},
    "주의": {"css": "medium", "icon": "🟠"},
    "권장": {"css": "medium", "icon": "🟠"},
    "양호": {"css": "low", "icon": "🟢"},
    "정보": {"css": "info", "icon": "🔵"},
}


class AIRecommendPlugin(PCButlerPlugin):
    plugin_name = "AI 진단 추천"
    description = "진단 결과를 분석하여 우선 작업을 추천하고, JSON 및 HTML로 저장합니다."

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        
        # BASE_DIR 설정
        base_path = self.settings.get("BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.report_dir = os.path.join(base_path, 'reports')
        self.source_json_name = "status_latest.json" # ReportMerge가 생성하는 최종 JSON 파일명
        self.html_report_name = f"AI_Recommendation_{analysis_id}.html"

    # 🚨 [핵심 수정]: run 메서드의 시그니처를 plugin_base.py와 완벽히 통일합니다.
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        # 부모 클래스의 run 메서드 호출 (로거 및 설정 초기화)
        # super().run()이 제대로 호출되어야 경고가 사라집니다.
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        
        log = self.logger
        progress_update = self.progress
        
        log(f"🔍 '{self.plugin_name}' 작업을 시작합니다.", "cyan")
        progress_update(10)
        
        source_path = os.path.join(self.report_dir, self.source_json_name)
        
        # 1. 최종 진단 결과 파일 로드 (ReportMerge가 생성한 파일)
        if not os.path.exists(source_path):
            summary = f"⚠️ 진단 결과 파일({os.path.basename(source_path)}) 없음. AI 추천 생성을 건너뜁니다."
            log(summary, "yellow")
            progress_update(100)
            return {"status": "warning", "summary": summary}
            
        progress_update(30)
        
        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                merged_report = json.load(f)
        except Exception as e:
            summary = f"❌ 최종 결과 JSON 파일을 읽는 중 오류 발생: {e}"
            log(summary, "red")
            progress_update(100)
            return {"status": "error", "summary": summary}

        # 2. AI 진단 로직 (단순화: 'error', 'warning' 상태를 우선 순위로 추출)
        recommendations = []
        
        for result in merged_report.get("plugin_results", []):
            status = result.get("status", "").upper()
            plugin_name = result.get("id", "알 수 없음")
            
            if status in ["ERROR", "FATAL_ERROR"]:
                recommendations.append(f"[심각] **{plugin_name}** 플러그인 오류 발생: {result.get('summary', '치명적 오류')}. 즉시 확인 및 조치 필요.")
            elif status in ["WARNING"]:
                recommendations.append(f"[경고] **{plugin_name}** 플러그인 경고 발생: {result.get('summary', '경고 사항')}. 점검을 권장합니다.")
        
        if not recommendations:
            recommendations.append("[양호] 모든 플러그인 진단 결과 'success' 또는 'info'입니다. 특별한 우선 조치 사항은 없습니다.")
            
        ai_data = {
            "생성 시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "분석 ID": self.analysis_id,
            "우선 추천 목록": recommendations
        }
        
        progress_update(70)

        # 3. JSON 파일 저장 (ReportMerge 파일과 별개)
        json_path = os.path.join(self.report_dir, f"ai_recommendation_{self.analysis_id}.json")
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(ai_data, f, indent=4, ensure_ascii=False)
            log(f"  -> AI 추천 결과 JSON 저장 완료: {os.path.basename(json_path)}", "gray")
        except Exception as e:
            log(f"❌ AI 추천 JSON 저장 실패: {e}", "red")

        # 4. HTML 파일 생성 및 저장
        html_path = os.path.join(self.report_dir, self.html_report_name)
        try:
            html_content = self._generate_html(ai_data)
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            summary = f"✅ AI 진단 추천 보고서 생성 완료. ({os.path.basename(html_path)})"
            log(summary, "lime")
        except Exception as e:
            summary = f"❌ AI 추천 HTML 보고서 생성 실패: {e}"
            log(summary, "red")
            return {"status": "error", "summary": summary}

        progress_update(100)
        return {"status": "success", "summary": summary}

    # HTML 생성 도우미 함수
    def _generate_html(self, ai_data: Dict[str, Any]) -> str:
        # (HTML 템플릿 코드 생략 - 수정 사항 없음)
        
        # ... (중간 HTML 스타일 및 구조 생략) ...
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <title>AI 진단 추천 보고서</title>
        <style>
            body {{ font-family: 'Malgun Gothic', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #333; margin: 0; padding: 20px; }}
            .container {{ max-width: 800px; margin: 0 auto; background-color: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); }}
            h1 {{ color: #007bff; border-bottom: 3px solid #007bff; padding-bottom: 10px; margin-top: 0; }}
            h2 {{ color: #555; margin-top: 25px; }}
            ul {{ list-style: none; padding: 0; }}
            li {{ margin-bottom: 15px; padding: 10px; border-left: 5px solid; border-radius: 4px; background-color: #f9f9f9; }}
            .status-icon {{ margin-right: 10px; font-size: 1.2em; }}
            .high {{ border-left-color: #dc3545; background-color: #f8d7da; color: #721c24; }} /* 심각 */
            .medium {{ border-left-color: #ffc107; background-color: #fff3cd; color: #856404; }} /* 경고, 주의, 권장 */
            .low {{ border-left-color: #28a745; background-color: #d4edda; color: #155724; }} /* 양호 */
            .info {{ border-left-color: #17a2b8; background-color: #d1ecf1; color: #0c5460; }} /* 정보 */
            .footer {{ margin-top: 30px; border-top: 1px solid #eee; padding-top: 10px; font-size: 0.8em; color: #999; text-align: right; }}
        </style>
        </head>
        <body>
        <div class=\"container\">
        <h1>AI 기반 우선 조치 추천 보고서</h1>
        <h2>분석 개요</h2>
        <p><strong>분석 ID:</strong> {ai_data['분석 ID']}</p>
        <p>이 보고서는 PC Butler의 진단 결과를 바탕으로 **우선적으로 확인하고 조치해야 할 사항**을 인공지능이 분석하여 추천한 목록입니다.</p>

        <h2>우선 추천 목록</h2>
        <ul>
        """
        
        # 목록 항목 처리
        for item in ai_data['우선 추천 목록']:
            css_class = "low"
            icon = "🟢"

            # item 문자열에 따라 클래스와 아이콘 결정
            if "심각" in item:
                css_class = "high"
                icon = "🔴"
            elif "경고" in item or "주의" in item or "권장" in item:
                css_class = "medium"
                icon = "🟠"
            elif "정보" in item:
                css_class = "info"
                icon = "🔵"
            
            # ** 굵은 글씨 마크다운을 HTML 태그로 변환하여 렌더링
            formatted_item = item.replace("**", "<strong>")
            
            html += f"<li class='{css_class}'><span class='status-icon'>{icon}</span>{formatted_item}</li>"
        
        html += f"""</ul>
        <div class="footer">생성 시각: {ai_data['생성 시각']}</div>
        </div></body></html>"""
        return html