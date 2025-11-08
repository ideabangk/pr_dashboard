# dashbord.py
# ---------------------------------------------------------
# OIDR 스카우팅 리포트 (Streamlit) - 단일 DF 버전
# 입력: df_oidr_ss.csv  → [선수, 팀, ADI, AER, ER, AEI, OIDR]
# ---------------------------------------------------------

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="공격기여도 스카우팅 리포트", layout="wide")

# ============================ 유틸 ============================
def read_csv_safe(path):
    """UTF-8-SIG 우선, 실패 시 CP949로 재시도"""
    path = Path(path)
    if not path.exists():
        st.error(f"파일을 찾을 수 없습니다: {path}")
        st.stop()
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        return pd.read_csv(path, encoding="cp949")

def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.replace("\ufeff", "", regex=True)  # BOM 제거
        .str.strip()
    )
    return df

def coerce_metrics(df: pd.DataFrame, metrics=("ADI","AER","ER","AEI","OCI")) -> pd.DataFrame:
    df = df.copy()
    for c in metrics:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def ensure_oidr(df: pd.DataFrame) -> pd.DataFrame:
    """OIDR 미존재/NaN이면 임시 가중치로 계산 (표준화 값 가정: ADI/AER/ER/AEI)"""
    df = df.copy()
    has_oidr_col = "OCI" in df.columns
    need_calc = (not has_oidr_col) or df["OCI"].isna().all()
    if need_calc:
        w = {"AEI":0.4, "ADI":0.3, "AER":0.2, "ER":0.1}
        missing = [k for k in w if k not in df.columns]
        if missing:
            st.error(f"임시 OCI 계산 불가 (누락 컬럼: {missing})")
            return df
        df["OCI"] = df["AEI"]*w["AEI"] + df["ADI"]*w["ADI"] + df["AER"]*w["AER"] - df["ER"]*w["ER"]
        st.info("ℹ️ OCI 값이 없어 임시 가중치로 계산했습니다. (AEI 0.4, ADI 0.3, AER 0.2, ER 0.1)")
    return df

# ============================ 데이터 로드 ============================
# 하나의 CSV만 사용 (파일명은 필요에 맞게 변경)
df_oidr_ss = read_csv_safe("남자부_지표.csv")  # 예: "남자부_통합.csv"로 저장했다면 파일명 변경
df_oidr_ss = clean_columns(df_oidr_ss)

# 필수 컬럼 체크
required_cols = {"선수","팀","ADI","AER","ER","AEI","OCI"}
missing_req = required_cols - set(df_oidr_ss.columns)
if missing_req:
    st.error(f"필수 컬럼 누락: {sorted(missing_req)}")
    st.stop()

# 숫자 캐스팅 & OIDR 확보
df_oidr_ss = coerce_metrics(df_oidr_ss, metrics=("ADI","AER","ER","AEI","OCI"))
df_oidr_ss = ensure_oidr(df_oidr_ss)

# ============================ 사이드바 ============================
st.sidebar.title("⚙️ 필터")
teams = ["전체"] + sorted(df_oidr_ss["팀"].dropna().unique().tolist())
sel_team = st.sidebar.selectbox("팀 선택", teams, index=0)

if sel_team != "전체":
    view_df = df_oidr_ss[df_oidr_ss["팀"] == sel_team].copy()
else:
    view_df = df_oidr_ss.copy()

players = sorted(view_df["선수"].dropna().unique().tolist())
sel_player = st.sidebar.selectbox("선수 선택 (프로파일/KPI)", players if players else ["(데이터 없음)"])

compare_players = st.sidebar.multiselect("비교 선수(최대 2명)", players, max_selections=2)

top_n = st.sidebar.slider(
    "Top/Bottom N", 
    min_value=5, 
    max_value=max(5, min(15, len(view_df))),
    value=min(10, len(view_df)) if len(view_df) >= 10 else len(view_df)
)

# ============================ 헤더 ============================
st.title("🏐 OCI 스카우팅 리포트 (단일 DF)")
st.caption("데이터: 선수별 공격지표 (선수, 팀, ADI, AER, ER, AEI, OCI)")

st.markdown("---")

# ============================ KPI (레이아웃 리디자인: 2단 + 4단 + OCI 대형) ============================
st.subheader("🏐 선수 KPI (선택 선수의 실제 지표값)")

