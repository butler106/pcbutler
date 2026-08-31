from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: Windows 서비스 상태 점검 (WindowsServiceStatus) - 최종 상세화 버전
# - PowerShell JSON 파싱을 통해 상세 정보를 추출합니다.
# ==============================================================================
from plugin_base import PCButlerPlugin
import subprocess
import os
import json
import io
import sys

# 콘솔 인코딩 문제 방지
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding = 'utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding = 'utf-8')
except:
    pass


class WindowsServiceStatusPlugin(PCButlerPlugin):
    """
    주요 Windows 서비스의 실행 상태를 점검하고 상세 결과를 반환합니다.
    """
    plugin_name = "Windows 서비스 상태 점검"
    description = "주요 Windows 서비스의 실행 상태를 점검하고 상세 결과를 반환합니다."
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description
        
        # 🚨 [수정] 점검할 중요 서비스 목록 확장
        self.critical_services = [
            "RpcSs",          # Remote Procedure Call (RPC)
            "LanmanWorkstation", # Workstation (네트워크 접근)
            "BITS",           # Background Intelligent Transfer Service
            "Spooler",        # Print Spooler
            "wuauserv",       # Windows Update
            "TermService"     # Remote Desktop Services (원격 접속 시 중요)
        ] 

    # 🚨 [핵심 수정] run 메서드 통합 및 상세 로직 적용
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🔍 '{self.name}' 작업을 시작합니다. (중요 서비스 {len(self.critical_services)}개)", "cyan")

        # 1. 플랫폼 체크 (Windows 전용)
        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            log(summary, "yellow")
            self.progress(100)
            return {"status": "WARNING", "summary": summary, "details": []}
            
        self.progress(10)
        
        missing_services = []
        all_service_details = []
        
        try:
            # 2. 각 서비스의 상태를 PowerShell로 상세 점검
            for i, service_name in enumerate(self.critical_services):
                if self.stop_event and self.self.stop_event.is_set():
                    break
                    
                log(f"  -> 서비스 상태 확인 중: '{service_name}'", "white")
                
                # PowerShell 명령어: 서비스 상태와 이름만 JSON으로 가져옵니다.
                cmd = f'powershell.exe -Command "Get-Service -Name \'{service_name}\' -ErrorAction SilentlyContinue | Select-Object Status, Name | ConvertTo-Json"'
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding='utf-8', 
                    errors='ignore',
                    shell=True,
                    check=False,
                    timeout=5 
                )
                
                output_json = result.stdout.strip()
                
                # 결과 파싱
                service_status = "NOT_FOUND"
                raw_status = ""
                
                try:
                    # PowerShell이 단일 객체를 반환할 때와 리스트를 반환할 때 모두 처리
                    service_data = json.loads(output_json)
                    if isinstance(service_data, list):
                        service_data = service_data[0] if service_data else None

                    if service_data and service_data.get("Status"):
                        raw_status = service_data["Status"].upper()
                        if raw_status in ["RUNNING", "실행 중"]:
                            service_status = "RUNNING"
                        else:
                            service_status = "STOPPED/PAUSED"
                    
                except json.JSONDecodeError:
                    # 서비스가 존재하지 않거나 오류가 발생한 경우 (Get-Service에서 에러가 발생하면 빈 문자열 또는 에러 메시지를 반환)
                    pass

                
                # 3. 상세 점검 결과 기록
                current_detail = {
                    "name": service_name,
                    "status": service_status,
                    "raw_output_status": raw_status # RUNNING, STOPPED 등 원시 상태
                }
                
                if service_status == "RUNNING":
                    log(f"  -> ✅ 서비스 '{service_name}' : 실행 중", "lime")
                else:
                    log(f"  -> ❌ 서비스 '{service_name}' : 중지되었거나 찾을 수 없음 (상태: {raw_status if raw_status else 'NOT_FOUND'})", "red")
                    missing_services.append(service_name)
                    
                all_service_details.append(current_detail)
                    
                self.progress(10 + int(80 * (i + 1) / len(self.critical_services)))

            self.progress(100)
            
            # 4. 최종 결과 요약
            if missing_services:
                summary = f"❌ **{len(missing_services)}개**의 중요 서비스가 실행 중이 아닙니다. (점검 필요: {', '.join(missing_services)})"
                status = "ERROR"
            else:
                summary = "✅ 모든 중요 서비스가 정상적으로 실행 중입니다. (양호)"
                status = "SUCCESS"

            # 🚨 [필수] 최종 결과를 details에 담아 반환
            return {"status": status, "summary": summary, "details": all_service_details}

        except Exception as e:
            error_message = f"❌ [치명적 오류] Windows 서비스 점검 실패: {type(e).__name__} - {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "ERROR", "summary": error_message, "details": []}