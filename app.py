    
    # Gemini에게 전달할 프롬프트 생성
    selected_features_info = ""
    for stage, features in plan['design'].items():
        if features:
            feature_names = [AIDT_FEATURES.get(f, {}).get('name', f) for f in features]
            selected_features_info += f"\n{stage}: {', '.join(feature_names)}"
    
    prompt = f"""
    당신은 초등 교육 전문가이자 수업 설계 컨설턴트입니다.
    아래의 수업 설계안에 대해 '수업의 강점', '발전 제안', '추가 에듀테크 도구 추천' 세 가지 항목으로 나누어 구체적이고 전문적인 피드백을 제공해주세요.
    
    - 수업 주제: {plan['topic']}
    - 대상 학생: {STUDENT_DATA[plan['student_name']]['name']} ({STUDENT_DATA[plan['student_name']]['type']})
    - 학생 특성: {STUDENT_DATA[plan['student_name']]['description']}
    - 맞춤 지도 계획: {plan['guidance']}
    - 적용 수업 모델: {plan['model']}
    - 선택된 AIDT 기능: {selected_features_info}
    
    피드백은 반드시 아래 형식에 맞춰 한글로 작성해주세요.

    ### 👍 수업의 강점
    - [강점 1]
    - [강점 2]

    ### 💡 발전 제안
    - [제안 1]
    - [제안 2]

    ### 🛠️ 추가 에듀테크 도구 추천
    - [도구 이름]: [도구 설명]
    - [도구 이름]: [도구 설명]
    """

    # AI 모델 호출 및 피드백 생성
    with st.spinner('🤖 AI가 수업 설계안을 분석하고 컨설팅 보고서를 작성하는 중입니다...'):
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            feedback_text = response.text
            
            feedback_dict = parse_feedback_from_gemini(feedback_text)
            
            st.markdown("""
            <div class="feedback-section">
            """, unsafe_allow_html=True)
            st.markdown(feedback_text)
            st.markdown("</div>", unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                st.download_button(
                    label="📥 결과물 JPG 다운로드",
                    data=generate_lesson_plan_image(plan, feedback_dict),
                    file_name=f"lesson_plan_{plan['student_name']}_{plan['unit']}.jpg",
                    mime="image/jpeg",
                    use_container_width=True
                )
            with col3:
                if st.button("🆕 새로운 수업 설계하기", type="primary", use_container_width=True):
                    reset_app()
                    st.rerun()

        except Exception as e:
            st.error(f"❌ AI 컨설팅 보고서 생성 중 오류가 발생했습니다: {e}")
            
            # 오류가 발생해도 기본 피드백과 다운로드는 제공
            basic_feedback = {
                'strengths': [f"'{STUDENT_DATA[plan['student_name']]['name']}' 학생을 위한 체계적인 수업 설계를 완료했습니다."],
                'suggestions': ["AI 컨설팅 기능에 일시적 오류가 발생했지만, 수업 설계안은 정상적으로 완성되었습니다."],
                'tools': []
            }
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                st.download_button(
                    label="📥 결과물 JPG 다운로드",
                    data=generate_lesson_plan_image(plan, basic_feedback),
                    file_name=f"lesson_plan_{plan['student_name']}_{plan['unit']}.jpg",
                    mime="image/jpeg",
                    use_container_width=True
                )
            with col3:
                if st.button("🆕 새로운 수업 설계하기", type="primary", use_container_width=True):
                    reset_app()
                    st.rerun()import streamlit as st
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
    
    .curriculum-card {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border: 2px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .curriculum-card:hover {
        border-color: #667eea;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
        transform: translateY(-2px);
    }
    
    .curriculum-card.selected {
        border-color: #667eea;
        background: linear-gradient(135deg, #ede9fe 0%, #f3f4f6 100%);
    }
    
    .subject-badge {
        background: #667eea;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 0.5rem;
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
    
    .edutech-card {
        background: white;
        border: 2px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .edutech-card:hover {
        border-color: #667eea;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
        transform: translateY(-2px);
    }
    
    .edutech-card.recommended {
        border-color: #10b981;
        background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 100%);
    }
    
    .edutech-card.ai-recommended {
        border-color: #8b5cf6;
        background: linear-gradient(135deg, #f3e8ff 0%, #faf5ff 100%);
    }
    
    .recommended-badge {
        background: #10b981;
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-left: 0.5rem;
    }
    
    .ai-recommended-badge {
        background: #8b5cf6;
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-left: 0.5rem;
    }
    
    .progress-container {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
    }
    
    .stage-container {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid #e2e8f0;
    }
    
    .stage-title {
        color: #1e293b;
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
    }
    
    .loading-container {
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 12px;
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
    
    .unit-info {
        background: linear-gradient(135deg, #fef3c7 0%, #fef9e7 100%);
        border: 1px solid #f59e0b;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# --- 데이터 로드 함수 ---
@st.cache_data
def load_json_data():
    """JSON 파일들을 로드하는 함수"""
    data = {
        'curriculum': [],
        'edutech': {}
    }
    
    try:
        # 단원학습내용.json 로드
        with open('단원학습내용.json', 'r', encoding='utf-8') as f:
            data['curriculum'] = json.load(f)
        st.success("✅ 교육과정 데이터 로드 완료")
        
        # 에듀테크 JSON 로드
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

# --- 데이터 로드 ---
json_data = load_json_data()

# --- 기본 AIDT 기능 정의 ---
AIDT_FEATURES = {
  'diagnosis': {
    'name': '🔍 학습진단 및 분석', 
    'description': '학생의 현재 수준과 취약점을 데이터로 확인합니다.',
    'icon': '🔍'
  },
  'dashboard': {
    'name': '📊 교사 대시보드', 
    'description': '학생별 학습 현황과 이력을 실시간으로 관리합니다.',
    'icon': '📊'
  },
  'path': {
    'name': '🛤️ 학습 경로 추천', 
    'description': '학생 수준에 맞는 학습 순서와 콘텐츠를 제안합니다.',
    'icon': '🛤️'
  },
  'tutor': {
    'name': '🤖 지능형 AI 튜터', 
    'description': '1:1 맞춤형 힌트와 피드백을 제공하여 문제 해결을 돕습니다.',
    'icon': '🤖'
  },
  'collaboration': {
    'name': '👥 소통 및 협업 도구', 
    'description': '모둠 구성, 과제 공동수행, 실시간 토론을 지원합니다.',
    'icon': '👥'
  },
  'portfolio': {
    'name': '📁 디지털 포트폴리오', 
    'description': '학생의 학습 과정과 결과물을 자동으로 기록하고 관리합니다.',
    'icon': '📁'
  },
}

STUDENT_DATA = {
  '이OO': {
    'name': '이OO',
    'type': '느린 학습자',
    'description': '평소 자리 정리를 잘 하지 않으며, 교사가 근처에 오면 급히 공부하는 척하는 모습을 보입니다. 특히 시각적, 공간적 이해를 요구하는 개념에 어려움을 겪습니다.',
    'data': [
      { "평가": "형성평가: 각", "정답률": 80 },
      { "평가": "형성평가: 직각", "정답률": 40 },
      { "평가": "형성평가: 직사각형", "정답률": 60 },
      { "평가": "AI 맞춤 진단", "정답률": 30 },
    ],
  },
  '정OO': {
    'name': '정OO',
    'type': '빠른 학습자',
    'description': '수업에 적극적이고 과제 해결 속도가 빠르지만, 조별 활동 시 친구들과의 마찰이 잦습니다. 학업 성취도는 높으나 협업 능력에 대한 지도가 필요합니다.',
    'data': [
      { "평가": "형성평가: 각", "정답률": 100 },
      { "평가": "형성평가: 직각", "정답률": 100 },
      { "평가": "단원평가", "정답률": 95 },
    ],
  },
  '조OO': {
    'name': '조OO',
    'type': '보통 학습자',
    'description': '내성적이고 조용하며 발표 시 긴장하는 경향이 있습니다. 평균적인 성취도를 보이나, 개념 이해에 대한 정서적 지지와 격려가 필요합니다.',
    'data': [
      { "평가": "형성평가: 똑같이 나누기", "정답률": 60 },
      { "평가": "형성평가: 곱셈과 나눗셈 관계", "정답률": 60 },
      { "평가": "평균 정답률", "정답률": 70 },
    ],
  }
}

# --- 세션 상태 초기화 ---
if 'step' not in st.session_state:
    st.session_state.step = 1
    st.session_state.lesson_plan = {
        "subject": "",
        "grade": 0,
        "semester": 0,
        "unit": "",
        "topic": "",
        "student_name": None,
        "guidance": "",
        "model": None,
        "design": {'도입': [], '개별 학습': [], '협력 학습': [], '정리': []},
        "ai_recommendations": {}
    }

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
        
        if subject not in subjects:
            subjects[subject] = {}
        if grade not in subjects[subject]:
            subjects[subject][grade] = {}
        if semester not in subjects[subject][grade]:
            subjects[subject][grade][semester] = []
        
        subjects[subject][grade][semester].append({
            'unit': unit,
            'achievement': item.get('성취기준', ''),
            'content': item.get('단원학습내용', ''),
            'area': item.get('영역', '')
        })
    
    return subjects, json_data['curriculum']

def get_ai_recommendations():
    """Gemini를 통해 AIDT 기능 추천을 받는 함수"""
    try:
        gemini_api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=gemini_api_key)
        
        plan = st.session_state.lesson_plan
        student = STUDENT_DATA[plan['student_name']]
        
        prompt = f"""
        당신은 초등교육 전문가입니다. 다음 정보를 바탕으로 수업 단계별로 가장 적합한 AIDT 기능을 추천해주세요.

        - 수업 주제: {plan['topic']}
        - 학생 유형: {student['type']}
        - 학생 특성: {student['description']}
        - 수업 모델: {plan['model']}
        - 맞춤 지도 계획: {plan['guidance']}

        사용 가능한 AIDT 기능:
        1. diagnosis: 학습진단 및 분석
        2. dashboard: 교사 대시보드  
        3. path: 학습 경로 추천
        4. tutor: 지능형 AI 튜터
        5. collaboration: 소통 및 협업 도구
        6. portfolio: 디지털 포트폴리오

        각 수업 단계(도입, 개별 학습, 협력 학습, 정리)별로 추천하는 기능을 JSON 형식으로 답변해주세요.
        각 단계마다 1-3개의 기능을 추천하고, 추천 이유도 간단히 포함해주세요.

        응답 형식:
        {{
            "도입": {{
                "recommended": ["diagnosis"],
                "reason": "수업 시작 전 학생의 현재 수준을 파악하기 위해"
            }},
            "개별 학습": {{
                "recommended": ["path", "tutor"],
                "reason": "개별 맞춤 학습을 위해"
            }},
            "협력 학습": {{
                "recommended": ["collaboration"],
                "reason": "모둠 활동 지원을 위해"
            }},
            "정리": {{
                "recommended": ["portfolio", "dashboard"],
                "reason": "학습 결과 정리 및 기록을 위해"
            }}
        }}
        """
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        # JSON 응답 파싱
        import re
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {}
        
    except Exception as e:
        st.error(f"AI 추천 생성 중 오류: {e}")
        return {}

def parse_feedback_from_gemini(text):
    """Gemini로부터 받은 텍스트를 파싱하여 딕셔너리로 변환하는 함수"""
    sections = {'strengths': [], 'suggestions': [], 'tools': []}
    current_section = None
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        if '수업의 강점' in line:
            current_section = 'strengths'
        elif '발전 제안' in line:
            current_section = 'suggestions'
        elif '추가 디지털 도구 추천' in line:
            current_section = 'tools'
        elif current_section:
            if line.startswith('- '):
                content = line[2:].strip()
                if current_section == 'tools':
                    if ':' in content:
                        name, desc = content.split(':', 1)
                        sections[current_section].append({'name': name.strip(), 'description': desc.strip()})
                else:
                    sections[current_section].append(content)
    return sections

def generate_lesson_plan_image(plan, feedback):
    """수업 설계안과 피드백을 바탕으로 JPG 이미지를 생성하는 함수"""
    width, height = 800, 1200
    bg_color = (255, 255, 255)
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    font_path = "NanumSquare_acB.ttf" 

    try:
        if not os.path.exists(font_path):
            raise IOError
        font_title = ImageFont.truetype(font_path, 28)
        font_header = ImageFont.truetype(font_path, 20)
        font_body = ImageFont.truetype(font_path, 14)
        font_small = ImageFont.truetype(font_path, 12)
    except IOError:
        st.warning(f"'{font_path}' 폰트 파일을 찾을 수 없습니다. 결과물 이미지가 영문으로 표시될 수 있습니다.")
        font_title = ImageFont.load_default()
        font_header = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_small = ImageFont.load_default()

    y = 30
    draw.text((width/2, y), "AI 코칭 기반 맞춤수업 설계안", font=font_title, fill=(0,0,0), anchor="mt")
    y += 60

    draw.text((40, y), f"1. 수업 분석: {plan['subject']} {plan['grade']}학년 {plan['semester']}학기", font=font_header, fill=(29, 78, 216))
    y += 35
    draw.text((50, y), f"■ 단원: {plan['unit']}", font=font_body, fill=(0,0,0))
    y += 25
    student = STUDENT_DATA[plan['student_name']]
    draw.text((50, y), f"■ 대상 학생: {student['name']} ({student['type']})", font=font_body, fill=(0,0,0))
    y += 25
    
    draw.text((40, y), "2. 맞춤 지도 계획", font=font_header, fill=(29, 78, 216))
    y += 35
    lines = textwrap.wrap(plan['guidance'], width=80)
    for line in lines:
        draw.text((50, y), line, font=font_body, fill=(0,0,0))
        y += 20
    y += 15

    draw.text((40, y), f"3. 수업 설계 ({plan['model']})", font=font_header, fill=(29, 78, 216))
    y += 35
    
    edutech_tools = categorize_edutech_tools(json_data['edutech'])
    for stage, selected_tools in plan['design'].items():
        if selected_tools:
            draw.text((50, y), f"■ {stage}:", font=font_body, fill=(0,0,0))
            y += 25
            for tool_name in selected_tools:
                draw.text((60, y), f"  - {tool_name}", font=font_small, fill=(50,50,50))
                y += 18
            y += 10
    y += 15
    
    draw.text((40, y), "4. AI 종합 컨설팅", font=font_header, fill=(29, 78, 216))
    y += 35
    
    draw.text((50, y), "👍 수업의 강점", font=font_body, fill=(21, 128, 61))
    y += 25
    for item in feedback['strengths']:
        lines = textwrap.wrap(f"  - {item}", width=80)
        for line in lines:
            draw.text((60, y), line, font=font_small, fill=(50,50,50))
            y += 18
    y += 15

    draw.text((50, y), "💡 발전 제안", font=font_body, fill=(202, 138, 4))
    y += 25
    for item in feedback['suggestions']:
        lines = textwrap.wrap(f"  - {item}", width=80)
        for line in lines:
            draw.text((60, y), line, font=font_small, fill=(50,50,50))
            y += 18

    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()

# --- UI 렌더링 함수 ---
def step1_analysis():
    st.markdown("""
    <div class="step-header">
        <h1>🔍 1단계: 수업 및 학습자 분석</h1>
        <p>실제 교육과정 데이터를 활용하여 수업을 선택하고, 학생 데이터를 분석하여 지도 계획을 수립합니다.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 교육과정 데이터 로드
    subjects_data, curriculum_data = get_curriculum_options()
    
    if not subjects_data:
        st.error("교육과정 데이터를 로드할 수 없습니다.")
        return
    
    # 교과 선택
    col1, col2, col3 = st.columns(3)
    
    with col1:
        subject = st.selectbox(
            "📚 교과 선택",
            options=list(subjects_data.keys()),
            index=list(subjects_data.keys()).index(st.session_state.lesson_plan['subject']) if st.session_state.lesson_plan['subject'] in subjects_data else 0
        )
    
    with col2:
        if subject:
            grades = list(subjects_data[subject].keys())
            grade = st.selectbox(
                "👨‍🎓 학년 선택", 
                options=grades,
                index=grades.index(st.session_state.lesson_plan['grade']) if st.session_state.lesson_plan['grade'] in grades else 0
            )
    
    with col3:
        if subject and grade:
            semesters = list(subjects_data[subject][grade].keys())
            semester = st.selectbox(
                "📅 학기 선택",
                options=semesters,
                index=semesters.index(st.session_state.lesson_plan['semester']) if st.session_state.lesson_plan['semester'] in semesters else 0
            )
    
    # 단원 선택
    if subject and grade and semester:
        st.markdown("### 📖 단원 선택")
        units = subjects_data[subject][grade][semester]
        
        # 라디오 버튼으로 단원 선택
        unit_options = [unit_data['unit'] for unit_data in units]
        if unit_options:
            selected_unit_name = st.radio(
                "단원을 선택하세요:",
                options=unit_options,
                index=unit_options.index(st.session_state.lesson_plan['unit']) if st.session_state.lesson_plan['unit'] in unit_options else 0,
                key="unit_selection"
            )
            
            # 선택된 단원 정보 업데이트
            if selected_unit_name != st.session_state.lesson_plan['unit']:
                st.session_state.lesson_plan.update({
                    'subject': subject,
                    'grade': grade,
                    'semester': semester,
                    'unit': selected_unit_name,
                    'topic': f"{subject} {grade}학년 {semester}학기 {selected_unit_name}"
                })
            
            # 선택된 단원의 상세 정보 표시
            selected_unit = next((unit for unit in units if unit['unit'] == selected_unit_name), None)
            if selected_unit:
                st.markdown(f"""
                <div class="unit-info">
                    <h4>📋 선택된 단원 정보</h4>
                    <p><strong>단원:</strong> {selected_unit['unit']}</p>
                    <p><strong>영역:</strong> {selected_unit['area']}</p>
                    <p><strong>성취기준:</strong> {selected_unit['achievement']}</p>
                    <p><strong>학습내용:</strong> {selected_unit['content']}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("해당 학년/학기에 등록된 단원이 없습니다.")
    
    # 데이터에 없는 교과목도 추가할 수 있도록 직접 입력 옵션 제공
    st.markdown("---")
    st.markdown("### ✏️ 또는 직접 입력")
    
    col1, col2 = st.columns(2)
    with col1:
        custom_subject = st.text_input("교과목 직접 입력", placeholder="예: 과학, 사회, 영어 등")
    with col2:
        custom_topic = st.text_input("수업 주제 직접 입력", placeholder="예: 5학년 과학 - 태양계와 별")
    
    if custom_subject and custom_topic:
        if st.button("직접 입력한 내용으로 설정", use_container_width=True):
            st.session_state.lesson_plan.update({
                'subject': custom_subject,
                'grade': 0,  # 직접 입력 시에는 0으로 설정
                'semester': 0,
                'unit': custom_topic,
                'topic': custom_topic
            })
            st.success(f"✅ '{custom_topic}' 주제로 설정되었습니다!")
            st.rerun()
    
    # 학생 선택
    st.markdown("### 👨‍🎓 지도할 학생 선택")
    student_names = list(STUDENT_DATA.keys())
    st.session_state.lesson_plan['student_name'] = st.selectbox(
        "",
        options=[None] + student_names,
        format_func=lambda x: "학생을 선택하세요" if x is None else x,
        label_visibility="collapsed"
    )

    student_name = st.session_state.lesson_plan['student_name']
    if student_name:
        student = STUDENT_DATA[student_name]
        
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
                st.markdown(f"""
                <div class="progress-container">
                    <strong>{item['평가']}</strong>
                </div>
                """, unsafe_allow_html=True)
                st.progress(item['정답률']/100, text=f"{item['정답률']}%")
        
        st.markdown("### ✍️ 맞춤 지도 계획")
        st.session_state.lesson_plan['guidance'] = st.text_area(
            "",
            height=120,
            placeholder=f"{student_name} 학생의 강점을 강화하고 약점을 보완하기 위한 지도 계획을 작성해 주세요.",
            label_visibility="collapsed",
            value=st.session_state.lesson_plan['guidance']
        )
    
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
                st.error("⚠️ 모든 항목을 입력해주세요.")

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
        st.markdown("### 💭 질문 1")
        q1 = st.radio(
            "학생별 수준, 취약점 확인이 필요한가요?", 
            ("선택하세요", "Yes", "No"), 
            horizontal=True,
            key="q1"
        )
    
    with col2:
        st.markdown("### 💭 질문 2")
        q2 = st.radio(
            "학습 목표 달성에 학생 간 수준 차이가 크게 영향을 미치나요?", 
            ("선택하세요", "Yes", "No"), 
            horizontal=True,
            key="q2"
        )

    # AI 추천 모델 표시
    recommended_model = None
    if q1 == "Yes" or q2 == "Yes":
        recommended_model = "개별 학습 우선 모델"
        model_description = "학생 개별 맞춤형 학습을 우선으로 하는 수업 모델입니다."
        model_color = "#10b981"
    elif q1 == "No" and q2 == "No":
        recommended_model = "협력 학습 중심 모델"
        model_description = "학생들 간의 협력과 상호작용을 중심으로 하는 수업 모델입니다."
        model_color = "#3b82f6"

    if recommended_model:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, {model_color}15 0%, {model_color}25 100%);
            border: 2px solid {model_color};
            border-radius: 12px;
            padding: 1.5rem;
            margin: 2rem 0;
            text-align: center;
        ">
            <h3 style="color: {model_color}; margin: 0;">🤖 AI 추천 수업 모델</h3>
            <h2 style="margin: 0.5rem 0; color: #1f2937;">{recommended_model}</h2>
            <p style="margin: 0; color: #6b7280;">{model_description}</p>
        </div>
        """, unsafe_allow_html=True)

    # 교사가 직접 선택할 수 있는 학습 모형 옵션들
    st.markdown("---")
    st.markdown("### 🎯 학습 모형 선택 (교사 선택)")
    st.markdown("AI 추천을 참고하되, 최종 결정은 교사가 직접 선택해주세요.")
    
    learning_models = {
        "개별 학습 우선 모델": {
            "description": "학생 개별 맞춤형 학습을 우선으로 하는 수업 모델",
            "characteristics": "• 개별 진단 및 맞춤 학습\n• 학습자 중심 자기주도학습\n• 개별 피드백 중심",
            "suitable": "학습 격차가 큰 경우, 기초학력 보충이 필요한 경우"
        },
        "협력 학습 중심 모델": {
            "description": "학생들 간의 협력과 상호작용을 중심으로 하는 수업 모델",
            "characteristics": "• 모둠별 협력 활동\n• 토론 및 발표 중심\n• 상호 피드백",
            "suitable": "의사소통 능력 향상, 사회성 발달이 필요한 경우"
        },
        "탐구 중심 모델": {
            "description": "학생들이 스스로 문제를 발견하고 해결하는 탐구 활동 중심 모델",
            "characteristics": "• 문제 발견 및 가설 설정\n• 실험 및 관찰 활동\n• 결론 도출 및 발표",
            "suitable": "과학적 사고력, 창의적 문제해결력 신장이 목표인 경우"
        },
        "프로젝트 기반 모델": {
            "description": "실제적인 프로젝트를 통해 학습하는 모델",
            "characteristics": "• 실생활 연계 주제\n• 장기간 프로젝트 수행\n• 창작물 제작 및 발표",
            "suitable": "융합적 사고, 실무 능력 개발이 필요한 경우"
        },
        "토의토론 중심 모델": {
            "description": "다양한 관점을 나누고 토론하는 활동 중심 모델",
            "characteristics": "• 찬반 토론 및 합의\n• 비판적 사고력 개발\n• 논리적 표현력 향상",
            "suitable": "의사소통능력, 논리적 사고력 향상이 목표인 경우"
        },
        "게임 기반 모델": {
            "description": "게임적 요소를 활용한 재미있는 학습 모델",
            "characteristics": "• 게임화 요소 적용\n• 경쟁과 협력의 균형\n• 즉시 피드백",
            "suitable": "학습 동기 유발, 참여도 향상이 필요한 경우"
        }
    }
    
    # 모델 선택을 위한 라디오 버튼
    model_options = list(learning_models.keys())
    
    # AI 추천 모델을 기본값으로 설정
    default_index = 0
    if recommended_model and recommended_model in model_options:
        default_index = model_options.index(recommended_model)
    elif st.session_state.lesson_plan['model'] in model_options:
        default_index = model_options.index(st.session_state.lesson_plan['model'])
    
    selected_model = st.radio(
        "학습 모형을 선택해주세요:",
        options=model_options,
        index=default_index,
        key="learning_model_selection"
    )
    
    # 선택된 모델 정보 표시
    if selected_model:
        model_info = learning_models[selected_model]
        
        # AI 추천 여부 표시
        is_ai_recommended = selected_model == recommended_model
        badge = " 🤖 AI 추천" if is_ai_recommended else ""
        
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
            border: 2px solid {'#10b981' if is_ai_recommended else '#e2e8f0'};
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
        ">
            <h3 style="color: #1f2937; margin: 0 0 0.5rem 0;">{selected_model}{badge}</h3>
            <p style="color: #6b7280; margin: 0 0 1rem 0; font-size: 1rem;"><strong>{model_info['description']}</strong></p>
            <div style="margin-bottom: 1rem;">
                <strong style="color: #374151;">🔸 특징:</strong>
                <pre style="color: #6b7280; margin: 0.5rem 0; font-family: inherit; white-space: pre-wrap;">{model_info['characteristics']}</pre>
            </div>
            <div>
                <strong style="color: #374151;">🎯 적합한 상황:</strong>
                <p style="color: #6b7280; margin: 0.5rem 0;">{model_info['suitable']}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.session_state.lesson_plan['model'] = selected_model

    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬅️ 이전 단계로", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
    with col3:
        if st.button("🚀 다음 단계로", type="primary", disabled=not selected_model, use_container_width=True):
            st.session_state.step = 3
            st.rerun()

def step3_structure():
    st.markdown("""
    <div class="step-header">
        <h1>🏗️ 3단계: 수업 구조화 및 AIDT 기능 선택</h1>
        <p>수업 단계별로 활동을 구성하고, AI 추천을 참고하여 활용할 AIDT 기능을 최종 선택합니다.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # AI 추천 받기
    if 'ai_recommendations' not in st.session_state.lesson_plan or not st.session_state.lesson_plan['ai_recommendations']:
        with st.spinner('🤖 AI가 최적의 AIDT 기능을 분석하고 추천하는 중입니다...'):
            st.session_state.lesson_plan['ai_recommendations'] = get_ai_recommendations()
    
    ai_recs = st.session_state.lesson_plan['ai_recommendations']
    
    # 기본 추천 로직 (AI 추천이 없을 경우)
    student_type = STUDENT_DATA[st.session_state.lesson_plan['student_name']]['type']
    model = st.session_state.lesson_plan['model']
    
    default_recs = {'도입': ['diagnosis'], '개별 학습': [], '협력 학습': [], '정리': ['portfolio', 'dashboard']}
    if model == '개별 학습 우선 모델':
        default_recs['개별 학습'].append('path')
        if student_type == '느린 학습자':
            default_recs['개별 학습'].append('tutor')
        default_recs['협력 학습'].append('collaboration')
    else:
        default_recs['협력 학습'].append('collaboration')
        if student_type == '빠른 학습자':
            default_recs['개별 학습'].append('path')

    stage_icons = {'도입': '🚀', '개별 학습': '📚', '협력 학습': '👥', '정리': '🎯'}
    stages = ['도입', '개별 학습', '협력 학습', '정리']
    
    for stage in stages:
        st.markdown(f"""
        <div class="stage-container">
            <div class="stage-title">
                {stage_icons[stage]} {stage}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # AI 추천 표시
        if ai_recs and stage in ai_recs:
            ai_recommended_features = ai_recs[stage].get('recommended', [])
            reason = ai_recs[stage].get('reason', '')
            if ai_recommended_features:
                st.info(f"🤖 **AI 추천**: {reason}")
        
        # AIDT 기능 선택
        options = list(AIDT_FEATURES.keys())
        selected_features = []
        
        # 기본 선택값 설정
        current_selections = st.session_state.lesson_plan['design'].get(stage, [])
        if not current_selections:
            ai_recommended = ai_recs.get(stage, {}).get('recommended', []) if ai_recs else []
            default_selection = ai_recommended if ai_recommended else default_recs.get(stage, [])
        else:
            default_selection = current_selections
        
        # 체크박스 형태로 기능 선택
        cols = st.columns(2)
        
        for i, feature_key in enumerate(options):
            feature = AIDT_FEATURES[feature_key]
            col_idx = i % 2
            
            with cols[col_idx]:
                # 추천 상태 확인
                is_ai_recommended = ai_recs and stage in ai_recs and feature_key in ai_recs[stage].get('recommended', [])
                is_default_recommended = feature_key in default_recs.get(stage, [])
                is_selected = feature_key in default_selection
                
                # 체크박스
                is_checked = st.checkbox(
                    "",
                    value=is_selected,
                    key=f"{stage}_{feature_key}",
                    label_visibility="collapsed"
                )
                
                if is_checked:
                    selected_features.append(feature_key)
                
                # 기능 카드
                card_class = "edutech-card"
                badge_html = ""
                
                if is_ai_recommended:
                    card_class += " ai-recommended"
                    badge_html = '<span class="ai-recommended-badge">AI 추천</span>'
                elif is_default_recommended:
                    card_class += " recommended"
                    badge_html = '<span class="recommended-badge">기본 추천</span>'
                
                st.markdown(f"""
                <div class="{card_class}">
                    <h4 style="margin: 0 0 0.5rem 0; color: #1f2937;">
                        {feature['name']} {badge_html}
                    </h4>
                    <p style="margin: 0; color: #6b7280; font-size: 0.9rem;">
                        {feature['description']}
                    </p>
                </div>
                """, unsafe_allow_html=True)
        
        st.session_state.lesson_plan['design'][stage] = selected_features
    
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬅️ 이전 단계로", use_container_width=True):
            st.session_state.step = 2
            st.rerun()
    with col2:
        if st.button("🔄 AI 추천 새로고침", use_container_width=True):
            st.session_state.lesson_plan['ai_recommendations'] = {}
            st.rerun()
    with col3:
        if st.button("🎯 제출하고 컨설팅 받기", type="primary", use_container_width=True):
            st.session_state.step = 4
            st.rerun()

def step4_feedback():
    st.markdown("""
    <div class="step-header">
        <h1>📋 4단계: AI 종합 컨설팅 보고서</h1>
        <p>제출하신 수업 설계안에 대한 AI의 분석과 제안입니다.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Gemini API 키 설정
    try:
        gemini_api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=gemini_api_key)
        api_available = True
    except (KeyError, AttributeError):
        api_available = False
        st.info("ℹ️ Gemini API 키가 설정되지 않았습니다. 규칙 기반의 기본 피드백이 제공됩니다.")
        
    plan = st.session_state.lesson_plan
    
    if not api_available:
        # 기본 피드백 로직
        student = STUDENT_DATA[plan['student_name']]
        feedback = {
            'strengths': [f"'{student['name']}' 학생을 위한 실제 교육과정 연계 수업 설계를 완료했습니다."],
            'suggestions': ["AI 컨설팅 기능을 사용하려면 Gemini API 키를 설정해주세요."],
            'tools': []
        }
        
        st.markdown("""
        <div class="feedback-section">
            <h3>👍 수업의 강점</h3>
        </div>
        """, unsafe_allow_html=True)
        for item in feedback['strengths']: 
            st.markdown(f"- {item}")
        
        st.markdown("""
        <div class="feedback-section">
            <h3>💡 발전 제안</h3>
        </div>
        """, unsafe_allow_html=True)
        for item in feedback['suggestions']: 
            st.markdown(f"- {item}")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🆕 새로운 수업 설계하기", type="primary", use_container_width=True):
                reset_app()
                st.rerun()
        return

    # 4단계에서 에듀테크 도구 추천을 위한 함수 추가
    def get_edutech_recommendations():
        """Gemini를 통해 에듀테크 도구 추천을 받는 함수"""
        try:
            gemini_api_key = st.secrets["GEMINI_API_KEY"]
            genai.configure(api_key=gemini_api_key)
            
            plan = st.session_state.lesson_plan
            student = STUDENT_DATA[plan['student_name']]
            
            # 에듀테크 120선 데이터에서 도구 정보 추출
            edutech_tools_info = ""
            if json_data['edutech'] and 'summary_table' in json_data['edutech']:
                for tool in json_data['edutech']['summary_table'][:20]:  # 상위 20개만
                    tool_name = tool.get('tool_name', '')
                    core_feature = tool.get('core_feature', '')
                    sub_category = tool.get('sub_category', '')
                    edutech_tools_info += f"- {tool_name} ({sub_category}): {core_feature}\n"
            
            prompt = f"""
            당신은 초등교육 전문가입니다. 다음 수업 설계안을 분석하고, 
            제공된 에듀테크 120선 데이터에서 가장 적합한 도구 3-5개를 추천해주세요.

            수업 정보:
            - 주제: {plan['topic']}
            - 학생: {student['name']} ({student['type']})
            - 수업 모델: {plan['model']}
            - 선택된 AIDT 기능: {plan['design']}

            에듀테크 120선 도구들:
            {edutech_tools_info}

            위 도구들 중에서 이 수업에 가장 적합한 도구들을 추천하고, 
            각각 어떻게 활용할 수 있는지 구체적으로 설명해주세요.
            """
            
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            return f"에듀테크 도구 추천 생성 중 오류가 발생했습니다: {e}"
    
    prompt = f"""
    당신은 초등 교육 전문가이자 수업 설계 컨설턴트입니다.
    아래의 수업 설계안에 대해 '수업의 강점', '발전 제안', '추가 디지털 도구 추천' 세 가지 항목으로 나누어 구체적이고 전문적인 피드백을 제공해주세요.
    
    - 수업 주제: {plan['subject']} {plan['grade']}학년 {plan['semester']}학기 {plan['unit']}
    - 대상 학생: {STUDENT_DATA[plan['student_name']]['name']} ({STUDENT_DATA[plan['student_name']]['type']})
    - 학생 특성: {STUDENT_DATA[plan['student_name']]['description']}
    - 맞춤 지도 계획: {plan['guidance']}
    - 적용 수업 모델: {plan['model']}
    - 선택된 에듀테크 도구: {selected_tools_info}
    
    피드백은 반드시 아래 형식에 맞춰 한글로 작성해주세요.

    ### 👍 수업의 강점
    - [강점 1]
    - [강점 2]

    ### 💡 발전 제안
    - [제안 1]
    - [제안 2]

    ### 🛠️ 추가 디지털 도구 추천
    - [도구 이름]: [도구 설명]
    - [도구 이름]: [도구 설명]
    """

    # AI 모델 호출 및 피드백 생성
    with st.spinner('🤖 AI가 수업 설계안을 분석하고 컨설팅 보고서를 작성하는 중입니다...'):
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            feedback_text = response.text
            
            feedback_dict = parse_feedback_from_gemini(feedback_text)
            
            st.markdown("""
            <div class="feedback-section">
            """, unsafe_allow_html=True)
            st.markdown(feedback_text)
            st.markdown("</div>", unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                st.download_button(
                    label="📥 결과물 JPG 다운로드",
                    data=generate_lesson_plan_image(plan, feedback_dict),
                    file_name=f"lesson_plan_{plan['student_name']}_{plan['unit']}.jpg",
                    mime="image/jpeg",
                    use_container_width=True
                )
            with col3:
                if st.button("🆕 새로운 수업 설계하기", type="primary", use_container_width=True):
                    reset_app()
                    st.rerun()

        except Exception as e:
            st.error(f"❌ AI 컨설팅 보고서 생성 중 오류가 발생했습니다: {e}")

# --- 메인 앱 로직 ---
st.markdown("""
<div style="text-align: center; padding: 2rem 0; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 15px; margin-bottom: 2rem;">
    <h1 style="margin: 0; font-size: 2.5rem; color: white;">🎯 AI 코칭 기반 맞춤수업 설계 시뮬레이터</h1>
    <p style="margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 1.1rem; color: white;">실제 교육과정과 에듀테크 120선 데이터로 만드는 맞춤형 수업</p>
</div>
""", unsafe_allow_html=True)

# 진행률 표시
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

# --- 워터마크 ---
st.markdown("""
<div style="
    position: fixed;
    bottom: 10px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(255, 255, 255, 0.9);
    padding: 0.5rem 1rem;
    border-radius: 20px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    font-size: 0.8rem;
    color: #6b7280;
    z-index: 999;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.2);
">
    © 서울가동초등학교 백인규
</div>
""", unsafe_allow_html=True)