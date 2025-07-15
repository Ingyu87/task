import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap
import json
import google.generativeai as genai
import os
import re # <-- 이 줄이 추가되었습니다!

# --- 페이지 설정 ---
st.set_page_config(
    page_title="AI 코칭 기반 맞춤수업 설계",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS 스타일링 ---
st.markdown("""
<style>
    .main > div { padding-top: 2rem; }
    .step-header { background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem 2rem; border-radius: 10px; margin-bottom: 2rem; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
    .student-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1.5rem; border-radius: 15px; margin: 1rem 0; box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1); }
    .student-card .student-type { background: rgba(255, 255, 255, 0.2); padding: 0.3rem 0.8rem; border-radius: 20px; display: inline-block; font-size: 0.9rem; margin-bottom: 1rem; }
    .unit-info { background: linear-gradient(135deg, #fef3c7 0%, #fef9e7 100%); border: 1px solid #f59e0b; border-radius: 8px; padding: 1rem; margin: 1rem 0; }
    .feedback-section { background: white; border-radius: 12px; padding: 2rem; margin: 1rem 0; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); border-left: 4px solid #10b981; }
    .stage-container { background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border-radius: 12px; padding: 1.5rem; margin: 1rem 0; border: 1px solid #e2e8f0; }
    .stage-title { color: #1e293b; font-size: 1.2rem; font-weight: 600; margin-bottom: 1rem; display: flex; align-items: center; }
</style>
""", unsafe_allow_html=True)

# --- 데이터 로드 ---
@st.cache_data
def load_json_data():
    data = {'curriculum': [], 'edutech': {}}
    try:
        with open('단원학습내용.json', 'r', encoding='utf-8') as f:
            data['curriculum'] = json.load(f)
        with open('2023-2025 대한민국 초등 교실을 혁신하는 에듀테크 120.json', 'r', encoding='utf-8') as f:
            data['edutech'] = json.load(f)
    except FileNotFoundError as e:
        st.error(f"❌ 파일을 찾을 수 없습니다: {e.filename}")
    except Exception as e:
        st.error(f"❌ 데이터 로드 중 오류: {e}")
    return data

AIDT_FEATURES = {
    'diagnosis': {'name': '🔍 학습진단 및 분석', 'icon': '🔍'}, 'dashboard': {'name': '📊 교사 대시보드', 'icon': '📊'},
    'path': {'name': '🛤️ 학습 경로 추천', 'icon': '🛤️'}, 'tutor': {'name': '🤖 지능형 AI 튜터', 'icon': '🤖'},
    'collaboration': {'name': '👥 소통 및 협업 도구', 'icon': '👥'}, 'portfolio': {'name': '📁 디지털 포트폴리오', 'icon': '📁'}
}
json_data = load_json_data()

# --- 세션 상태 초기화 ---
if 'step' not in st.session_state:
    st.session_state.step = 1
    st.session_state.lesson_plan = {}
    st.session_state.generated_students = None

# --- 헬퍼 함수 ---
def get_curriculum_options():
    # ... (이전과 동일)
    if not json_data['curriculum']: return {}
    subjects = {}
    for item in json_data['curriculum']:
        subject = item.get('과목', '')
        grade = item.get('학년', 0)
        semester = item.get('학기', 0)
        unit = item.get('단원명', '')
        if subject not in subjects: subjects[subject] = {}
        if grade not in subjects[subject]: subjects[subject][grade] = {}
        if semester not in subjects[subject][grade]: subjects[subject][grade][semester] = []
        subjects[subject][grade][semester].append({
            'unit': unit, 'achievement': item.get('성취기준', ''),
            'content': item.get('단원학습내용', ''), 'area': item.get('영역', '')
        })
    return subjects

def generate_student_profiles_with_gemini(subject, grade, semester, unit):
    # ... (이전과 동일)
    try:
        gemini_api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=gemini_api_key)
        prompt = f"""
        당신은 초등학교 교육과정 전문가입니다. 주어진 교과 단원 정보에 맞춰, 가상의 초등학생 프로필 3개를 생성해주세요.
        - 대상: 느린 학습자, 중간 학습자, 빠른 학습자 각 1명
        - 조건: 각 학생의 특성 설명과 학습 데이터는 반드시 주어진 단원 내용과 직접적으로 관련되어야 합니다.
        - 출력 형식: 반드시 아래와 같은 순수한 JSON 형식으로만 응답해주세요. 설명이나 다른 텍스트는 절대 포함하지 마세요.

        [입력 정보]
        - 교과: {subject}, 학년: {grade}, 학기: {semester}, 단원: {unit}

        [JSON 출력 형식]
        {{
            "김O 학습자 (느린 학습자)": {{"name": "김O 학습자", "type": "느린 학습자", "description": "{unit} 단원의 기본 개념을 이해하는 데 어려움을 겪으며, 시각적 자료나 구체적 조작 활동이 필요합니다.", "data": [{{"평가": "선행개념 확인", "정답률": 45}}, {{"평가": "핵심개념 형성평가", "정답률": 30}}]}},
            "이O 학습자 (중간 학습자)": {{"name": "이O 학습자", "type": "중간 학습자", "description": "{unit} 단원의 기본 개념은 이해했지만, 응용 문제 해결에 실수가 잦아 개념을 자신의 언어로 정리하는 연습이 필요합니다.", "data": [{{"평가": "선행개념 확인", "정답률": 80}}, {{"평가": "핵심개념 형성평가", "정답률": 75}}]}},
            "박O 학습자 (빠른 학습자)": {{"name": "박O 학습자", "type": "빠른 학습자", "description": "{unit} 단원의 학습 내용을 빠르게 습득하며, 도전적인 과제를 통해 학습 동기를 유지시켜줄 필요가 있습니다.", "data": [{{"평가": "선행개념 확인", "정답률": 100}}, {{"평가": "핵심개념 단원평가 수준", "정답률": 95}}]}}
        }}
        """
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        clean_response = response.text.strip().lstrip("```json").rstrip("```")
        return json.loads(clean_response)
    except Exception as e:
        st.error(f"AI 학생 프로필 생성 중 오류 발생: {e}")
        return None

