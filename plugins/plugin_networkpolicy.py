from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 네트워크 정책 점검 (NetworkPolicy) - 필수 속성 추가
# ==============================================================================
from plugin_base import PCButlerPlugin
import subprocess
import os
import json

class NetworkPolicyPlugin(PCButlerPlugin):
    """
    Windows 방화벽의 현재 정책 설정을 점검합니다. (FirewallCheck와 유사)
    """
    # 🚨 [수정] 필수 속성 추가
    plugin_name = "NetworkPolicy"
    description = "Windows 방화벽 정책(Inbound/Outbound)의 허용 상태를 점검합니다."
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        
        self.logger(f"🔍 '{self.name}' 작업을 시작합니다.", "cyan")

        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            self.logger(summary, "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}
            
        self.progress(10)
        
        try:
            # PowerShell을 사용하여 기본 방화벽 정책(Default Action) 확인
            ps_script = """
            $profiles = Get-NetFirewallProfile -PolicyStore ActiveStore
            $status = @{}
            foreach ($p in $profiles) {
                $status[$p.Name] = @{
                    Inbound = $p.DefaultInboundAction
                    Outbound = $p.DefaultOutboundAction
                }
            }
            $status | ConvertTo-Json -Compress
            """
            
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                encoding='cp949', 
                errors='ignore',
                shell=True,
                check=False,
                timeout=10
            )
            
            output = result.stdout.strip()
            
            if not output:
                summary = "방화벽 정책 정보를 가져오지 못했습니다."
                return {"status": "error", "summary": summary}
                
            data = json.loads(output)
            
            self.progress(70)

            warnings = []
            
            # Allow: 허용 (보안 취약), Block: 차단 (보안 양호)
            for profile_name, actions in data.items():
                if actions['Inbound'] == 'Allow':
                    warnings.append(f"⚠️ {profile_name} Inbound : Allow (주의)")
                if actions['Outbound'] == 'Allow':
                    warnings.append(f"⚠️ {profile_name} Outbound : Allow (주의)")
                
                self.logger(f"  -> {profile_name} (In: {actions['Inbound']}, Out: {actions['Outbound']})", "lime" if actions['Inbound'] == 'Block' and actions['Outbound'] == 'Allow' else "yellow")

            self.progress(100)
            
            if warnings:
                summary = f"⚠️ {len(warnings)}개의 방화벽 정책이 기본 허용(Allow)으로 설정되어 있습니다. (보안 점검 필요)"
                status = "warning"
            else:
                summary = "✅ 모든 방화벽 정책의 기본 동작이 '차단'으로 설정되어 있습니다. (양호)"
                status = "success"

            return {"status": status, "summary": summary, "details": data}

        except Exception as e:
            error_message = f"❌ [오류] 네트워크 정책 점검 실패: {e}"
            self.logger(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}