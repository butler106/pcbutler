from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# ==============================================================================
# 🐍 PC Butler Plugin: 로그인 기록 분석 (LoginCheck) - 최종 안정화 및 출력 개선 버전
# [수정 사항] 모든 기록을 출력하지 않고, 의심 활동(Administrator, RemoteInteractive)만 요약하여 출력
# ==============================================================================
import subprocess
import os 
from datetime import datetime
import json
import re # 정규식 모듈 추가

class LoginCheckPlugin(PCButlerPlugin):
    plugin_name = "로그인 기록 분석"
    description = "최근 로그인 이력을 확인하고 관리자 또는 외부 접속 흔적을 점검합니다."
    version = "1.2"

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🔍 '{self.plugin_name}' 작업을 시작합니다. (최근 7일 로그인 기록 분석)", "cyan")
        self.progress(10)

        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            log(summary, "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}
        
        # 기본 상태 및 요약 설정
        final_status = "success"
        final_summary = "✅ 로그인 기록 분석 완료. 특이 사항 없음."
        suspect_logs = []

        try:
            # 최근 7일간의 윈도우 보안 이벤트 로그 (ID 4624: 로그인 성공)를 PowerShell로 조회
            # -FilterXPath를 사용하여 7일 이내의 로그만 필터링합니다.
            start_date = (datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
            
            # 🚨 최종 수정: LogFormat.logtime을 사용하여 로그 시간 및 주요 정보만 추출
            powershell_command = (
                f"Get-WinEvent -LogName Security -FilterXPath \"*[System[(EventID=4624) and TimeCreated[timediff(@SystemTime) <= 604800000]]]*\" | "
                f"Select-Object -Property TimeCreated, @{{Name='TargetUserName';Expression={{$_.Properties[5].Value}}}}, @{{Name='LogonType';Expression={{$_.Properties[8].Value}}}} | "
                f"Format-List | Out-String"
            )
            
            self.progress(50, message="로그인 이벤트 로그 조회 중...")

            result = subprocess.run(
                ["powershell", "-Command", powershell_command],
                capture_output=True,
                text=True,
                check=True, # 오류 발생 시 예외 발생
                timeout=60,
                encoding='utf-8',
                errors='ignore'
            )

            output = result.stdout.strip()
            lines = [line.strip() for line in output.split('\n') if line.strip()]

            # ----------------------------------------------------------------------
            # 2. 결과 분석 및 요약 (로그 상세 출력 제거)
            # ----------------------------------------------------------------------
            if lines:
                log(f"📌 총 {len(lines)}건의 로그인 기록 확인.", "lime")
                
                # 로그 타입 매핑 (Windows 이벤트 로그 표준)
                logon_type_map = {
                    "2": "대화형(Interactive) - 로컬 로그인",
                    "3": "네트워크(Network) - 원격/네트워크 공유 접속",
                    "4": "일괄(Batch) - 예약 작업",
                    "5": "서비스(Service) - 백그라운드 서비스",
                    "7": "잠금 해제(Unlock)",
                    "8": "네트워크 클리어텍스트(NetworkCleartext)",
                    "9": "새로운 자격 증명(NewCredentials)",
                    "10": "원격 대화형(RemoteInteractive) - RDP/원격 데스크톱",
                    "11": "캐시된 대화형(CachedInteractive)"
                }
                
                for line in lines:
                    # TargetUserName, LogonType 값만 추출
                    match_user = re.search(r'TargetUserName\s*:\s*(.*)', line)
                    match_type = re.search(r'LogonType\s*:\s*(.*)', line)
                    
                    username = match_user.group(1).strip() if match_user else '알 수 없음'
                    logon_type_id = match_type.group(1).strip() if match_type else '알 수 없음'
                    
                    logon_type = logon_type_map.get(logon_type_id, f"LogonType {logon_type_id}")
                    
                    # 🚨 의심 활동 검사 (관리자 또는 원격 접속 흔적)
                    if "Administrator" in username or logon_type_id == "10":
                        
                        log(f"⚠️ 의심 활동 감지: 사용자: {username}, 유형: {logon_type}", "yellow")
                        
                        suspect_logs.append({
                            "type": "suspect",
                            "username": username,
                            "logon_type": logon_type,
                            "raw_line": line
                        })
                        
                        final_status = "warning"
                
                # 최종 요약 설정
                if suspect_logs:
                    count = len(suspect_logs)
                    final_summary = f"⚠️ 최근 로그인 기록에서 **총 {count}건**의 관리자 또는 원격 접속 의심 흔적이 감지되었습니다."
                
            else:
                log("ℹ️ 로그인 기록 없음 또는 보안 로그 확인 불가.", "gray")
                final_summary = "로그인 기록을 찾을 수 없거나 로그 조회 권한이 부족합니다."
                final_status = "info"

            self.progress(100)
            
            return {"status": final_status, "summary": final_summary, "details": {"suspect_logs": suspect_logs}}
            
        except subprocess.CalledProcessError as e:
            error_message = f"❌ PowerShell 명령 실행 실패 (코드: {e.returncode}) - 관리자 권한을 확인하십시오."
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}
            
        except subprocess.TimeoutExpired:
            error_message = "❌ 로그인 기록 분석 명령 실행 시간 초과 (TimeoutExpired)."
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}

        except Exception as e:
            error_message = f"❌ 로그인 기록 분석 중 치명적 오류 발생: {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "FATAL_ERROR", "summary": error_message}

# --- 독립 실행을 위한 테스트 블록 --
if __name__ == "__main__":
    print("플러그인 단독 실행 테스트는 생략합니다.")