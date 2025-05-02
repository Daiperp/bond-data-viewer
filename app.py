import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io
from datetime import datetime
import time
import numpy as np

# --- ページ設定 ---
st.set_page_config(page_title="JSDA Bond Spread Viewer", layout="wide")
st.title("発行体別 社債利回り（複利）/ スプレッド（複利）ビューア")

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
    gov_df = gov_df.dropna(subset=["Years to Maturity", "col_5"])
    gov_df["col_5"] = pd.to_numeric(gov_df["col_5"], errors="coerce")
    gov_df = gov_df.dropna(subset=["col_5"])
    curve = gov_df.groupby("Years to Maturity")["col_5"].mean().to_dict()
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
date_input = st.date_input("日付を選択", value=st.session_state.selected_date)
st.session_state.selected_date = date_input

view_mode = st.radio("表示モードを選択", ["利回り（複利）", "スプレッド（複利）"], horizontal=True)

if st.button("データ取得"):
    fname, url = construct_url(date_input)
    df = download_csv(url)
    if df is not None and df.shape[1] >= 6:
        df.columns = [f"col_{i}" for i in range(df.shape[1])]
        st.session_state.df = df
    else:
        st.error("CSVが壊れているか、列数が不足しています")
        st.session_state.df = None

if st.session_state.df is not None:
    df = st.session_state.df.copy()
    df["issuer_code"] = df["col_2"].astype(str).str[-4:]
    df["issuer_name"] = df["col_3"].str.extract(r"([^\d]+)")

    issuer_list = df[~df["col_3"].astype(str).str.contains("国債")]["issuer_name"].dropna().unique().tolist()
    issuer = st.selectbox("発行体を選択", issuer_list)

    df_issuer = df[df["issuer_name"] == issuer].copy()
    df_issuer["Years to Maturity"] = df_issuer.apply(
        lambda row: calculate_maturity_years(row["col_0"], row["col_4"]), axis=1
    )
    df_issuer["col_5"] = pd.to_numeric(df_issuer["col_5"], errors="coerce")
    df_issuer = df_issuer.dropna(subset=["Years to Maturity", "col_5"])

    gov_curve = build_gov_curve(df)

    if view_mode == "スプレッド（複利）":
        df_issuer["gov_yield"] = df_issuer["Years to Maturity"].apply(
            lambda y: interpolate_from_curve(y, gov_curve)
        )
        df_issuer["Spread"] = df_issuer["col_5"] - df_issuer["gov_yield"]
        y_col = "Spread"
        y_label = "スプレッド（複利, %）"
    else:
        y_col = "col_5"
        y_label = "利回り（複利, %）"

    if not df_issuer.empty:
        fig = px.scatter(
            df_issuer,
            x="Years to Maturity",
            y=y_col,
            hover_data=["col_3"],
            title=f"{issuer} の {view_mode} カーブ",
            labels={y_col: y_label, "Years to Maturity": "残存年限（年）"}
        )
        fig.update_layout(plot_bgcolor="white", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("該当するデータが存在しません。")

