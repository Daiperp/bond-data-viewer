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
                    df = pd.read_csv(io.StringIO(content), header=None, sep="\t")
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


def calculate_years_to_maturity(due_date_str, selected_date):
    """
    Calculate years to maturity based on due date and selected date.
    
    Args:
        due_date_str (str): Due date in YYYYMMDD format
        selected_date (datetime): Selected date
    
    Returns:
        float: Years to maturity
    """
    try:
        due_date = datetime.strptime(str(due_date_str), "%Y%m%d")
        days_to_maturity = (due_date - selected_date).days
        years_to_maturity = days_to_maturity / 365.25  # Account for leap years
        return round(years_to_maturity, 2)
    except Exception:
        return None


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
                if df.shape[1] < 4:
                    st.error("Data format invalid or download failed")
                    return
                
                column_names = [
                    "Date",           # Column 0
                    "Issue Type",     # Column 1
                    "Code",           # Column 2
                    "Issues",         # Column 3 (bond name)
                    "Due Date",       # Column 4
                    "Coupon Rate",    # Column 5
                    "Average Compound Yield",  # Column 6
                    "Average Price(Yen)",      # Column 7
                    "Change (Yen)",            # Column 8
                    "Interest Payment Date",   # Column 9
                    "Information",             # Column 10
                    "Average Simple Yield",    # Column 11
                    "High",                    # Column 12
                    "Low",                     # Column 13
                    "Invalid",                 # Column 14
                    "Number of Reporting Members",  # Column 15
                    "Highest Compound Yield",       # Column 16
                    "Highest Price Change (Yen)",   # Column 17
                    "Lowest Compound Yield",        # Column 18
                    "Lowest Price Change (Yen)",    # Column 19
                    "Median Compound Yield",        # Column 20
                    "Median Simple Yield",          # Column 21
                    "Median Price(Yen)",            # Column 22
                    "Median Price Change (Yen)"     # Column 23
                ]
                
                df.columns = column_names[:df.shape[1]]
                
                if df.shape[1] > 4:  # Due Date is column 4 (index 4)
                    df["Years to Maturity"] = df["Due Date"].apply(
                        lambda x: calculate_years_to_maturity(x, selected_date)
                    )
                
                st.session_state.bond_data = df

                st.subheader("Bond Data")
                st.dataframe(df)

                bond_name_column = "Issues"
                bond_names = df[bond_name_column].unique().tolist()

                if bond_names:
                    selected_bond = st.selectbox(
                        "Select a bond to visualize",
                        bond_names
                    )

                    bond_data = df[df[bond_name_column] == selected_bond]

                    yield_column = "Average Compound Yield"
                    
                    if yield_column in bond_data.columns:
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
                        st.warning("Could not identify a column for yield data")
                else:
                    st.warning("No bond names found in the data.")


if __name__ == "__main__":
    main()
