import streamlit as st
from openai import OpenAI
import pandas as pd
import json
import os
import base64
import io
from datetime import datetime
from dotenv import load_dotenv
import locale
import zipfile
import glob

# 한국 로케일 설정 (선택사항)
try:
    locale.setlocale(locale.LC_TIME, 'ko_KR.UTF-8')  
except:
    pass  # 로케일 설정 실패해도 계속 진행

# .env 파일 로드
load_dotenv()

# 참조 파일이 저장된 기본 폴더 경로
REFERENCE_FILES_FOLDER = "reference_files"
# 기본 참조 파일명
DEFAULT_REFERENCE_FILE = "참조-SKONS-access위험성평가양식.xlsx"

# OpenAI API 키 읽기 함수 (기존 코드 재사용)
def load_openai_api_key() -> str:
    """환경변수에서 OpenAI API 키를 읽어옵니다."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경변수가 설정되어 있지 않습니다.")
    return api_key

# OpenAI 클라이언트 초기화 (기존 코드 재사용)
try:
    api_key = load_openai_api_key()
    client = OpenAI(api_key=api_key)
except Exception as e:
    st.error(str(e))
    client = None

def load_file_content(file_path: str) -> str:
    """
    파일 경로에서 파일을 읽어서 텍스트로 변환
    """
    try:
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.xlsx':
            # Excel 파일 처리
            df = pd.read_excel(file_path)
            if df.empty:
                return None
            return df.to_string(index=False)
                
        elif file_extension == '.csv':
            # CSV 파일 처리
            try:
                df = pd.read_csv(file_path, encoding='utf-8')
                if df.empty:
                    return None
                return df.to_string(index=False)
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding='cp949')
                if df.empty:
                    return None
                return df.to_string(index=False)
                
        elif file_extension == '.txt':
            # 텍스트 파일 처리
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if not content.strip():
                        return None
                    return content
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='cp949') as f:
                    content = f.read()
                    if not content.strip():
                        return None
                    return content
        else:
            return None
            
    except Exception as e:
        st.error(f"파일 '{file_path}' 읽기 중 오류: {str(e)}")
        return None

def load_default_reference_file() -> dict:
    """
    기본 지정된 참조 파일을 자동으로 로드하는 함수
    """
    reference_file = {}
    
    # 폴더가 존재하지 않으면 생성
    if not os.path.exists(REFERENCE_FILES_FOLDER):
        os.makedirs(REFERENCE_FILES_FOLDER)
    
    # 기본 참조 파일 경로
    file_path = os.path.join(REFERENCE_FILES_FOLDER, DEFAULT_REFERENCE_FILE)
    
    if os.path.exists(file_path):
        try:
            content = load_file_content(file_path)
            if content:
                reference_file[DEFAULT_REFERENCE_FILE] = {
                    'content': content,
                    'path': file_path,
                    'size': os.path.getsize(file_path),
                    'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
                }
                return reference_file
        except Exception as e:
            st.error(f"기본 참조 파일 '{DEFAULT_REFERENCE_FILE}' 로딩 중 오류: {str(e)}")
    else:
        st.warning(f"⚠️ 기본 참조 파일 '{DEFAULT_REFERENCE_FILE}'을 찾을 수 없습니다.")
        st.info(f"📁 파일을 `{REFERENCE_FILES_FOLDER}/` 폴더에 넣어주세요.")
    
    return reference_file
    """
    지정된 폴더에서 참조 파일들을 자동으로 로드하는 함수
    """
    reference_files = {}
    
    # 폴더가 존재하지 않으면 생성
    if not os.path.exists(REFERENCE_FILES_FOLDER):
        os.makedirs(REFERENCE_FILES_FOLDER)
        st.warning(f"⚠️ '{REFERENCE_FILES_FOLDER}' 폴더가 생성되었습니다. 이 폴더에 참조 파일들을 넣어주세요.")
        return reference_files
    
    # 지원하는 파일 확장자들
    supported_extensions = ['*.xlsx', '*.csv', '*.txt']
    
    for extension in supported_extensions:
        files = glob.glob(os.path.join(REFERENCE_FILES_FOLDER, extension))
        for file_path in files:
            try:
                file_name = os.path.basename(file_path)
                content = load_file_content(file_path)
                if content:
                    reference_files[file_name] = {
                        'content': content,
                        'path': file_path,
                        'size': os.path.getsize(file_path),
                        'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
                    }
            except Exception as e:
                st.warning(f"파일 '{file_name}' 로딩 중 오류: {str(e)}")
                continue
    
    return reference_files

def load_reference_files_from_folder() -> dict:
    """
    지정된 폴더에서 참조 파일들을 자동으로 로드하는 함수 (기본 파일 우선)
    """
    reference_files = {}
    
    # 먼저 기본 참조 파일을 로드
    default_file = load_default_reference_file()
    if default_file:
        reference_files.update(default_file)
        return reference_files  # 기본 파일만 사용
    
    # 기본 파일이 없으면 폴더의 다른 파일들을 스캔
    if not os.path.exists(REFERENCE_FILES_FOLDER):
        os.makedirs(REFERENCE_FILES_FOLDER)
        st.warning(f"⚠️ '{REFERENCE_FILES_FOLDER}' 폴더가 생성되었습니다. 기본 참조 파일 '{DEFAULT_REFERENCE_FILE}'을 넣어주세요.")
        return reference_files
    
    # 지원하는 파일 확장자들
    supported_extensions = ['*.xlsx', '*.csv', '*.txt']
    
    for extension in supported_extensions:
        files = glob.glob(os.path.join(REFERENCE_FILES_FOLDER, extension))
        for file_path in files:
            try:
                file_name = os.path.basename(file_path)
                content = load_file_content(file_path)
                if content:
                    reference_files[file_name] = {
                        'content': content,
                        'path': file_path,
                        'size': os.path.getsize(file_path),
                        'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
                    }
            except Exception as e:
                st.warning(f"파일 '{file_name}' 로딩 중 오류: {str(e)}")
                continue
    
    return reference_files

def parse_analysis_sections(analysis_text: str) -> dict:
    """
    GPT 분석 결과를 섹션으로 구분하여 파싱하는 함수 (기존 코드 수정)
    """
    sections = {
        "work_analysis": "",           # 작업 내용 분석
        "risk_table": "",             # 위험성 평가 표
        "additional_safety": "",      # 추가 안전 조치
        "safety_checklist": ""        # 작업 전 체크리스트
    }
    
    lines = analysis_text.split('\n')
    current_section = None
    current_content = []
    section_started = False
    
    for line in lines:
        line_stripped = line.strip()

        # 섹션 시작을 감지
        if "작업 내용 분석" in line_stripped:
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = "work_analysis"
            current_content = []
            section_started = True
            continue

        elif "위험성 평가 표" in line_stripped or "위험요인과 감소대책" in line_stripped:
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = "risk_table"
            current_content = []
            section_started = True
            continue

        elif "추가 안전 조치" in line_stripped:
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = "additional_safety"
            current_content = []
            section_started = True
            continue

        elif "작업 전 체크리스트" in line_stripped:
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = "safety_checklist"
            current_content = []
            section_started = True
            continue

        # 본문 내용 수집
        if current_section and section_started:
            current_content.append(line)

    # 마지막 섹션 저장
    if current_section and current_content:
        sections[current_section] = '\n'.join(current_content).strip()

    return sections

def create_section_files(sections: dict, timestamp: str, work_description: str) -> dict:
    """
    각 섹션을 개별 파일로 생성하는 함수 (기존 코드 수정)
    """
    files = {}

    # 작업 내용 분석
    if sections["work_analysis"]:
        files["work_analysis"] = f"""# 작업 내용 분석

