import streamlit as st
from openai import OpenAI
from anthropic import Anthropic
import PyPDF2
import io
import pandas as pd
import re

# 페이지 설정
st.set_page_config(
    page_title="사업계획서 작성 도우미",
    page_icon="📝",
    layout="wide"
)

# 세션 상태 초기화
if 'openai_api_key' not in st.session_state:
    st.session_state.openai_api_key = ""
if 'claude_api_key' not in st.session_state:
    st.session_state.claude_api_key = ""
if 'pdf_content' not in st.session_state:
    st.session_state.pdf_content = ""
if 'references' not in st.session_state:
    st.session_state.references = {}
if 'announcement_df' not in st.session_state:
    st.session_state.announcement_df = None
if 'openai_models' not in st.session_state:
    st.session_state.openai_models = []
if 'selected_openai_model' not in st.session_state:
    st.session_state.selected_openai_model = "gpt-4"
if 'claude_models' not in st.session_state:
    st.session_state.claude_models = []
if 'selected_claude_model' not in st.session_state:
    st.session_state.selected_claude_model = "claude-2"

# 사이드바에 API 키 입력
with st.sidebar:
    st.title("API 설정")
    
    # OpenAI API 키 및 모델 설정
    openai_key = st.text_input("OpenAI API 키를 입력하세요", 
                              type="password",
                              value=st.session_state.openai_api_key)
    if openai_key:
        st.session_state.openai_api_key = openai_key
        try:
            client = OpenAI(api_key=openai_key)
            models = client.models.list()
            st.session_state.openai_models = [model.id for model in models.data if "gpt" in model.id]
            st.session_state.selected_openai_model = st.selectbox(
                "OpenAI 모델 선택",
                st.session_state.openai_models,
                index=st.session_state.openai_models.index(st.session_state.selected_openai_model) if st.session_state.selected_openai_model in st.session_state.openai_models else 0
            )
        except Exception as e:
            st.error(f"OpenAI API 키 검증 실패: {str(e)}")
            
    # Claude API 키 및 모델 설정    
    claude_key = st.text_input("Claude API 키를 입력하세요",
                              type="password",
                              value=st.session_state.claude_api_key)
    if claude_key:
        st.session_state.claude_api_key = claude_key
        try:
            claude = Anthropic(api_key=claude_key)
            models = claude.models.list()
            st.session_state.claude_models = [model.id for model in models.data]
            st.session_state.selected_claude_model = st.selectbox(
                "Claude 모델 선택",
                st.session_state.claude_models,
                index=st.session_state.claude_models.index(st.session_state.selected_claude_model) if st.session_state.selected_claude_model in st.session_state.claude_models else 0
            )
        except Exception as e:
            st.error(f"Claude API 키 검증 실패: {str(e)}")

# 메인 페이지
st.title("정부지원사업 사업계획서 작성")

# API 키 확인
if not st.session_state.openai_api_key and not st.session_state.claude_api_key:
    st.error("API 키를 먼저 설정해주세요.")
    st.stop()

# 회사 정보 입력
st.subheader("회사 정보 입력")
col1, col2 = st.columns(2)
with col1:
    company_name = st.text_input("회사명")
    business_type = st.text_input("업종")
with col2:
    employee_count = st.number_input("직원 수", min_value=0)
    annual_revenue = st.number_input("연매출(백만원)", min_value=0)

# PDF 파일 업로드
st.subheader("공고문 업로드")
uploaded_file = st.file_uploader("공고 PDF 파일을 업로드해주세요", type="pdf")

