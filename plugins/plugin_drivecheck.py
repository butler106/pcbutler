from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 장치 드라이버 상태 점검 (Drivercheck/Drivecheck) - 안정화 버전
# - 결과 반환 누락 및 명령어 실행/디코딩 오류 해결
# ==============================================================================
from plugin_base import PCButlerPlugin
import subprocess
import os
import sys
import time

class DriverCheckPlugin(PCButlerPlugin):
    """
    WMI/PowerShell을 사용하여 설치된 드라이버 목록과 상태를 점검합니다.
    """
    # 필수 속성
    plugin_name = "장치 드라이버 점검" # 기능명에 맞게 명시
    description = "설치된 드라이버 목록을 확인하고 오류 또는 누락된 드라이버를 점검합니다."

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        """플러그인의 메인 실행 로직"""
        
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs) 
        
        self.logger(f"🔍 '{self.name}' 작업을 시작합니다.", "cyan")

        # Windows 환경 확인
        if sys.platform != "win32":
            summary = "이 플러그인은 Windows 환경에서만 작동합니다."
            self.logger(f"  -> ℹ️ [정보] {summary}", "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}
        
        self.progress(10)
        
        # 최종 반환 값 초기화
        final_status = "success"
        final_summary = "장치 드라이버 상태 양호."
        error_lines = []
        
        try:
            self.logger("  -> 🧩 장치 드라이버 상태 점검 중... (WMI/PowerShell 사용)", "yellow")
            
            # Win32_PnPSignedDriver를 사용하여 장치 이름, 버전, 상태를 가져옵니다.
            cmd = 'powershell.exe -Command "Get-WmiObject Win32_PnPSignedDriver | Select-Object DeviceName,DriverVersion,DriverDate,Manufacturer,Status"'
            
            # 🚨 [수정 1]: check_output 대신 subprocess.run 사용 + 안정적인 디코딩
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                shell=True,
                check=False,
                timeout=30 # 30초 타임아웃
            )
            
            # 🚨 [수정 2]: 수동 디코딩 (CP949 > UTF-8)
            output = ""
            try:
                output = result.stdout.decode('cp949', errors='ignore').strip()
            except Exception:
                output = result.stdout.decode('utf-8', errors='ignore').strip()
            
            self.progress(50)
            
            # PowerShell 명령 실행 실패 시 처리
            if result.returncode != 0:
                final_status = "error"
                final_summary = f"❌ PowerShell 명령 실행 실패 (코드: {result.returncode}). 드라이버 정보를 가져올 수 없습니다."
                self.logger(final_summary, "red")
                self.progress(100)
                return {"status": final_status, "summary": final_summary, "details": output}

            # WMI 출력 파싱 (헤더 및 구분선 건너뛰기)
            lines = [line.strip() for line in output.split("\n") if line.strip()]
            
            # WMI 출력은 보통 3줄부터 실제 데이터 시작 (헤더, 구분선, 빈 줄/데이터)
            if len(lines) > 2:
                # 첫 2줄은 헤더/구분선이므로 제외
                driver_entries = lines[2:]
                self.logger(f"  -> ✅ 설치된 드라이버 수: {len(driver_entries)}개 확인.", "lime")
                
                # 'Status'가 'OK'가 아니거나, 'Error', 'Problem', 'Unknown' 같은 키워드를 포함하는 항목 검색
                error_lines = [
                    line for line in driver_entries 
                    if not line.strip().startswith("OK") 
                    and any(keyword in line for keyword in ["Error", "Problem", "Unknown", "Degraded"])
                ]
                
                if error_lines:
                    final_status = "warning"
                    final_summary = f"⚠️ {len(error_lines)}개의 장치 드라이버에서 문제/경고 상태가 감지되었습니다."
                    self.logger("\n  -> ⚠️ 오류 또는 문제 있는 드라이버 발견:", "yellow")
                    
                    for i, line in enumerate(error_lines[:5]): # 최대 5개 샘플 출력
                        self.logger(f"  -> 📌 {i+1}. {line}", "yellow")
                    if len(error_lines) > 5:
                        self.logger(f"  -> ... 외 {len(error_lines) - 5}개 항목이 더 있습니다.", "yellow")
                else:
                    self.logger("  -> ✅ 모든 드라이버 상태 양호 (오류/경고 항목 없음)", "lime")
            else:
                final_status = "warning"
                final_summary = "ℹ️ WMI 출력 형식이 예상과 다릅니다. (드라이버 목록을 가져오지 못함)"
                self.logger(f"  -> ⚠️ {final_summary}", "yellow")

        except Exception as e:
            final_status = "error"
            final_summary = f"❌ [치명적 오류] 드라이버 점검 실행 중 예상치 못한 오류 발생: {e}"
            self.logger(final_summary, "red")
            
        self.progress(100)
        
        # 🚨 [수정 3]: 최종 결과 딕셔너리 반환
        return {"status": final_status, "summary": final_summary, "details": "\n".join(error_lines) if error_lines else "No problematic drivers found."}