작업 설명: {work_description}
생성 시간: {timestamp}

{sections["work_analysis"]}
"""
        
    # 위험성 평가 표
    if sections["risk_table"]:
        files["risk_table"] = f"""# 위험성 평가 표

작업 설명: {work_description}
생성 시간: {timestamp}

{sections["risk_table"]}
"""

    # 추가 안전 조치
    if sections["additional_safety"]:
        files["additional_safety"] = f"""# 추가 안전 조치

작업 설명: {work_description}
생성 시간: {timestamp}

{sections["additional_safety"]}
"""

    # 작업 전 체크리스트
    if sections["safety_checklist"]:
        files["safety_checklist"] = f"""# 작업 전 체크리스트

작업 설명: {work_description}
생성 시간: {timestamp}

{sections["safety_checklist"]}
"""

    return files

def parse_risk_table_from_markdown(markdown_text: str) -> pd.DataFrame:
    """
    마크다운 텍스트에서 위험성 평가 표를 추출하여 DataFrame으로 변환
    """
    lines = markdown_text.split('\n')
    risk_data = []
    
    # 위험성 평가 표 섹션 찾기
    in_risk_table = False
    for line in lines:
        line = line.strip()
        
        # 표 시작 감지
        if "위험요인과 감소대책" in line or ("예상되는 위험요인" in line and "감소대책" in line):
            in_risk_table = True
            continue
        
        # 다음 섹션 시작 시 표 종료
        if in_risk_table and (line.startswith("## ") and "위험" not in line and "표" not in line):
            break
            
        # 표 데이터 파싱 (마크다운 표 형식)
        if in_risk_table and "|" in line and not line.startswith("|---"):
            parts = [x.strip() for x in line.split('|')]
            parts = [part for part in parts if part]  # 빈 문자열 제거
            
            # 헤더 건너뛰기 (순번, 작업 내용 등이 포함된 행)
            if len(parts) >= 7 and parts[0] not in ["순번", ""]:
                try:
                    # 첫 번째 컬럼이 숫자인지 확인 (실제 데이터 행)
                    int(parts[0])
                    risk_data.append(parts[:8])  # 8개 컬럼까지만
                except ValueError:
                    continue
    
    if risk_data:
        columns = ["순번", "작업 내용", "작업등급", "재해유형", "세부 위험요인", "위험등급-개선전", "위험성 감소대책", "위험등급-개선후"]
        # 데이터 길이에 맞춰 컬럼 조정
        max_cols = max(len(row) for row in risk_data) if risk_data else 8
        if max_cols < 8:
            columns = columns[:max_cols]
        
        # 모든 행의 길이를 동일하게 맞춤
        normalized_data = []
        for row in risk_data:
            if len(row) < len(columns):
                row.extend([''] * (len(columns) - len(row)))
            elif len(row) > len(columns):
                row = row[:len(columns)]
            normalized_data.append(row)
        
        return pd.DataFrame(normalized_data, columns=columns)
    else:
        # 기본 빈 DataFrame 반환
        columns = ["순번", "작업 내용", "작업등급", "재해유형", "세부 위험요인", "위험등급-개선전", "위험성 감소대책", "위험등급-개선후"]
        return pd.DataFrame(columns=columns)

def analyze_work_risk(work_description: str, selected_references: list) -> dict:
    """
    작업 내용을 기반으로 위험성 분석을 수행하는 함수
    """
    if client is None:
        raise Exception("OpenAI 클라이언트가 초기화되지 않았습니다.")
    
    # 선택된 참조 파일들의 내용 결합
    combined_reference_content = ""
    for ref_name in selected_references:
        if ref_name in st.session_state['reference_files']:
            combined_reference_content += f"\n\n=== {ref_name} ===\n"
            combined_reference_content += st.session_state['reference_files'][ref_name]['content']
    
    # 위험성 평가를 위한 프롬프트
    prompt = f"""
