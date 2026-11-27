#시작 전 cd "C:\Users\lette\Documents\AI개발환경\my-dashboard\my-dashboard"
#streamlit run app.py

import streamlit as st  # 웹 화면을 만드는 라이브러리
import pandas as pd  # 표(데이터) 다루는 라이브러리

# ----- 1. 페이지 기본 설정 -----
st.set_page_config(page_title="지역·카테고리별 월 매출 현황", layout="wide")  # 탭 제목 + 넓은 화면

# ----- 2. 제목과 캡션 -----
st.title("📊 지역·카테고리별 월 매출 현황")  # 화면 맨 위 큰 제목 (무엇을 보는 화면인지)
st.caption("영업팀장용 · 다음 달 집중 지역 선정 참고 · 데이터 기준: 2026년 1~10월")  # 누가, 왜 보는지 + 데이터 기간

DATA_FILE = "sales_sample.csv"  # 읽을 데이터 파일 이름
REQUIRED_COLUMNS = ["date", "region", "category", "sales", "quantity"]  # 꼭 있어야 하는 열 5개


# ----- 3. 데이터 불러오기 -----
@st.cache_data  # 한 번 읽은 파일은 기억해 두어서 다시 읽지 않음 (속도 향상)
def load_data():
    return pd.read_csv(DATA_FILE)  # CSV 읽기 (날짜 변환은 열 검사 뒤에 함)


# 안전장치 1) 파일이 없거나 읽을 수 없을 때
try:
    df = load_data()
except FileNotFoundError:  # 파일이 없을 때
    st.warning(f"'{DATA_FILE}' 파일을 찾을 수 없어요. 파일 이름이 정확한지, app.py와 같은 폴더에 있는지 확인해 주세요.")
    st.stop()  # 여기서 실행 멈춤
except Exception:  # 빈 파일, 깨진 파일 등 그 밖의 읽기 문제
    st.warning(f"'{DATA_FILE}' 파일을 읽을 수 없어요. 엑셀에서 열어 내용이 비어 있거나 깨지지 않았는지 확인해 주세요.")
    st.stop()

# 안전장치 2) 꼭 필요한 열이 빠졌을 때
missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]  # 필요한 열 중 데이터에 없는 것만 모음
if missing:  # 빠진 열이 하나라도 있으면
    st.warning(f"데이터에 꼭 필요한 열이 없어요: {', '.join(missing)}. CSV 첫 줄(열 이름)에 이 열을 추가하거나 이름을 고쳐 주세요.")
    st.stop()

# 날짜·숫자 정리: 잘못된 값은 오류 대신 빈칸으로 바꾼 뒤 그 행은 뺌
df["date"] = pd.to_datetime(df["date"], errors="coerce")  # 날짜로 못 바꾸는 값은 빈칸(NaT)
df["sales"] = pd.to_numeric(df["sales"], errors="coerce")  # 숫자로 못 바꾸는 값은 빈칸(NaN)
df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
df = df.dropna(subset=REQUIRED_COLUMNS)  # 필요한 열 중 하나라도 빈칸인 행은 제외
if df.empty:  # 정리하고 나니 남은 행이 없으면
    st.warning("데이터에 쓸 수 있는 행이 없어요. date는 날짜, sales·quantity는 숫자로 들어 있는지 CSV를 확인해 주세요.")
    st.stop()
df["month"] = df["date"].dt.month  # 월(1~12)만 뽑아서 새 열로 추가


# ----- 3-2. 메뉴 API에서 데이터 받아오기 (12주차 서버) -----
# 주소와 API 키는 코드에 직접 쓰지 않고 .streamlit/secrets.toml(비밀 설정 파일)에서 읽음
try:
    MENU_API_URL = st.secrets.get("MENU_API_URL", "http://127.0.0.1:8000/menu")  # 없으면 내 컴퓨터 서버 주소
    API_KEY = st.secrets.get("API_KEY", "")  # 없으면 빈 값 (키 없이 요청)
except Exception:  # secrets.toml 파일 자체가 없을 때도 화면이 깨지지 않게
    MENU_API_URL = "http://127.0.0.1:8000/menu"
    API_KEY = ""


@st.cache_data(ttl=10)  # 10초 동안만 기억 → 서버 메뉴가 바뀌면 10초 뒤 새로 받아옴
def load_menu():
    headers = {"X-API-Key": API_KEY} if API_KEY else None  # 키가 있을 때만 요청에 같이 보냄
    return pd.read_json(MENU_API_URL, storage_options=headers)  # 주소로 요청해서 받은 JSON을 표로 바꿈


# ----- 4. 왼쪽 사이드바: 조건 선택 -----
st.sidebar.header("조건 선택")  # 사이드바 제목

