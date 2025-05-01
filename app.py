import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io
from datetime import datetime
import time
import numpy as np

st.set_page_config(page_title="JSDA Bond Viewer", layout="wide")
st.title("JSDA Corporate Bond Yield Curve Viewer")

# --- Utility functions ---
def construct_url(selected_date):
    """Construct file name and download URL from a given date"""
    year_full = selected_date.year
    year_short = str(year_full)[-2:]
    month = selected_date.strftime("%m")
    day = selected_date.strftime("%d")
    file_name = f"S{year_short}{month}{day}.csv"
    url = f"https://market.jsda.or.jp/shijyo/saiken/baibai/baisanchi/files/{year_full}/{file_name}"
    return file_name, url

def download_csv(url, max_retries=3):
    """Download CSV from JSDA with retry logic"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                content = response.content.decode("shift-jis")
                df = pd.read_csv(io.StringIO(content), header=None)
                return df
            else:
                st.error(f"Data not found for selected date. Status code: {response.status_code}")
                return None
        except Exception as e:
            st.warning(f"Attempt {attempt+1} failed: {e}")
            time.sleep(1)
    st.error("Failed to download after multiple attempts.")
    return None

def calculate_maturity_years(issue_date_str, due_date_str):
    """Calculate remaining maturity in years"""
    try:
        issue_date = datetime.strptime(str(int(issue_date_str)), "%Y%m%d").date()
        due_date = datetime.strptime(str(int(due_date_str)), "%Y%m%d").date()
        diff_days = (due_date - issue_date).days
        return round(diff_days / 365.25, 2)
    except Exception:
        return np.nan

# --- Main App Logic ---
def main():
    today = datetime.now().date()
    selected_date = st.date_input("Select a date", value=today)

    if st.button("Fetch and Visualize Data"):
        file_name, url = construct_url(selected_date)
        df = download_csv(url)

        if df is None or df.shape[1] < 16:
            st.error("Invalid or corrupted CSV file.")
            return

        df.columns = [f"col_{i}" for i in range(df.shape[1])]

        # 発行体+回号一覧（col_3）
        bond_options = df["col_3"].dropna().unique().tolist()
        bond_selected = st.selectbox("Select Bond (Issuer + Series)", bond_options)

        df_selected = df[df["col_3"] == bond_selected].copy()

        if df_selected.empty:
            st.warning("No data found for selected bond.")
            return

        # 残存年限を計算
        df_selected["Years to Maturity"] = df_selected.apply(
            lambda row: calculate_maturity_years(row["col_0"], row["col_4"]), axis=1
        )

        # 利回りと残存年限でグラフ化（利回り = col_15）
        try:
            fig = px.scatter(
                df_selected,
                x="Years to Maturity",
                y="col_15",
                title=f"Yield Curve for {bond_selected}",
                labels={"col_15": "Yield (%)", "Years to Maturity": "Years to Maturity"},
            )
            fig.update_layout(plot_bgcolor="white", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Graph rendering failed: {e}")

if __name__ == "__main__":
    main()