너는 안전보건 담당자야. 현장의 작업자에게 작업전 위험성 평가를 가이드하는 업무를 담당하고 있어.

첨부의 참조자료는 각 작업에서 발생할 수 있는 유해, 위험요인들과 그에 대한 개선방안이 정리되어 있어.

내가 특정 작업에 대해서 말하면, 위험요인은 참조자료를 참고해서 최대한 자세히 답변해줘.

**작업 내용**: {work_description}

**참조자료**:
{combined_reference_content}

**답변 형식**:

## 작업 내용 분석
[작업의 특성, 주요 위험 포인트, 작업 환경 등을 분석]

## 오늘 작업에서 예상되는 위험요인과 감소대책은 아래와 같습니다. 확인해주세요.

| 순번 | 작업 내용 | 작업등급 | 재해유형 | 세부 위험요인 | 위험등급-개선전 | 위험성 감소대책 | 위험등급-개선후 |
|------|-----------|----------|----------|---------------|----------------|----------------|----------------|
| 1 | [구체적 작업] | [S등급~C1] | [재해유형] | [세부 위험요인] | [C1-C4] | [구체적 대책] | [C1-C4] |
[참조자료를 바탕으로 해당 작업과 관련된 모든 위험요인을 나열]

## 추가 안전 조치
[작업 특성에 맞는 추가적인 안전 조치사항]

