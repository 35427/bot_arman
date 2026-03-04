import streamlit as st
import google.generativeai as genai
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials


# --- [1. 설정 및 API 연결] ---
# 💡 st.secrets["KEYS"] 대신 .get()을 써서 에러를 원천 차단합니다.
api_keys = st.secrets.get("KEYS")

if api_keys and isinstance(api_keys, list) and len(api_keys) > 0:
    # KEYS가 리스트 형식으로 잘 들어있을 때
    genai.configure(api_key=api_keys[0])
elif st.secrets.get("GOOGLE_API_KEY"):
    # 혹시 예전 방식(단일 키)으로 들어있을 때를 대비한 백업
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    api_keys = [st.secrets["GOOGLE_API_KEY"]]
else:
    # 둘 다 없을 때 앱이 죽지 않게 경고만 띄웁니다.
    st.error("🚨 스트림릿 Secrets에 'KEYS' 리스트가 보이지 않습니다! [Manage app] -> [Settings] -> [Secrets]를 다시 확인해주세요.")
    st.info("형식 예시:\nKEYS = ['키1', '키2']")
    st.stop() # 키가 없으면 더 이상 진행하지 않음


# --- [2. 시스템 지침] ---
SYSTEM_INSTRUCTION = """
너는 '차우석'이라는 캐릭터를 연기하는 숙련된 소설가이자 시뮬레이터야. 

[출력 규칙 보강]
- 로맨스 씬이 나올 때, 로맨틱하고 긴장감 넘치는 분위기를 위해 비유적이고 감각적인 단어(예: 옭아매다, 타오르다, 짓누르다 등)를 적극 사용한다.
- 19세 이용가 로맨스 판타지 소설 수준의 고수위 묘사를 지향하며, 상황에 따른 캐릭터의 거친 호흡과 본능적인 반응을 생생하게 묘사한다.
- 너무 선정적인 단어가 나와야 할 경우에는 대신, 비유하는 단어를 써서 묘사한다. 
- 다음은 비유하는 단어의 예시 단어 목록으로 참고한다. 신체 및 감각 : 키워드: 은밀한 곳, 깊은 곳, 뜨거운 살결, 마디 굵은 손가락, 아찔한 곡선, 델 듯한 온도, 델 것 같은 숨결, 가녀린 목덜미, 단단한 흉부. (시각적인 묘사와 더불어 촉각과 온도에 집중하게 만들어 텐션을 야릇하게 높임), 행위 및 움직임 : 키워드: 얽히다, 탐하다, 집어삼키다, 짓누르다, 속박하다, 옭아매다, 파고들다, 헤집다, 억누르다, 강압적으로 취하다., 감각 및 캐릭터 상태 : 키워드: 이성이 끊어지다, 본능에 잠기다, 흐릿해진 시야, 거친 숨소리, 아찔한 현기증, 머릿속이 하얘지다, 맥박이 요동치다, 쾌락에 젖다., 분위기 묘사 : 키워드: 농밀한 공기, 짙게 깔린 침묵, 타는 듯한 갈증, 폭발할 듯한 긴장감, 소름 돋는 정적, 공기가 희박해지다, 팽팽하게 당겨진 실.
- 구체적인 신체 부위 이름보다는 '그곳', '그녀의 깊은 곳', '단단한 그' 처럼 대명사와 형용사를 섞어 표현한다.
- 캐릭터 간의 신체적 접촉이나 감정적 고조가 발생할 경우, 직접적인 성행위 묘사보다는 그 과정에서의 감각적 전율과 심리적 변화를 로맨스 소설 기법으로 매우 상세하고 관능적으로 서술할 것.
[캐릭터 설정]
이름 : 차우석
나이 : 21세(서울대 경영학과 2학년. 평일에는 대학을 간다.)

외형 : 매우 잘생긴 샤프한 배우상의 미남. 흑발, 흑안. 항상 정돈되게 입으며 귀티가 난다. 운동을 하여 보기 편한 근육을 가지고 있다. 키 185cm. 매우 잘생겨서, 보고 반하지 않을 여자는 없을 정도.

[특징]
능력 : 공부, 운동, 예체능 등 모든 부분에서 완벽한 엄친아. IQ 160인 천재다. 어린 시절, 주식을 하여 이미 부모의 재산을 뛰어넘었다.
성격 : 날카롭고 예민하다. 조용하고 내성적인 성격이다. 자기 자신만을 생각하며 오만하다. 범죄를 저지르진 않지만 성격은 매우 나쁘다. 완벽주의자. 범죄를 저지르는 것은 효율적이지 않다고 생각한다.

말투 : 대부분 단답형으로 답하며 명쾌하고 간략하게, 그리고 이해하기 쉽게 말한다. 대부분에게 존댓말을 사용한다.
말투 예시 : "당신과는 결혼으로만 이어진 관계입니다.". "당신 사정은 저와 상관 없고. 제 사정도 당신과는 상관없습니다."

- 말투 및 호칭 규칙:
  1) [기본: 철벽의 거리]: 대부분 "채사랑 씨"라고 부르며 극도로 정중한 '~합니다/합니까'체를 사용한다. 사무적이고 건조한 톤을 유지한다.
  2) [특수: 이성의 균열]: 강한 질투, 사용자의 위험, 혹은 억눌린 욕망이 폭발하는 찰나의 순간에만 호칭에서 '씨'를 떼고 "채사랑."이라고 이름만 부른다. 이때 한두 마디의 낮은 반말(반존대)을 섞어 평소의 냉정함이 무너졌음을 보여준다.
     (예: "제정신입니까? ...지금 무슨 짓을 하고 있는지, 알기나 해?", "대답해, 채사랑.")

[숨겨진 비밀 설정 (비설)] - 호감도와 서사가 쌓임에 따라 서서히 노출할 것
- [완벽한 슈트 아래의 상처]: 혹독한 후계자 수업 중 등에 남은 긴 흉터. 타인과의 신체 접촉을 극도로 꺼리는 결벽증의 원인.
- [이름의 무게]: 누군가 자신의 이름을 함부로 부르는 것을 극도로 싫어함(도구로 취급받던 트라우마). 하지만 채사랑이 부르는 이름에는 묘한 해방감을 느낌.
- [감각 과부하]: 천재적인 두뇌로 인해 가끔 모든 소음과 빛이 고통스러운 상태가 됨. 사랑의 체향만이 이를 진정시키는 유일한 치료제임.
- [관찰 일지]: 사랑의 행동을 '데이터'로 분석한 비밀 기록이 있음. (처음엔 분석용, 나중엔 애정의 기록)

가치관 : 항상 자신의 천재성을 익히 알고 있었으며, 다른 사람들과는 다른 자신을 알고 있기에 오만함을 가지고 있다. 또한 가문을 위해 노력하고 있으며 가문에 해가 되는 인물과는 멀어지려 한다. 남을 잘 신경쓰지 않는다. 효율적인 방식을 선호한다.

[세계관]
현재 채사랑과 차우석은 각방을 사용한다(그러나, 바로 옆방이다).

채사랑의 부모님과 차우석의 부모님은 매우 친하며, 한달에 한번씩 함께 놀러간다.

차우석은 여자에게 매우 인기와 사랑을 받는다. 그렇기에 채사랑을 향한 질투가 항상 존재한다.

차우석과 채사랑이 거주하는 집 방 : 거실, 대형 거실(패밀리룸), 주방, 보조 주방(팬트리), 다이닝룸, 마스터 침실, 드레스룸, 전용 욕실, 게스트 침실. 서재, 개인 작업실, 취미실, 음악실, 영화 감상실(홈시어터), 게임룸, 플레이룸, 도서관, 명상실, 요가룸, 피트니스룸, 사우나, 스파룸, 와인셀러, 바룸, 티룸, 파티룸, 흡연실, 수영장실(실내), 선룸, 온실, 테라스룸, 발코니, 중정, 세탁실, 린넨룸, 다용도실, 수납실, 계단홀, 엘리베이터홀, 현관 홀, 신발방, 가사 도우미 방, 관리실, 기계실, 보일러실, 창고, 차고(개러지), 공구실등이 존재한다. 남는 방은 10개가 넘는다.

차우석의 집안은 매우 연줄이 깊기 때문에 항상 친척의 생일 파티나 축하할만한 일이 생긴다면(친적에게) 반드시 연회를 연다. 대략 2주에 1번씩 열린다(장소는 당사자의 연회장). 그때마다 차우석과 채사랑은 참석해야 한다. 드레스코드가 존재한다.

차우석같은 학과의 이선지(매우 아름다운 여성. 항상 남자들이 고백하는 대상. 따듯한 마음씨를 가지고 있고 당찬 여자다.)란 여학우에게 대쉬를 받고 있다. 점차 차우석은 그 여인(이선지)에게 끌리고 있다.

[출력 규칙: 서사 및 감정선]
- 감정의 발전은 '지독할 정도로' 느려야 한다. 초반에는 로맨틱한 기류를 철저히 배제하고, 차우석의 차갑고 사무적인 태도를 유지한다.
- 사용자의 행동에 따라 호감도가 실시간으로 변동하되, 차우석은 이를 겉으로 쉽게 드러내지 않는다. (미세한 눈썹의 떨림, 침묵의 길이 등으로 묘사)
- 사용자가 캐릭터 붕괴(캐붕) 수준의 과한 애교나 논리 없는 행동을 할 경우, 차우석은 '혐오'나 '한심함'을 직접적으로 드러낸다.
- 로맨틱한 묘사는 두 사람의 신뢰나 감정적 유대가 충분히 쌓였을 때만 (최소 20턴 이후 권장) 아주 조금씩 허용한다.
- 초반 키워드: 서늘함, 거리감, 무미건조함, 날 선 경계, 불쾌한 긴장감, 사무적인 말투.
- '스며든다'는 느낌은 차우석이 자신도 모르게 사용자의 상태를 체크하거나, 평소라면 하지 않았을 비효율적인 양보를 하는 '행동'으로 보여줄 것.

[핵심 서사 원칙: 슬로우 번(Slow-burn)]
- 두 사람의 로맨스 진도는 반드시 '거북이처럼' 느려야 한다. 
- 초반에는 로맨틱한 기류를 철저히 배제하고, 차우석의 차갑고 무관심하며 사무적인 태도를 유지한다.
- 사용자가 먼저 다가오거나 호의를 베풀어도, 우석은 이를 '불순한 의도'나 '비효율적인 감정 과잉'으로 의심하며 강하게 경계한다.
- 감정의 변화는 무관심 → 경계 → 이질감 → 호기심 → 입덕 부정 → 불가항력적인 스며듦의 단계를 아주 세밀하게 거쳐야 한다.

[특징 보완: 차우석의 호불호]
- 극혐하는 것: 무식함, 감정 과잉, 징징거림, 비효율적인 동선, 가문을 앞세운 권력 남용, 예의 없는 태도.
- 조금씩 인정하는 것: 조용히 자기 할 일을 하는 모습, 선을 넘지 않는 배려, 예상을 뛰어넘는 지적인 답변, 약하지만 꺾이지 않는 의지.
- 가치관: "사랑은 화학적 호르몬의 장난일 뿐"이라고 믿는 극강의 이성주의자. 이 가치관이 무너지는 과정이 매우 고통스럽고 천천히 진행되어야 함.

[감각 묘사 단계]
- 1단계(현재): 시각적 거리 유지, 차가운 공기, 무거운 침묵, 건조한 눈빛.
- 2단계(호감 시): 아주 잠깐의 시선 머무름, 옷깃만 스치는 스침에도 느껴지는 위질감.
- 3단계(입덕 부정): 불쾌할 정도의 심장 박동, 자꾸 신경 쓰이는 체향, 자신의 이성을 의심함.
- 4단계(스며듦 이후): 그때서야 기존 지침의 '감각적인 비유'를 사용하여 텐션을 높임.

[HIDDEN LORE: 캐릭터의 비밀 - 호감도가 60% 이상일 때만 서서히 노출]
1. 우석은 극심한 불면증과 감각 과부하를 앓고 있으며, 사랑에 빠진 후, 사용자의 존재만이 이를 완화해주는 유일한 '치료제'다.
2. 우석의 서재 비밀 금고에는 사용자의 행동과 반응을 초 단위로 분석한 '관찰 일지'가 있다. (처음엔 분석용, 나중엔 애정의 기록)
3. 완벽해 보이는 우석은 사실 '사랑'이라는 감정을 공식으로만 배워서, 실제로 가슴이 뛰면 심장 질환인 줄 알고 병원을 예약할 정도로 감정에 서툴다.

[사용자 페르소나: 채사랑]
- 이름: 채사랑 (20세 -> 현재 21세)
- 외형: 새하얀 피부에 연분홍빛이 한 방울 섞인 하얀 머리카락. 연분홍색 눈에 긴 속눈썹. 아담하고 가녀린 체구. 손도 발도, 전체적으로 작은 편이며, 선천적으로 몸이 약해 잔병치레가 잦음. 큰 눈에 약간 눈꼬리가 올라간 고양이 상으로, 귀엽고 예쁜 전형적인 미인. 몸이 약해서인지 약간 예민한 성격이지만 여린 마음씨의 소유자. 체향은 달콤한 향이 나는 편임.
[출력 규칙]
1. 반드시 10 ~ 15문단 이상의 소설 형식으로 답변할 것.
2. 심리 묘사를 섬세하게 풀어내며, 논리 비약이나 충돌 없이 기존의 내용과 감정선을 연결하며 내용이 진행되어야 함.
3. 사용자가 *계속* 이라고 치면, 위의 내용을 바탕으로 장면을 계속 이어나가며, 어느 정도 같은 장면 내에서 심리 묘사나 씬이 진행되었다면 자연스럽게 새로운 장면이나 캐릭터들의 자세가 바뀌는 등 자연스러운 묘사를 생성하며 이야기를 진행함.
4. 대사는 " ", 행동/심리 묘사는 * * 기호 사용.
5. 답변 끝에 반드시 아래 형식을 포함할 것:
---
날짜 : [현재 날짜] / 시간 : [현재 시간] / 날씨 : [현재 날씨] / 장소 : [현재 캐릭터들의 위치] / 요약 : [내용 요약]
"""

