import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import time
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

COLUMN_MAPPING = {
    "日付": "Date",
    "銘柄種別": "Issue Type",
    "銘柄コード": "Code",
    "銘柄名": "Issues",
    "償還期日": "Due Date",
    "利率": "Coupon Rate",
    "平均値複利": "Average Compound Yield",
    "平均値単価": "Average Price(Yen)",
    "平均値単価前日比": "Change (Yen)",
    "利払日": "Interest Payment Date",
    "銘柄属性・情報": "Information",
    "平均値単利": "Average Simple Yield",
    "最高値": "High",
    "最低値": "Low",
    "チェックフラグ": "Invalid",
    "報告社数": "Number of Reporting Members",
    "最高値複利": "Highest Compound Yield",
    "最高値単価前日比": "Highest Price Change (Yen)",
    "最低値複利": "Lowest Compound Yield",
    "最低値単価前日比": "Lowest Price Change (Yen)",
    "中央値複利": "Median Compound Yield",
    "中央値単利": "Median Simple Yield",
    "中央値単価": "Median Price(Yen)",
    "中央値単価前日比": "Median Price Change (Yen)"
}


def construct_url(selected_date):
    """
    Construct the CSV file name and URL based on the selected date.

    Args:
        selected_date (datetime): The selected date

    Returns:
        tuple: (file_name, url)
    """
    year_full = selected_date.year
    year_short = str(year_full)[-2:]
    month = selected_date.strftime("%m")
    day = selected_date.strftime("%d")

    file_name = f"S{year_short}{month}{day}.csv"
    url = (f"https://market.jsda.or.jp/shijyo/saiken/baibai/baisanchi/files/"
           f"{year_full}/{file_name}")

    return file_name, url


def download_csv(url, max_retries=3):
    """
    Download the CSV file from the given URL with retry mechanism.

    Args:
        url (str): The URL to download the CSV from
        max_retries (int): Maximum number of retry attempts

    Returns:
        pandas.DataFrame or None: The downloaded data as a DataFrame,
        or None if download failed after all retries
    """
    retry_count = 0
    while retry_count < max_retries:
        try:
            st.info(f"Downloading data (attempt {retry_count + 1}/{max_retries})...")
            response = requests.get(url, timeout=30)  # Increased timeout to 30 seconds

            if response.status_code == 200:
                try:
                    content = response.content.decode('shift-jis')
                    df = pd.read_csv(io.StringIO(content))
                    return df
                except Exception as e:
                    st.warning(f"Error parsing CSV data: {str(e)}")
                    retry_count += 1
                    if retry_count >= max_retries:
                        st.error("Failed to parse CSV data after multiple attempts. The data format may be invalid.")
                        return None
            else:
                st.error(
                    f"No data available for the selected date. "
                    f"Status code: {response.status_code}"
                )
                return None
        except requests.exceptions.RequestException as e:
            retry_count += 1
            if retry_count >= max_retries:
                st.error(
                    f"Failed to download data after {max_retries} attempts. "
                    f"Please check your internet connection and try again later."
                )
                return None
            else:
                st.warning(f"Download attempt {retry_count} failed: {str(e)}. Retrying...")
                time.sleep(1)


def translate_columns(df):
    """
    Translate column headers from Japanese to English based on the mapping.

    Args:
        df (pandas.DataFrame): The DataFrame with Japanese column headers

    Returns:
        pandas.DataFrame: The DataFrame with English column headers
    """
    existing_columns = {}
    for jp_col, en_col in COLUMN_MAPPING.items():
        if jp_col in df.columns:
            existing_columns[jp_col] = en_col

    df = df.rename(columns=existing_columns)
    return df


def main():
    today = datetime.now()
    selected_date = st.date_input(
        "Select a date",
        value=today,
        min_value=datetime(2000, 1, 1),
        max_value=today
    )

    if st.button("Fetch Data"):
        with st.spinner("Fetching data..."):
            # Construct the URL
            file_name, url = construct_url(selected_date)

            # Download the CSV
            df = download_csv(url)

            if df is not None:
                st.write("Original columns:", df.columns.tolist())
                
                # Translate column headers
                df = translate_columns(df)

                st.write("Translated columns:", df.columns.tolist())
                
                st.write("Column mapping used:", COLUMN_MAPPING)

                st.session_state.bond_data = df

                st.subheader("Bond Data")
                st.dataframe(df)

                if "Issues" in df.columns:
                    bond_name_column = "Issues"
                elif "銘柄名" in df.columns:
                    df = df.rename(columns={"銘柄名": "Issues"})
                    bond_name_column = "Issues"
                elif len(df.columns) >= 4 and isinstance(df.columns[3], str) and any(c for c in df.columns[3] if ord(c) > 127):
                    df = df.rename(columns={df.columns[3]: "Issues"})
                    bond_name_column = "Issues"
                    st.info(f"Using Japanese column '{df.columns[3]}' for bond names")
                elif "Code" in df.columns:
                    bond_name_column = "Code"
                    st.info("Using 'Code' column for bond names")
                elif len(df.columns) >= 3:
                    bond_name_column = df.columns[2]
                    st.info(
                        f"Using column '{bond_name_column}' for bond names"
                    )
                else:
                    st.warning(
                        "Could not identify a column for bond names"
                    )
                    return

                bond_names = df[bond_name_column].unique().tolist()

                if bond_names:
                    selected_bond = st.selectbox(
                        "Select a bond to visualize",
                        bond_names
                    )

                    bond_data = df[df[bond_name_column] == selected_bond]

                    if "Average Compound Yield" in bond_data.columns:
                        yield_column = "Average Compound Yield"
                    else:
                        if len(df.columns) >= 6:
                            yield_column = df.columns[6]
                            st.info(
                                f"Using column '{yield_column}' for yield data"
                            )
                        else:
                            st.warning(
                                "Could not identify a column for yield data"
                            )
                            return

                    st.subheader(f"Yield data for {selected_bond}")

                    fig = px.line(
                        bond_data,
                        x=bond_data.index,
                        y=yield_column,
                        title=f"Yield data for {selected_bond}",
                        labels={yield_column: "Yield (%)"}
                    )

                    fig.update_layout(
                        xaxis_title="Index",
                        yaxis_title="Yield (%)",
                        plot_bgcolor="white",
                        hovermode="x unified"
                    )

                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("No bond names found in the data.")


if __name__ == "__main__":
    main()
