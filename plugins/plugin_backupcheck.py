from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# plugin_backupcheck.py
# 플러그인: 백업 유효성 점검 (v1.2 - run 메서드 및 return 값 오류 수정)

# -*- coding: utf-8 -*-
import sys
import io
import os
import json
from datetime import datetime
import time

# 콘솔 인코딩 문제 방지 (필요하다면 추가)
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding = 'utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding = 'utf-8')
except:
    pass # detach가 불가능한 환경일 경우 무시

class BackupCheckPlugin(PCButlerPlugin):
    plugin_name = "백업 유효성 점검"
    description = "설정된 백업 폴더 내 모든 파일의 수정 날짜를 확인하여 백업 상태를 진단합니다."

    # 설정 파일에 사용될 키 이름들을 상수로 정의
    CONFIG_FILE = "user_config.json"
    ENABLED_KEY = "backup_check_enabled"
    PATH_KEY = "backup_check_path"
    DAYS_KEY = "backup_warning_days"

    # 🚨 [핵심 수정] run 메서드는 유지하고, return 값 누락 문제 해결
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs) 
        log = self.logger # self.logger 사용
        
        log(f"🔎 '{self.plugin_name}' 작업을 시작합니다.", "cyan")

        # BASE_DIR을 settings에서 가져와 config 경로를 구성합니다.
        # main.py에서 settings에 BASE_DIR을 전달한다고 가정
        base_path = self.settings.get("BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(base_path, "config", self.CONFIG_FILE)

        # 1. user_config.json에서 설정값 읽기
        backup_path = None
        warning_days = 7
        is_enabled = True
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    is_enabled = config.get(self.ENABLED_KEY, True)
                    backup_path = config.get(self.PATH_KEY)
                    warning_days = config.get(self.DAYS_KEY, 7)
            except Exception as e:
                log(f"  -> ⚠️ [경고] 설정 파일 로드 실패: {e}", "yellow")

        if not is_enabled:
            summary = "설정에서 백업 유효성 점검이 비활성화되어 있습니다."
            log(f"  -> ℹ️ [정보] {summary}", "gray")
            # 🚨 [필수] return 값 추가
            return {"status": "info", "summary": summary}

        if not backup_path or not os.path.isdir(backup_path):
            summary = "백업 경로(backup_check_path)가 설정되지 않았거나 유효하지 않습니다."
            log(f"  -> ⚠️ [경고] {summary}", "yellow")
            # 🚨 [필수] return 값 추가
            return {"status": "warning", "summary": summary}

        # 2. 백업 경로 및 기준값 출력
        log(f"  -> ⚙️ [설정] 백업 경로: {backup_path}", "white")
        log(f"  -> ⚙️ [설정] 최신 백업 기준: {warning_days}일", "white")

        warning_threshold_seconds = warning_days * 86400 # 일(day)을 초(second)로 변환
        
        all_backup_files = []
        
        # 하위 폴더까지 재귀적으로 검색
        for root, _, files in os.walk(backup_path):
            for file in files:
                all_backup_files.append(os.path.join(root, file))

        if not all_backup_files:
            summary = "백업 폴더 내에서 파일을 찾을 수 없습니다. (폴더 비어 있음)"
            log(f"  -> ⚠️ [경고] {summary}", "yellow")
            # 🚨 [필수] return 값 추가
            return {"status": "warning", "summary": summary}

        # 3. 모든 백업 파일의 수정 날짜 확인 및 진단
        old_files = []
        
        for fpath in all_backup_files:
            try:
                mod_timestamp = os.path.getmtime(fpath)
                age_seconds = time.time() - mod_timestamp
                
                if age_seconds > warning_threshold_seconds:
                    old_files.append(fpath)
                    
            except Exception as e:
                log(f"  -> ❌ [오류] 파일 시간 정보 읽기 실패 ({fpath}): {e}", "red")
                # 파일 읽기 실패는 전체 오류로 간주하고 즉시 반환
                error_message = f"백업 파일 시간 정보 읽기 중 오류 발생: {e}"
                return {"status": "error", "summary": error_message}

        # 4. 결과 출력
        total_files = len(all_backup_files)
        old_file_count = len(old_files)
        
        log(f"\n  📊 총 백업 파일 수: {total_files}개", "white")
        log(f"  📊 {warning_days}일 이상 경과된 파일 수: {old_file_count}개", "white")

        if old_file_count == 0:
            summary = "모든 백업 파일이 최신 기준을 만족합니다."
            log(f"  -> ✅ [양호] {summary}", "lime")
            final_status = "success"
        elif old_file_count < total_files / 2:
            summary = f"오래된 파일({old_file_count}개)이 일부 있지만, 심각한 수준은 아닙니다."
            log(f"  -> ℹ️ [정보] {summary}", "gray")
            log(f"     (가장 오래된 파일 샘플: {old_files[0] if old_files else 'N/A'})", "gray")
            final_status = "info"
        else:
            summary = f"백업 파일({old_file_count}개)의 절반 이상이 기준 기간({warning_days}일)을 초과했습니다. 주기적인 백업 점검을 권장합니다."
            log(f"  -> ❗ [경고] {summary}", "yellow")
            if old_files:
                log("      (가장 오래된 파일 샘플):", "yellow")
                for i, f in enumerate(old_files[:3]):
                    log(f"      - {i+1}. {f}", "yellow")
            final_status = "warning"
            
        # 🚨 [필수] 최종 결과 반환
        return {"status": final_status, "summary": summary}
                
    # 🚨 [수정] plugin_stop은 정리 작업만 수행하도록 변경 (return 문 제거)
    def plugin_stop(self):
        self.logger("🛑 백업 유효성 점검 플러그인 종료됨", "gray")
        pass