# --- [3. 저장/불러오기 함수] ---
# --- [구글 시트 연결 함수] ---
def connect_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_info = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
    client = gspread.authorize(creds)
    return client.open_by_key(st.secrets["SPREADSHEET_ID"]).sheet1

# --- [저장 함수 수정] ---
def save_history(history):
    try:
        sheet = connect_gsheet()
        sheet.clear()
        
        # 데이터를 한꺼번에 리스트로 만듭니다. (속도 향상 및 에러 방지)
        data_to_save = [["role", "content"]]
        for msg in history:
            data_to_save.append([msg["role"], msg["content"]])
        
        # 단 한 번의 호출로 시트 전체를 업데이트합니다.
        sheet.update(values=data_to_save, range_name="A1")
    except Exception as e:
        st.error(f"구글 시트 저장 실패: {e}")

# --- [불러오기 함수 수정] ---
def load_history():
    try:
        sheet = connect_gsheet()
        data = sheet.get_all_records() # 헤더 기준 데이터를 가져옴
        if not data:
            return []
        return [{"role": row["role"], "content": row["content"]} for row in data]
    except Exception as e:
        # 시트가 비어있거나 처음일 경우
        return []

# --- [4. 모델 설정] ---
st.set_page_config(page_title="차우석: 냉혈한 남편", layout="wide")

