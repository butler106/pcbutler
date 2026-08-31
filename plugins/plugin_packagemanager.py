from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 패키지 관리자 상태 점검 (PackageManagerCheck) - 완벽한 버전
# - Winget, Chocolatey의 설치 여부를 확인하고 상세 보고 데이터를 제공합니다.
# ==============================================================================
from plugin_base import PCButlerPlugin
import subprocess
import os

class PackageManagerPlugin(PCButlerPlugin):
    """
    Winget, Chocolatey 등 주요 Windows 패키지 관리자의 설치 여부를 확인합니다.
    """
    plugin_name = "PackageManagerCheck"
    description = "Winget, Chocolatey 등 패키지 관리자의 설치 여부를 확인하고 상태를 보고합니다."
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def _check_command(self, command):
        """특정 명령어가 시스템에서 실행 가능한지 확인"""
        # Winget, Choco가 PATH에 있는지, 실행 가능한지 확인
        try:
            # help 명령어로 실행 가능 여부만 빠르게 확인
            # check=False로 설정하여 명령이 실패해도 파이썬 오류를 발생시키지 않음
            subprocess.run(
                [command, "--version"], 
                capture_output=True, 
                text=True, 
                timeout=5, 
                check=False
            )
            return True
        except FileNotFoundError:
            return False # 명령어를 찾을 수 없음
        except Exception:
            return False # 기타 실행 오류

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        # 표준 run 메서드 시작
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🔍 '{self.name}' 작업을 시작합니다. (패키지 관리자 점검)", "cyan")
        self.progress(10)

        # --------------------------------------------------------
        # 1. OS 환경 점검 (Windows 전용)
        # --------------------------------------------------------
        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            log(summary, "yellow")
            self.progress(100)
            # ✅ [완벽한 흐름 유지] Windows가 아니어도 Warning 반환
            return {"status": "warning", "summary": summary}
            
        # --------------------------------------------------------
        # 2. 주요 패키지 관리자 점검 목록
        # --------------------------------------------------------
        checks = [
            ("Winget", "winget", "Windows 10/11 기본 패키지 관리자"),
            ("Chocolatey", "choco", "오래되고 안정적인 타사 패키지 관리자")
        ]
        
        results = {}
        
        for i, (name, cmd, desc) in enumerate(checks):
            is_installed = self._check_command(cmd)
            results[name] = is_installed
            
            # 진행률 업데이트
            self.progress(10 + int(80 * (i + 1) / len(checks)))
            
            # 로깅
            if is_installed:
                log(f"  -> ✅ {name} ({desc}): 설치됨", "lime")
            else:
                log(f"  -> ❌ {name} ({desc}): 설치 안됨", "red")
                
        # --------------------------------------------------------
        # 3. 최종 결과 분석 및 보고
        # --------------------------------------------------------
        winget_installed = results.get('Winget', False)
        choco_installed = results.get('Chocolatey', False)
        
        if winget_installed:
            summary = "✅ Winget이 설치되어 있어 시스템 관리가 용이합니다."
            status = "success"
        elif choco_installed:
            summary = "⚠️ Winget이 누락되었으나, Chocolatey가 설치되어 있어 패키지 관리가 가능합니다."
            status = "warning"
        else:
            summary = "❌ Winget과 Chocolatey 모두 설치되어 있지 않습니다. Winget 설치를 권장합니다."
            status = "warning" # 설치 실패가 아니므로 error 대신 warning

        log(summary, "lime" if status == "success" else "yellow")
        self.progress(100)
        
        # 🚨 [완벽한 반환] 수집된 모든 결과를 details에 담아 반환
        return {"status": status, "summary": summary, "details": results}