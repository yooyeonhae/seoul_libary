import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="서울 도서관 표준데이터 분석", layout="wide")

CSV_PATH = "전국도서관표준데이터.csv"
SIDO_NAME = "서울특별시"

CATEGORICAL = ["#2a78d6", "#1baf7a", "#eda100", "#008300",
               "#4a3aa7", "#e34948", "#e87ba4", "#eb6834"]
SEQUENTIAL_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5",
                   "#256abf", "#184f95", "#0d366b"]
BLUE = "#2a78d6"

NUMERIC_COLS = ["열람좌석수", "자료수(도서)", "자료수(연속간행물)", "자료수(비도서)",
                 "대출가능권수", "대출가능일수", "부지면적", "건물면적", "위도", "경도"]


@st.cache_data
def load_seoul_data():
    df = pd.read_csv(CSV_PATH, encoding="cp949")
    df = df[df["시도명"] == SIDO_NAME].copy()
    for c in NUMERIC_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["자료수(전체)"] = df[["자료수(도서)", "자료수(연속간행물)", "자료수(비도서)"]].sum(axis=1)
    return df


def to_hours(t):
    try:
        h, m = str(t).split(":")
        return int(h) + int(m) / 60
    except (ValueError, AttributeError):
        return np.nan


def add_duration_cols(df):
    df = df.copy()
    for label, start_col, end_col in [
        ("평일", "평일운영시작시각", "평일운영종료시각"),
        ("토요일", "토요일운영시작시각", "토요일운영종료시각"),
        ("공휴일", "공휴일운영시작시각", "공휴일운영종료시각"),
    ]:
        s = df[start_col].apply(to_hours)
        e = df[end_col].apply(to_hours)
        dur = (e - s).where(lambda x: x > 0)
        df[f"{label}운영시간"] = dur
    return df


df = load_seoul_data()
type_order = df["도서관유형"].value_counts().index.tolist()
TYPE_COLOR = {t: CATEGORICAL[i % len(CATEGORICAL)] for i, t in enumerate(type_order)}
gu_order_all = df["시군구명"].value_counts().index.tolist()

st.sidebar.title("📚 서울 도서관 표준데이터")
page = st.sidebar.radio(
    "메뉴",
    ["개요", "자치구별 분석", "유형별 분석", "운영시간 분석", "지도", "데이터 탐색"],
)

st.sidebar.markdown("---")
st.sidebar.subheader("필터")
sel_gu = st.sidebar.multiselect("자치구", sorted(df["시군구명"].unique()))
sel_type = st.sidebar.multiselect("도서관유형", type_order)

fdf = df.copy()
if sel_gu:
    fdf = fdf[fdf["시군구명"].isin(sel_gu)]
if sel_type:
    fdf = fdf[fdf["도서관유형"].isin(sel_type)]
st.sidebar.caption(f"필터 적용 결과: {len(fdf):,}개관 / 서울 전체 {len(df):,}개관")


# ---------------------------------------------------------------- 개요
if page == "개요":
    st.title("서울특별시 공공도서관 현황 개요")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("도서관 수", f"{len(fdf):,}개관")
    c2.metric("열람좌석수 합계", f"{fdf['열람좌석수'].sum():,.0f}석")
    c3.metric("보유 자료수 합계", f"{fdf['자료수(전체)'].sum():,.0f}점")
    c4.metric("평균 건물면적", f"{fdf['건물면적'].mean():,.0f}㎡")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("자치구별 도서관 수")
        by_gu = fdf["시군구명"].value_counts().reset_index()
        by_gu.columns = ["시군구명", "도서관수"]
        fig = px.bar(by_gu, x="도서관수", y="시군구명", orientation="h",
                     color_discrete_sequence=[BLUE])
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=650)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("도서관 유형별 분포")
        by_type = fdf["도서관유형"].value_counts().reset_index()
        by_type.columns = ["도서관유형", "도서관수"]
        fig = px.bar(by_type, x="도서관수", y="도서관유형", orientation="h",
                     color="도서관유형", color_discrete_map=TYPE_COLOR)
        fig.update_layout(yaxis={"categoryorder": "total ascending"},
                           showlegend=False, height=650)
        st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------- 자치구별 분석
