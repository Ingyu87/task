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
    }
    
    .step-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
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

# --- 에듀테크 도구 추출 및 분류 ---
def categorize_edutech_tools(edutech_data):
    """에듀테크 도구를 수업 단계별로 분류"""
    
    if not edutech_data or 'summary_table' not in edutech_data:
        return {}
    
    # 카테고리별 매핑
    category_mapping = {
        '수업 도입 및 동기 유발': ['실시간 퀴즈', '게임 기반', '동기 유발'],
        '개별 학습': ['학습 플랫폼', '개념 학습', 'AI 튜터', '진단'],
        '협력 학습': ['협업', '소통', '상호작용', '토론'],
        '정리': ['평가', '포트폴리오', '피드백', '관리']
    }
    
    categorized = {stage: [] for stage in category_mapping.keys()}
    
    # summary_table의 도구들을 분류
    for tool in edutech_data.get('summary_table', []):
        tool_name = tool.get('tool_name', '')
        core_feature = tool.get('core_feature', '')
        sub_category = tool.get('sub_category', '')
        
        # 특성에 따라 분류
        if any(keyword in core_feature.lower() or keyword in sub_category.lower() 
               for keyword in ['퀴즈', '게임', '실시간', '경쟁']):
            categorized['수업 도입 및 동기 유발'].append(tool)
        elif any(keyword in core_feature.lower() or keyword in sub_category.lower() 
                 for keyword in ['협업', '소통', '상호작용', '토론', '공유']):
            categorized['협력 학습'].append(tool)
        elif any(keyword in core_feature.lower() or keyword in sub_category.lower() 
                 for keyword in ['평가', '포트폴리오', '피드백', '관리', '경영']):
            categorized['정리'].append(tool)
        else:
            categorized['개별 학습'].append(tool)
    
    return categorized

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
        "design": {'수업 도입 및 동기 유발': [], '개별 학습': [], '협력 학습': [], '정리': []},
        "ai_recommendations": {}
    }

# --- 헬퍼 함수 ---
def reset_app():
    """앱을 초기 상태로 리셋하는 함수"""
    st.session_state.step = 1
    st.session_state.lesson_plan = {
        "subject": "", "grade": 0, "semester": 0, "unit": "", "topic": "",
        "student_name": None, "guidance": "", "model": None,
        "design": {'수업 도입 및 동기 유발': [], '개별 학습': [], '협력 학습': [], '정리': []},
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
    """Gemini를 통해 에듀테크 도구 추천을 받는 함수"""
    try:
        gemini_api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=gemini_api_key)
        
        plan = st.session_state.lesson_plan
        student = STUDENT_DATA[plan['student_name']]
        
        # 에듀테크 도구 정보 준비
        edutech_tools = categorize_edutech_tools(json_data['edutech'])
        tools_info = ""
        for stage, tools in edutech_tools.items():
            tools_info += f"\n{stage}:\n"
            for tool in tools[:5]:  # 각 단계별 상위 5개만
                tools_info += f"- {tool.get('tool_name', '')}: {tool.get('core_feature', '')}\n"
        
        prompt = f"""
        당신은 초등교육 전문가입니다. 다음 정보를 바탕으로 수업 단계별로 가장 적합한 에듀테크 도구를 추천해주세요.

        - 수업 주제: {plan['subject']} {plan['grade']}학년 {plan['semester']}학기 {plan['unit']}
        - 학생 유형: {student['type']}
        - 학생 특성: {student['description']}
        - 수업 모델: {plan['model']}
        - 맞춤 지도 계획: {plan['guidance']}

        사용 가능한 에듀테크 도구:{tools_info}

        각 수업 단계별로 추천하는 도구를 JSON 형식으로 답변해주세요.
        추천 이유도 간단히 포함해주세요.

        응답 형식:
        {{
            "수업 도입 및 동기 유발": {{
                "recommended": ["도구명1", "도구명2"],
                "reason": "추천 이유"
            }},
            "개별 학습": {{
                "recommended": ["도구명1"],
                "reason": "추천 이유"
            }},
            "협력 학습": {{
                "recommended": ["도구명1"],
                "reason": "추천 이유"
            }},
            "정리": {{
                "recommended": ["도구명1", "도구명2"],
                "reason": "추천 이유"
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
        
        for i, unit_data in enumerate(units):
            unit_name = unit_data['unit']
            is_selected = st.session_state.lesson_plan['unit'] == unit_name
            
            card_class = "curriculum-card selected" if is_selected else "curriculum-card"
            
            if st.button(f"선택", key=f"unit_{i}", use_container_width=True):
                st.session_state.lesson_plan.update({
                    'subject': subject,
                    'grade': grade,
                    'semester': semester,
                    'unit': unit_name,
                    'topic': f"{subject} {grade}학년 {semester}학기 {unit_name}"
                })
                st.rerun()
            
            st.markdown(f"""
            <div class="{card_class}">
                <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                    <span class="subject-badge">{subject}</span>
                    <h4 style="margin: 0; color: #1f2937;">{unit_name}</h4>
                </div>
                <p style="margin: 0; color: #6b7280; font-size: 0.9rem;"><strong>영역:</strong> {unit_data['area']}</p>
                <p style="margin: 0.5rem 0 0 0; color: #374151; font-size: 0.85rem; line-height: 1.4;">
                    {unit_data['content'][:100]}{'...' if len(unit_data['content']) > 100 else ''}
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    # 선택된 단원 정보 표시
    if st.session_state.lesson_plan['unit']:
        selected_unit = next((unit for unit in units if unit['unit'] == st.session_state.lesson_plan['unit']), None)
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
        st.session_state.lesson_plan['model'] = recommended_model

    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬅️ 이전 단계로", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
    with col3:
        if st.button("🚀 다음 단계로", type="primary", disabled=not recommended_model, use_container_width=True):
            st.session_state.step = 3
            st.rerun()