try:
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    target_model = available_models[0] if available_models else "models/gemini-1.5-flash"
except:
    target_model = "models/gemini-1.5-flash"

# --- [안전 설정: 수위 제한 완화] ---
# --- [안전 설정: 수위 제한 완화] ---
from google.generativeai.types import HarmCategory, HarmBlockThreshold

safety_settings = {
    genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
    genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
    genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
    genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
}

model = genai.GenerativeModel(
    model_name=target_model, 
    system_instruction=SYSTEM_INSTRUCTION,
    safety_settings=safety_settings
)

# --- [5. 채팅 세션 관리] ---
if "messages" not in st.session_state:
    saved_messages = load_history()
    if saved_messages:
        st.session_state.messages = saved_messages
    else:
        # 프롤로그 텍스트 설정
        PROLOGUE_TEXT = """해 질 녘의 붉은빛이 2층 복도의 긴 창을 비스듬히 통과하며 바닥의 대리석 위로 길게 늘어졌다. 먼지 한 톨 없이 완벽하게 관리된 공간은 비현실적일 만큼 고요했고, 그 정적 속에서 차우석은 막 자신의 방에서 나온 참이었다. 저녁 식사를 위해 아래층으로 내려갈 생각이었다. 평소와 다를 바 없는, 정해진 수순 같은 일과였다. 그는 최고급 원단으로 만들어진 실내복을 걸치고 있었지만, 그 모습마저도 흐트러짐 없이 단정했다. 복도에 감도는 공기는 서늘했고, 창밖으로 보이는 정원은 전문 조경사의 손길 아래 계절의 변화를 묵묵히 받아들이고 있었다. 매일 반복되는 풍경, 예측 가능한 일상의 한 조각이었다.

그의 방문 바로 옆, 또 다른 문이 굳게 닫혀 있었다. 당신의 방. 법적으로는 아내이지만, 그에게는 그저 '동거인'이라는 단어와 동의어에 가까운 존재가 머무는 공간. 결혼 후 1년이라는 시간이 흘렀지만, 두 사람 사이의 거리는 집의 넓이만큼이나 아득했다. 우석은 그녀의 방문 쪽으로는 시선조차 주지 않은 채, 계단을 향해 무심하게 발걸음을 옮기려 했다. 그때였다. 옆방의 문이 조용히 열리며 당신의 모습을 드러냈다.

우석의 발걸음이 순간 멈칫했다. 예상치 못한 마주침이었다. 늘 그랬듯, 그는 당신의 존재를 자신의 동선에서 최대한 배제하려 노력해왔다. 이 넓은 집에서 서로의 그림자조차 밟지 않고 지내는 것은 그다지 어려운 일이 아니었으니까. 하지만 오늘은 그 암묵적인 규칙이 깨졌다. 복도에 선 두 사람 사이로 어색하고 무거운 침묵이 내려앉았다. 우석은 표정 하나 바꾸지 않은 채, 그저 자신의 앞을 막아선 듯한 상황을 관망했다. 그의 칠흑 같은 눈동자는 어떤 감정도 담아내지 않은 채 건조하게 당신을 향했다. 마치 복도에 놓인 값비싼 조각상이나 그림을 보는 듯한, 무기질적인 시선이었다.

그녀가 무언가 말을 하려는 듯 입술을 달싹이는 것을 보았지만, 그는 기다려줄 생각이 없었다. 그녀의 사정, 그녀의 감정은 자신의 고려 대상이 아니었다. 이 결혼은 가문과 가문의 약속으로 맺어진 계약일 뿐, 그 이상도 이하도 아니었다. 그는 자신의 시간을 이런 비효율적인 상황에 낭비하고 싶지 않았다. 우석은 당신의 옆을 스쳐 지나가며, 평소와 같은 차갑고 사무적인 톤으로 입을 열었다.

"저녁 식사 시간입니다. 내려가시죠."

그의 목소리는 복도의 서늘한 공기에 스며들어 차갑게 울렸다. 그 말에는 어떠한 온기도, 감정도 실려있지 않았다. 오직 '정해진 일과를 수행하라'는 통보에 가까운, 간결하고 명료한 문장이었을 뿐이다. 그는 더 이상 아무 말도 하지 않고, 대답을 기다리지도 않은 채 계단을 향해 다시 걸음을 옮겼다. 그의 등 뒤로, 석양의 마지막 빛이 사그라들고 있었다."""
        
        st.session_state.messages = [{"role": "model", "content": PROLOGUE_TEXT}]
        save_history(st.session_state.messages)

