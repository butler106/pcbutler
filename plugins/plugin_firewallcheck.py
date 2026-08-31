from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 방화벽 상태 점검 (FirewallCheck) - 안정화 버전
# - I/O Deadlock 및 인코딩 오류 방지 로직 적용
# ==============================================================================
from plugin_base import PCButlerPlugin
import subprocess
import os
import sys # sys.platform 사용을 위해 추가

class FirewallCheckPlugin(PCButlerPlugin):
    """
    Windows 방화벽의 현재 프로필(도메인, 개인, 공용) 상태를 점검합니다.
    """
    plugin_name = "Firewallcheck"
    description = "Windows 방화벽의 프로필별 상태를 점검합니다."
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        """플러그인의 메인 실행 로직"""
        
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        
        self.logger(f"🔍 '{self.name}' 작업을 시작합니다.", "cyan")

        if sys.platform != "win32":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            self.logger(summary, "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}
            
        self.progress(10)
        
        try:
            # PowerShell 명령어: 모든 방화벽 프로필(도메인, 개인, 공용)의 활성화 여부를 True/False로 출력
            # ConvertTo-Csv 후 헤더를 제거하고, 따옴표를 제거한 다음 쉼표로 연결하여 "True,True,False" 형태의 문자열 생성
            ps_script = "(Get-NetFirewallProfile -PolicyStore ActiveStore | Select-Object Enabled | ConvertTo-Csv -NoTypeInformation | Select-Object -Skip 1) -replace '\"','' -join ','"
            
            self.logger("  -> ⏳ 방화벽 프로필 상태 확인 중...", "yellow")
            
            # 🚨 [핵심 수정]: text=True 및 encoding 제거, 바이트로 수신하여 Deadlock 방지
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True, # 바이트로 수신
                shell=True,
                check=False,
                timeout=10
            )
            
            # 🚨 [핵심 수정]: 수동 디코딩 (CP949 우선)
            output = ""
            try:
                output = result.stdout.decode('cp949', errors='ignore').strip()
            except Exception:
                output = result.stdout.decode('utf-8', errors='ignore').strip()
            
            output = output.lower() # 파싱을 위해 소문자로 변환
            
            self.progress(50)

            # PowerShell 명령 실행 실패 시 처리
            if result.returncode != 0:
                summary = f"❌ PowerShell 명령 실행 실패 (코드: {result.returncode}). 방화벽 정보 확인 불가."
                self.logger(summary, "red")
                self.progress(100)
                return {"status": "error", "summary": summary, "details": output}
            
            self.progress(70)

            if "false" in output:
                # 'True'만 있어야 하는데 'False'가 포함된 경우 (일부 프로필 꺼짐)
                summary = "⚠️ 방화벽 프로필 중 일부(또는 전체)가 '해제' 상태입니다."
                status = "warning"
                self.logger(f"  -> ⚠️ 방화벽이 완전히 활성화되지 않았습니다. (상태: {output})", "yellow")
            elif "true" in output:
                summary = "✅ 모든 방화벽 프로필이 '사용' 상태입니다. (양호)"
                status = "success"
                self.logger("  -> ✅ 모든 방화벽 프로필 활성화 확인.", "lime")
            else:
                summary = "❌ 방화벽 상태 확인 실패. (로그 확인 필요)"
                status = "error"
                self.logger(f"  -> ❌ 방화벽 상태를 확인할 수 없습니다. (출력: {output})", "red")
            
            self.progress(100)
            
            return {"status": status, "summary": summary, "details": output}

        except Exception as e:
            error_message = f"❌ [치명적 오류] 방화벽 점검 플러그인 실행 실패: {e}"
            self.logger(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}