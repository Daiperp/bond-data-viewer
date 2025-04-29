import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime
import io

st.set_page_config(
    page_title="Corporate Bond Data Viewer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Corporate Bond Data Viewer")
st.markdown("Visualize corporate bond data from the JSDA website.")

# URLを作成
def construct_url(selected_date):
    year_full = selected_date.year
    year_short = str(year_full)[-2:]
    month = selected_date.strftime("%m")
    day = selected_date.strftime("%d")
    file_name = f"S{year_short}{month}{day}.csv"
    url = (f"https://market.jsda.or.jp/shijyo/saiken/baibai/baisanchi/files/"
           f"{year_full}/{file_name}")
    return file_name, url

# CSVダウンロード
def download_csv(url):
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            try:
                content = response.content.decode('shift-jis')
                df = pd.read_csv(io.StringIO(content), header=None, sep="\t")
                return df
            except Exception as e:
                st.error(f"Error parsing CSV data: {str(e)}")
                return None
        else:
            st.error(f"No data available for the selected date. Status code: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error downloading data: {str(e)}")
        return None

def main():
    # SessionState初期化
    if 'bond_data' not in st.session_state:
        st.session_state.bond_data = None

    today = datetime.now()
    selected_date = st.date_input(
        "Select a date",
        value=today,
        min_value=datetime(2000, 1, 1),
        max_value=today
    )

    if st.button("Fetch Data"):
        with st.spinner("Fetching data..."):
            file_name, url = construct_url(selected_date)
            df = download_csv(url)
            if df is not None:
                st.session_state.bond_data = df

    if st.session_state.bond_data is not None:
        df = st.session_state.bond_data

        # 🔥ここで防御！！
        if df.shape[1] <= 3:
            st.error("Downloaded CSV does not have enough columns. Data may be corrupted.")
            return

        bond_name_column = 3  # 4列目が銘柄名（国庫短期証券など）
        due_date_column = 4   # 5列目が償還期日
        y_column_index = 6    # 7列目が利回りっぽい値

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

                # Years to Maturityを計算
                bond_data["Years to Maturity"] = bond_data.apply(
                    lambda row: (datetime.strptime(str(row[due_date_column]), "%Y%m%d") - selected_date).days / 365,
                    axis=1
                )

                y_value_column = df.columns[y_column_index]

                st.subheader(f"Yield curve for {selected_bond}")

                fig = px.line(
                    bond_data,
                    x="Years to Maturity",
                    y=y_value_column,
                    title=f"Yield curve for {selected_bond}",
                    labels={
                        y_value_column: "Yield (%)",
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

if __name__ == "__main__":
    main()
