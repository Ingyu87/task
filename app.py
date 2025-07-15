import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap
import json
import google.generativeai as genai
import os

# --- 데이터 영역 ---
# 실제 애플리케이션에서는 이 데이터를 외부 DB나 파일에서 불러올 수 있습니다.
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

AIDT_FEATURES = {
  'diagnosis': {'name': '학습진단 및 분석', 'description': '학생의 현재 수준과 취약점을 데이터로 확인합니다.'},
  'dashboard': {'name': '교사 대시보드', 'description': '학생별 학습 현황과 이력을 실시간으로 관리합니다.'},
  'path': {'name': '학습 경로 추천', 'description': '학생 수준에 맞는 학습 순서와 콘텐츠를 제안합니다.'},
  'tutor': {'name': '지능형 AI 튜터', 'description': '1:1 맞춤형 힌트와 피드백을 제공하여 문제 해결을 돕습니다.'},
  'collaboration': {'name': '소통 및 협업 도구', 'description': '모둠 구성, 과제 공동수행, 실시간 토론을 지원합니다.'},
  'portfolio': {'name': '디지털 포트폴리오', 'description': '학생의 학습 과정과 결과물을 자동으로 기록하고 관리합니다.'},
}

# --- 세션 상태 초기화 ---
if 'step' not in st.session_state:
    st.session_state.step = 1
    st.session_state.lesson_plan = {
        "topic": "",
        "student_name": None,
        "guidance": "",
        "model": None,
        "design": {'도입': [], '개별 학습': [], '협력 학습': [], '정리': []}
    }

# --- 헬퍼 함수 ---
def reset_app():
    """앱을 초기 상태로 리셋하는 함수"""
    st.session_state.step = 1
    st.session_state.lesson_plan = {
        "topic": "", "student_name": None, "guidance": "", "model": None,
        "design": {'도입': [], '개별 학습': [], '협력 학습': [], '정리': []}
    }

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

# --- 4단계: 결과물 이미지 생성 함수 ---
def generate_lesson_plan_image(plan, feedback):
    """수업 설계안과 피드백을 바탕으로 JPG 이미지를 생성하는 함수"""
    width, height = 800, 1200
    bg_color = (255, 255, 255)
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # 폰트 파일 경로 설정 (사용자가 업로드한 폰트 파일 이름으로 수정)
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

    draw.text((40, y), f"1. 수업 분석: {plan['topic']}", font=font_header, fill=(29, 78, 216))
    y += 35
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
    for stage, features in plan['design'].items():
        if features:
            draw.text((50, y), f"■ {stage}:", font=font_body, fill=(0,0,0))
            y += 25
            feature_names = [f"  - {AIDT_FEATURES[f]['name']}" for f in features]
            for name in feature_names:
                draw.text((60, y), name, font=font_small, fill=(50,50,50))
                y += 18
            y += 10
    y+=15
    
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
    y += 15

    draw.text((50, y), "🛠️ 추가 디지털 도구 추천", font=font_body, fill=(37, 99, 235))
    y += 25
    for tool in feedback['tools']:
        draw.text((60, y), f"  - {tool['name']}: {tool['description']}", font=font_small, fill=(50,50,50))
        y += 18

    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()

# --- UI 렌더링 함수 ---
def step1_analysis():
    st.header("1단계: 수업 및 학습자 분석")
    st.write("수업 주제를 정하고, 학생 데이터를 분석하여 지도 계획을 수립합니다.")
    
    st.session_state.lesson_plan['topic'] = st.text_input(
        "분석할 수업명", 
        value=st.session_state.lesson_plan['topic'],
        placeholder="예: 4학년 1학기 수학, 2. 각도"
    )
    
    student_names = list(STUDENT_DATA.keys())
    st.session_state.lesson_plan['student_name'] = st.selectbox(
        "지도할 학생 선택", 
        options=[None] + student_names,
        format_func=lambda x: "학생을 선택하세요" if x is None else x
    )

    student_name = st.session_state.lesson_plan['student_name']
    if student_name:
        student = STUDENT_DATA[student_name]
        with st.container(border=True):
            st.subheader(f"{student['name']} 학생 데이터")
            st.info(f"**학생 유형:** {student['type']}")
            st.write(student['description'])
            for item in student['data']:
                st.text(f"{item['평가']}:")
                st.progress(item['정답률'], text=f"{item['정답률']}%")
        
        st.session_state.lesson_plan['guidance'] = st.text_area(
            "맞춤 지도 계획",
            height=150,
            placeholder=f"{student_name} 학생의 강점을 강화하고 약점을 보완하기 위한 지도 계획을 작성해 주세요."
        )
    
    if st.button("다음 단계로", type="primary"):
        if st.session_state.lesson_plan['topic'] and st.session_state.lesson_plan['student_name'] and st.session_state.lesson_plan['guidance']:
            st.session_state.step = 2
            st.rerun()
        else:
            st.error("모든 항목을 입력해주세요.")

def step2_method():
    st.header("2단계: 교수·학습 방법 결정")
    st.write("수업의 목표와 학생 특성을 고려하여 적합한 수업 모델을 결정합니다.")

    q1 = st.radio("질문 1: 학생별 수준, 취약점 확인이 필요한가요?", ("선택하세요", "Yes", "No"), horizontal=True)
    q2 = st.radio("질문 2: 학습 목표 달성에 학생 간 수준 차이가 크게 영향을 미치나요?", ("선택하세요", "Yes", "No"), horizontal=True)

    recommended_model = None
    if q1 == "Yes" or q2 == "Yes":
        recommended_model = "개별 학습 우선 모델"
    elif q1 == "No" and q2 == "No":
        recommended_model = "협력 학습 중심 모델"

    if recommended_model:
        st.success(f"**AI 추천 모델:** {recommended_model}")
        st.session_state.lesson_plan['model'] = recommended_model

    col1, col2 = st.columns(2)
    with col1:
        if st.button("이전 단계로"):
            st.session_state.step = 1
            st.rerun()
    with col2:
        if st.button("다음 단계로", type="primary", disabled=not recommended_model):
            st.session_state.step = 3
            st.rerun()