# (1) 지역: 여러 개 선택, 기본은 전체
region_list = sorted(df["region"].unique())  # 지역 목록 (중복 제거 + 가나다순)
selected_regions = st.sidebar.multiselect("지역", region_list, default=region_list)  # 처음엔 전체 선택

# (2) 카테고리: 드롭다운 하나 선택, 맨 앞에 '전체' 포함
category_list = ["전체"] + sorted(df["category"].unique())  # ['전체', '식품', '의류', ...] 목록 만들기
selected_category = st.sidebar.selectbox("카테고리", category_list)  # 처음엔 맨 앞 '전체'가 선택됨

# (3) 기간: 시작일~종료일을 고르는 슬라이더
min_date = df["date"].min().date()  # 데이터에서 가장 이른 날짜
max_date = df["date"].max().date()  # 데이터에서 가장 늦은 날짜
if min_date < max_date:  # 날짜가 이틀 이상일 때만 슬라이더 표시 (하루뿐이면 슬라이더가 오류남)
    start_date, end_date = st.sidebar.slider(
        "기간", min_value=min_date, max_value=max_date,
        value=(min_date, max_date),  # 처음엔 전체 기간 선택
        format="YYYY-MM-DD",  # 슬라이더에 날짜를 '2026-01-01' 모양으로 표시
    )
else:
    start_date = end_date = min_date  # 하루뿐이면 그 날짜로 고정
    st.sidebar.write(f"기간: {min_date}")


# ----- 5. 조건에 맞는 데이터만 남기기 → filtered -----
condition = (
    df["region"].isin(selected_regions)  # 선택한 지역 중 하나인지
    & (df["date"].dt.date >= start_date)  # 시작일 이후인지
    & (df["date"].dt.date <= end_date)  # 종료일 이전인지
)
if selected_category != "전체":  # '전체'가 아니면 카테고리 조건을 하나 더 붙임
    condition = condition & (df["category"] == selected_category)

filtered = df[condition]  # 조건이 모두 맞는 행만 남긴 표 (아래 지표·그래프·표는 전부 이것만 씀)

# 필터 아래에 몇 건이 남았는지 표시
st.sidebar.divider()  # 구분선
st.sidebar.write(f"선택 조건: **{len(filtered):,}건** / 전체 {len(df):,}건")  # ** ** 사이 글자는 굵게

# 안전장치 3) 조건에 맞는 데이터가 0건일 때 보여줄 안내
EMPTY_MESSAGE = "선택한 조건에 맞는 데이터가 0건이에요. 왼쪽에서 지역을 더 고르거나 기간·카테고리를 넓혀 보세요."


# ----- 6. 본문 탭 세 개 -----
tab_summary, tab_detail, tab_menu = st.tabs(["요약", "상세데이터", "카페 메뉴"])  # 탭 3개 만들기

with tab_summary:  # '요약' 탭
    if filtered.empty:  # 0건이면 안내만 보여주고 지표·그래프는 그리지 않음
        st.info(EMPTY_MESSAGE)
    else:
        # (1) 맨 위: 핵심 숫자 3개를 가로로
        total_sales = int(filtered["sales"].sum())  # 총 매출 (매출 열을 모두 더함)
        order_count = len(filtered)  # 주문 건수 (행 1개 = 주문 1건)
        avg_order = total_sales / order_count  # 평균 주문액 = 총 매출 ÷ 주문 건수

        col1, col2, col3 = st.columns(3)  # 가로로 3칸 나누기
        col1.metric("총 매출", f"{total_sales:,}원")  # :, 는 천 단위 쉼표
        col2.metric("주문 건수", f"{order_count:,}건")
        col3.metric("평균 주문액", f"{avg_order:,.0f}원")  # :,.0f = 쉼표 + 소수점 없이 반올림

        # (2) 월별 매출 추이 → 선 그래프
        st.subheader("월별 매출 추이")
        monthly = filtered.groupby("month")["sales"].sum()  # 월마다 매출 합계 (1, 2, 3 ... 순서 유지)
        st.line_chart(monthly, x_label="월", y_label="매출(원)")  # 꺾은선 그래프 + 축 이름

        # (3) 지역별 월 매출 추이 (어느 지역이 오르고 있는지 보기)
        st.subheader("지역별 월 매출 추이")
        region_monthly = filtered.pivot_table(  # 표 모양 바꾸기: 행=월, 열=지역
            index="month", columns="region", values="sales",
            aggfunc="sum", fill_value=0,  # 같은 칸끼리 더하고, 거래 없는 달은 0으로 채움
        )
        st.line_chart(region_monthly, x_label="월", y_label="매출(원)")  # 지역마다 선 하나씩

        # (4) 지역별 / 카테고리별 매출 → 큰 순서 막대 그래프
        # 막대 그래프는 이름을 가나다순으로 자동 정렬해서, 이름 앞에 '1위', '2위'를 붙여 큰 순서를 지킴
        left, right = st.columns(2)  # 가로로 2칸 나누기
        with left:
            st.subheader("지역별 매출 (큰 순서)")
            region_sales = filtered.groupby("region")["sales"].sum().sort_values(ascending=False)  # 합계 → 큰 순서 정렬
            region_sales.index = [f"{rank}위 {name}" for rank, name in enumerate(region_sales.index, start=1)]  # '1위 부산' 모양으로 이름 바꾸기
            st.bar_chart(region_sales, x_label="지역", y_label="매출(원)")  # 막대 그래프
        with right:
            st.subheader("카테고리별 매출 (큰 순서)")
            category_sales = filtered.groupby("category")["sales"].sum().sort_values(ascending=False)
            category_sales.index = [f"{rank}위 {name}" for rank, name in enumerate(category_sales.index, start=1)]
            st.bar_chart(category_sales, x_label="카테고리", y_label="매출(원)")