def get_ai_recommendations():
    try:
        gemini_api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=gemini_api_key)
        plan = st.session_state.lesson_plan
        student = st.session_state.generated_students[plan['student_name']]
        prompt = f"""
        당신은 초등교육 전문가입니다. 다음 정보를 바탕으로 수업 단계별로 가장 적합한 AIDT 기능을 추천해주세요.
        - 수업 주제: {plan['topic']}, 학생 유형: {student['type']}, 학생 특성: {student['description']}, 수업 모델: {plan['model']}
        - 사용 가능 기능: diagnosis, dashboard, path, tutor, collaboration, portfolio
        - 각 수업 단계(도입, 개별 학습, 협력 학습, 정리)별 추천 기능과 이유를 JSON 형식으로 응답해주세요.
        - 응답 형식: {{"도입": {{"recommended": ["diagnosis"], "reason": "수업 전 학생 수준 파악"}}, ...}}
        """
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {}
    except Exception as e:
        st.error(f"AI 추천 생성 중 오류: {e}")
        return {}
        
# --- UI 렌더링 함수 ---
def step1_analysis():
    st.markdown("<h1>🔍 1단계: 수업 및 학습자 분석</h1>", unsafe_allow_html=True)
    subjects_data = get_curriculum_options()
    if not subjects_data: st.error("교육과정 데이터를 로드할 수 없습니다."); return

    # --- 교과, 단원 선택 ---
    # ... (이전과 동일)
    col1, col2, col3 = st.columns(3)
    with col1: subject = st.selectbox("📚 교과", list(subjects_data.keys()))
    with col2: grade = st.selectbox("👨‍🎓 학년", list(subjects_data.get(subject, {}).keys()))
    with col3: semester = st.selectbox("📅 학기", list(subjects_data.get(subject, {}).get(grade, {}).keys()))

    if not all([subject, grade, semester]): st.warning("교과/학년/학기를 선택해주세요."); return
    
    units = subjects_data.get(subject, {}).get(grade, {}).get(semester, [])
    unit_options = [u['unit'] for u in units]
    if not unit_options: st.warning("해당 학기에 단원 정보가 없습니다."); return
    
    selected_unit_name = st.radio("📖 단원", unit_options, key="unit_radio")
    
    if selected_unit_name != st.session_state.lesson_plan.get('unit'):
        st.session_state.lesson_plan = {'unit': selected_unit_name, 'topic': f"{subject} {grade}-{semester} {selected_unit_name}"}
        st.session_state.generated_students = None
        st.rerun()

    # --- AI 학생 프로필 생성 ---
    st.markdown("---")
    if st.session_state.generated_students is None:
        st.info("단원 선택이 완료되었습니다. 아래 버튼을 눌러 AI 학생 프로필을 생성해주세요.")
        if st.button("🤖 선택 단원 맞춤 AI 학생 프로필 생성", type="primary", use_container_width=True):
            with st.spinner('🤖 AI가 맞춤 학생 프로필을 생성 중입니다...'):
                profiles = generate_student_profiles_with_gemini(subject, grade, semester, selected_unit_name)
                if profiles:
                    st.session_state.generated_students = profiles
                    st.rerun()
    else:
        st.info("✅ AI 학생 프로필 생성이 완료되었습니다.")
        student_names = list(st.session_state.generated_students.keys())
        st.session_state.lesson_plan['student_name'] = st.selectbox("지도할 학생 선택", [None] + student_names, format_func=lambda x: x or "학생을 선택하세요")

        if st.session_state.lesson_plan.get('student_name'):
            student = st.session_state.generated_students[st.session_state.lesson_plan['student_name']]
            with st.container(border=True):
                st.markdown(f"#### {student['name']} ({student['type']})")
                st.write(student['description'])
                if student.get('data'):
                    cols = st.columns(len(student['data']))
                    for i, item in enumerate(student['data']):
                        cols[i].metric(label=item['평가'], value=f"{item.get('정답률', 0)}%")
            
            st.session_state.lesson_plan['guidance'] = st.text_area("✍️ 맞춤 지도 계획", placeholder="학생의 강점을 강화하고 약점을 보완하기 위한 지도 계획을 작성해 주세요.")
            
    # --- 다음 단계로 ---
    st.markdown("---")
    if st.button("🚀 다음 단계로", use_container_width=True):
        if st.session_state.lesson_plan.get('student_name') and st.session_state.lesson_plan.get('guidance'):
            st.session_state.step = 2
            st.rerun()
        else:
            st.error("⚠️ 학생과 지도 계획을 모두 입력해주세요.")

