from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 장치 드라이버 점검 (DriverCheck) - JSON 파싱 및 안정화 버전
# - Get-PnpDevice의 JSON 출력 파싱 안정화 및 인코딩 문제 해결
# ==============================================================================
import os
import sys
import subprocess
import re
import json
from io import StringIO 
from plugin_base import PCButlerPlugin 

class DriverCheckPlugin(PCButlerPlugin):
    """
    Windows 장치 관리자의 드라이버 상태(ProblemCode)를 점검합니다.
    """
    plugin_name = "장치 드라이버 점검"
    description = "Windows 장치 관리자의 드라이버 상태(ProblemCode)를 점검합니다."
    version = "2.2.1" # 수정 버전 업데이트

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description
        
    def _get_error_description(self, code):
        """ProblemCode(ConfigManagerErrorCode)에 대한 설명을 반환합니다."""
        descriptions = {
            0: "장치가 올바르게 작동하고 있습니다.",
            1: "장치가 올바르게 구성되지 않았습니다. (시스템 재부팅 필요)",
            10: "장치가 시작될 수 없습니다.",
            12: "장치가 시스템의 다른 리소스를 사용하고 있습니다.",
            14: "시스템을 다시 시작해야 장치가 올바르게 작동합니다.",
            22: "장치가 비활성화되었습니다.",
            24: "장치가 존재하지 않거나 작동하지 않습니다.",
            28: "장치용 드라이버가 설치되지 않았습니다.",
            31: "장치용 드라이버를 로드할 수 없습니다.",
            39: "드라이버가 손상되었거나 누락되었습니다.",
            43: "Windows에서 이 장치를 중지했습니다. (문제 보고)",
            # 기타 오류 코드 추가 가능
        }
        return descriptions.get(code, f"알 수 없는 오류 코드 ({code})")

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        """플러그인의 메인 실행 로직"""
        
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        self.logger(f"🔍 '{self.name}' 작업을 시작합니다. (ProblemCode 점검)", "cyan")

        if sys.platform != "win32":
            summary = "이 플러그인은 Windows 환경에서만 작동합니다."
            self.logger(summary, "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}
            
        self.progress(10)
        
        # PowerShell 명령어: ProblemCode를 포함하는 PnpDevice 정보를 JSON으로 변환
        # -OutVariable를 사용하면 일부 환경에서 문제를 일으킬 수 있어 제거했습니다.
        cmd = 'powershell.exe -Command "Get-PnpDevice | Select-Object Status, Class, FriendlyName, Problem, ProblemCode | ConvertTo-Json"'
        
        try:
            # 🚨 [수정 1]: check_output 대신 subprocess.run 사용 + 안정적인 바이트 수신
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                shell=True,
                check=False,
                timeout=30 
            )
            
            # 🚨 [수정 2]: 수동 디코딩 (CP949 > UTF-8)
            output = ""
            try:
                output = result.stdout.decode('cp949', errors='ignore').strip()
            except Exception:
                output = result.stdout.decode('utf-8', errors='ignore').strip()
            
            self.progress(40)

            # PowerShell 명령 실행 실패 시 처리
            if result.returncode != 0:
                summary = f"❌ PowerShell 명령 실행 실패 (코드: {result.returncode}). 드라이버 정보를 가져올 수 없습니다."
                self.logger(summary, "red")
                self.progress(100)
                return {"status": "error", "summary": summary, "details": output}

            # 🚨 [수정 3]: JSON 파싱 안정화
            try:
                device_list = json.loads(output)
            except json.JSONDecodeError as jde:
                summary = f"❌ JSON 파싱 오류 발생. PowerShell 출력 형식이 올바르지 않습니다. ({jde})"
                self.logger(summary, "red")
                self.logger(f"  -> ℹ️ 원본 출력: {output[:300]}...", "gray")
                self.progress(100)
                return {"status": "error", "summary": summary, "details": output}
                
            self.progress(70)

            # 데이터 분석
            problem_devices = []
            
            for device in device_list:
                # ProblemCode가 0이 아니면 문제가 있는 장치로 판단
                # ProblemCode 자체가 없을 경우(None)를 0으로 간주하지 않도록 명시적 체크
                code = device.get('ProblemCode')
                if code is not None and code != 0:
                    description = self._get_error_description(code)
                    problem_devices.append({
                        "name": device.get('FriendlyName', 'Unknown Device'),
                        "class": device.get('Class', 'Unknown'),
                        "status": device.get('Status', 'N/A'),
                        "problem_code": code,
                        "description": description
                    })

            self.progress(90)
            
            # 최종 결과 정리
            if problem_devices:
                final_status = "warning"
                final_summary = f"⚠️ {len(problem_devices)}개의 장치 드라이버에서 문제(ProblemCode != 0)가 감지되었습니다. 즉시 확인이 필요합니다."
                self.logger(f"\n  -> ⚠️ {final_summary}", "yellow")
                
                # 상세 로그 요약
                details_summary = [f"[{d['problem_code']}] {d['name']} ({d['description']})" for d in problem_devices]
            else:
                final_status = "success"
                final_summary = "✅ 모든 장치 드라이버의 ProblemCode가 0(정상)입니다."
                self.logger(f"  -> ✅ {final_summary}", "lime")
                details_summary = ["No problems found."]
            
            self.progress(100)
            
            return {"status": final_status, "summary": final_summary, "details": problem_devices}

        except Exception as e:
            error_message = f"❌ [치명적 오류] 드라이버 점검 플러그인 실행 실패: {e}"
            self.logger(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}