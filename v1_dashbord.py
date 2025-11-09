# dashbord.py
# ---------------------------------------------------------
# OCI 스카우팅 리포트 (남/여 선택 버전)
# - 입력 CSV:
#   men_df_oidr_ss.csv    → [선수, 팀, ADI, AER, ER, AEI, OCI]
#   women_df_oidr_ss.csv  → [선수, 팀, ADI, AER, ER, AEI, OCI]
# - 남/여 비교가 아니라, "선택"해서 각각 별도로 조회
# ---------------------------------------------------------

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="OCI 스카우팅 리포트", layout="wide")

# ============================ 유틸 ============================
def read_csv_safe(path):
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
    # 문자열 컬럼 공백 정리
    for c in ["선수", "팀"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()  # ✅ 수정된 부분
    return df


def prepare_df(df):
    df = clean_columns(df)
    # 필수 컬럼 체크
    req = {"선수","팀","ADI","AER","ER","AEI","OCI"}
    miss = req - set(df.columns)
    if miss:
        st.error(f"필수 컬럼 누락: {sorted(miss)}")
        st.stop()
    
    # --- 정규화(0~1 범위로 스케일링) ---
    from sklearn.preprocessing import MinMaxScaler

    # 정규화할 지표 컬럼
    scale_cols = ["ADI", "AER", "ER", "AEI", "OCI"]

    scaler = MinMaxScaler(feature_range=(0, 1))
    df[scale_cols] = scaler.fit_transform(df[scale_cols])
    return coerce_metrics(df)

# ============================ 데이터 로드 ============================
MEN_FILE   = "남자부_지표.csv"    # 남자부 파일명
WOMEN_FILE = "여자부_지표.csv"  # 여자부 파일명

df_men   = prepare_df(read_csv_safe(MEN_FILE))
df_women = prepare_df(read_csv_safe(WOMEN_FILE))

# ============================ 리그 선택 & 뷰 데이터 ============================
st.sidebar.title("⚙️ 필터")
league = st.sidebar.radio("리그 선택", ["남자부", "여자부"], horizontal=True)
base_df = df_men if league == "남자부" else df_women

teams = ["전체"] + sorted(base_df["팀"].dropna().unique().tolist())
sel_team = st.sidebar.selectbox("팀 선택", teams, index=0)

view_df = base_df if sel_team == "전체" else base_df[base_df["팀"] == sel_team].copy()

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
st.title(f"🏐 OCI 스카우팅 리포트 — {league}")
st.caption("데이터: ADI(다양성) · AER(참여도) · ER(안정성) · AEI(효율기여) · OCI(종합점수)")
st.markdown("---")

# ============================ KPI (2단 + 4단 + OCI 대형) ============================
st.subheader("선수 KPI (선택 선수의 실제 지표값)")

st.markdown("""
<style>
.kpi-grid-left{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
.kpi{padding:16px;border-radius:16px;background:#f8f9fb;border:1px solid #e9edf5}
.kpi .label{font-size:13px;color:#6b7280;margin-bottom:6px}
.kpi .value{font-size:28px;font-weight:800;color:#111827;line-height:1}
.kpi .sub{font-size:12px;color:#9ca3af;margin-top:4px}
.kpi .tag{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;background:#fff;border:1px solid #e5e7eb;font-size:12px;color:#374151;margin-top:6px}
.kpi .emoji{font-size:18px}
.kpi.span2{grid-column:span 2}
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

    v_oci = prow["OCI"]
    v_adi = prow["ADI"]
    v_aer = prow["AER"]
    v_er  = prow["ER"]
    v_aei = prow["AEI"]

    col_left, col_right = st.columns([2,1], gap="large")

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
            <div class="label">ER (안정성)</div>
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

    with col_right:
        oci_cls = "kpi-oci negative" if (pd.notna(v_oci) and v_oci < 0) else "kpi-oci"
        st.markdown(f"""
        <div class="{oci_cls}">
          <div class="label">🏐 OCI (종합 파워랭킹 점수)</div>
          <div class="value">{fmt(v_oci)}</div>
          <div class="sub">효율·다양성·참여·안정성 통합 지표</div>
          <div class="tag"><span class="emoji">📈</span>{league} 영향력</div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("선수를 선택하세요.")

# ============================ Power Ranking 미니박스 (KPI 내부, 가로형) ============================
rank_all = (base_df[["선수","팀","OCI"]]
            .dropna(subset=["OCI"])
            .sort_values("OCI", ascending=False)
            .reset_index(drop=True))
total_n = len(rank_all)

if total_n > 0 and prow["선수"] in rank_all["선수"].values:
    league_rank = int(rank_all.index[rank_all["선수"] == prow["선수"]][0]) + 1
    pct = 100.0 * (total_n - league_rank + 1) / total_n
else:
    league_rank, pct = None, None

team_rank_df = (rank_all[rank_all["팀"] == prow["팀"]]
                .sort_values("OCI", ascending=False)
                .reset_index(drop=True))
team_n = len(team_rank_df)
if team_n > 0 and prow["선수"] in team_rank_df["선수"].values:
    team_rank = int(team_rank_df.index[team_rank_df["선수"] == prow["선수"]][0]) + 1
else:
    team_rank = None

# 스타일 정의
st.markdown("""
<style>
.pr-wide{margin-top:18px;padding:22px 28px;border-radius:18px;
         background:linear-gradient(135deg,#f0f9ff,#e0f2fe);
         border:1px solid #bae6fd;}
.pr-title{font-size:17px;font-weight:700;color:#0f172a;margin-bottom:12px;display:flex;align-items:center;gap:6px}
.pr-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;align-items:center;text-align:center;}
.pr-item{background:#ffffffb3;padding:16px;border-radius:14px;border:1px solid #dbeafe;}
.pr-value{font-size:38px;font-weight:800;color:#0f172a;line-height:1.1}
.pr-sub{font-size:14px;color:#475569;margin-top:4px}
.pr-badge{display:inline-flex;align-items:center;gap:6px;
          background:#fff;border:1px solid #cbd5e1;
          padding:4px 10px;border-radius:999px;font-size:12px;color:#334155;margin-top:14px}
</style>
""", unsafe_allow_html=True)

# 텍스트 포맷팅
fmt = lambda x, nd=1: "NA" if pd.isna(x) else f"{x:.{nd}f}"
league_txt = f"리그 {league_rank}위 / {total_n}명" if league_rank else "리그 순위 정보 없음"
pct_txt = f"상위 {fmt(pct)}%" if pct else ""
team_txt = f"{prow['팀']} {team_rank}위 / {team_n}명" if team_rank else "팀 순위 정보 없음"

# 렌더링
st.markdown(f"""
<div class="pr-wide">
  <div class="pr-title">🏆 Power Ranking</div>
  <div class="pr-grid">
    <div class="pr-item">
      <div class="pr-value">{f'{league_rank} 위' if league_rank else 'NA'}</div>
      <div class="pr-sub">{league_txt} · {pct_txt}</div>
    </div>
    <div class="pr-item">
      <div class="pr-value">{f'{team_rank} 위' if team_rank else 'NA'}</div>
      <div class="pr-sub">팀 내 순위 · {team_txt}</div>
    </div>
  </div>
  <div class="pr-badge">📊 {league} 리그 파워랭킹 기준</div>
</div>
""", unsafe_allow_html=True)


st.markdown("---")

# ============================ OCI Top/Bottom ============================
st.subheader(f"🏆 {league} OCI 랭킹")
rank_df = view_df[["선수","팀","OCI"]].dropna().copy().sort_values("OCI", ascending=False)

c1, c2 = st.columns(2)
with c1:
    st.markdown("**Top 랭킹**")
    top_df = rank_df.head(top_n)
    fig_top = px.bar(top_df, x="선수", y="OCI", color="OCI",
                     color_continuous_scale="Blues", height=420)
    fig_top.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig_top, use_container_width=True)
    st.dataframe(top_df.reset_index(drop=True))
with c2:
    st.markdown("**Bottom 랭킹**")
    bot_df = rank_df.tail(top_n).sort_values("OCI", ascending=True)
    fig_bot = px.bar(bot_df, x="선수", y="OCI", color="OCI",
                     color_continuous_scale="Reds", height=420)
    fig_bot.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig_bot, use_container_width=True)
    st.dataframe(bot_df.reset_index(drop=True))