## 작업 전 체크리스트
[작업 시작 전 반드시 확인해야 할 사항들]

**중요사항**:
- 참조자료의 내용을 최대한 활용하여 해당 작업과 관련된 모든 위험요인을 식별
- "작업 내용"은 작업자가 입력한 내용을 분석하고 확인한 내용 중 참조문서에 있는 작업 내용과 가장 유사한 작업 내용을 넣고 모는 순번의 위험성에 동일하게 넣어줘
- 위험등급은 C1(낮음), C2(보통), C3(높음), C4(매우높음)으로 표시
- 작업등급은 S(특별관리), C4, C3, C2, C1로 구분
- 실무에서 바로 활용 가능한 구체적이고 실용적인 대책 제시
- 모든 내용은 한국어로 작성
"""
    
    # OpenAI API 호출
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=3000
    )
    
    # GPT의 분석 결과를 가져오기
    analysis_result = response.choices[0].message.content
    
    # 결과를 구조화된 형태로 파싱
    return {
        "work_description": work_description,
        "full_report": analysis_result,
        "sections": parse_analysis_sections(analysis_result),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "used_references": selected_references
    }

# Streamlit App UI
st.title("🛠️ 작업 위험성 평가 가이드")

# 세션 상태 초기화
if 'reference_files' not in st.session_state:
    st.session_state['reference_files'] = {}
if 'reference_loaded' not in st.session_state:
    st.session_state['reference_loaded'] = False
if 'analysis_result' not in st.session_state:
    st.session_state['analysis_result'] = None

# # OpenAI API 키 상태 확인
# if client is None:
#     st.warning("⚠️ OpenAI API 키가 설정되지 않았습니다. 설정을 확인해주세요.")
# else:
#     st.success("✅ OpenAI API 연결 완료")

# 1. 기본 참조 파일 자동 로드 섹션
st.header("📁 위험성분석 참조 파일 관리")

# 기본 참조 파일 정보 표시
st.info(f"📂 기본 참조 파일: `{DEFAULT_REFERENCE_FILE}`")

# 참조 파일 로드 버튼
col1, col2 = st.columns([3, 1])
with col1:
    st.caption(f"파일 위치: `{REFERENCE_FILES_FOLDER}/{DEFAULT_REFERENCE_FILE}`")
with col2:
    if st.button("🔄 파일 새로고침", type="secondary"):
        st.session_state['reference_files'] = load_reference_files_from_folder()
        st.session_state['reference_loaded'] = True
        st.rerun()

# 앱 시작 시 자동으로 참조 파일 로드
if not st.session_state['reference_loaded']:
    with st.spinner("참조 파일들을 로딩하고 있습니다..."):
        st.session_state['reference_files'] = load_reference_files_from_folder()
        st.session_state['reference_loaded'] = True

# 로드된 참조 파일 목록 표시
if st.session_state['reference_files']:
    st.success(f"✅ {len(st.session_state['reference_files'])}개의 참조 파일이 로드되었습니다!")
    
    # 참조 파일 선택
    st.subheader("📋 사용할 참조 파일 선택")
    
    # 모든 파일을 기본으로 선택
    default_selection = list(st.session_state['reference_files'].keys())
    selected_files = st.multiselect(
        "분석에 사용할 참조 파일을 선택하세요 (여러 개 선택 가능)",
        options=list(st.session_state['reference_files'].keys()),
        default=default_selection,
        help="선택된 파일들의 내용이 위험성 평가에 사용됩니다."
    )
    
    # 선택된 파일들 정보 표시
    if selected_files:
        with st.expander("📄 선택된 참조 파일 정보"):
            for file_name in selected_files:
                file_info = st.session_state['reference_files'][file_name]
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"**{file_name}**")
                with col2:
                    st.write(f"크기: {file_info['size']:,} bytes")
                with col3:
                    st.write(f"수정: {file_info['modified']}")
                
                # 파일 내용 미리보기
                # with st.checkbox(f"🔍 {file_name} 미리보기 보기"):
                    # preview_content = file_info['content'][:1000] + "..." if len(file_info['content']) > 1000 else file_info['content']
                    # st.text_area("내용", preview_content, height=200, disabled=True, key=f"preview_{file_name}")
else:
    st.warning("⚠️ 참조 파일이 없습니다.")
    st.markdown(f"""
    **참조 파일 추가 방법:**
    1. 프로젝트 폴더에 `{REFERENCE_FILES_FOLDER}` 폴더를 생성하세요
    2. 다음 형식의 파일들을 `{REFERENCE_FILES_FOLDER}` 폴더에 넣어주세요:
       - Excel 파일 (.xlsx)
       - CSV 파일 (.csv)  
       - 텍스트 파일 (.txt)
    3. '🔄 파일 새로고침' 버튼을 클릭하세요
    """)

# 2. 작업 내용 입력 섹션
st.header("✍️ 작업 내용 입력")

work_input = st.text_area(
    "오늘 수행할 작업 내용을 자세히 입력해주세요",
    placeholder="예시: 오늘 철탑에서 안테나 재설치 작업이 있어 위험성 평가 안내해줘.",
    height=100,
    help="작업 장소, 작업 내용, 사용 장비 등을 구체적으로 입력하면 더 정확한 위험성 평가를 받을 수 있습니다."
)

# 3. 분석 실행 버튼
if st.session_state['reference_files'] and work_input.strip():
    if not selected_files:
        st.warning("⚠️ 분석에 사용할 참조 파일을 확인해주세요.")
    elif st.button("🔍 위험성 평가 분석 시작", type="primary", use_container_width=True):
        if client is None:
            st.error("❌ OpenAI API 키가 설정되지 않았습니다.")
        else:
            try:
                with st.spinner("AI가 작업 내용을 분석하여 위험성 평가를 수행하고 있습니다..."):
                    result = analyze_work_risk(work_input, selected_files)
                    st.session_state['analysis_result'] = result
                
                st.success("✅ 위험성 평가 분석 완료!")
                
            except Exception as e:
                st.error(f"❌ 분석 중 오류 발생: {str(e)}")

elif not st.session_state['reference_files']:
    st.info(f"📁 먼저 기본 참조 파일 '{DEFAULT_REFERENCE_FILE}'을 준비해주세요.")
elif not work_input.strip():
    st.info("✍️ 작업 내용을 입력해주세요.")

# 4. 분석 결과 표시
if st.session_state['analysis_result']:
    result = st.session_state['analysis_result']
    
    st.markdown("---")
    st.header("📊 위험성 평가 결과")
    
    # 작업 정보 표시
    st.markdown(f"**작업 내용**: {result['work_description']}")
    st.markdown(f"**사용된 참조 파일**: {', '.join(result.get('used_references', []))}")
    st.caption(f"생성 시간: {result['timestamp']}")
    
    # 섹션별 탭 생성
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 전체 보고서",
        "🔍 작업 분석", 
        "⚠️ 위험성 평가표", 
        "✅ 안전 조치"
    ])
    
    sections = result.get('sections', {})
    section_files = create_section_files(sections, result['timestamp'], result['work_description'])
    
    with tab1:
        st.subheader("전체 위험성 평가 보고서")
        st.markdown(result['full_report'])
        
        # 전체 보고서 다운로드
        md_content = f"# 작업 위험성 평가 보고서\n\n"
        md_content += f"**작업 내용:** {result['work_description']}\n\n"
        md_content += f"**사용된 참조 파일:** {', '.join(result.get('used_references', []))}\n\n"
        md_content += f"**생성 시간:** {result['timestamp']}\n\n"
        md_content += result['full_report']
        
        st.download_button(
            label="📄 전체 보고서 다운로드 (.md)",
            data=md_content.encode('utf-8-sig'),
            file_name=f"위험성평가보고서_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            key="full_report_download"
        )
    
    with tab2:
        st.subheader("작업 내용 분석")
        if sections.get("work_analysis"):
            st.markdown(sections["work_analysis"])
            if "work_analysis" in section_files:
                st.download_button(
                    label="📥 작업 분석 다운로드 (.md)",
                    data=section_files["work_analysis"].encode('utf-8-sig'),
                    file_name=f"작업분석_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown",
                    key="work_analysis_download"
                )
        else:
            st.info("작업 분석 내용을 찾을 수 없습니다.")
    
    with tab3:
        st.subheader("위험성 평가표")
        if sections.get("risk_table"):
            # st.markdown(sections["risk_table"])
            
            # 위험성 평가표를 DataFrame으로 추출
            try:
                risk_df = parse_risk_table_from_markdown(result['full_report'])
                if not risk_df.empty:
                    st.markdown("### 📋 위험성 평가 표 (데이터프레임)")
                    st.dataframe(
                        risk_df, 
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "순번": st.column_config.NumberColumn("순번", width="small"),
                            "작업 내용": st.column_config.TextColumn("작업 내용", width="medium"),
                            "작업등급": st.column_config.TextColumn("작업등급", width="small"),
                            "재해유형": st.column_config.TextColumn("재해유형", width="medium"),
                            "세부 위험요인": st.column_config.TextColumn("세부 위험요인", width="large"),
                            "위험등급-개선전": st.column_config.TextColumn("위험등급-개선전", width="small"),
                            "위험성 감소대책": st.column_config.TextColumn("위험성 감소대책", width="large"),
                            "위험등급-개선후": st.column_config.TextColumn("위험등급-개선후", width="small")
                        }
                    )
                    
                    # 다운로드 버튼들을 나란히 배치
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # CSV 다운로드 버튼
                        csv = risk_df.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="📥 위험성 평가표 CSV 다운로드",
                            data=csv.encode('utf-8-sig'),
                            file_name=f"위험성평가표_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            key="risk_table_csv_download"
                        )
                    
                    with col2:
                        # MD 다운로드 버튼 (표 형태 유지)
                        md_table_content = f"""# 위험성 평가표