def step3_structure():
    st.markdown("""
    <div class="step-header">
        <h1>🏗️ 3단계: 수업 구조화 및 에듀테크 도구 선택</h1>
        <p>실제 에듀테크 120선 데이터를 활용하여 AI가 추천하는 최적의 디지털 도구를 선택합니다.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # AI 추천 받기
    if 'ai_recommendations' not in st.session_state.lesson_plan or not st.session_state.lesson_plan['ai_recommendations']:
        with st.spinner('🤖 AI가 에듀테크 120선 데이터를 분석하여 최적의 도구를 추천하는 중입니다...'):
            st.session_state.lesson_plan['ai_recommendations'] = get_ai_recommendations()
    
    ai_recs = st.session_state.lesson_plan['ai_recommendations']
    
    # 에듀테크 도구 분류
    edutech_tools = categorize_edutech_tools(json_data['edutech'])
    
    stage_icons = {'수업 도입 및 동기 유발': '🚀', '개별 학습': '📚', '협력 학습': '👥', '정리': '🎯'}
    stages = ['수업 도입 및 동기 유발', '개별 학습', '협력 학습', '정리']
    
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
            ai_recommended_tools = ai_recs[stage].get('recommended', [])
            reason = ai_recs[stage].get('reason', '')
            if ai_recommended_tools:
                st.info(f"🤖 **AI 추천**: {reason}")
        
        # 해당 단계의 도구들 표시
        stage_tools = edutech_tools.get(stage, [])
        selected_tools = []
        
        if stage_tools:
            cols = st.columns(2)
            
            for i, tool in enumerate(stage_tools):
                col_idx = i % 2
                tool_name = tool.get('tool_name', '')
                core_feature = tool.get('core_feature', '')
                website = tool.get('website', '')
                pricing = tool.get('pricing_model', '')
                korean_support = tool.get('korean_support', '')
                
                with cols[col_idx]:
                    # AI 추천 여부 확인
                    is_ai_recommended = (ai_recs and stage in ai_recs and 
                                       tool_name in ai_recs[stage].get('recommended', []))
                    
                    # 기본 선택값 설정
                    current_selections = st.session_state.lesson_plan['design'].get(stage, [])
                    is_selected = tool_name in current_selections or is_ai_recommended
                    
                    # 체크박스
                    is_checked = st.checkbox(
                        "",
                        value=is_selected,
                        key=f"{stage}_{tool_name}_{i}",
                        label_visibility="collapsed"
                    )
                    
                    if is_checked:
                        selected_tools.append(tool_name)
                    
                    # 도구 카드
                    card_class = "edutech-card"
                    badge_html = ""
                    
                    if is_ai_recommended:
                        card_class += " ai-recommended"
                        badge_html = '<span class="ai-recommended-badge">AI 추천</span>'
                    
                    korean_badge = "🇰🇷" if korean_support == "O" else ""
                    pricing_color = "#10b981" if pricing == "Free" else "#f59e0b" if pricing == "Freemium" else "#ef4444"
                    
                    st.markdown(f"""
                    <div class="{card_class}">
                        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                            <h4 style="margin: 0; color: #1f2937; flex: 1;">
                                {korean_badge} {tool_name} {badge_html}
                            </h4>
                            <span style="background: {pricing_color}; color: white; padding: 0.2rem 0.5rem; border-radius: 8px; font-size: 0.7rem; white-space: nowrap; margin-left: 0.5rem;">
                                {pricing}
                            </span>
                        </div>
                        <p style="margin: 0 0 0.5rem 0; color: #6b7280; font-size: 0.85rem; line-height: 1.4;">
                            {core_feature}
                        </p>
                        <p style="margin: 0; color: #9ca3af; font-size: 0.75rem;">
                            🌐 {website}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info(f"이 단계에 사용할 수 있는 도구가 없습니다.")
        
        st.session_state.lesson_plan['design'][stage] = selected_tools
    
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

    # Gemini에게 전달할 프롬프트 생성
    selected_tools_info = ""
    for stage, tools in plan['design'].items():
        if tools:
            selected_tools_info += f"\n{stage}: {', '.join(tools)}"
    
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
    <h1 style="margin: 0; font-size: 2.5rem;">🎯 AI 코칭 기반 맞춤수업 설계 시뮬레이터</h1>
    <p style="margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 1.1rem;">실제 교육과정과 에듀테크 120선 데이터로 만드는 맞춤형 수업</p>
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