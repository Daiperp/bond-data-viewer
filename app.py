import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import time
from datetime import datetime
import io

# ページ設定
st.set_page_config(
    page_title="Corporate Bond Data Viewer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Corporate Bond Data Viewer")
st.markdown("Visualize corporate bond data from the JSDA website.")

# URL作成
def construct_url(selected_date):
    year_full = selected_date.year
    year_short = str(year_full)[-2:]
    month = selected_date.strftime("%m")
    day = selected_date.strftime("%d")
    file_name = f"S{year_short}{month}{day}.csv"
    url = f"https://market.jsda.or.jp/shijyo/saiken/baibai/baisanchi/files/{year_full}/{file_name}"
    return file_name, url

# CSVダウンロード
def download_csv(url, max_retries=3):
    retry_count = 0
    while retry_count < max_retries:
        try:
            st.info(f"Downloading data (attempt {retry_count + 1}/{max_retries})...")
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                try:
                    content = response.content.decode('shift-jis')
                    df = pd.read_csv(io.StringIO(content), header=None, sep="\t")
                    return df
                except Exception as e:
                    st.warning(f"Error parsing CSV data: {str(e)}")
                    retry_count += 1
                    if retry_count >= max_retries:
                        st.error("Failed to parse CSV data after multiple attempts. The CSV format may be invalid or the data is corrupted.")
                        return None
            else:
                st.error(f"No data available for the selected date. Status code: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            retry_count += 1
            if retry_count >= max_retries:
                st.error(f"Failed to download data after {max_retries} attempts. Please check your internet connection and try again later.")
                return None
            else:
                st.warning(f"Download attempt {retry_count} failed: {str(e)}. Retrying...")
                time.sleep(1)

# 年限計算
def calculate_years_to_maturity(due_date_str, selected_date):
    try:
        due_date = datetime.strptime(str(int(due_date_str)), "%Y%m%d").date()

        if isinstance(selected_date, datetime):
            selected_date = selected_date.date()

        days_to_maturity = (due_date - selected_date).days
        years_to_maturity = days_to_maturity / 365.25
        return round(years_to_maturity, 2)
    except Exception as e:
        st.warning(f"Error calculating years to maturity: {str(e)}")
        return None

# メイン関数
def main():
    today = datetime.now().date()
    selected_date = st.date_input(
        "Select a date",
        value=today,
        min_value=datetime(2000, 1, 1).date(),
        max_value=today
    )

    if st.button("Fetch Data"):
        with st.spinner("Fetching data..."):
            file_name, url = construct_url(selected_date)
            df = download_csv(url)

            if df is not None and df.shape[1] >= 5:
                st.session_state.bond_data = df

                bond_name_column = 3  # 銘柄名列
                due_date_column = 4   # 償還期日列
                yield_column_index = 6  # 利回り列とみなす

                bond_names = df.iloc[:, bond_name_column].dropna().unique().tolist()
                bond_names = [name for name in bond_names if not str(name).isnumeric()]

                if bond_names:
                    selected_bond = st.selectbox(
                        "Select a bond to visualize",
                        bond_names
                    )

                    bond_data = df[df.iloc[:, bond_name_column] == selected_bond]

                    if not bond_data.empty:
                        bond_data = bond_data.copy()
                        bond_data["Years to Maturity"] = bond_data.iloc[:, due_date_column].apply(
                            lambda x: calculate_years_to_maturity(x, selected_date)
                        )

                        st.subheader(f"Yield curve for {selected_bond}")

                        fig = px.line(
                            bond_data,
                            x="Years to Maturity",
                            y=bond_data.columns[yield_column_index],
                            title=f"Yield curve for {selected_bond}",
                            labels={
                                bond_data.columns[yield_column_index]: "Yield (%)",
                                "Years to Maturity": "Years to Maturity"
                            }
                        )

                        fig.update_layout(
                            xaxis_title="Years to Maturity",
                            yaxis_title="Yield (%)",
                            plot_bgcolor="white",
                            hovermode="x unified"
                        )

                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("No data available for the selected bond.")
                else:
                    st.warning("No bond names found in the data.")
            else:
                st.error("Downloaded CSV does not have enough columns. Data may be corrupted.")

if __name__ == "__main__":
    main()
