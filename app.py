from shiny import reactive, render
from shiny.express import ui, input
from ipyleaflet import Map, Marker
from shinywidgets import render_widget, render_plotly
import random
from datetime import datetime
from collections import deque
import pandas as pd
import plotly.express as px
from scipy import stats
from faicons import icon_svg
import requests
from bs4 import BeautifulSoup

# --------------------------------------------
# --------------------------------------------

UPDATE_INTERVAL_SECS: int = 30  # Updated to 30 seconds for more frequent readings
DEQUE_SIZE: int = 5
reactive_value_wrapper = reactive.value(deque(maxlen=DEQUE_SIZE))

# --------------------------------------------
# get Australia temperature
# --------------------------------------------

def get_australia_temperature():
    url = "http://www.bom.gov.au/nsw/forecasts/sydney.shtml"
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        temp_elem = soup.find('em', {'class': 'temp'})
        if temp_elem:
            return float(temp_elem.text.strip('°'))
    except:
        pass
    return None

# --------------------------------------------
# reactive cals
# --------------------------------------------

@reactive.calc()
def reactive_calc_combined():
    reactive.invalidate_later(UPDATE_INTERVAL_SECS)

    temp_celsius = get_australia_temperature()
    if temp_celsius is None:
        temp_celsius = round(random.uniform(15, 25), 1) 
    
    # convert celsius to fahrenheit
    temp_fahrenheit = (temp_celsius * 1.8) + 32
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_dictionary_entry = {"temp_celsius": temp_celsius, "temp_fahrenheit": temp_fahrenheit, "timestamp": timestamp}

    reactive_value_wrapper.get().append(new_dictionary_entry)
    deque_snapshot = reactive_value_wrapper.get()
    df = pd.DataFrame(deque_snapshot)

    return deque_snapshot, df, new_dictionary_entry


ui.page_opts(title="Live Sydney Temperature", fillable=True)

with ui.sidebar(open="open"):
    ui.h2("Sydney Weather Explorer", class_="text-center")
    ui.p(
        "Real-time temperature readings in Sydney, Australia.",
        class_="text-center",
    )
    ui.hr()
    ui.input_radio_buttons(
        "temp_unit",
        "Choose temperature unit:",
        {
            "celsius": ui.HTML("<span style='color:red;'>Celsius</span>"),
            "fahrenheit": "Fahrenheit",
        },
    )

with ui.layout_columns(col_widths=[4, 4, 4]):
    with ui.value_box(
        showcase=icon_svg("sun"),
        theme="bg-gradient-green-yellow",
        full_screen=False
    ):
        "Current Temperature"

        @render.text
        def display_temp():
            deque_snapshot, df, latest_dictionary_entry = reactive_calc_combined()
            temp_unit = input.temp_unit()
            if temp_unit == "celsius":
                return f"{latest_dictionary_entry['temp_celsius']:.1f} °C"
            else:
                return f"{latest_dictionary_entry['temp_fahrenheit']:.1f} °F"

        "in Sydney"

    with ui.card(full_screen=False):
        ui.card_header("Current Date and Time")

        @render.text
        def display_time():
            deque_snapshot, df, latest_dictionary_entry = reactive_calc_combined()
            return f"{latest_dictionary_entry['timestamp']}"

    with ui.card(full_screen=False):
        ui.card_header("Temperature Readings")

        @render.data_frame
        def display_df():
            deque_snapshot, df, latest_dictionary_entry = reactive_calc_combined()
            temp_unit = input.temp_unit()
            if temp_unit == "celsius":
                df_display = df[["timestamp", "temp_celsius"]].rename(columns={"temp_celsius": "Temperature (°C)"})
            else:
                df_display = df[["timestamp", "temp_fahrenheit"]].rename(columns={"temp_fahrenheit": "Temperature (°F)"})
            pd.set_option('display.width', None)
            return render.DataGrid(df_display, width="100%")

# layout columns for charts and map
with ui.layout_columns(col_widths=[6, 6]):
    with ui.card(full_screen=False):
        ui.card_header("Temperature Trend")

        @render_plotly
        def display_plot():
            deque_snapshot, df, latest_dictionary_entry = reactive_calc_combined()
            temp_unit = input.temp_unit()

            if not df.empty:
                df["timestamp"] = pd.to_datetime(df["timestamp"])

                temp_col = "temp_celsius" if temp_unit == "celsius" else "temp_fahrenheit"
                temp_label = "Temperature (°C)" if temp_unit == "celsius" else "Temperature (°F)"

                fig = px.scatter(df,
                    x="timestamp",
                    y=temp_col,
                    title=f"Temperature Readings ({temp_label})",
                    labels={temp_col: temp_label, "timestamp": "Time"},
                    color_discrete_sequence=["blue"])

                sequence = range(len(df))
                x_vals = list(sequence)
                y_vals = df[temp_col]

                slope, intercept, r_value, p_value, std_err = stats.linregress(x_vals, y_vals)
                df['best_fit_line'] = [slope * x + intercept for x in x_vals]
                fig.add_scatter(x=df["timestamp"], y=df['best_fit_line'], mode='lines', name='Regression Line')

                fig.update_layout(height=400)
                return fig

    with ui.card(full_screen=False):
        ui.card_header("Sydney Map")

        @render_widget
        def map():
            sydney_coords = (-33.8688, 151.2093)
            m = Map(center=sydney_coords, zoom=10, height=400)
            
            marker = Marker(location=sydney_coords)
            m.add_layer(marker)
            
            return m