if uploaded_file:
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    pdf_text = ""
    
    # PDF 내용을 페이지별로 데이터프레임에 저장
    data = []
    for i, page in enumerate(pdf_reader.pages, 1):
        text = page.extract_text()
        # 섹션 구분을 위한 패턴 찾기
        sections = re.split(r'\n(?=[1-9]\.|[ㄱ-ㅎ가-힣]\.|[IVXLC]\.|□|\d{1,2}\.)', text)
        
        for section in sections:
            if section.strip():
                data.append({
                    'page': i,
                    'content': section.strip(),
                    'section': re.match(r'^([1-9]\.|[ㄱ-ㅎ가-힣]\.|[IVXLC]\.|□|\d{1,2}\.)?(.+)?', section).group(1) if re.match(r'^([1-9]\.|[ㄱ-ㅎ가-힣]\.|[IVXLC]\.|□|\d{1,2}\.)?(.+)?', section) else None
                })
    
    # 데이터프레임 생성 및 저장
    st.session_state.announcement_df = pd.DataFrame(data)
    st.session_state.pdf_content = pdf_text
    
    # 사업계획서 작성 버튼
    st.subheader("사업계획서 작성")
    if st.button("사업계획서 작성하기"):
        with st.spinner("사업계획서를 작성중입니다..."):
            try:
                system_prompt = f"""당신은 정부지원사업 사업계획서 작성 전문가입니다.
                회사 정보:
                - 회사명: {company_name}
                - 업종: {business_type}
                - 직원 수: {employee_count}명
                - 연매출: {annual_revenue}백만원
                
                각 항목별 작성 방향을 제시할 때, 공고문의 어느 부분을 참고했는지 명확히 표시해주세요.
                형식은 다음과 같습니다:
                
                ## [항목명]
                작성 방향 설명...
                
                참고 출처:
                - 페이지 X: "실제 공고문 인용"
                """
                
                if st.session_state.openai_api_key:
                    client = OpenAI(api_key=st.session_state.openai_api_key)
                    response = client.chat.completions.create(
                        model=st.session_state.selected_openai_model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"다음 공고 내용을 분석하여 사업계획서의 주요 항목들을 추출하고, 각 항목별 작성 방향을 제시해주세요. 각 항목마다 참고한 공고문의 구체적인 내용을 반드시 포함해주세요:\n\n{st.session_state.announcement_df.to_string()}"}
                        ],
                        stream=True
                    )
                    
                    # 스트리밍 응답을 위한 컨테이너
                    response_container = st.empty()
                    full_response = ""
                    
                    # 스트리밍 응답 처리
                    for chunk in response:
                        if chunk.choices[0].delta.content is not None:
                            full_response += chunk.choices[0].delta.content
                            response_container.markdown(full_response)
                    
                    # AI 응답 파싱 및 데이터프레임에서 관련 내용 찾기
                    sections = re.split(r'\n##\s+', full_response)
                    
                    st.subheader("사업계획서 작성 결과")
                    for section in sections:
                        if section.strip():
                            # 섹션 제목 추출
                            section_title = section.split('\n')[0].strip('[]')
                            
                            # 데이터프레임에서 관련 내용 검색
                            relevant_content = st.session_state.announcement_df[
                                st.session_state.announcement_df['content'].str.contains(section_title, na=False)
                            ]
                            
                            st.subheader(f"## {section_title}")
                            st.write(section)
                            
                            if not relevant_content.empty:
                                st.info("📑 관련 공고문 내용:")
                                for _, row in relevant_content.iterrows():
                                    st.write(f"페이지 {row['page']}: {row['content']}")
                    
                    # 출처 정보 저장
                    st.session_state.references = full_response
                
                elif st.session_state.claude_api_key:
                    anthropic = Anthropic(api_key=st.session_state.claude_api_key)
                    # Claude API 호출 - stream=True 파라미터 사용
                    message = anthropic.messages.create(
                        model=st.session_state.selected_claude_model,
                        max_tokens=4000,
                        messages=[
                            {
                                "role": "user",
                                "content": f"다음 공고 내용을 분석하여 사업계획서의 주요 항목들을 추출하고, 각 항목별 작성 방향을 제시해주세요. 각 항목마다 참고한 공고문의 구체적인 내용을 반드시 명시해주세요:\n\n시스템 프롬프트: {system_prompt}\n\n공고 내용: {st.session_state.announcement_df.to_string()}"
                            }
                        ]
                    )
                    
                    # 스트리밍 응답을 위한 컨테이너
                    response_container = st.empty()
                    
                    # 스트리밍 없이 전체 응답 표시
                    full_response = message.content[0].text
                    response_container.markdown(full_response)
                    
                    # AI 응답 파싱 및 데이터프레임에서 관련 내용 찾기
                    sections = re.split(r'\n##\s+', full_response)
                    
                    st.subheader("사업계획서 작성 결과")
                    for section in sections:
                        if section.strip():
                            section_title = section.split('\n')[0].strip('[]')
                            relevant_content = st.session_state.announcement_df[
                                st.session_state.announcement_df['content'].str.contains(section_title, na=False)
                            ]
                            
                            st.subheader(f"## {section_title}")
                            st.write(section)
                            
                            if not relevant_content.empty:
                                st.info("📑 관련 공고문 내용:")
                                for _, row in relevant_content.iterrows():
                                    st.write(f"페이지 {row['page']}: {row['content']}")
                    
                    # 출처 정보 저장
                    st.session_state.references = full_response
                
                # 전체 참고 출처 표시
                st.subheader("📚 전체 참고 출처 모음")
                st.info("각 항목별 작성 근거가 된 공고문의 구체적인 내용입니다.")
                st.dataframe(st.session_state.announcement_df)
            
            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")
                import traceback
                st.error(f"상세 오류: {traceback.format_exc()}")
