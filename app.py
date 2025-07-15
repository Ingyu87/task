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
st.markdown("""
<style>
    .main > div { padding-top: 2rem; }
    .step-header { background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem 2rem; border-radius: 10px; margin-bottom: 2rem; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
    .student-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1.5rem; border-radius: 15px; margin: 1rem 0; box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1); }
    .student-card .student-type { background: rgba(255, 255, 255, 0.2); padding: 0.3rem 0.8rem; border-radius: 20px; display: inline-block; font-size: 0.9rem; margin-bottom: 1rem; }
    .unit-info { background: linear-gradient(135deg, #fef3c7 0%, #fef9e7 100%); border: 1px solid #f59e0b; border-radius: 8px; padding: 1rem; margin: 1rem 0; }
    .feedback-section { background: white; border-radius: 12px; padding: 2rem; margin: 1rem 0; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); border-left: 4px solid #10b981; }
    .stage-container { background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border-radius: 12px; padding: 1.5rem; margin: 1rem 0; border: 1px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

# --- 데이터 및 기능 정의 ---
@st.cache_data
def load_json_data():
    data = {'curriculum': [], 'edutech': {}}
    try:
        with open('단원학습내용.json', 'r', encoding='utf-8') as f: data['curriculum'] = json.load(f)
        with open('2023-2025 대한민국 초등 교실을 혁신하는 에듀테크 120.json', 'r', encoding='utf-8') as f: data['edutech'] = json.load(f)
    except FileNotFoundError as e:
        st.error(f"❌ 파일을 찾을 수 없습니다: {e.filename}")
    return data

AIDT_FEATURES = {
    'diagnosis': {'name': '학습진단 및 분석', 'icon': '🔍'}, 'dashboard': {'name': '교사 대시보드', 'icon': '📊'},
    'path': {'name': '학습 경로 추천', 'icon': '🛤️'}, 'tutor': {'name': '지능형 AI 튜터', 'icon': '🤖'},
    'collaboration': {'name': '소통 및 협업 도구', 'icon': '👥'}, 'portfolio': {'name': '디지털 포트폴리오', 'icon': '📁'}
}
json_data = load_json_data()

# --- 세션 상태 초기화 ---
if 'step' not in st.session_state:
    st.session_state.step = 1
    st.session_state.lesson_plan = {}
    st.session_state.generated_students = None

# --- 헬퍼 함수 ---
def get_curriculum_options():
    if not json_data['curriculum']: return {}
    subjects = {}
    for item in json_data['curriculum']:
        subject, grade, semester, unit = item.get('과목', ''), item.get('학년', 0), item.get('학기', 0), item.get('단원명', '')
        if subject not in subjects: subjects[subject] = {}
        if grade not in subjects[subject]: subjects[subject][grade] = {}
        if semester not in subjects[subject][grade]: subjects[subject][grade][semester] = []
        subjects[subject][grade][semester].append({'unit': unit, 'achievement': item.get('성취기준', ''), 'area': item.get('영역', '')})
    return subjects

def generate_student_profiles_with_gemini(subject, grade, semester, unit):
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        prompt = f"""당신은 초등학교 교육과정 전문가입니다. 주어진 교과 단원 정보({subject} {grade}-{semester} {unit})에 맞춰, 느린/중간/빠른 학습자 프로필 3개를 생성해주세요. 각 프로필은 이름, 유형, 단원 관련 설명, 관련 학습 데이터(형성평가 등)를 포함해야 합니다. 출력은 반드시 순수한 JSON 형식으로만 응답해주세요."""
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return json.loads(response.text.strip().lstrip("```json").rstrip("```"))
    except Exception as e:
        st.error(f"AI 학생 프로필 생성 중 오류: {e}"); return None

def get_ai_recommendations():
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        plan = st.session_state.lesson_plan
        student = st.session_state.generated_students[plan['student_name']]
        prompt = f"""수업 설계 컨설턴트로서 다음 정보에 기반해 수업 단계별 AIDT 기능을 추천하고 이유를 JSON으로 답해주세요. 정보: 수업 주제={plan['topic']}, 학생 유형={student['type']}, 수업 모델={plan['model']}. 형식: {{"도입": {{"recommended": ["diagnosis"], "reason": "..."}}, ...}}"""
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
    except Exception as e:
        st.error(f"AI 추천 생성 중 오류: {e}"); return {}

def parse_feedback_from_gemini(text):
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

def generate_lesson_plan_image(plan, feedback):
    width, height = 800, 1100
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font_title = ImageFont.truetype("NanumSquare_acB.ttf", 28)
        font_header = ImageFont.truetype("NanumSquare_acB.ttf", 20)
        font_body = ImageFont.truetype("NanumSquare_acB.ttf", 14)
    except IOError:
        font_title, font_header, font_body = [ImageFont.load_default() for _ in range(3)]
        st.warning("폰트 파일을 찾을 수 없어 기본 폰트로 이미지를 생성합니다.")

    y = 30; draw.text((width/2, y), "AI 코칭 기반 맞춤수업 설계안", font=font_title, fill="black", anchor="mt"); y += 60
    student = st.session_state.generated_students[plan['student_name']]
    draw.text((40, y), f"1. 수업 분석: {plan['topic']} | 대상: {student['name']}({student['type']})", font=font_header, fill="blue"); y += 40
    # ... 이미지에 더 많은 내용을 그리는 로직 추가 가능 ...
    draw.text((40, y), "2. AI 종합 컨설팅", font=font_header, fill="green"); y += 40
    draw.text((50, y), "👍 수업의 강점", font=font_body, fill="black"); y += 25
    for item in feedback['strengths']: y += 20; draw.text((60, y), f"- {item}", font=font_body, fill="black")
    y += 30; draw.text((50, y), "💡 발전 제안", font=font_body, fill="black"); y += 25
    for item in feedback['suggestions']: y += 20; draw.text((60, y), f"- {item}", font=font_body, fill="black")
    buf = io.BytesIO(); img.save(buf, format='JPEG'); return buf.getvalue()

# --- UI 렌더링 함수 ---
def step1_analysis():
    st.header("🔍 1단계: 수업 및 학습자 분석")
    subjects_data = get_curriculum_options()
    if not subjects_data: st.error("교육과정 데이터 로드 실패."); return

    col1, col2, col3 = st.columns(3)
    subject = col1.selectbox("📚 교과", list(subjects_data.keys()))
    grade = col2.selectbox("👨‍🎓 학년", list(subjects_data.get(subject, {}).keys()))
    semester = col3.selectbox("📅 학기", list(subjects_data.get(subject, {}).get(grade, {}).keys()))

    if not all([subject, grade, semester]): st.warning("교과/학년/학기를 선택해주세요."); return
    
    unit_options = [u['unit'] for u in subjects_data.get(subject, {}).get(grade, {}).get(semester, [])]
    if not unit_options: st.warning("해당 학기에 단원 정보가 없습니다."); return
    
    selected_unit_name = st.radio("📖 단원", unit_options)
    
    if selected_unit_name != st.session_state.lesson_plan.get('unit'):
        st.session_state.lesson_plan = {'subject': subject, 'grade': grade, 'semester': semester, 'unit': selected_unit_name, 'topic': f"{subject} {grade}-{semester} {selected_unit_name}"}
        st.session_state.generated_students = None
        st.rerun()

    st.markdown("---")
    if st.session_state.generated_students is None:
        if st.button("🤖 선택 단원 맞춤 AI 학생 프로필 생성", type="primary", use_container_width=True):
            with st.spinner('AI가 프로필을 생성 중입니다...'):
                st.session_state.generated_students = generate_student_profiles_with_gemini(subject, grade, semester, selected_unit_name)
                st.rerun()
    else:
        st.session_state.lesson_plan['student_name'] = st.selectbox("지도할 학생 선택", [None] + list(st.session_state.generated_students.keys()), format_func=lambda x: x or "학생 선택")
        if st.session_state.lesson_plan.get('student_name'):
            student = st.session_state.generated_students[st.session_state.lesson_plan['student_name']]
            with st.container(border=True):
                st.markdown(f"**{student['name']} ({student['type']})**: {student['description']}")
            st.session_state.lesson_plan['guidance'] = st.text_area("✍️ 맞춤 지도 계획")
            
    if st.button("다음 🚀", use_container_width=True):
        if st.session_state.lesson_plan.get('student_name') and st.session_state.lesson_plan.get('guidance'):
            st.session_state.step = 2; st.rerun()
        else:
            st.error("학생과 지도 계획을 모두 입력해주세요.")

def step2_method():
    st.header("🎯 2단계: 교수·학습 방법 결정")
    st.session_state.lesson_plan['model'] = st.selectbox("학습 모형 선택", ["개별 학습 우선 모델", "협력 학습 중심 모델", "프로젝트 기반 모델"])
    col1, col2 = st.columns(2)
    if col1.button("⬅️ 이전"): st.session_state.step = 1; st.rerun()
    if col2.button("다음 🚀"): st.session_state.step = 3; st.rerun()

def step3_structure():
    st.header("🏗️ 3단계: 수업 구조화 및 AIDT 기능 선택")
    if 'ai_recommendations' not in st.session_state.lesson_plan:
        with st.spinner('AI가 기능을 추천 중입니다...'):
            st.session_state.lesson_plan['ai_recommendations'] = get_ai_recommendations()
    ai_recs = st.session_state.lesson_plan.get('ai_recommendations', {})
    
    st.session_state.lesson_plan['design'] = {}
    for stage, icon in {'도입': '🚀', '개별 학습': '📚', '협력 학습': '👥', '정리': '🎯'}.items():
        with st.container(border=True):
            st.markdown(f"**{icon} {stage}**")
            if stage in ai_recs: st.caption(f"AI 추천 이유: {ai_recs[stage].get('reason', 'N/A')}")
            st.session_state.lesson_plan['design'][stage] = st.multiselect(f"{stage} 기능", list(AIDT_FEATURES.keys()), format_func=lambda x: f"{AIDT_FEATURES[x]['icon']} {AIDT_FEATURES[x]['name']}", default=ai_recs.get(stage, {}).get('recommended', []), key=f"{stage}_ms")

    col1, col2 = st.columns(2)
    if col1.button("⬅️ 이전"): st.session_state.step = 2; st.rerun()
    if col2.button("다음 🚀", type="primary"): st.session_state.step = 4; st.rerun()

def step4_feedback():
    st.header("📋 4단계: AI 종합 컨설팅 보고서")
    with st.spinner('🤖 AI가 수업 설계안을 분석하고 컨설팅 보고서를 작성하는 중입니다...'):
        try:
            plan = st.session_state.lesson_plan
            student = st.session_state.generated_students[plan['student_name']]
            features_info = "\n".join([f"- {s}: {', '.join(f)}" for s, f in plan['design'].items() if f])
            
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            prompt = f"초등 교육 전문가로서 다음 수업 설계안에 대해 '수업의 강점', '발전 제안', '추가 에듀테크 도구 추천'으로 나누어 구체적인 피드백을 한글로 작성해주세요.\n\n- 수업 정보: {plan['topic']}, {plan['model']}\n- 학생 정보: {student['name']}({student['type']}), {student['description']}\n- 지도 계획: {plan['guidance']}\n- 선택 기능:\n{features_info}"
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            feedback_text = response.text
            
            feedback_dict = parse_feedback_from_gemini(feedback_text)
            
            with st.container(border=True):
                st.markdown(feedback_text)
            
            st.download_button(
                label="📥 결과물 JPG 다운로드",
                data=generate_lesson_plan_image(plan, feedback_dict),
                file_name=f"lesson_plan_{plan['student_name']}.jpg",
                mime="image/jpeg",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"❌ AI 컨설팅 보고서 생성 중 오류가 발생했습니다: {e}")
            
    if st.button("🎉 처음으로 돌아가기", use_container_width=True):
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