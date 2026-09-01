from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: Winget 패키지 업그레이드 (WingetUpgrade) - 최종 상세화 버전
# - Winget 명령 실행 결과를 details에 상세히 기록합니다.
# ==============================================================================
from plugin_base import PCButlerPlugin
import subprocess
import os
import sys

# 콘솔 인코딩 문제 방지
# (subprocess 결과 디코딩을 위해 utf-8을 사용합니다.)
import io
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except:
    pass

class WingetUpgradePlugin(PCButlerPlugin):
    """
    Windows Package Manager(Winget)를 사용하여 모든 설치된 앱을 업그레이드합니다.
    """
    plugin_name = "Winget 패키지 업그레이드"
    description = "Winget을 사용하여 모든 설치된 앱을 일괄 업그레이드합니다. (관리자 권한 추천)"
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    # 🚨 [핵심 수정] run 메서드 통합 및 상세 로직 적용
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🔍 '{self.name}' 작업을 시작합니다. (Winget 실행)", "cyan")

        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            log(summary, "yellow")
            self.progress(100)
            return {"status": "WARNING", "summary": summary, "details": ""}
            
        self.progress(10)
        
        # winget upgrade --all 명령어 실행
        # --disable-interactivity를 추가하여 사용자 입력을 방지
        command = ['winget', 'upgrade', '--all', '--disable-interactivity']
        
        try:
            log("🚀 winget 업그레이드 명령 실행 중... (최대 10분 소요될 수 있음)", "yellow")
            
            # 🚨 [수정] stderr까지 캡처하여 전체 로그 확보
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='utf-8', # Winget의 최신 버전은 UTF-8 출력을 지원합니다.
                errors='ignore',
                shell=True,
                check=False,
                timeout=600 # 10분 대기
            )
            
            # stdout과 stderr을 합쳐서 최종 상세 로그로 사용
            output = result.stdout.strip()
            error_output = result.stderr.strip()
            full_log = (output + "\n" + error_output).strip()
            
            self.progress(80)
            
            # 2. 결과 분석 (핵심 문구로 판단)
            output_lower = full_log.lower()
            
            # 2-1. 관리자 권한 오류 감지
            if "관리자 권한" in output_lower or "access is denied" in output_lower or "uac" in output_lower or result.returncode == 1223:
                summary = "❌ Winget 업그레이드 실패: 관리자 권한이 필요합니다. 플러그인을 관리자 권한으로 실행해야 합니다."
                status = "ERROR"
                log(f"  -> ❌ 관리자 권한 부족 오류 감지.", "red")
            
            # 2-2. 업그레이드 없음
            elif "no packages are installed that can be upgraded" in output_lower or "업그레이드할 수 있는 설치된 패키지가 없습니다" in output_lower:
                summary = "✅ Winget: 업그레이드할 패키지가 없습니다. (최신 상태)"
                status = "SUCCESS"
                log(f"  -> ✅ 모든 패키지 최신 상태.", "lime")
                
            # 2-3. 업그레이드 성공 (일부만 확인)
            elif "successfully upgraded" in output_lower or "성공적으로 업그레이드했습니다" in output_lower:
                success_count = output_lower.count("successfully upgraded") + output_lower.count("성공적으로 업그레이드했습니다")
                summary = f"✅ Winget: **{success_count}개 이상**의 패키지를 성공적으로 업그레이드했습니다."
                status = "SUCCESS"
                log(f"  -> ✅ {success_count}개 이상 업그레이드 성공.", "lime")
                
            # 2-4. 기타 오류/경고 (결과 분석 실패 또는 경고)
            else:
                summary = "⚠️ Winget 업그레이드 중 문제 발생 또는 결과 분석 실패. (상세 로그 확인 필요)"
                status = "WARNING"
                log(f"  -> ⚠️ 업그레이드 완료 여부 불분명. 로그 확인.", "yellow")
            
            self.progress(100)
            
            # 🚨 [필수] 최종 결과를 details에 담아 반환
            return {"status": status, "summary": summary, "details": full_log}
            
        except FileNotFoundError:
            error_message = "❌ Winget 명령어를 찾을 수 없습니다. Winget이 설치되어 있지 않거나 PATH에 추가되지 않았습니다."
            log(error_message, "red")
            self.progress(100)
            return {"status": "ERROR", "summary": error_message, "details": ""}

        except subprocess.TimeoutExpired:
            error_message = "❌ Winget 업그레이드 시간 초과(10분). 네트워크 상태를 확인하거나 수동으로 실행하십시오."
            log(error_message, "red")
            self.progress(100)
            return {"status": "ERROR", "summary": error_message, "details": full_log}
            
        except Exception as e:
            error_message = f"❌ Winget 업그레이드 중 예상치 못한 오류 발생: {type(e).__name__} - {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "ERROR", "summary": error_message, "details": full_log}