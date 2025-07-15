import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap
import json
import google.generativeai as genai
import os

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
    .main > div {
        padding-top: 2rem;
    }
    .step-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .step-header h1 {
        margin: 0;
        font-size: 1.8rem;
        font-weight: 600;
        color: white;
    }
    .step-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        color: white;
    }
    .student-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
    }
    .student-card h3 {
        margin: 0 0 0.5rem 0;
        font-size: 1.3rem;
    }
    .student-card .student-type {
        background: rgba(255, 255, 255, 0.2);
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        display: inline-block;
        font-size: 0.9rem;
        margin-bottom: 1rem;
    }
    .unit-info {
        background: linear-gradient(135deg, #fef3c7 0%, #fef9e7 100%);
        border: 1px solid #f59e0b;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .feedback-section {
        background: white;
        border-radius: 12px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border-left: 4px solid #10b981;
    }
    /* 다른 모든 CSS 스타일은 원래 코드와 동일하게 유지됩니다. */
    .curriculum-card { background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border: 2px solid #e2e8f0; border-radius: 12px; padding: 1.5rem; margin: 1rem 0; transition: all 0.3s ease; cursor: pointer; }
    .curriculum-card:hover { border-color: #667eea; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15); transform: translateY(-2px); }
    .curriculum-card.selected { border-color: #667eea; background: linear-gradient(135deg, #ede9fe 0%, #f3f4f6 100%); }
    .subject-badge { background: #667eea; color: white; padding: 0.3rem 0.8rem; border-radius: 15px; font-size: 0.8rem; font-weight: 600; margin-right: 0.5rem; }
    .edutech-card { background: white; border: 2px solid #e2e8f0; border-radius: 12px; padding: 1rem; margin: 0.5rem 0; transition: all 0.3s ease; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05); }
    .edutech-card:hover { border-color: #667eea; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15); transform: translateY(-2px); }
    .edutech-card.recommended { border-color: #10b981; background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 100%); }
    .edutech-card.ai-recommended { border-color: #8b5cf6; background: linear-gradient(135deg, #f3e8ff 0%, #faf5ff 100%); }
    .recommended-badge { background: #10b981; color: white; padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600; margin-left: 0.5rem; }
    .ai-recommended-badge { background: #8b5cf6; color: white; padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600; margin-left: 0.5rem; }
    .progress-container { background: white; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; border-left: 4px solid #667eea; }
    .stage-container { background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border-radius: 12px; padding: 1.5rem; margin: 1rem 0; border: 1px solid #e2e8f0; }
    .stage-title { color: #1e293b; font-size: 1.2rem; font-weight: 600; margin-bottom: 1rem; display: flex; align-items: center; }
    .loading-container { text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 12px; margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)

# --- 데이터 로드 함수 ---
@st.cache_data
def load_json_data():
    """JSON 파일들을 로드하는 함수"""
    data = {'curriculum': [], 'edutech': {}}
    try:
        with open('단원학습내용.json', 'r', encoding='utf-8') as f:
            data['curriculum'] = json.load(f)
        st.success("✅ 교육과정 데이터 로드 완료")
        
        with open('2023-2025 대한민국 초등 교실을 혁신하는 에듀테크 120.json', 'r', encoding='utf-8') as f:
            edutech_data = json.load(f)
            data['edutech'] = edutech_data
        st.success("✅ 에듀테크 데이터 로드 완료")
    except FileNotFoundError as e:
        st.error(f"❌ 파일을 찾을 수 없습니다: {e}")
    except json.JSONDecodeError as e:
        st.error(f"❌ JSON 파싱 오류: {e}")
    except Exception as e:
        st.error(f"❌ 데이터 로드 중 오류: {e}")
    return data

# --- 기본 AIDT 기능 정의 ---
AIDT_FEATURES = {
    'diagnosis': {'name': '🔍 학습진단 및 분석', 'description': '학생의 현재 수준과 취약점을 데이터로 확인합니다.', 'icon': '🔍'},
    'dashboard': {'name': '📊 교사 대시보드', 'description': '학생별 학습 현황과 이력을 실시간으로 관리합니다.', 'icon': '📊'},
    'path': {'name': '🛤️ 학습 경로 추천', 'description': '학생 수준에 맞는 학습 순서와 콘텐츠를 제안합니다.', 'icon': '🛤️'},
    'tutor': {'name': '🤖 지능형 AI 튜터', 'description': '1:1 맞춤형 힌트와 피드백을 제공하여 문제 해결을 돕습니다.', 'icon': '🤖'},
    'collaboration': {'name': '👥 소통 및 협업 도구', 'description': '모둠 구성, 과제 공동수행, 실시간 토론을 지원합니다.', 'icon': '👥'},
    'portfolio': {'name': '📁 디지털 포트폴리오', 'description': '학생의 학습 과정과 결과물을 자동으로 기록하고 관리합니다.', 'icon': '📁'},
}

# --- 데이터 로드 ---
json_data = load_json_data()

# --- 세션 상태 초기화 ---
if 'step' not in st.session_state:
    st.session_state.step = 1
    st.session_state.lesson_plan = {
        "subject": "", "grade": 0, "semester": 0, "unit": "", "topic": "",
        "student_name": None, "guidance": "", "model": None,
        "design": {'도입': [], '개별 학습': [], '협력 학습': [], '정리': []},
        "ai_recommendations": {}
    }
    st.session_state.generated_students = None # 생성된 학생 데이터 저장

# --- 헬퍼 함수 ---
def reset_app():
    """앱을 초기 상태로 리셋하는 함수"""
    st.session_state.step = 1
    st.session_state.lesson_plan = {
        "subject": "", "grade": 0, "semester": 0, "unit": "", "topic": "",
        "student_name": None, "guidance": "", "model": None,
        "design": {'도입': [], '개별 학습': [], '협력 학습': [], '정리': []},
        "ai_recommendations": {}
    }
    st.session_state.generated_students = None

def get_curriculum_options():
    """교육과정 데이터에서 선택지 추출"""
    if not json_data['curriculum']:
        return {}, {}
    
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
    return subjects, json_data['curriculum']

def generate_student_profiles_with_gemini(subject, grade, semester, unit):
    """Gemini를 통해 선택된 단원에 맞는 학생 프로필을 생성하는 함수"""
    try:
        gemini_api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=gemini_api_key)

        prompt = f"""
        당신은 초등학교 교육과정 전문가입니다.
        주어진 교과 단원 정보에 맞춰, 가상의 초등학생 프로필 3개를 생성해주세요.
        - 대상: 느린 학습자, 중간 학습자, 빠른 학습자 각 1명
        - 조건: 각 학생의 특성 설명과 학습 데이터는 반드시 주어진 단원 내용과 직접적으로 관련되어야 합니다.
        - 출력 형식: 반드시 아래와 같은 순수한 JSON 형식으로만 응답해주세요. 설명이나 다른 텍스트는 절대 포함하지 마세요.

        [입력 정보]
        - 교과: {subject}
        - 학년: {grade}
        - 학기: {semester}
        - 단원: {unit}

        [JSON 출력 형식 예시]
        {{
            "김O 학습자 (느린 학습자)": {{
                "name": "김O 학습자",
                "type": "느린 학습자",
                "description": "{unit} 단원의 기본 개념인 [핵심 개념 1]을 이해하는 데 어려움을 겪으며, 특히 [구체적 어려움] 부분에서 실수가 잦습니다. 시각적 자료나 구체적 조작 활동을 통해 학습할 때 효과가 좋습니다.",
                "data": [
                    {{ "평가": "[단원 관련 선행개념] 확인", "정답률": 45 }},
                    {{ "평가": "[단원 핵심개념 1] 형성평가", "정답률": 30 }},
                    {{ "평가": "[단원 핵심개념 2] 형성평가", "정답률": 40 }}
                ]
            }},
            "이O 학습자 (중간 학습자)": {{
                "name": "이O 학습자",
                "type": "중간 학습자",
                "description": "{unit} 단원의 기본 개념은 이해했지만, 응용 문제를 해결할 때 종종 실수를 합니다. 개념을 설명하도록 하면 주저하는 경향이 있어, 자신의 언어로 개념을 정리하는 연습이 필요합니다.",
                "data": [
                    {{ "평가": "[단원 관련 선행개념] 확인", "정답률": 80 }},
                    {{ "평가": "[단원 핵심개념 1] 형성평가", "정답률": 75 }},
                    {{ "평가": "[단원 핵심개념 2] 형성평가", "정답률": 65 }}
                ]
            }},
            "박O 학습자 (빠른 학습자)": {{
                "name": "박O 학습자",
                "type": "빠른 학습자",
                "description": "{unit} 단원의 학습 내용을 빠르게 습득하고 정확하게 문제를 해결합니다. 이미 대부분의 내용을 이해하고 있어, 도전적인 과제나 심화 문제를 통해 학습 동기를 유지시켜줄 필요가 있습니다.",
                "data": [
                    {{ "평가": "[단원 관련 선행개념] 확인", "정답률": 100 }},
                    {{ "평가": "[단원 핵심개념 1] 형성평가", "정답률": 95 }},
                    {{ "평가": "[단원 핵심개념 2] 단원평가 수준", "정답률": 90 }}
                ]
            }}
        }}
        """
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        # 응답 텍스트에서 JSON 부분만 추출
        clean_response = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(clean_response)

    except Exception as e:
        st.error(f"AI 학생 프로필 생성 중 오류 발생: {e}")
        return None
        
# --- 나머지 헬퍼 함수들은 원래 코드와 동일하게 유지됩니다 ---
def get_ai_recommendations():
    """Gemini를 통해 AIDT 기능 추천을 받는 함수"""
    try:
        gemini_api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=gemini_api_key)
        
        plan = st.session_state.lesson_plan
        student = st.session_state.generated_students[plan['student_name']]
        
        prompt = f"""
        당신은 초등교육 전문가입니다. 다음 정보를 바탕으로 수업 단계별로 가장 적합한 AIDT 기능을 추천해주세요.

        - 수업 주제: {plan['topic']}
        - 학생 유형: {student['type']}
        - 학생 특성: {student['description']}
        - 수업 모델: {plan['model']}
        - 맞춤 지도 계획: {plan['guidance']}

        사용 가능한 AIDT 기능:
        1. diagnosis: 학습진단 및 분석, 2. dashboard: 교사 대시보드, 3. path: 학습 경로 추천, 4. tutor: 지능형 AI 튜터, 5. collaboration: 소통 및 협업 도구, 6. portfolio: 디지털 포트폴리오
        
        각 수업 단계(도입, 개별 학습, 협력 학습, 정리)별로 추천하는 기능을 JSON 형식으로 답변해주세요.
        각 단계마다 1-3개의 기능을 추천하고, 추천 이유도 간단히 포함해주세요.

        응답 형식:
        {{
            "도입": {{"recommended": ["diagnosis"], "reason": "수업 시작 전 학생의 현재 수준을 파악하기 위해"}},
            "개별 학습": {{"recommended": ["path", "tutor"], "reason": "개별 맞춤 학습을 위해"}},
            "협력 학습": {{"recommended": ["collaboration"], "reason": "모둠 활동 지원을 위해"}},
            "정리": {{"recommended": ["portfolio", "dashboard"], "reason": "학습 결과 정리 및 기록을 위해"}}
        }}
        """
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match: return json.loads(json_match.group())
        return {}
        
    except Exception as e:
        st.error(f"AI 추천 생성 중 오류: {e}")
        return {}

def parse_feedback_from_gemini(text):
    """Gemini로부터 받은 텍스트를 파싱하여 딕셔너리로 변환하는 함수"""
    sections = {'strengths': [], 'suggestions': [], 'tools': []}
    current_section = None
    # 마크다운 헤더를 기준으로 파싱
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if '### 👍 수업의 강점' in line: current_section = 'strengths'
        elif '### 💡 발전 제안' in line: current_section = 'suggestions'
        elif '### 🛠️ 추가 에듀테크 도구 추천' in line: current_section = 'tools'
        elif current_section and (line.startswith('- ') or line.startswith('* ')):
            content = line[2:].strip()
            if current_section == 'tools' and ':' in content:
                name, desc = content.split(':', 1)
                sections[current_section].append({'name': name.strip(), 'description': desc.strip()})
            else:
                sections[current_section].append(content)
    return sections

def generate_lesson_plan_image(plan, feedback):
    """수업 설계안과 피드백을 바탕으로 JPG 이미지를 생성하는 함수"""
    width, height = 800, 1400
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    font_path = "NanumSquare_acB.ttf" 

    try:
        font_title = ImageFont.truetype(font_path, 28)
        font_header = ImageFont.truetype(font_path, 20)
        font_body = ImageFont.truetype(font_path, 14)
        font_small = ImageFont.truetype(font_path, 12)
    except IOError:
        st.warning(f"'{font_path}' 폰트 파일을 찾을 수 없어 기본 폰트로 이미지를 생성합니다.")
        font_title, font_header, font_body, font_small = [ImageFont.load_default() for _ in range(4)]

    y = 30
    draw.text((width/2, y), "AI 코칭 기반 맞춤수업 설계안", font=font_title, fill=(0,0,0), anchor="mt")
    y += 60

    # 1. 수업 분석
    draw.text((40, y), f"1. 수업 분석: {plan['topic']}", font=font_header, fill=(29, 78, 216)); y += 35
    student = st.session_state.generated_students[plan['student_name']]
    draw.text((50, y), f"■ 대상 학생: {student['name']} ({student['type']})", font=font_body, fill=(0,0,0)); y += 25
    
    # 2. 맞춤 지도 계획
    draw.text((40, y), "2. 맞춤 지도 계획", font=font_header, fill=(29, 78, 216)); y += 35
    lines = textwrap.wrap(plan['guidance'], width=80)
    for line in lines:
        draw.text((50, y), line, font=font_body, fill=(0,0,0)); y += 20
    y += 15

    # 3. 수업 설계
    draw.text((40, y), f"3. 수업 설계 ({plan['model']})", font=font_header, fill=(29, 78, 216)); y += 35
    for stage, features in plan['design'].items():
        if features:
            draw.text((50, y), f"■ {stage}:", font=font_body, fill=(0,0,0)); y += 25
            for feature in features:
                feature_name = AIDT_FEATURES.get(feature, {}).get('name', feature)
                draw.text((60, y), f"   - {feature_name}", font=font_small, fill=(50,50,50)); y += 18
            y += 10
    y += 15
    
    # 4. AI 종합 컨설팅
    draw.text((40, y), "4. AI 종합 컨설팅", font=font_header, fill=(29, 78, 216)); y += 35
    draw.text((50, y), "👍 수업의 강점", font=font_body, fill=(21, 128, 61)); y += 25
    for item in feedback['strengths']:
        lines = textwrap.wrap(f"   - {item}", width=80)
        for line in lines: draw.text((60, y), line, font=font_small, fill=(50,50,50)); y += 18
    y += 15

    draw.text((50, y), "💡 발전 제안", font=font_body, fill=(202, 138, 4)); y += 25
    for item in feedback['suggestions']:
        lines = textwrap.wrap(f"   - {item}", width=80)
        for line in lines: draw.text((60, y), line, font=font_small, fill=(50,50,50)); y += 18
    y += 15

    draw.text((50, y), "🛠️ 추가 에듀테크 도구 추천", font=font_body, fill=(37, 99, 235)); y += 25
    for tool in feedback['tools']:
        lines = textwrap.wrap(f"   - {tool['name']}: {tool['description']}", width=80)
        for line in lines: draw.text((60, y), line, font=font_small, fill=(50,50,50)); y += 18
    y += 15
    
    draw.text((width/2, height-50), "© 서울가동초등학교 백인규", font=font_small, fill=(150,150,150), anchor="mt")

    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()
    
# --- UI 렌더링 함수 ---
def step1_analysis():
    st.markdown("""
    <div class="step-header">
        <h1>🔍 1단계: 수업 및 학습자 분석</h1>
        <p>실제 교육과정 데이터를 활용하여 수업을 선택하고, AI를 통해 단원에 맞는 학습자 프로필을 생성합니다.</p>
    </div>
    """, unsafe_allow_html=True)
    
    subjects_data, _ = get_curriculum_options()
    if not subjects_data:
        st.error("교육과정 데이터를 로드할 수 없습니다."); return
    
    # --- 1. 교과 및 단원 선택 ---
    # (이 부분은 이전 코드와 동일)
    col1, col2, col3 = st.columns(3)
    with col1:
        subject = st.selectbox("📚 교과 선택", options=list(subjects_data.keys()))
    with col2:
        grades = list(subjects_data[subject].keys())
        grade = st.selectbox("👨‍🎓 학년 선택", options=grades)
    with col3:
        semesters = list(subjects_data[subject][grade].keys())
        semester = st.selectbox("📅 학기 선택", options=semesters)

    if subject and grade and semester:
        st.markdown("### 📖 단원 선택")
        units = subjects_data[subject][grade][semester]
        unit_options = [u['unit'] for u in units]
        
        selected_unit_name = st.radio("단원을 선택하세요:", options=unit_options, key="unit_selection")

        if selected_unit_name != st.session_state.lesson_plan['unit']:
            st.session_state.lesson_plan.update({
                'subject': subject, 'grade': grade, 'semester': semester,
                'unit': selected_unit_name,
                'topic': f"{subject} {grade}학년 {semester}학기 - {selected_unit_name}",
                'student_name': None
            })
            st.session_state.generated_students = None
            st.rerun()

        selected_unit = next((u for u in units if u['unit'] == selected_unit_name), None)
        if selected_unit:
            st.markdown(f"""
            <div class="unit-info">
                <h4>📋 선택된 단원 정보</h4>
                <p><strong>단원:</strong> {selected_unit['unit']}</p>
                <p><strong>영역:</strong> {selected_unit['area']}</p>
                <p><strong>성취기준:</strong> {selected_unit['achievement']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # --- 2. AI 학생 프로필 생성 ---
            st.markdown("### 👨‍🎓 AI 기반 학습자 프로필 생성")
            if st.session_state.generated_students is None:
                
                # ▼▼▼▼▼ [수정된 부분] ▼▼▼▼▼
                # 오류가 발생한 텍스트 줄 대신, st.info()를 사용하여 화면에 안내 메시지를 표시합니다.
                st.info("단원 선택이 완료되었습니다. 아래 버튼을 눌러 AI 학생 프로필을 생성해주세요.")
                # ▲▲▲▲▲ [수정된 부분] ▲▲▲▲▲

                if st.button("🤖 선택 단원 맞춤 AI 학생 프로필 생성", type="primary", use_container_width=True):
                    with st.spinner('🤖 AI가 맞춤 학생 프로필을 생성 중입니다... 잠시만 기다려주세요.'):
                        profiles = generate_student_profiles_with_gemini(subject, grade, semester, selected_unit_name)
                        if profiles:
                            st.session_state.generated_students = profiles
                            st.rerun()
                        else:
                            st.error("학생 프로필 생성에 실패했습니다. 다시 시도해주세요.")
            else:
                # (이후 코드는 이전과 동일)
                st.info("✅ AI 학생 프로필 생성이 완료되었습니다. 지도할 학생을 선택해주세요.")
                student_names = list(st.session_state.generated_students.keys())
                st.session_state.lesson_plan['student_name'] = st.selectbox(
                    "지도할 학생을 선택하세요", options=[None] + student_names,
                    format_func=lambda x: "학생을 선택하세요" if x is None else x
                )
                
                student_name = st.session_state.lesson_plan['student_name']
                if student_name:
                    student = st.session_state.generated_students[student_name]
                    st.markdown(f"""
                    <div class="student-card">
                        <h3>{student['name']} 학생 프로필</h3>
                        <div class="student-type">{student['type']}</div>
                        <p>{student['description']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.subheader("📈 학습 성취도 데이터")
                    cols = st.columns(len(student['data']))
                    for i, item in enumerate(student['data']):
                        with cols[i]:
                            st.metric(label=item['평가'], value=f"{item['정답률']}%")
                    
                    st.markdown("### ✍️ 맞춤 지도 계획")
                    st.session_state.lesson_plan['guidance'] = st.text_area(
                        "학생의 강점을 강화하고 약점을 보완하기 위한 지도 계획을 작성해 주세요.", height=120,
                        value=st.session_state.lesson_plan.get('guidance', '')
                    )

    # --- 5. 다음 단계로 이동 ---
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col3:
        if st.button("🚀 다음 단계로", type="primary", use_container_width=True):
            if (st.session_state.lesson_plan['topic'] and 
                st.session_state.lesson_plan['student_name'] and 
                st.session_state.lesson_plan['guidance']):
                st.session_state.step = 2
                st.rerun()
            else:
                st.error("⚠️ 모든 항목(단원, 학생, 지도계획)을 입력해주세요.")

# --- 나머지 step2, step3, step4, 메인 로직은 원래 코드와 거의 동일하게 유지됩니다 ---
# (단, STUDENT_DATA를 st.session_state.generated_students로 참조하는 부분만 수정)
def step2_method():
    st.markdown("""
    <div class="step-header">
        <h1>🎯 2단계: 교수·학습 방법 결정</h1>
        <p>수업의 목표와 학생 특성을 고려하여 적합한 수업 모델을 결정합니다.</p>
    </div>
    """, unsafe_allow_html=True)

    # AI 추천을 위한 질문
    col1, col2 = st.columns(2)
    with col1:
        q1 = st.radio("학생별 수준, 취약점 확인이 필요한가요?", ("선택하세요", "Yes", "No"), horizontal=True)
    with col2:
        q2 = st.radio("학습 목표 달성에 학생 간 수준 차이가 크게 영향을 미치나요?", ("선택하세요", "Yes", "No"), horizontal=True)

    recommended_model = None
    if q1 == "Yes" or q2 == "Yes": recommended_model = "개별 학습 우선 모델"
    elif q1 == "No" and q2 == "No": recommended_model = "협력 학습 중심 모델"

    if recommended_model:
        model_color = "#10b981" if "개별" in recommended_model else "#3b82f6"
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, {model_color}15 0%, {model_color}25 100%); border: 2px solid {model_color}; border-radius: 12px; padding: 1.5rem; margin: 2rem 0; text-align: center;">
            <h3 style="color: {model_color}; margin: 0;">🤖 AI 추천 수업 모델</h3>
            <h2 style="margin: 0.5rem 0; color: #1f2937;">{recommended_model}</h2>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---<h3>🎯 학습 모형 선택 (교사 선택)</h3>", unsafe_allow_html=True)
    learning_models = ["개별 학습 우선 모델", "협력 학습 중심 모델", "탐구 중심 모델", "프로젝트 기반 모델", "토의토론 중심 모델", "게임 기반 모델"]
    
    default_index = learning_models.index(recommended_model) if recommended_model in learning_models else 0
    selected_model = st.radio("학습 모형을 선택해주세요:", options=learning_models, index=default_index, key="learning_model_selection")
    st.session_state.lesson_plan['model'] = selected_model
    
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬅️ 이전 단계로", use_container_width=True): st.session_state.step = 1; st.rerun()
    with col3:
        if st.button("🚀 다음 단계로", type="primary", use_container_width=True): st.session_state.step = 3; st.rerun()

def step3_structure():
    st.markdown("""
    <div class="step-header">
        <h1>🏗️ 3단계: 수업 구조화 및 AIDT 기능 선택</h1>
        <p>수업 단계별로 활동을 구성하고, AI 추천을 참고하여 활용할 AIDT 기능을 최종 선택합니다.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.lesson_plan['ai_recommendations']:
        with st.spinner('🤖 AI가 최적의 AIDT 기능을 분석하고 추천하는 중입니다...'):
            st.session_state.lesson_plan['ai_recommendations'] = get_ai_recommendations()
    
    ai_recs = st.session_state.lesson_plan['ai_recommendations']
    student_type = st.session_state.generated_students[st.session_state.lesson_plan['student_name']]['type']
    
    stages = {'도입': '🚀', '개별 학습': '📚', '협력 학습': '👥', '정리': '🎯'}
    for stage, icon in stages.items():
        st.markdown(f"""<div class="stage-container"><div class="stage-title">{icon} {stage}</div></div>""", unsafe_allow_html=True)
        if ai_recs and stage in ai_recs and ai_recs[stage].get('reason'):
            st.info(f"🤖 **AI 추천**: {ai_recs[stage]['reason']}")
        
        selected_features = st.multiselect(
            f"{stage} 단계에서 사용할 기능을 선택하세요:",
            options=list(AIDT_FEATURES.keys()),
            format_func=lambda x: f"{AIDT_FEATURES[x]['icon']} {AIDT_FEATURES[x]['name']}",
            default=ai_recs.get(stage, {}).get('recommended', []),
            key=f"{stage}_multiselect"
        )
        st.session_state.lesson_plan['design'][stage] = selected_features

    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬅️ 이전 단계로", use_container_width=True): st.session_state.step = 2; st.rerun()
    with col2:
        if st.button("🔄 AI 추천 새로고침", use_container_width=True): st.session_state.lesson_plan['ai_recommendations'] = {}; st.rerun()
    with col3:
        if st.button("🎯 제출하고 컨설팅 받기", type="primary", use_container_width=True): st.session_state.step = 4; st.rerun()

def step4_feedback():
    st.markdown("""
    <div class="step-header">
        <h1>📋 4단계: AI 종합 컨설팅 보고서</h1>
        <p>제출하신 수업 설계안에 대한 AI의 분석과 제안입니다.</p>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        gemini_api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=gemini_api_key)
    except Exception:
        st.error("Gemini API 키를 설정해주세요."); return

    plan = st.session_state.lesson_plan
    student = st.session_state.generated_students[plan['student_name']]
    
    selected_features_info = ""
    for stage, features in plan['design'].items():
        if features:
            feature_names = [AIDT_FEATURES.get(f, {}).get('name', f) for f in features]
            selected_features_info += f"\n- {stage}: {', '.join(feature_names)}"
    
    prompt = f"""
    당신은 초등 교육 전문가이자 수업 설계 컨설턴트입니다.
    아래의 수업 설계안에 대해 '수업의 강점', '발전 제안', '추가 에듀테크 도구 추천' 세 가지 항목으로 나누어 구체적이고 전문적인 피드백을 한글로 제공해주세요. 피드백은 반드시 마크다운 형식에 맞춰 작성해주세요.

    - 수업 주제: {plan['topic']}
    - 대상 학생: {student['name']} ({student['type']})
    - 학생 특성: {student['description']}
    - 맞춤 지도 계획: {plan['guidance']}
    - 적용 수업 모델: {plan['model']}
    - 선택된 AIDT 기능: {selected_features_info}
    
    ### 👍 수업의 강점
    - [강점 1]
    - [강점 2]

    ### 💡 발전 제안
    - [제안 1]
    - [제안 2]

    ### 🛠️ 추가 에듀테크 도구 추천
    - **[도구 이름]**: [도구 설명 및 수업 활용 방안]
    - **[도구 이름]**: [도구 설명 및 수업 활용 방안]
    """

    with st.spinner('🤖 AI가 수업 설계안을 분석하고 컨설팅 보고서를 작성하는 중입니다...'):
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            feedback_text = response.text
            feedback_dict = parse_feedback_from_gemini(feedback_text)
            
            st.markdown(feedback_text, unsafe_allow_html=True)
            
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                st.download_button(
                    label="📥 결과물 JPG 다운로드",
                    data=generate_lesson_plan_image(plan, feedback_dict),
                    file_name=f"lesson_plan_{plan['student_name']}.jpg",
                    mime="image/jpeg",
                    use_container_width=True
                )
            with col3:
                if st.button("🆕 새로운 수업 설계하기", type="primary", use_container_width=True):
                    reset_app(); st.rerun()
        except Exception as e:
            st.error(f"❌ AI 컨설팅 보고서 생성 중 오류가 발생했습니다: {e}")

# --- 메인 앱 로직 ---
st.markdown("""
<div style="text-align: center; padding: 2rem 0; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 15px; margin-bottom: 2rem;">
    <h1 style="margin: 0; font-size: 2.5rem; color: white;">🎯 AI 코칭 기반 맞춤수업 설계 시뮬레이터</h1>
    <p style="margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 1.1rem; color: white;">실제 교육과정 데이터와 AI로 만드는 맞춤형 수업</p>
</div>
""", unsafe_allow_html=True)

progress = st.session_state.step / 4
st.progress(progress, text=f"진행률: {int(progress * 100)}% ({st.session_state.step}/4 단계)")

if st.session_state.step == 1:
    step1_analysis()
elif st.session_state.step == 2:
    step2_method()
elif st.session_state.step == 3:
    step3_structure()
elif st.session_state.step == 4:
    step4_feedback()

st.markdown("""
<div style="position: fixed; bottom: 10px; left: 50%; transform: translateX(-50%); background: rgba(255, 255, 255, 0.9); padding: 0.5rem 1rem; border-radius: 20px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1); font-size: 0.8rem; color: #6b7280; z-index: 999;">
    © 서울가동초등학교 백인규
</div>
""", unsafe_allow_html=True)
