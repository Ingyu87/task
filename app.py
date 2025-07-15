import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap
import json
import google.generativeai as genai
import os
import re

# --- 페이지 설정 ---
st.set_page_config(
    page_title="AI 코칭 기반 맞춤수업 설계",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS 스타일링 ---
st.markdown("""<style> .stButton>button {width:100%;} </style>""", unsafe_allow_html=True)

# --- 데이터 로드 ---
@st.cache_data
def load_data():
    data = {'curriculum': []}
    try:
        with open('단원학습내용.json', 'r', encoding='utf-8') as f:
            data['curriculum'] = json.load(f)
    except FileNotFoundError:
        st.error("'단원학습내용.json' 파일을 찾을 수 없습니다. 실행 경로를 확인해주세요.")
    return data

# --- 상수 및 데이터 정의 ---
AIDT_FEATURES = {
    'diagnosis': {'name': '학습진단 및 분석', 'icon': '🔍'},
    'dashboard': {'name': '교사 대시보드', 'icon': '📊'},
    'path': {'name': '학습 경로 추천', 'icon': '🛤️'},
    'tutor': {'name': '지능형 AI 튜터', 'icon': '🤖'},
    'collaboration': {'name': '소통 및 협업 도구', 'icon': '👥'},
    'portfolio': {'name': '디지털 포트폴리오', 'icon': '📁'}
}
json_data = load_data()

# --- 세션 상태 초기화 ---
if 'step' not in st.session_state:
    st.session_state.step = 1
    st.session_state.lesson_plan = {}
    st.session_state.generated_students = None

# --- 헬퍼(Helper) 함수 ---
def get_curriculum_options():
    if not json_data['curriculum']: return {}
    subjects = {}
    for item in json_data['curriculum']:
        subject, grade, semester, unit = item.get('과목',''), item.get('학년',0), item.get('학기',0), item.get('단원명','')
        if subject not in subjects: subjects[subject] = {}
        if grade not in subjects[subject]: subjects[subject][grade] = {}
        if semester not in subjects[subject][grade]: subjects[subject][grade][semester] = []
        subjects[subject][grade][semester].append({'unit': unit})
    return subjects

def call_gemini(prompt):
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    return response.text

def generate_student_profiles(topic):
    try:
        prompt = f"당신은 초등학교 교육 전문가입니다. '{topic}' 수업 주제에 맞춰, 가상의 '느린 학습자', '중간 학습자', '빠른 학습자' 프로필 3개를 생성해주세요. 각 프로필은 이름, 유형, 주제 관련 특성, 관련 학습 데이터(예: 형성평가 점수)를 포함해야 합니다. 출력은 반드시 순수한 JSON 형식으로만 응답해주세요."
        response_text = call_gemini(prompt)
        return json.loads(response_text.strip().lstrip("```json").rstrip("```"))
    except Exception as e:
        st.error(f"AI 학생 프로필 생성 중 오류: {e}"); return None

def parse_feedback(text):
    sections = {'strengths': [], 'suggestions': [], 'tools': []}
    current_section = None
    for line in text.split('\n'):
        line = line.strip()
        if '수업의 강점' in line: current_section = 'strengths'
        elif '발전 제안' in line: current_section = 'suggestions'
        elif '추가 에듀테크' in line: current_section = 'tools'
        elif current_section and (line.startswith('-') or line.startswith('*')):
            content = line[2:].strip()
            if current_section == 'tools' and ':' in content:
                name, desc = content.split(':', 1)
                sections[current_section].append({'name': name.strip(), 'description': desc.strip()})
            else:
                sections[current_section].append(content)
    return sections

def generate_image(plan, feedback):
    width, height = 800, 1200
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        # 폰트 파일이 없다면, 아래 경로를 수정하거나 주석 처리하고 기본 폰트를 사용하세요.
        font_title = ImageFont.truetype("NanumSquare_acB.ttf", 28)
        font_header = ImageFont.truetype("NanumSquare_acB.ttf", 20)
        font_body = ImageFont.truetype("NanumSquare_acB.ttf", 14)
    except IOError:
        st.warning("폰트 파일을 찾을 수 없어 기본 폰트로 이미지를 생성합니다.")
        font_title = ImageFont.load_default(); font_header = ImageFont.load_default(); font_body = ImageFont.load_default()

    y = 30
    draw.text((width/2, y), "AI 코칭 기반 맞춤수업 설계안", font=font_title, fill="black", anchor="mt"); y += 60
    
    student = st.session_state.generated_students[plan['student_name']]
    draw.text((40, y), "1. 수업 분석", font=font_header, fill="#00008B"); y += 35
    draw.text((50, y), f"■ 수업 주제: {plan['topic']}", font=font_body, fill="black"); y += 25
    draw.text((50, y), f"■ 대상 학생: {student['name']} ({student['type']})", font=font_body, fill="black"); y += 25
    
    y += 10
    draw.text((40, y), "2. AI 종합 컨설팅", font=font_header, fill="#006400"); y += 35
    draw.text((50, y), "👍 수업의 강점", font=font_body, fill="black"); y += 25
    for item in feedback.get('strengths', []):
        lines = textwrap.wrap(f"- {item}", width=80)
        for line in lines:
            draw.text((60, y), line, font=font_body, fill="black"); y += 20
    y += 15
    draw.text((50, y), "💡 발전 제안", font=font_body, fill="black"); y += 25
    for item in feedback.get('suggestions', []):
        lines = textwrap.wrap(f"- {item}", width=80)
        for line in lines:
            draw.text((60, y), line, font=font_body, fill="black"); y += 20
            
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()

# --- UI 렌더링 함수 ---
def step1_analysis():
    st.header("🔍 1단계: 수업 및 학습자 분석")
    with st.expander("✏️ 수업 주제 직접 입력하기 (선택)"):
        manual_topic = st.text_input("수업 주제 입력", placeholder="예: 5학년 과학 - 태양계와 별")
        if st.button("직접 입력한 주제로 설정"):
            if manual_topic:
                st.session_state.lesson_plan = {'topic': manual_topic}
                st.session_state.generated_students = None
                st.success(f"'{manual_topic}' 주제로 설정! 아래에서 학생 프로필을 생성하세요."); st.rerun()
            else:
                st.warning("주제를 입력해주세요.")

    st.subheader("📖 교육과정에서 수업 선택")
    subjects_data = get_curriculum_options()
    col1, col2, col3 = st.columns(3)
    subject = col1.selectbox("📚 교과", list(subjects_data.keys()))
    grade = col2.selectbox("👨‍🎓 학년", list(subjects_data.get(subject, {}).keys()))
    semester = col3.selectbox("📅 학기", list(subjects_data.get(subject, {}).get(grade, {}).keys()))
    
    if all([subject, grade, semester]):
        unit_options = [u['unit'] for u in subjects_data.get(subject, {}).get(grade, {}).get(semester, [])]
        if unit_options:
            selected_unit_name = st.radio("단원", unit_options)
            if st.button("선택한 단원으로 설정"):
                topic = f"{subject} {grade}-{semester} {selected_unit_name}"
                st.session_state.lesson_plan = {'topic': topic}
                st.session_state.generated_students = None
                st.success(f"'{topic}' 주제로 설정! 아래에서 학생 프로필을 생성하세요."); st.rerun()
    
    if st.session_state.lesson_plan.get('topic'):
        st.markdown("---"); st.subheader(f"👨‍🎓 학습자 분석 (주제: {st.session_state.lesson_plan['topic']})")
        if not st.session_state.generated_students:
            if st.button("🤖 AI 학생 프로필 생성", type="primary"):
                with st.spinner('AI가 맞춤 학생 프로필을 생성 중입니다...'):
                    st.session_state.generated_students = generate_student_profiles(st.session_state.lesson_plan['topic'])
                    st.rerun()
        else:
            st.info("✅ 학생 프로필 생성 완료! 지도할 학생과 지도 계획을 입력해주세요.")
            st.session_state.lesson_plan['student_name'] = st.selectbox("학생 선택", [None] + list(st.session_state.generated_students.keys()), format_func=lambda x: x or "선택")
            if st.session_state.lesson_plan.get('student_name'):
                student = st.session_state.generated_students[st.session_state.lesson_plan['student_name']]
                with st.container(border=True): st.markdown(f"**{student['name']} ({student['type']})**: {student['description']}")
                st.session_state.lesson_plan['guidance'] = st.text_area("✍️ 맞춤 지도 계획", placeholder="학생의 강점과 약점을 고려한 지도 계획을 작성해주세요.")

    if st.button("다음 🚀"):
        if st.session_state.lesson_plan.get('student_name') and st.session_state.lesson_plan.get('guidance'):
            st.session_state.step = 2; st.rerun()
        else: st.error("주제 설정, 학생 선택, 지도 계획을 모두 입력해주세요.")

def step2_method():
    st.header("🎯 2단계: 교수·학습 방법 결정")
    models = ["개별 학습 우선 모델", "협력 학습 중심 모델", "탐구 중심 모델", "프로젝트 기반 모델", "토의토론 중심 모델", "게임 기반 모델"]
    st.session_state.lesson_plan['model'] = st.selectbox("적용할 학습 모형을 선택하세요.", models)
    col1, col2 = st.columns(2)
    if col1.button("⬅️ 이전"): st.session_state.step = 1; st.rerun()
    if col2.button("다음 🚀"): st.session_state.step = 3; st.rerun()

def step3_structure():
    st.header("🏗️ 3단계: 수업 구조화 및 AIDT 기능 선택")
    plan = st.session_state.lesson_plan
    if 'ai_recommendations' not in plan:
        with st.spinner('AI가 최적의 기능을 추천 중입니다...'):
            prompt = f"'{plan['topic']}' 수업에서 '{plan['model']}' 모델로 '{plan['student_name']}' 학생을 지도할 때, 수업 단계(도입, 개별 학습, 협력 학습, 정리)별 가장 효과적인 AIDT 기능과 이유를 JSON 형식으로 추천해줘."
            try: plan['ai_recommendations'] = json.loads(re.search(r'\{.*\}', call_gemini(prompt), re.DOTALL).group())
            except Exception: plan['ai_recommendations'] = {}
    
    ai_recs = plan.get('ai_recommendations', {})
    plan['design'] = {}
    for stage, icon in {'도입': '🚀', '개별 학습': '📚', '협력 학습': '👥', '정리': '🎯'}.items():
        with st.container(border=True):
            st.markdown(f"**{icon} {stage}**")
            if stage in ai_recs: st.caption(f"AI 추천: {ai_recs[stage].get('reason', 'N/A')}")
            plan['design'][stage] = st.multiselect("", list(AIDT_FEATURES.keys()), format_func=lambda x: f"{AIDT_FEATURES[x]['icon']} {AIDT_FEATURES[x]['name']}", default=ai_recs.get(stage, {}).get('recommended', []), key=f"{stage}_ms")

    col1, col2 = st.columns(2)
    if col1.button("⬅️ 이전"): st.session_state.step = 2; st.rerun()
    if col2.button("결과 보기 🚀", type="primary"): st.session_state.step = 4; st.rerun()

def step4_feedback():
    st.header("📋 4단계: AI 종합 컨설팅 보고서")
    with st.spinner('🤖 AI가 수업 설계안을 분석하고 보고서를 작성하는 중입니다...'):
        try:
            plan = st.session_state.lesson_plan
            student = st.session_state.generated_students[plan['student_name']]
            features_info = "\n".join([f"- {s}: {', '.join(plan['design'].get(s,[]))}" for s in plan.get('design', {})])
            
            prompt = f"초등교육 컨설턴트로서 다음 수업 설계안에 대해 '### 👍 수업의 강점', '### 💡 발전 제안' 형식으로 구체적인 피드백을 한글로 작성해주세요.\n\n- 수업 주제: {plan['topic']}\n- 적용 모델: {plan['model']}\n- 대상 학생: {student['name']}({student['type']})\n- 지도 계획: {plan['guidance']}\n- 선택 기능:\n{features_info}"
            feedback_text = call_gemini(prompt)
            feedback_dict = parse_feedback(feedback_text)
            
            with st.container(border=True): st.markdown(feedback_text)
            
            st.download_button(
                label="📥 결과물 JPG 다운로드",
                data=generate_image(plan, feedback_dict),
                file_name=f"lesson_plan_{student['name']}.jpg",
                mime="image/jpeg",
            )
        except Exception as e:
            st.error(f"❌ 보고서 생성 중 오류가 발생했습니다: {e}")
            
    if st.button("🎉 처음으로 돌아가기"):
        st.session_state.clear(); st.rerun()

# --- 메인 앱 로직 ---
st.title("🎯 AI 코칭 기반 맞춤수업 설계")
progress = st.session_state.get('step', 1) / 4.0
st.progress(progress, text=f"진행률: {int(progress * 100)}%")

if 'step' not in st.session_state: st.session_state.step = 1

if st.session_state.step == 1: step1_analysis()
elif st.session_state.step == 2: step2_method()
elif st.session_state.step == 3: step3_structure()
elif st.session_state.step == 4: step4_feedback()