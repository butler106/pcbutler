from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
import subprocess
import os
import io
import sys
import re

# 스크립트의 표준 출력(stdout)과 표준 오류(stderr)의 인코딩을 UTF-8로 강제 설정
# (메인 프로그램 환경에서는 불필요하나, 단독 실행 테스트를 위해 유지)
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding = 'utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding = 'utf-8')
except Exception:
    pass

class UserCheckPlugin(PCButlerPlugin):
    plugin_name = "사용자 계정 점검"
    description = "로컬 사용자 계정 목록과 비밀번호 정책, 관리자 권한 여부를 점검합니다. (Windows 전용)"

    # 🚨 [최종 수정] execute_plugin의 로직을 run 메서드로 통합
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        """플러그인의 메인 실행 로직"""
        # PCButlerPlugin의 run 초기화 로직 호출
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs) 
        log = self.logger # 로거 함수 재정의
        
        status = "SUCCESS"
        summary = "로컬 사용자 계정 점검 완료."
        warning_count = 0
        
        log("👤 사용자 계정 점검 시작...", "cyan")
        self.progress(10)
        
        # 1. 플랫폼 체크 (Windows 전용)
        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            log(summary, "yellow")
            self.progress(100)
            return {"status": "WARNING", "summary": summary}
            
        try:
            # 2. PowerShell 명령 실행 (Get-LocalUser)
            # Enabled, PasswordRequired, PasswordLastSet, MemberOf Group을 조회하여 위험도를 판단합니다.
            cmd = 'powershell.exe -Command "Get-LocalUser | Select-Object Name, Enabled, PasswordRequired, PasswordLastSet, @{Name=\'IsAdmin\';Expression={$_.SID -in (Get-LocalGroupMember -Name Administrators).SID}} | ConvertTo-Json"'
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8', 
                errors='ignore',
                check=False,
                timeout=30 
            )
            
            # PowerShell 결과 파싱
            output_json = result.stdout.strip()
            
            import json
            try:
                user_data = json.loads(output_json)
            except json.JSONDecodeError:
                # JSON 파싱 실패 시, 원시 출력을 오류로 기록
                log(f"❌ PowerShell 출력 파싱 실패. 원시 출력: {output_json[:200]}...", "red")
                self.progress(100)
                return {"status": "ERROR", "summary": "사용자 계정 정보 파싱 실패."}
            
            self.progress(50)
            
            # 3. 계정 분석
            problematic_accounts = []
            
            # user_data가 단일 객체일 경우 리스트로 변환
            if isinstance(user_data, dict):
                user_data = [user_data]

            for user in user_data:
                user_name = user.get("Name", "UNKNOWN")
                
                # Built-in 계정은 점검에서 제외 (Guest, DefaultAccount 등)
                if user_name in ["Guest", "DefaultAccount", "WDAGUtilityAccount"]:
                    continue

                is_enabled = user.get("Enabled", False)
                pwd_required = user.get("PasswordRequired", False)
                is_admin = user.get("IsAdmin", False)
                
                user_status = "OK"
                issue_list = []

                # 비활성화된 계정은 경고하지 않음.
                if is_enabled:
                    # 1. 비밀번호 불필요 (보안 취약)
                    if not pwd_required:
                        issue_list.append("비밀번호 불필요")
                        user_status = "WARNING"
                        
                    # 2. 관리자 권한
                    if is_admin and user_name != os.getlogin(): # 현재 사용자가 아닌 다른 관리자 계정
                        issue_list.append("불필요한 관리자 권한")
                        if user_status != "WARNING": # 이미 WARNING이면 덮어쓰지 않음
                            user_status = "WARNING"
                            
                    # 3. 비밀번호 만료일 (PasswordLastSet) 확인은 제외: Get-LocalUser가 만료일 자체를 제공하지 않음
                    
                    if issue_list:
                        warning_count += 1
                        problematic_accounts.append({
                            "name": user_name,
                            "issues": issue_list,
                            "is_enabled": is_enabled,
                            "is_admin": is_admin
                        })
                        log(f"  -> ⚠️ 발견: 계정 '{user_name}' - {', '.join(issue_list)}", "yellow")
                    else:
                        log(f"  -> ✅ 양호: 계정 '{user_name}' (활성)", "gray")

            self.progress(80)

            # 4. 최종 상태 업데이트
            if warning_count > 0:
                status = "WARNING"
                summary = f"⚠️ 총 {warning_count}개의 문제성 사용자 계정 설정 발견. (비밀번호/권한 정책 확인 필요)"
                log(f"\n⚠️ [결과] {summary}", "yellow")
            else:
                log("✅ 모든 활성 사용자 계정이 정책을 준수합니다.", "lime")
                
        except FileNotFoundError:
            # PowerShell 실행 파일(powershell.exe)을 찾을 수 없을 때
            log("❌ PowerShell 실행 파일을 찾을 수 없습니다. 사용자 계정 점검을 건너뜁니다.", "red")
            status = "ERROR"
            summary = "필수 모듈(PowerShell)을 찾을 수 없어 점검 실패."
        except Exception as e:
            # 기타 예상치 못한 오류
            log(f"❌ 사용자 계정 점검 중 치명적 오류 발생: {e}", "red")
            status = "ERROR"
            summary = f"치명적 오류 발생: {e}"
            
        self.progress(100)
        
        # 🚨 [필수] 최종 결과를 딕셔너리 형태로 반환
        return {"status": status, "summary": summary, "details": problematic_accounts}

    # PC Butler v106 호환성을 위해 기존 execute_plugin은 삭제하거나 비워둡니다.
    def execute_plugin(self, data=None):
        pass

    def plugin_stop(self):
        pass