elif page == "자치구별 분석":
    st.title("자치구별 분석")

    metric = st.selectbox(
        "지표 선택",
        ["도서관 수", "열람좌석수", "자료수(전체)", "부지면적", "건물면적"],
    )

    if metric == "도서관 수":
        agg = fdf.groupby("시군구명").size().reset_index(name="값")
    else:
        agg = fdf.groupby("시군구명")[metric].sum().reset_index(name="값")
    agg = agg.sort_values("값", ascending=False)

    fig = px.bar(agg, x="시군구명", y="값", color="값",
                 color_continuous_scale=SEQUENTIAL_BLUE)
    fig.update_layout(xaxis={"categoryorder": "total descending"},
                       coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("자치구별 도서관 유형 구성")
    stack = fdf.groupby(["시군구명", "도서관유형"]).size().reset_index(name="도서관수")
    gu_order = fdf["시군구명"].value_counts().index.tolist()
    fig2 = px.bar(stack, x="시군구명", y="도서관수", color="도서관유형",
                  color_discrete_map=TYPE_COLOR,
                  category_orders={"시군구명": gu_order})
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("순위표")
    st.dataframe(agg.reset_index(drop=True), use_container_width=True)


# ---------------------------------------------------------------- 유형별 분석
elif page == "유형별 분석":
    st.title("도서관 유형별 분석")

    summary = fdf.groupby("도서관유형").agg(
        도서관수=("도서관명", "count"),
        평균열람좌석수=("열람좌석수", "mean"),
        평균자료수=("자료수(전체)", "mean"),
        평균건물면적=("건물면적", "mean"),
    ).reset_index().sort_values("도서관수", ascending=False)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(summary, x="도서관유형", y="평균열람좌석수",
                     color="도서관유형", color_discrete_map=TYPE_COLOR)
        fig.update_layout(showlegend=False, title="유형별 평균 열람좌석수")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(summary, x="도서관유형", y="평균자료수",
                     color="도서관유형", color_discrete_map=TYPE_COLOR)
        fig.update_layout(showlegend=False, title="유형별 평균 보유 자료수")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("요약 통계표")
    st.dataframe(
        summary.style.format({
            "평균열람좌석수": "{:.1f}", "평균자료수": "{:.1f}", "평균건물면적": "{:.1f}",
        }),
        use_container_width=True,
    )


# ---------------------------------------------------------------- 운영시간 분석
elif page == "운영시간 분석":
    st.title("운영시간 분석")
    hdf = add_duration_cols(fdf)

    avg_hours = hdf[["평일운영시간", "토요일운영시간", "공휴일운영시간"]].mean().reset_index()
    avg_hours.columns = ["구분", "평균운영시간"]
    fig = px.bar(avg_hours, x="구분", y="평균운영시간", color="구분",
                 color_discrete_sequence=CATEGORICAL)
    fig.update_layout(showlegend=False, title="평일/토요일/공휴일 평균 운영시간(시간)")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("평일 운영시간 분포")
    fig2 = px.histogram(hdf.dropna(subset=["평일운영시간"]), x="평일운영시간",
                         nbins=30, color_discrete_sequence=[BLUE])
    fig2.update_layout(xaxis_title="평일 운영시간(시간)", yaxis_title="도서관 수")
    st.plotly_chart(fig2, use_container_width=True)

    st.caption("※ 시작·종료 시각이 모두 00:00인 경우(토요일·공휴일 휴관 등)는 운영시간 계산에서 제외했습니다.")

    st.subheader("운영시간이 가장 긴 도서관 Top 20 (평일 기준)")
    top20 = hdf.dropna(subset=["평일운영시간"]).sort_values(
        "평일운영시간", ascending=False
    )[["도서관명", "시군구명", "도서관유형", "평일운영시작시각", "평일운영종료시각", "평일운영시간"]].head(20)
    st.dataframe(top20.reset_index(drop=True), use_container_width=True)


# ---------------------------------------------------------------- 지도
elif page == "지도":
    st.title("서울 도서관 위치 지도")
    mdf = fdf.dropna(subset=["위도", "경도"])
    st.caption(f"좌표 정보가 있는 {len(mdf):,}개관을 표시합니다 (전체 {len(fdf):,}개관 중 좌표 결측 {len(fdf) - len(mdf):,}개관 제외).")

    fig = px.scatter_map(
        mdf, lat="위도", lon="경도", color="도서관유형",
        color_discrete_map=TYPE_COLOR,
        hover_name="도서관명",
        hover_data={"시군구명": True, "소재지도로명주소": True, "위도": False, "경도": False},
        zoom=10, height=650,
    )
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------- 데이터 탐색
elif page == "데이터 탐색":
    st.title("데이터 탐색")

    keyword = st.text_input("도서관명 / 주소 검색")
    view = fdf.copy()
    if keyword:
        mask = (
            view["도서관명"].str.contains(keyword, case=False, na=False)
            | view["소재지도로명주소"].str.contains(keyword, case=False, na=False)
        )
        view = view[mask]

    st.caption(f"{len(view):,}개관 표시 중")
    display_cols = [
        "도서관명", "시군구명", "도서관유형", "소재지도로명주소",
        "열람좌석수", "자료수(도서)", "자료수(연속간행물)", "자료수(비도서)",
        "부지면적", "건물면적", "운영기관명", "도서관전화번호", "홈페이지주소",
    ]
    st.dataframe(view[display_cols].reset_index(drop=True), use_container_width=True)

    csv = view[display_cols].to_csv(index=False).encode("cp949", errors="ignore")
    st.download_button("CSV 다운로드", data=csv, file_name="서울_도서관_검색결과.csv", mime="text/csv")
