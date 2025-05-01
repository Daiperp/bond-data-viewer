import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io
from datetime import datetime
import time
import numpy as np

st.set_page_config(page_title="JSDA Yield Curve Viewer", layout="wide")
st.title("発行体別 社債利回りカーブビューア")

# --- Utility functions ---
def construct_url(selected_date):
    year_full = selected_date.year
    year_short = str(year_full)[-2:]
    month = selected_date.strftime("%m")
    day = selected_date.strftime("%d")
    file_name = f"S{year_short}{month}{day}.csv"
    url = f"https://market.jsda.or.jp/shijyo/saiken/baibai/baisanchi/files/{year_full}/{file_name}"
    return file_name, url

def download_csv(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                content = response.content.decode("shift-jis")
                df = pd.read_csv(io.StringIO(content), header=None)
                return df
            else:
                st.error(f"データが見つかりません。ステータスコード: {response.status_code}")
                return None
        except Exception as e:
            st.warning(f"{attempt+1}回目失敗: {e}")
            time.sleep(1)
    st.error("ダウンロード失敗")
    return None

def calculate_maturity_years(issue_date_str, due_date_str):
    try:
        issue_date = datetime.strptime(str(int(issue_date_str)), "%Y%m%d").date()
        due_date = datetime.strptime(str(int(due_date_str)), "%Y%m%d").date()
        diff_days = (due_date - issue_date).days
        return round(diff_days / 365.25, 2)
    except Exception:
        return np.nan

# --- セッション状態管理 ---
if "df" not in st.session_state:
    st.session_state.df = None
if "selected_date" not in st.session_state:
    st.session_state.selected_date = datetime.now().date()

# --- ユーザー入力 ---
selected_date = st.date_input("日付を選択", value=st.session_state.selected_date)
st.session_state.selected_date = selected_date

if st.button("データ取得"):
    file_name, url = construct_url(selected_date)
    df = download_csv(url)
    if df is not None and df.shape[1] >= 15:
        df.columns = [f"col_{i}" for i in range(df.shape[1])]
        st.session_state.df = df
    else:
        st.error("CSV形式エラーまたは列不足")
        st.session_state.df = None

# --- 可視化処理 ---
if st.session_state.df is not None:
    df = st.session_state.df.copy()

    # 発行体コード（下4桁）と発行体名（銘柄名から回号を除去）を取得
    df["issuer_code"] = df["col_2"].astype(str).str[-4:]
    df["issuer_name"] = df["col_3"].str.extract(r"([^\d]+)")  # 数字以外の部分＝発行体名

    issuer_names = df["issuer_name"].dropna().unique().tolist()
    issuer_selected = st.selectbox("発行体を選択", issuer_names)

    df_issuer = df[df["issuer_name"] == issuer_selected].copy()
    df_issuer["Years to Maturity"] = df_issuer.apply(
        lambda row: calculate_maturity_years(row["col_0"], row["col_4"]), axis=1
    )

    # 利回りを数値化し、異常値除去（例：0～10%）
    df_issuer["col_14"] = pd.to_numeric(df_issuer["col_14"], errors="coerce")
    df_issuer = df_issuer[(df_issuer["col_14"] > 0) & (df_issuer["col_14"] < 10)]

    # グラフ描画
    if not df_issuer.empty:
        fig = px.scatter(
            df_issuer,
            x="Years to Maturity",
            y="col_14",
            hover_data=["col_3"],  # 銘柄名をホバー表示
            title=f"{issuer_selected} の利回りカーブ",
            labels={"col_14": "利回り（%）", "Years to Maturity": "残存年限（年）"}
        )
        fig.update_layout(plot_bgcolor="white", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("該当発行体の利回りデータが存在しません。")
