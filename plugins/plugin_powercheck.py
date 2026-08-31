from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 전원 설정 점검 (PowerCheck) - 최종 완벽 버전
# - powercfg 명령어를 사용하여 현재 활성 전원 계획 및 절전 모드를 분석합니다.
# ==============================================================================
from plugin_base import PCButlerPlugin
import subprocess
import re
import os
import sys

class PowerCheckPlugin(PCButlerPlugin):
    """
    현재 활성 전원 관리 모드(고성능, 균형 조정 등)와 최대 절전 모드 설정을 점검합니다.
    """
    plugin_name = "PowerCheck"
    description = "현재 전원 관리 모드와 절전 설정을 점검하고 성능 권장 사항을 제공합니다."
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        # 표준 run 메서드 시작
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🔍 '{self.name}' 작업을 시작합니다. (전원 설정 및 절전 모드 점검)", "cyan")
        self.progress(10)

        # --------------------------------------------------------
        # 1. OS 환경 점검 (Windows 전용)
        # --------------------------------------------------------
        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            log(summary, "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}
            
        final_status = "success"
        
        try:
            # --------------------------------------------------------
            # 2. 활성 전원 계획 (Active Power Scheme) 확인
            # --------------------------------------------------------
            log("🔧 활성 전원 계획 GUID 확인 중...", "white")
            
            # powercfg는 한국어 Windows에서 cp949 인코딩을 사용하므로 이를 명시
            scheme_result = subprocess.run(
                ['powercfg', '/getactivescheme'], 
                capture_output=True, 
                text=True, 
                check=True,
                timeout=10,
                encoding='cp949',
                errors='ignore'
            )
            
            scheme_output = scheme_result.stdout
            
            # GUID와 이름을 정규식으로 파싱
            match = re.search(r'Power Scheme GUID: ([0-9a-f-]+)\s+\((.*?)\)', scheme_output, re.IGNORECASE)
            
            if not match:
                raise ValueError("활성 전원 계획 정보를 파싱할 수 없습니다.")
                
            active_guid = match.group(1).upper()
            active_name = match.group(2).strip()
            
            self.progress(40)
            
            # --------------------------------------------------------
            # 3. 최대 절전 모드 (Hibernation) 상태 확인
            # --------------------------------------------------------
            log("🔧 최대 절전 모드 (Hibernation) 상태 확인 중...", "white")
            hiber_result = subprocess.run(
                ['powercfg', '/h', 'query'], 
                capture_output=True, 
                text=True, 
                check=False,
                timeout=5,
                encoding='cp949',
                errors='ignore'
            )
            
            # 활성화 여부 판단 (영문 또는 한글 메시지 모두 커버)
            hiber_enabled = bool(re.search(r'(enabled|사용하도록 설정)', hiber_result.stdout, re.IGNORECASE))
            hiber_status_str = "✅ 사용함 (권장: 시스템에 따라 다름)" if hiber_enabled else "❌ 사용 안함 (권장: 고성능 환경)"
            
            self.progress(70)

            # --------------------------------------------------------
            # 4. 최종 분석 및 보고
            # --------------------------------------------------------
            # 고성능 관련 키워드 확인 (GUID 기반 확인이 가장 정확함)
            # 고성능: 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
            # 최고의 성능: e9a42b02-d5df-448d-aa00-03f14749f610
            is_high_performance_scheme = active_guid in [
                '8C5E7FDA-E8BF-4A96-9A85-A6E23A8C635C', # High Performance (고성능)
                'E9A42B02-D5DF-448D-AA00-03F14749F610'  # Ultimate Performance (최고의 성능)
            ]
            
            log(f"  -> ⚡ 활성 전원 계획: **{active_name}** ({active_guid})", "lime" if is_high_performance_scheme else "yellow")
            log(f"  -> 🔋 최대 절전 모드: {hiber_status_str}", "gray")

            if is_high_performance_scheme:
                summary = f"✅ 전원 계획이 **{active_name}**으로 설정되어 있어 성능이 양호합니다."
                final_status = "success"
            else:
                summary = f"⚠️ 전원 계획이 **{active_name}**으로 설정되어 있습니다. 고성능 환경을 위해 '고성능' 또는 '최고의 성능'으로 변경을 권장합니다."
                final_status = "warning"
                
            self.progress(100)
            
            details = {
                "active_scheme_name": active_name,
                "active_scheme_guid": active_guid,
                "is_high_performance": is_high_performance_scheme,
                "hibernation_enabled": hiber_enabled
            }

            # 🚨 [완벽한 반환] 수집된 모든 정보를 details에 담아 반환
            return {"status": final_status, "summary": summary, "details": details}
            
        except subprocess.CalledProcessError as e:
            error_message = f"❌ 전원 설정 점검 실패: powercfg 명령어 실행 오류. (코드: {e.returncode})"
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}
            
        except Exception as e:
            error_message = f"❌ 전원 설정 점검 중 치명적인 오류 발생: {type(e).__name__}: {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}