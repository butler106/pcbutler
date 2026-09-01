from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# plugin_graphgen.py
# 플러그인: 보고서 그래프 시각화 (v1.1 - NoneType 오류 수정)
import os
import matplotlib.pyplot as plt
import subprocess
import sys
import io

# 콘솔 인코딩 문제 방지
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except:
    pass

class GraphGenPlugin(PCButlerPlugin):
    plugin_name = "보고서 그래프 생성"
    description = "디스크, RAM, CPU 사용률을 시각화하여 보고서에 포함합니다."

    # 🚨 [핵심 수정] execute_plugin 대신 run 메서드를 사용하고, 표준 인자를 받도록 변경
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        # 표준 run 메서드 시작
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🔍 '{self.plugin_name}' 작업을 시작합니다.", "cyan")
        self.progress(10)

        # BASE_DIR을 settings에서 가져와 보고서 경로를 구성합니다.
        base_path = self.settings.get("BASE_DIR", os.path.dirname(os.path.abspath(__file__)))
        report_dir = os.path.join(base_path, "reports")
        
        # main.py에서 전달받을 데이터를 시뮬레이션 (실제로는 data=None이므로 settings 또는 data를 활용해야 함)
        # 플러그인 테스트를 위해 임시 데이터를 사용합니다.
        # 실제 환경에서는 다른 플러그인의 결과를 status_latest.json 등에서 읽어야 합니다.
        try:
            # 1. 시각화할 데이터 준비 (예시 데이터)
            # 실제 플러그인 연동 시, self.settings.get('진단결과') 등을 사용하여 실제 데이터를 가져와야 합니다.
            usage = {
                "CPU 사용률": self.settings.get("cpu_usage", 12.5), 
                "RAM 사용률": self.settings.get("ram_usage", 42.3), 
                "디스크 사용률": self.settings.get("disk_usage", 88.1)
            }
            
            log(f"📊 그래프 생성 데이터: {usage}", "white")

            labels = list(usage.keys())
            values = list(usage.values())

            # 2. 그래프 생성
            plt.figure(figsize=(8, 5))
            
            # 색상 설정: 초록(CPU), 파랑(RAM), 빨강(Disk)
            colors = ["#4caf50", "#2196f3", "#f44336"]
            
            bars = plt.bar(labels, values, color=colors, width=0.6)
            plt.ylim(0, 100)
            
            # 폰트 깨짐 방지를 위해 Matplotlib 설정
            # (시스템에 Nanum Gothic이 설치되어 있어야 합니다)
            try:
                plt.rcParams['font.family'] = 'NanumGothic'
            except:
                log("⚠️ Matplotlib 폰트 설정 실패: 나눔고딕이 설치되어 있는지 확인하십시오.", "yellow")

            plt.title("📊 시스템 리소스 사용률", fontsize=14, fontweight='bold')
            plt.ylabel("사용률 (%)", fontsize=12)
            
            # 막대 위에 값 표시
            for bar in bars:
                yval = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2.0, yval + 2, f"{yval:.1f}%", ha='center', va='bottom', fontsize=10)

            # 3. 파일 저장
            os.makedirs(report_dir, exist_ok=True)
            graph_path = os.path.join(report_dir, "resource_graph_latest.png")
            
            plt.savefig(graph_path)
            plt.close() # 메모리 해제
            self.progress(80)

            summary = f"✅ 그래프 이미지 생성 완료 → {graph_path}"
            log(summary, "lime")
            self.progress(100)
            
            # 🚨 [필수] Success 반환
            return {"status": "success", "summary": summary}

        except ImportError:
            error_message = "❌ 그래프 생성 실패: 'matplotlib' 라이브러리가 설치되어 있지 않습니다. (pip install matplotlib)"
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}
            
        except Exception as e:
            error_message = f"❌ 그래프 생성 실패: {e}"
            log(error_message, "red")
            self.progress(100)
            
            # 🚨 [필수] Error 반환
            return {"status": "error", "summary": error_message}

    # 🚨 [수정] plugin_stop은 정리 작업만 수행하도록 변경 (불필요한 return 제거)
    def plugin_stop(self):
        self.logger("🛑 그래프 생성 플러그인 종료됨", "gray")
        pass