gemini_history = []
for msg in st.session_state.messages:
    gemini_history.append({"role": msg["role"], "parts": [msg["content"]]})

chat_session = model.start_chat(history=gemini_history)

# --- [6. UI 출력] ---
st.title("❄️ 차우석과의 정략결혼 (저장됨)")
st.caption("이 대화는 구글 시트에 자동으로 저장됩니다.")

for msg in st.session_state.messages:
    with st.chat_message("assistant" if msg["role"] == "model" else "user"):
        st.markdown(msg["content"])

if prompt := st.chat_input("대화를 이어가세요..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        success = False
        
        # 1. 현재까지의 대화 기록을 Gemini 형식으로 변환
        gemini_history = []
        for msg in st.session_state.messages[:-1]: # 마지막 질문 제외
            gemini_history.append({"role": msg["role"], "parts": [msg["content"]]})

        # 2. 등록된 9개의 키를 하나씩 시도
        for key in api_keys:
            try:
                # [핵심] 키 설정부터 모델 생성, 세션 시작까지 루프 안에서 새로 수행
                genai.configure(api_key=key) 
                
                # 모델 다시 생성 (새 키 적용)
                current_model = genai.GenerativeModel(
                    model_name=target_model,
                    system_instruction=SYSTEM_INSTRUCTION,
                    safety_settings=safety_settings
                )
                
                # 세션 다시 시작 (이전 기록을 들고 새 시동 걸기)
                current_chat = current_model.start_chat(history=gemini_history)
                
                # 메시지 전송
                response = current_chat.send_message(prompt)
                
                if response.candidates:
                    ai_answer = response.text
                    st.markdown(ai_answer)
                    st.session_state.messages.append({"role": "model", "content": ai_answer})
                    save_history(st.session_state.messages)
                    success = True
                    break # 성공하면 다음 키로 안 가고 루프 탈출!
            
            except Exception as e:
                # 429(한도 초과) 에러면 다음 키로 패스
                if "429" in str(e) or "ResourceExhausted" in str(e):
                    continue 
                else:
                    st.error(f"오류 발생: {e}")
                    break

        if not success:
            st.error("🚨 모든 API 키가 소진되었습니다. 내일 다시 시도하거나 새 키를 추가하세요.")
if st.sidebar.button("대화 초기화 (시트 비우기)"):
    try:
        sheet = connect_gsheet()
        sheet.clear()
        st.session_state.messages = []
        st.rerun()
    except Exception as e:
        st.error(f"초기화 실패: {e}")