st.markdown("---")

# ============================ 팀별 Top10 인원 수 ============================
st.subheader(f"🏟️ {league} 팀별 Top10 포함 선수 수")
rank_all = base_df[["선수","팀","OCI"]].dropna().sort_values("OCI", ascending=False)  # 리그 전체 기준
top10_all = rank_all.head(10)
cnt_by_team = top10_all["팀"].value_counts().reset_index()
cnt_by_team.columns = ["팀","Top10_인원"]

c3, c4 = st.columns([2,1])
with c3:
    fig_cnt = px.bar(cnt_by_team, x="팀", y="Top10_인원", text="Top10_인원",
                     color="Top10_인원", color_continuous_scale="Viridis", height=420)
    fig_cnt.update_traces(textposition="outside")
    st.plotly_chart(fig_cnt, use_container_width=True)
with c4:
    st.dataframe(cnt_by_team, use_container_width=True)

st.markdown("---")

# ============================ 선수 비교 ============================
st.subheader("🔍 선수 비교")
radar_cols = ["ADI","AER","ER","AEI"]
if len(compare_players) == 0:
    st.info("비교할 선수를 사이드바에서 선택하세요. (최대 2명)")
else:
    cols_exist = [c for c in ["선수","팀","OCI"] + radar_cols if c in view_df.columns]
    comp_df = view_df[view_df["선수"].isin(compare_players)][cols_exist].copy()
    st.dataframe(comp_df.reset_index(drop=True), use_container_width=True)

    if len(compare_players) >= 1:
        fig_cmp = go.Figure()
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
                fill='toself', name=f"{p} ({r['팀']})", opacity=0.6
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
            "ADI": float(r1["ADI"]) - float(r2["ADI"]),
            "AER": float(r1["AER"]) - float(r2["AER"]),
            "ER":  float(r1["ER"])  - float(r2["ER"]),
            "AEI": float(r1["AEI"]) - float(r2["AEI"]),
        }
        ddf = pd.DataFrame({"지표": list(deltas.keys()), "Δ(1-2)": list(deltas.values())})
        st.dataframe(ddf, use_container_width=True)

st.markdown("---")

# ============================ 필터 테이블 & 다운로드 ============================
st.subheader("📄 현재 필터 테이블")
st.dataframe(view_df.reset_index(drop=True), use_container_width=True)

csv = view_df.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="CSV 다운로드 (현재 필터 적용)",
    data=csv,
    file_name=f"{league}_OCI_scouting_filtered.csv",
    mime="text/csv",
)