# CSS
st.markdown("""
<style>
.kpi-grid-left{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
.kpi{padding:16px;border-radius:16px;background:#f8f9fb;border:1px solid #e9edf5}
.kpi .label{font-size:13px;color:#6b7280;margin-bottom:6px}
.kpi .value{font-size:28px;font-weight:800;color:#111827;line-height:1}
.kpi .sub{font-size:12px;color:#9ca3af;margin-top:4px}
.kpi .tag{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;background:#fff;border:1px solid #e5e7eb;font-size:12px;color:#374151;margin-top:6px}
.kpi .emoji{font-size:18px}

.kpi.span2{grid-column:span 2}         /* 상단 2분할 */
.kpi-oci{padding:22px;border-radius:20px;background:linear-gradient(135deg,#eef2ff,#e0f2fe);border:1px solid #cfe8ff}
.kpi-oci.negative{background:linear-gradient(135deg,#fff1f2,#fee2e2);border-color:#fecaca}
.kpi-oci .label{font-size:14px;color:#334155}
.kpi-oci .value{font-size:40px}
.kpi-oci .sub{font-size:13px}
</style>
""", unsafe_allow_html=True)

if sel_player and sel_player in view_df["선수"].values:
    prow = view_df[view_df["선수"] == sel_player].iloc[0]
    fmt = lambda x, nd=3: "NA" if pd.isna(x) else f"{x:.{nd}f}"

    v_oci = prow.get("OCI", np.nan)
    v_adi = prow.get("ADI", np.nan)
    v_aer = prow.get("AER", np.nan)
    v_er  = prow.get("ER",  np.nan)
    v_aei = prow.get("AEI", np.nan)

    # 전체 영역을 좌/우로 나눔: 왼쪽(2행 그리드), 오른쪽(OCI 대형)
    col_left, col_right = st.columns([2,1], gap="large")

    # ----- 왼쪽: 상단 2분할(선수/팀) + 하단 4분할(ADI/AER/ER/AEI)
    with col_left:
        st.markdown(f"""
        <div class="kpi-grid-left">
          <!-- 상단 2분할 -->
          <div class="kpi span2">
            <div class="label">선수</div>
            <div class="value">{prow['선수']}</div>
            <div class="tag"><span class="emoji">🧑🏻‍🦱</span>선수명</div>
          </div>
          <div class="kpi span2">
            <div class="label">팀</div>
            <div class="value">{prow['팀']}</div>
            <div class="tag"><span class="emoji">🏟️</span>소속팀</div>
          </div>

          <!-- 하단 4분할 -->
          <div class="kpi">
            <div class="label">ADI (다양성)</div>
            <div class="value">{fmt(v_adi)}</div>
            <div class="sub">공격 루트 분산도</div>
          </div>
          <div class="kpi">
            <div class="label">AER (참여도)</div>
            <div class="value">{fmt(v_aer)}</div>
            <div class="sub">공격 관여 비율</div>
          </div>
          <div class="kpi">
            <div class="label">ER (낮을수록↑)</div>
            <div class="value">{fmt(v_er)}</div>
            <div class="sub">범실·실패 영향</div>
          </div>
          <div class="kpi">
            <div class="label">AEI (효율기여)</div>
            <div class="value">{fmt(v_aei)}</div>
            <div class="sub">팀 효율에 대한 기여</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ----- 오른쪽: OCI 대형 카드
    with col_right:
        oci_cls = "kpi-oci negative" if (pd.notna(v_oci) and v_oci < 0) else "kpi-oci"
        st.markdown(f"""
        <div class="{oci_cls}">
          <div class="label">🏐 OCI (종합 파워랭킹 점수)</div>
          <div class="value">{fmt(v_oci)}</div>
          <div class="sub">효율·다양성·참여·안정성 통합 지표</div>
          <div class="tag"><span class="emoji">📈</span>선수 전반 영향력</div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("선수를 선택하세요.")


# ============================ 레이더 ============================
st.subheader("📈 선수 프로파일 (레이더)")
radar_cols = ["ADI","AER","ER","AEI"]
if sel_player and sel_player in view_df["선수"].values:
    row = view_df[view_df["선수"] == sel_player].iloc[0]
    cats = [c for c in radar_cols if c in view_df.columns]
    vals = [row[c] for c in cats]

    cats_c = cats + [cats[0]]
    vals_c = vals + [vals[0]]

    # 데이터 기반 축 범위
    lo = float(np.nanmin(view_df[cats].values)) if cats else -3
    hi = float(np.nanmax(view_df[cats].values)) if cats else 3
    pad = max(0.5, (hi - lo) * 0.1)
    rmin, rmax = lo - pad, hi + pad

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=vals_c, theta=cats_c, fill='toself', name=sel_player
    ))
    fig_radar.update_layout(
        title=f"{sel_player} (팀: {row['팀']})",
        polar=dict(radialaxis=dict(visible=True, range=[rmin, rmax])),
        showlegend=False,
        height=420
    )
    st.plotly_chart(fig_radar, use_container_width=True)
else:
    st.info("선수를 선택하세요.")

st.markdown("---")

