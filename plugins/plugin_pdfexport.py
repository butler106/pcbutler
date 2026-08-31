from typing import Dict, Any, Callable, Optional, Union, List
from plugin_base import PCButlerPlugin
import os
import json
import time
from fpdf import FPDF # PDF 생성을 위한 라이브러리

# PDF 클래스 정의 (fpdf 상속)
class PDF(FPDF):
    """PDF 보고서 생성을 위한 FPDF 확장 클래스"""

    # 🚨 FIX (2026-08-31): 기존 코드는 add_korean_font()가 폰트 등록에 실패해도
    # header/footer/chapter_* 메서드들이 여전히 'MalgunGothic'을 하드코딩해서 호출했다.
    # add_font()가 실패하면(파일을 못 찾으면) 'MalgunGothic'은 fpdf에 등록되지 않은 채로
    # 남아 있어서, 실제로 그 폰트를 쓰려는 순간(header() 등) 항상
    # "Undefined font: malgungothicB" 오류로 죽었다. 이제 실제로 폰트가 등록됐는지
    # (self.korean_font_loaded)를 추적해서, 실패 시 모든 메서드가 일관되게 Arial로
    # 대체되도록 수정했다.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.korean_font_loaded = False

    def _font_name(self):
        return 'MalgunGothic' if self.korean_font_loaded else 'Arial'

    def header(self):
        # 보고서 상단 헤더
        self.set_font(self._font_name(), 'B', 15)
        self.cell(0, 10, 'PC Butler 시스템 진단 보고서', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        # 보고서 하단 푸터
        self.set_y(-15)
        self.set_font(self._font_name(), 'I', 8)
        self.cell(0, 10, f'페이지 {self.page_no()}/{{nb}}', 0, 0, 'C')

    def chapter_title(self, title):
        # 챕터 제목 스타일
        self.set_font(self._font_name(), 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 6, title, 0, 1, 'L', 1)
        self.ln(2)

    def chapter_body(self, txt):
        # 챕터 본문 스타일
        self.set_font(self._font_name(), '', 10)
        self.multi_cell(0, 5, txt)
        self.ln()

    def add_korean_font(self):
        # 한글 폰트 추가 (FPDF는 기본적으로 한글을 지원하지 않아 폰트 파일이 필요함)
        # 🚨 FIX (2026-08-31): 기존 코드는 'malgun.ttf'라는 상대 파일명만 넘겼는데,
        # fpdf는 이를 작업 디렉터리 기준으로 찾으므로 실제로는 거의 항상 실패했다.
        # 실제 배포 대상이 Windows이므로 Windows 시스템 폰트 폴더(C:\Windows\Fonts)의
        # 맑은 고딕 파일을 우선 사용하도록 절대 경로 후보를 명시했다.
        windir = os.environ.get('WINDIR', r'C:\Windows')
        regular_candidates = [os.path.join(windir, 'Fonts', 'malgun.ttf'), 'malgun.ttf']
        bold_candidates = [os.path.join(windir, 'Fonts', 'malgunbd.ttf'), 'malgunbd.ttf']

        regular_path = next((p for p in regular_candidates if os.path.exists(p)), None)
        bold_path = next((p for p in bold_candidates if os.path.exists(p)), None)

        if not regular_path:
            # 폰트 파일을 찾지 못하면 등록을 시도하지 않고 Arial로 폴백한다
            # (등록되지 않은 폰트 이름을 나중에 set_font로 호출하면 fpdf가 예외를 던진다).
            self.korean_font_loaded = False
            return

        try:
            self.add_font('MalgunGothic', '', regular_path)
            self.add_font('MalgunGothic', 'B', bold_path or regular_path)
            self.add_font('MalgunGothic', 'I', regular_path)
            self.korean_font_loaded = True
        except Exception:
            # 폰트 파일은 찾았지만 등록 자체가 실패한 경우에도 동일하게 폴백
            self.korean_font_loaded = False


class PDFExport(PCButlerPlugin):
    plugin_name = "PDFExport"
    description = "최종 TXT 보고서를 PDF 파일로 변환합니다."

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        
        self.progress(10)

        # 🚨 CRITICAL FIX 1: REPORT_DIR_FINAL 경로 사용
        report_dir = self.settings.get('REPORT_DIR_FINAL')
        if not report_dir:
            return {
                "status": "error",
                "summary": "❌ 최종 보고서 경로 (REPORT_DIR_FINAL) 설정을 찾을 수 없습니다.",
                "execution_time": "0.00s"
            }

        # ReportMerge가 생성한 TXT 파일의 이름 구조
        txt_file_name = f"Analysis_Report_{self.analysis_id}.txt"
        txt_file_path = os.path.join(report_dir, txt_file_name)
        
        pdf_file_name = f"Analysis_Report_{self.analysis_id}.pdf"
        pdf_file_path = os.path.join(report_dir, pdf_file_name)

        self.progress(20)

        # 1. 입력 TXT 파일 존재 여부 확인
        if not os.path.exists(txt_file_path):
            return {
                "status": "error",
                "summary": f"❌ PDF로 변환할 입력 보고서 파일({txt_file_name})을 찾을 수 없습니다.",
                "execution_time": "0.00s"
            }
        
        self.progress(30)

        # 2. PDF 생성 로직
        try:
            pdf = PDF('P', 'mm', 'A4')
            pdf.add_korean_font() # 한글 폰트 설정
            pdf.alias_nb_pages()
            pdf.add_page()
            
            # TXT 파일 내용 읽기
            with open(txt_file_path, 'r', encoding='utf-8') as f:
                report_content = f.read()

            # 전체 내용을 하나의 텍스트 블록으로 PDF에 추가
            pdf.chapter_title("최종 진단 및 요약 보고서")
            pdf.chapter_body(report_content)
            
            # PDF 저장
            pdf.output(pdf_file_path, 'F')
            
            self.logger(f"✅ PDF 보고서 생성 완료: {pdf_file_path}", 'green')
            
            final_result = {
                "status": "success",
                "summary": f"✅ PDF 보고서가 {os.path.basename(pdf_file_path)} 경로에 성공적으로 생성되었습니다.",
                "details": {"file_path": pdf_file_path},
            }
            
            self.progress(80)

        except Exception as e:
            self.logger(f"❌ PDF 생성 중 오류 발생: {e}", 'red')
            final_result = {
                "status": "error",
                "summary": f"❌ PDF 생성 실패: {e}",
            }
        
        # execution_time은 main.py에서 채워지므로 여기서는 딕셔너리에 추가만 합니다.
        final_result['execution_time'] = kwargs.get('execution_time', "N/A")

        self.progress(100)
        return final_result