def step3_structure():
    st.header("3단계: 수업 구조화 및 AIDT 기능 선택")
    st.write("수업 단계별로 활동을 구성하고, AI 추천을 참고하여 활용할 디지털 도구를 최종 선택합니다.")

    student_type = STUDENT_DATA[st.session_state.lesson_plan['student_name']]['type']
    model = st.session_state.lesson_plan['model']
    
    recs = {'도입': ['diagnosis'], '개별 학습': [], '협력 학습': [], '정리': ['portfolio', 'dashboard']}
    if model == '개별 학습 우선 모델':
        recs['개별 학습'].append('path')
        if student_type == '느린 학습자':
            recs['개별 학습'].append('tutor')
        recs['협력 학습'].append('collaboration')
    else:
        recs['협력 학습'].append('collaboration')
        if student_type == '빠른 학습자':
            recs['개별 학습'].append('path')

    stages = ['도입', '개별 학습', '협력 학습', '정리']
    for stage in stages:
        with st.container(border=True):
            st.subheader(stage)
            options = list(AIDT_FEATURES.keys())
            default_selection = [opt for opt in options if opt in recs.get(stage, [])]
            
            selected_features = st.multiselect(
                f"{stage} 단계에서 활용할 AIDT 기능을 선택하세요.",
                options=options,
                format_func=lambda x: f"{AIDT_FEATURES[x]['name']}{' (AI 추천)' if x in recs.get(stage, []) else ''}",
                default=default_selection,
                key=f"design_{stage}"
            )
            st.session_state.lesson_plan['design'][stage] = selected_features
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("이전 단계로"):
            st.session_state.step = 2
            st.rerun()
    with col2:
        if st.button("제출하고 컨설팅 받기", type="primary"):
            st.session_state.step = 4
            st.rerun()

def step4_feedback():
    st.header("4단계: AI 종합 컨설팅 보고서")
    st.write("제출하신 수업 설계안에 대한 AI의 분석과 제안입니다.")
    
    # Gemini API 키 설정
    try:
        gemini_api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=gemini_api_key)
        api_available = True
    except (KeyError, AttributeError):
        api_available = False
        st.info("Gemini API 키가 설정되지 않았습니다. 규칙 기반의 기본 피드백이 제공됩니다.")
        
    plan = st.session_state.lesson_plan
    
    if not api_available:
        # 기본 피드백 로직 (API 없을 경우 대비)
        student = STUDENT_DATA[plan['student_name']]
        feedback = {
            'strengths': [f"'{student['name']}' 학생을 위한 수업 설계를 시작해주셔서 감사합니다."],
            'suggestions': ["AI 컨설팅 기능을 사용하려면 Gemini API 키를 설정해주세요."],
            'tools': []
        }
        with st.container(border=True):
            st.markdown("### 👍 수업의 강점")
            for item in feedback['strengths']: st.markdown(f"- {item}")
            st.markdown("### 💡 발전 제안")
            for item in feedback['suggestions']: st.markdown(f"- {item}")
        
        if st.button("새로운 수업 설계하기", type="primary"):
            reset_app()
            st.rerun()
        return

    # Gemini에게 전달할 프롬프트 생성
    prompt = f"""
    당신은 초등 교육 전문가이자 수업 설계 컨설턴트입니다.
    아래의 수업 설계안에 대해 '수업의 강점', '발전 제안', '추가 디지털 도구 추천' 세 가지 항목으로 나누어 구체적이고 전문적인 피드백을 제공해주세요.
    
    - 수업 주제: {plan['topic']}
    - 대상 학생: {STUDENT_DATA[plan['student_name']]['name']} ({STUDENT_DATA[plan['student_name']]['type']})
    - 맞춤 지도 계획: {plan['guidance']}
    - 적용 수업 모델: {plan['model']}
    - 단계별 AIDT 활용 계획: {json.dumps(plan['design'], ensure_ascii=False)}
    
    피드백은 반드시 아래 형식에 맞춰 한글로 작성해주세요. 각 항목은 '###'으로 시작해야 합니다.

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
    with st.spinner('AI가 수업 설계안을 분석하고 컨설팅 보고서를 작성하는 중입니다...'):
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            feedback_text = response.text
            
            feedback_dict = parse_feedback_from_gemini(feedback_text)
            
            with st.container(border=True):
                st.markdown(feedback_text)
            
            st.download_button(
                label="결과물 JPG로 다운로드",
                data=generate_lesson_plan_image(plan, feedback_dict),
                file_name=f"lesson_plan_{plan['student_name']}.jpg",
                mime="image/jpeg"
            )

        except Exception as e:
            st.error(f"AI 컨설팅 보고서 생성 중 오류가 발생했습니다: {e}")

    if st.button("새로운 수업 설계하기", type="primary"):
        reset_app()
        st.rerun()

# --- 메인 앱 로직 ---
st.title("AI 코칭 기반 맞춤수업 설계 시뮬레이터")

if st.session_state.step == 1:
    step1_analysis()
elif st.session_state.step == 2:
    step2_method()
elif st.session_state.step == 3:
    step3_structure()
elif st.session_state.step == 4:
    step4_feedback()