def step2_method():
    st.markdown("<h1>🎯 2단계: 교수·학습 방법 결정</h1>", unsafe_allow_html=True)
    q1 = st.radio("학생별 수준, 취약점 확인이 필요한가요?", ("Yes", "No"), horizontal=True, index=1)
    q2 = st.radio("학습 목표 달성에 학생 간 수준 차이가 크게 영향을 미치나요?", ("Yes", "No"), horizontal=True, index=1)
    
    if q1 == "Yes" or q2 == "Yes": recommended_model = "개별 학습 우선 모델"
    else: recommended_model = "협력 학습 중심 모델"
    
    st.info(f"🤖 AI 추천 모델: **{recommended_model}**")
    
    st.session_state.lesson_plan['model'] = st.selectbox("🎯 학습 모형 최종 선택", ["개별 학습 우선 모델", "협력 학습 중심 모델", "탐구 중심 모델", "프로젝트 기반 모델"])

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ 이전", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
    with col2:
        if st.button("🚀 다음", use_container_width=True):
            st.session_state.step = 3
            st.rerun()

def step3_structure():
    st.markdown("<h1>🏗️ 3단계: 수업 구조화 및 AIDT 기능 선택</h1>", unsafe_allow_html=True)
    if 'ai_recommendations' not in st.session_state.lesson_plan:
        with st.spinner('🤖 AI가 최적의 AIDT 기능을 추천 중입니다...'):
            st.session_state.lesson_plan['ai_recommendations'] = get_ai_recommendations()

    ai_recs = st.session_state.lesson_plan.get('ai_recommendations', {})
    
    st.session_state.lesson_plan['design'] = {}
    for stage, icon in {'도입': '🚀', '개별 학습': '📚', '협력 학습': '👥', '정리': '🎯'}.items():
        with st.container(border=True):
            st.markdown(f"#### {icon} {stage}")
            if stage in ai_recs:
                st.caption(f"🤖 AI 추천 이유: {ai_recs[stage].get('reason', 'N/A')}")

            st.session_state.lesson_plan['design'][stage] = st.multiselect(
                f"{stage} 단계에서 사용할 기능",
                options=list(AIDT_FEATURES.keys()),
                format_func=lambda x: f"{AIDT_FEATURES[x]['icon']} {AIDT_FEATURES[x]['name']}",
                default=ai_recs.get(stage, {}).get('recommended', []),
                key=f"{stage}_multiselect"
            )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ 이전", use_container_width=True): st.session_state.step = 2; st.rerun()
    with col2:
        if st.button("🎯 제출하고 컨설팅 받기", type="primary", use_container_width=True):
            st.session_state.step = 4
            st.rerun()

def step4_feedback():
    st.markdown("<h1>📋 4단계: AI 종합 컨설팅 보고서</h1>", unsafe_allow_html=True)
    # ... (이전과 동일, 생략)
    st.info("최종 컨설팅 기능은 구현 대기 중입니다.")
    if st.button("🎉 처음으로 돌아가기", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# --- 메인 앱 로직 ---
st.markdown("""
<div style="text-align: center; padding: 2rem 0; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 15px; margin-bottom: 2rem;">
    <h1 style="margin: 0; font-size: 2.5rem; color: white;">🎯 AI 코칭 기반 맞춤수업 설계 시뮬레이터</h1>
</div>
""", unsafe_allow_html=True)

progress = st.session_state.get('step', 1) / 4.0
st.progress(progress, text=f"진행률: {int(progress * 100)}% ({st.session_state.get('step', 1)}/4 단계)")

if st.session_state.get('step', 1) == 1:
    step1_analysis()
elif st.session_state.step == 2:
    step2_method()
elif st.session_state.step == 3:
    step3_structure()
elif st.session_state.step == 4:
    step4_feedback()