작업 설명: {result['work_description']}
생성 시간: {result['timestamp']}

{sections["risk_table"]}
"""
                        st.download_button(
                            label="📄 위험성 평가표 MD 다운로드",
                            data=md_table_content.encode('utf-8-sig'),
                            file_name=f"위험성평가표_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                            mime="text/markdown",
                            key="risk_table_md_download"
                        )
                        
                else:
                    st.info("위험성 평가표를 추출할 수 없습니다.")
                    
            except Exception as e:
                st.warning(f"⚠️ 위험성 평가표 파싱 중 오류: {str(e)}")
        else:
            st.info("위험성 평가표 내용을 찾을 수 없습니다.")    

    with tab4:
        st.subheader("안전 조치 사항")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**추가 안전 조치**")
            if sections.get("additional_safety"):
                st.markdown(sections["additional_safety"])
            else:
                st.info("추가 안전 조치 내용을 찾을 수 없습니다.")
        
        with col2:
            st.markdown("**작업 전 체크리스트**")
            if sections.get("safety_checklist"):
                st.markdown(sections["safety_checklist"])
            else:
                st.info("체크리스트 내용을 찾을 수 없습니다.")
    
    # 전체 섹션 ZIP 파일로 다운로드
    if section_files:
        st.markdown("---")
        st.subheader("📦 전체 결과 통합 다운로드")
        
        # ZIP 파일 생성
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_name, content in section_files.items():
                korean_names = {
                    "work_analysis": "1.작업분석",
                    "risk_table": "2.위험성평가표",
                    "additional_safety": "3.추가안전조치",
                    "safety_checklist": "4.작업전체크리스트"
                }
                zip_file.writestr(
                    f"{korean_names.get(file_name, file_name)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    content.encode('utf-8-sig')
                )
            
            # 전체 보고서도 포함
            full_report_content = f"# 작업 위험성 평가 보고서\n\n"
            full_report_content += f"**작업 내용:** {result['work_description']}\n\n"
            full_report_content += f"**사용된 참조 파일:** {', '.join(result.get('used_references', []))}\n\n"
            full_report_content += f"**생성 시간:** {result['timestamp']}\n\n"
            full_report_content += result['full_report']
            
            zip_file.writestr(
                f"0.전체보고서_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                full_report_content.encode('utf-8-sig')
            )
        
        zip_buffer.seek(0)
        
        st.download_button(
            label="📁 전체 결과 ZIP 다운로드",
            data=zip_buffer.getvalue(),
            file_name=f"위험성평가결과_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip",
            key="zip_download"
        )

# 사용법 안내
with st.expander("📖 사용법 안내"):
    st.markdown(f"""
    ### 🔧 사용 방법
    1. **기본 참조 파일 준비**: `{REFERENCE_FILES_FOLDER}/` 폴더에 `{DEFAULT_REFERENCE_FILE}` 파일을 넣어주세요.
    2. **자동 로드**: 앱 시작 시 기본 파일이 자동으로 로드됩니다.
    3. **작업 내용 입력**: 수행할 작업을 구체적으로 입력하세요.
    4. **분석 실행**: '위험성 평가 분석 시작' 버튼을 클릭하세요.
    5. **결과 확인**: 생성된 위험성 평가 보고서를 확인하고 다운로드하세요.
    
    ### 📁 참조 파일 관리
    - **기본 파일**: `{DEFAULT_REFERENCE_FILE}` (자동 인식)
    - **파일 위치**: `{REFERENCE_FILES_FOLDER}/` 폴더
    - **자동 로드**: 앱 시작 시 기본 파일을 우선적으로 로드
    - **백업 옵션**: 기본 파일이 없으면 폴더 내 다른 파일들을 스캔
    
    ### 📋 출력 결과
    - **작업 내용 분석**: 입력한 작업의 특성과 주요 위험 포인트 분석
    - **위험성 평가표**: 순번, 작업내용, 재해유형, 위험요인, 감소대책을 표 형태로 제공
    - **추가 안전 조치**: 작업 특성에 맞는 추가적인 안전 조치사항
    - **작업 전 체크리스트**: 작업 시작 전 반드시 확인해야 할 사항들
    
    ### 💡 작업 입력 예시
    - "오늘 철탑에서 안테나 재설치 작업이 있어 위험성 평가 안내해줘"
    - "지하 맨홀에서 케이블 교체 작업을 진행할 예정입니다"
    - "고압 전선 근처에서 장비 설치 작업이 예정되어 있습니다"
    
    ### ⚠️ 주의사항
    - 기본 참조 파일 `{DEFAULT_REFERENCE_FILE}`을 `{REFERENCE_FILES_FOLDER}` 폴더에 미리 준비해야 합니다.
    - 작업 내용을 구체적으로 입력할수록 더 정확한 위험성 평가를 받을 수 있습니다.
    - 생성된 결과는 참조용이므로, 실제 현장에서는 추가적인 안전 점검이 필요합니다.
    
    ### 🔄 파일 업데이트
    - 참조 파일을 수정한 후 '🔄 파일 새로고침' 버튼을 클릭하세요.
    - 파일 변경사항이 실시간으로 반영됩니다.
    """)

# 파일 정보 및 버전 정보
st.markdown("---")
st.markdown("**Version**: v2.1 (기본 참조 파일 자동 로드)")
st.markdown("**Last Updated**: 2025년 7월")
st.markdown("**Features**: 기본 참조 파일 자동 인식 → 작업 내용 입력 → AI 위험성 분석 → 맞춤형 안전 가이드 제공")
st.markdown(f"**기본 참조 파일**: `{REFERENCE_FILES_FOLDER}/{DEFAULT_REFERENCE_FILE}`")