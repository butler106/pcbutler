from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 이벤트 로그 점검 (Eventlogcheck) - 안정화 버전
# - Get-WinEvent JSON 출력의 디코딩 및 파싱 안정화
# ==============================================================================
from plugin_base import PCButlerPlugin
import subprocess
import os
import json
from datetime import datetime, timedelta
import sys # sys.platform 사용을 위해 추가

class EventLogPlugin(PCButlerPlugin):
    """
    최근 7일간의 시스템 및 애플리케이션 이벤트 로그에서 오류 및 경고 개수를 확인합니다.
    """
    plugin_name = "Eventlogcheck"
    description = "최근 이벤트 로그에서 시스템 오류 및 경고 횟수를 집계합니다."
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        """플러그인의 메인 실행 로직"""
        
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        
        self.logger(f"🔍 '{self.name}' 작업을 시작합니다. (최근 7일 기준)", "cyan")

        if sys.platform != "win32":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            self.logger(summary, "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}
            
        self.progress(10)
        
        try:
            # 7일 전 시간 계산 (ISO 8601 포맷)
            time_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
            
            # PowerShell 명령어: 최근 7일간의 Critical, Error, Warning 이벤트를 개수별로 집계하여 JSON으로 출력
            # LogName: System, Application (가장 중요한 두 로그)
            # Group-Object -Property LevelDisplayName: 레벨별로 그룹화
            cmd = f"""powershell.exe -Command "Get-WinEvent -FilterHashTable @{{LogName='System','Application'; StartTime='{time_start}'}} | Group-Object -Property LevelDisplayName | Select-Object Name, Count | ConvertTo-Json" """
            
            self.logger("  -> ⏳ 이벤트 로그 집계 중... (최대 1분 소요)", "yellow")
            
            # 🚨 [수정 1]: text=True 및 encoding 제거, 바이트로 수신하여 I/O Deadlock 방지
            result = subprocess.run(
                cmd,
                capture_output=True,
                shell=True,
                check=False,
                timeout=60 # 60초 타임아웃
            )
            
            # 🚨 [수정 2]: 수동 디코딩 (CP949 우선)
            output = ""
            try:
                output = result.stdout.decode('cp949', errors='ignore').strip()
            except Exception:
                output = result.stdout.decode('utf-8', errors='ignore').strip()
                
            self.progress(50)
            
            # PowerShell 명령 실행 실패 시 처리
            if result.returncode != 0:
                summary = f"❌ PowerShell 명령 실행 실패 (코드: {result.returncode}). 이벤트 로그를 가져올 수 없습니다."
                self.logger(summary, "red")
                self.progress(100)
                return {"status": "error", "summary": summary, "details": output}
                
            # 🚨 [수정 3]: JSON 파싱 안정화
            try:
                # 결과는 JSON 배열 형태일 가능성이 높습니다.
                log_groups = json.loads(output)
            except json.JSONDecodeError as jde:
                summary = f"❌ JSON 파싱 오류 발생. 이벤트 로그 출력이 올바르지 않습니다. ({jde})"
                self.logger(summary, "red")
                self.logger(f"  -> ℹ️ 원본 출력: {output[:300]}...", "gray")
                self.progress(100)
                return {"status": "error", "summary": summary, "details": output}

            self.progress(70)

            # 이벤트 레벨별 카운트 집계
            log_counts = {
                'Critical': 0,
                'Error': 0,
                'Warning': 0,
                'Total': 0
            }
            
            # 레벨 이름은 OS 언어 설정에 따라 달라질 수 있으므로 유연하게 처리
            for item in log_groups:
                name = item.get('Name', '').lower()
                count = item.get('Count', 0)
                
                if 'critical' in name or '심각' in name:
                    log_counts['Critical'] += count
                elif 'error' in name or '오류' in name:
                    log_counts['Error'] += count
                elif 'warning' in name or '경고' in name:
                    log_counts['Warning'] += count
                log_counts['Total'] += count
            
            self.progress(90)
            
            error_count = log_counts['Error'] + log_counts['Critical']
            warning_count = log_counts['Warning']
            total_count = log_counts['Total']
            
            self.logger(f"\n  -> 🔴 오류 (Critical + Error) 개수: {error_count}개", "red" if error_count > 10 else "lime")
            self.logger(f"  -> ⚠️ 경고 (Warning) 개수: {warning_count}개", "yellow" if warning_count > 30 else "lime")
            
            # 최종 상태 판별 로직 (기준 유지)
            if error_count > 10:
                summary = f"❌ 최근 7일간 오류 이벤트가 {error_count}개로 매우 많습니다. (심각)"
                status = "error"
            elif error_count > 3 or warning_count > 30:
                summary = f"⚠️ 최근 7일간 오류 {error_count}개, 경고 {warning_count}개 발생. (주의)"
                status = "warning"
            else:
                summary = f"✅ 최근 7일간 오류 {error_count}개 발생. 이벤트 로그 상태 양호."
                status = "success"
                
            self.progress(100)
            
            return {"status": status, "summary": summary, "details": log_groups}

        except Exception as e:
            error_message = f"❌ [치명적 오류] 이벤트 로그 점검 플러그인 실행 실패: {e}"
            self.logger(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}