# ============================ OIDR Top/Bottom ============================
st.subheader("🏆 OCI 랭킹")
if "OCI" in view_df.columns and view_df["OCI"].notna().any():
    rank_df = view_df[["선수","팀","OCI"]].dropna().copy()
    rank_df = rank_df.sort_values("OCI", ascending=False)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Top 랭킹**")
        top_df = rank_df.head(top_n)
        fig_top = px.bar(
            top_df, x="선수", y="OCI", color="OCI",
            color_continuous_scale="Blues", height=420
        )
        fig_top.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig_top, use_container_width=True)
        st.dataframe(top_df.reset_index(drop=True))
    with c2:
        st.markdown("**Bottom 랭킹**")
        bot_df = rank_df.tail(top_n).sort_values("OCI", ascending=True)
        fig_bot = px.bar(
            bot_df, x="선수", y="OCI", color="OCI",
            color_continuous_scale="Reds", height=420
        )
        fig_bot.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig_bot, use_container_width=True)
        st.dataframe(bot_df.reset_index(drop=True))
else:
    st.warning("⚠️ OCI 값을 찾을 수 없습니다.")

st.markdown("---")

# ============================ 팀별 Top10 인원 수 ============================
st.subheader("🏟️ 팀별 Top10 포함 선수 수")
# 전체(필터 무시) 기준 Top10 집계가 보통 의미가 큼 → 원본 df 기준
rank_all = df_oidr_ss[["선수","팀","OCI"]].dropna().sort_values("OCI", ascending=False)
top10_all = rank_all.head(10)
cnt_by_team = top10_all["팀"].value_counts().reset_index()
cnt_by_team.columns = ["팀","Top10_인원"]

c3, c4 = st.columns([2,1])
with c3:
    fig_cnt = px.bar(cnt_by_team, x="팀", y="Top10_인원", text="Top10_인원", color="Top10_인원",
                     color_continuous_scale="Viridis", height=420)
    fig_cnt.update_traces(textposition="outside")
    st.plotly_chart(fig_cnt, use_container_width=True)
with c4:
    st.dataframe(cnt_by_team, use_container_width=True)

st.markdown("---")

# ============================ 선수 비교 ============================
st.subheader("🔍 선수 비교")
if len(compare_players) == 0:
    st.info("비교할 선수를 사이드바에서 선택하세요. (최대 2명)")
else:
    cols_exist = [c for c in ["선수","팀","OCI"] + radar_cols if c in view_df.columns]
    comp_df = view_df[view_df["선수"].isin(compare_players)][cols_exist].copy()
    st.dataframe(comp_df.reset_index(drop=True), use_container_width=True)

    # 비교 레이더
    if len(compare_players) >= 1:
        fig_cmp = go.Figure()

        # 축 범위 데이터 기반
        lo = float(np.nanmin(view_df[radar_cols].values))
        hi = float(np.nanmax(view_df[radar_cols].values))
        pad = max(0.5, (hi - lo) * 0.1)
        rmin, rmax = lo - pad, hi + pad

        for p in compare_players:
            r = view_df[view_df["선수"] == p].iloc[0]
            cats = [c for c in radar_cols if c in view_df.columns]
            vals = [r[c] for c in cats]
            fig_cmp.add_trace(go.Scatterpolar(
                r=vals + [vals[0]],
                theta=cats + [cats[0]],
                fill='toself',
                name=f"{p} ({r['팀']})",
                opacity=0.6
            ))
        fig_cmp.update_layout(
            title="선수 비교 레이더",
            polar=dict(radialaxis=dict(visible=True, range=[rmin, rmax])),
            height=460
        )
        st.plotly_chart(fig_cmp, use_container_width=True)

    if len(compare_players) == 2:
        p1, p2 = compare_players
        r1 = view_df[view_df["선수"] == p1].iloc[0]
        r2 = view_df[view_df["선수"] == p2].iloc[0]
        deltas = {
            "OCI": float(r1.get("OCI", np.nan)) - float(r2.get("OCI", np.nan)),
            "ADI":  float(r1["ADI"])  - float(r2["ADI"]),
            "AER":  float(r1["AER"])  - float(r2["AER"]),
            "ER":   float(r1["ER"])   - float(r2["ER"]),
            "AEI":  float(r1["AEI"])  - float(r2["AEI"]),
        }
        ddf = pd.DataFrame({"지표": list(deltas.keys()), "Δ(1-2)": list(deltas.values())})
        st.dataframe(ddf, use_container_width=True)

st.markdown("---")

# ============================ 원본/필터 테이블 & 다운로드 ============================
st.subheader("📄 현재 필터 테이블")
st.dataframe(view_df.reset_index(drop=True), use_container_width=True)

csv = view_df.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="CSV 다운로드 (현재 필터 적용)",
    data=csv,
    file_name="OCI_scouting_filtered.csv",
    mime="text/csv",
)
