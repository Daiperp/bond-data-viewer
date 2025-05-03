import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io
from datetime import datetime
import time
import numpy as np
import unicodedata

# --- ページ設定 ---
st.set_page_config(page_title="JSDA Bond Spread Viewer", layout="wide")
st.markdown("""
    <style>
    .blue-label {
        color: #1f77b4;
        font-weight: bold;
        font-size: 18px;
    }
    .divider {
        border-left: 1px solid #ddd;
        height: 100%;
        margin: 0 20px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("発行体別 社債利回り（複利）/ スプレッド（bp）ビューア")

# --- テキスト正規化関数 ---
def normalize_text(text):
    return unicodedata.normalize("NFKC", str(text)).lower()

# --- 関数群 ---
def construct_url(selected_date):
    y, m, d = selected_date.year, selected_date.strftime("%m"), selected_date.strftime("%d")
    fname = f"S{str(y)[-2:]}{m}{d}.csv"
    url = f"https://market.jsda.or.jp/shijyo/saiken/baibai/baisanchi/files/{y}/{fname}"
    return fname, url

def download_csv(url):
    try:
        res = requests.get(url, timeout=30)
        if res.status_code == 200:
            content = res.content.decode("shift-jis")
            return pd.read_csv(io.StringIO(content), header=None)
    except:
        return None

def calculate_maturity_years(issue_date_str, due_date_str):
    try:
        i = datetime.strptime(str(int(issue_date_str)), "%Y%m%d").date()
        d = datetime.strptime(str(int(due_date_str)), "%Y%m%d").date()
        return round((d - i).days / 365.25, 2)
    except:
        return np.nan

def build_gov_curve(df):
    gov_df = df[df["col_3"].astype(str).str.contains("国債")].copy()
    gov_df["Years to Maturity"] = gov_df.apply(
        lambda row: calculate_maturity_years(row["col_0"], row["col_4"]), axis=1
    )
    gov_df["col_6"] = pd.to_numeric(gov_df["col_6"], errors="coerce")
    gov_df = gov_df[(gov_df["col_6"] <= 999)].dropna(subset=["Years to Maturity", "col_6"])
    curve = gov_df.groupby(gov_df["Years to Maturity"].round())["col_6"].mean().to_dict()
    return curve

def interpolate_from_curve(years, curve):
    keys = sorted(curve.keys())
    if not keys:
        return np.nan
    if years <= keys[0]:
        return curve[keys[0]]
    if years >= keys[-1]:
        return curve[keys[-1]]
    for i in range(len(keys) - 1):
        y0, y1 = keys[i], keys[i+1]
        if y0 <= years <= y1:
            r0, r1 = curve[y0], curve[y1]
            weight = (years - y0) / (y1 - y0)
            return round(r0 + (r1 - r0) * weight, 4)
    return np.nan

# --- セッション初期化 ---
if "df" not in st.session_state:
    st.session_state.df = None
if "selected_date" not in st.session_state:
    st.session_state.selected_date = datetime.now().date()

# --- UI入力 ---
st.markdown('<div class="blue-label">日付を選択</div>', unsafe_allow_html=True)
date_input = st.date_input("", value=st.session_state.selected_date)
st.session_state.selected_date = date_input

if st.button("データ取得"):
    fname, url = construct_url(date_input)
    df = download_csv(url)
    if df is not None and df.shape[1] >= 7:
        df.columns = [f"col_{i}" for i in range(df.shape[1])]
        st.session_state.df = df
    else:
        st.error("指定された日のデータがありません。別の日を指定してください")
        st.session_state.df = None

if st.session_state.df is not None:
    df = st.session_state.df.copy()
    df["issuer_code"] = df["col_2"].astype(str).str[-4:]
    df["issuer_name"] = df["col_3"].str.extract(r"([^\d]+)")

    issuer_list = df[~df["col_3"].astype(str).str.contains("国債")]["issuer_name"].dropna().unique().tolist()

    st.markdown('<div class="blue-label">発行体を検索（部分一致）</div>', unsafe_allow_html=True)
    search_term = st.text_input("")
    if search_term:
        normalized_search = normalize_text(search_term)
        filtered_issuers = [name for name in issuer_list if normalized_search in normalize_text(name)]
        if filtered_issuers:
            st.markdown('<div class="blue-label">発行体を選択</div>', unsafe_allow_html=True)
            issuer = st.selectbox("", filtered_issuers)
        else:
            st.warning("該当する発行体が見つかりません。")
            st.stop()
    else:
        st.info("検索語を入力してください。")
        st.stop()

    df_issuer = df[df["issuer_name"] == issuer].copy()
    df_issuer["Years to Maturity"] = df_issuer.apply(
        lambda row: calculate_maturity_years(row["col_0"], row["col_4"]), axis=1
    )
    df_issuer["col_6"] = pd.to_numeric(df_issuer["col_6"], errors="coerce")
    df_issuer = df_issuer[(df_issuer["col_6"] <= 999)].dropna(subset=["Years to Maturity", "col_6"])

    gov_curve = build_gov_curve(df)

    df_issuer["gov_yield"] = df_issuer["Years to Maturity"].apply(
        lambda y: interpolate_from_curve(y, gov_curve)
    )
    df_issuer["spread_bp"] = ((df_issuer["col_6"] - df_issuer["gov_yield"]) * 100).round(1)

    if not df_issuer.empty:
        col1, spacer, col2 = st.columns([5, 0.2, 5])

        with col1:
            fig1 = px.scatter(
                df_issuer,
                x="Years to Maturity",
                y="col_6",
                hover_data=["col_3"],
                title=f"{issuer} の 利回りカーブ（複利）",
                labels={"col_6": "利回り（複利, %）", "Years to Maturity": "残存年限（年）"}
            )
            fig1.update_layout(
                font=dict(size=16),
                xaxis=dict(title_font=dict(size=18), tickfont=dict(size=16)),
                yaxis=dict(title_font=dict(size=18), tickfont=dict(size=16)),
                plot_bgcolor="white",
                hovermode="x unified"
            )
            st.plotly_chart(fig1, use_container_width=True)

        with spacer:
            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        with col2:
            fig2 = px.scatter(
                df_issuer,
                x="Years to Maturity",
                y="spread_bp",
                hover_data=["col_3"],
                title=f"{issuer} の スプレッドカーブ（bp）",
                labels={"spread_bp": "スプレッド（bp）", "Years to Maturity": "残存年限（年）"}
            )
            fig2.update_layout(
                font=dict(size=16),
                xaxis=dict(title_font=dict(size=18), tickfont=dict(size=16)),
                yaxis=dict(title_font=dict(size=18), tickfont=dict(size=16)),
                plot_bgcolor="white",
                hovermode="x unified"
            )
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("該当するデータが存在しません。")