with tab_detail:  # '상세데이터' 탭
    st.subheader("전체 데이터")
    if filtered.empty:  # 0건이면 안내만 보여주고 표는 그리지 않음
        st.info(EMPTY_MESSAGE)
    else:
        st.write(f"조건에 맞는 데이터: {len(filtered)}건")  # 몇 건인지 표시
        show = filtered.drop(columns="month").sort_values("date")  # 보조용 month 열은 빼고 날짜순 정렬
        show["date"] = show["date"].dt.strftime("%Y-%m-%d")  # 날짜를 '2026-01-01' 모양으로
        st.dataframe(show, use_container_width=True, hide_index=True)  # 화면 폭에 맞춤 + 행 번호 숨김

with tab_menu:  # '카페 메뉴' 탭 (사이드바 조건과 상관없이 따로 동작)
    st.subheader("카페 메뉴 (12주차 메뉴 API 연결)")
    try:
        menu = load_menu()  # API에서 메뉴 받아오기
    except Exception:  # 서버가 꺼져 있는 등 연결이 안 될 때
        menu = None  # '받아오지 못함' 표시
        st.warning("메뉴 API에 연결할 수 없어요. 창 B에서 uvicorn main:app --reload 로 서버를 켠 뒤 10초 후 새로고침해 주세요.")

    if menu is not None:  # 받아오기에 성공했을 때만 아래 실행
        menu_missing = [col for col in ["name", "category", "price"] if col not in menu.columns]  # 메뉴에 필요한 열 검사
        if menu.empty:
            st.info("메뉴 API에서 받은 메뉴가 0개예요. main.py에 메뉴 데이터가 들어 있는지 확인해 주세요.")
        elif menu_missing:
            st.warning(f"메뉴 데이터에 필요한 열이 없어요: {', '.join(menu_missing)}. 브라우저에서 /menu 화면의 열 이름을 확인해 주세요.")
        else:
            # (1) 조건 고르기: 카테고리(드롭다운) + 최대 가격(슬라이더)를 가로로
            c1, c2 = st.columns(2)
            menu_categories = ["전체"] + sorted(menu["category"].unique())  # '전체' + 메뉴 카테고리 목록
            selected_menu_cat = c1.selectbox("메뉴 카테고리", menu_categories)
            top_price = max(int(menu["price"].max()), 500)  # 가장 비싼 가격 (최소 500으로 해서 슬라이더 오류 방지)
            max_price = c2.slider(
                "최대 가격(원)",
                min_value=0,
                max_value=top_price,  # 가장 비싼 메뉴 가격까지
                value=top_price,  # 처음엔 전체 가격 선택
                step=500,  # 500원 단위로 움직임
            )

            # (2) 조건으로 메뉴 걸러내기
            menu_condition = menu["price"] <= max_price  # 최대 가격 이하인지
            if selected_menu_cat != "전체":  # '전체'가 아니면 카테고리 조건 추가
                menu_condition = menu_condition & (menu["category"] == selected_menu_cat)
            menu_filtered = menu[menu_condition].sort_values("price", ascending=False)  # 비싼 순 정렬

            st.write(f"조건에 맞는 메뉴: **{len(menu_filtered)}개** / 전체 {len(menu)}개")

            if menu_filtered.empty:  # 남은 메뉴가 없으면
                st.info("조건에 맞는 메뉴가 0개예요. 최대 가격을 올리거나 카테고리를 '전체'로 바꿔 보세요.")
            else:
                # (3) 표
                st.dataframe(menu_filtered, use_container_width=True, hide_index=True)
                # (4) 막대 그래프: 메뉴 이름별 가격
                st.subheader("메뉴별 가격")
                st.bar_chart(menu_filtered.set_index("name")["price"], x_label="메뉴", y_label="가격(원)")