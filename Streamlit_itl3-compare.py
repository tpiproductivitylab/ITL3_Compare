import streamlit as st
import pandas as pd
import time
import numpy as np
import visualisations
import asyncio
import os
import base64

async def animate_gauge_async(chart_placeholder, fig, region, frames, bounds):
    value = fig.data[0].value
    steps = np.linspace(bounds[0], value, num=frames)
    for i, v in enumerate(steps):
        if np.isnan(value):
            await asyncio.sleep(0.01 + 0.08 * (i / len(steps))**4)
            continue
        fig.data[0].value = v
        if v * 1.15 > bounds[1]:
            fig.data[0].gauge.axis.range = [bounds[0], v * 1.15]
        chart_placeholder.plotly_chart(fig, use_container_width=True, key=f'gauge-{region}-{v}')
        await asyncio.sleep(0.01 + 0.08 * (i / len(steps))**4)
    fig.data[0].value = round(value, 3)
    chart_placeholder.plotly_chart(fig, use_container_width=True, key=f'gauge-{region}-final')

async def animate_time_series_async(chart_placeholder, fig, data, selected_indicator, regions, frames):
    traces = []
    data = data.dropna()
    for region in regions:
        temp = data.loc[data['name'] == region, :].sort_values(by='year')
        years = temp['year'].tolist()
        values = temp[selected_indicator].tolist()
        traces.append({'region': region, 'years': years, 'values': values, 'animated_years': [], 'animated_values': []})
    
    max_steps = max(len(trace['years']) - 1 for trace in traces)
    for i in range(len(traces[0]['years']) - 1):
        # Interpolate for all traces in parallel
        interp_steps = []
        for trace in traces:
            if i >= len(trace['years']) - 1:
                interp_steps.append(([], []))  # Add empty interpolation for this trace
                continue
            
            if np.isnan(trace['years'][i]) or np.isnan(trace['years'][i + 1]) or \
               np.isnan(trace['values'][i]) or np.isnan(trace['values'][i + 1]):
                continue
            interp_years = np.linspace(trace['years'][i], trace['years'][i + 1], int(frames / len(traces[0]['years'])))
            interp_values = np.linspace(trace['values'][i], trace['values'][i + 1], int(frames / len(traces[0]['years'])))
            interp_steps.append((interp_years, interp_values))

        for j in range(len(interp_steps[0][0])):
            for idx, trace in enumerate(traces):
                if len(interp_steps[idx][0]) > 0:  # Only update if interpolation exists
                    trace['animated_years'] = trace['years'][:i + 1] + [interp_steps[idx][0][j]]
                    trace['animated_values'] = trace['values'][:i + 1] + [interp_steps[idx][1][j]]
                    fig.data[idx].x = trace['animated_years']
                    fig.data[idx].y = trace['animated_values']
            chart_placeholder.plotly_chart(fig, use_container_width=True, key=f'time_series-{i}-{j}')
            await asyncio.sleep(0.02 + 0.1 * (j / len(interp_steps[0][0]))**4)


    for trace in traces:
        trace['animated_years'].append(trace['years'][-1])
        trace['animated_values'].append(trace['values'][-1])
    for idx, trace in enumerate(traces):
        fig.data[idx].x = trace['animated_years']
        fig.data[idx].y = trace['animated_values']
    chart_placeholder.plotly_chart(fig, use_container_width=True, key=f'time_series-final')

async def animate_spider_async(chart_placeholder, fig, region, frames):
    # Extract the initial radial values (r) from the figure
    initial_r = np.full(len(fig.data[0].r), 20)  # Start with 59 for all indicators
    final_r = np.array(fig.data[0].r)  # Final values from the spider plot

    # Interpolate the radial values for each frame
    steps = np.linspace(0, 1, frames)  # Create interpolation steps
    for step in steps:
        # Interpolate between initial and final values
        current_r = initial_r + step * (final_r - initial_r)
        
        # Update the figure with the interpolated values
        fig.data[0].r = current_r
        chart_placeholder.plotly_chart(fig, use_container_width=True, key=f'spider-{region}-{step}')
        
        # Add a small delay for animation
        await asyncio.sleep(0.03 + 0.3 * (step / len(steps))**4)

    # Finalize the animation with the full radial values
    fig.data[0].r = final_r
    chart_placeholder.plotly_chart(fig, use_container_width=True, key=f'spider-{region}-final')

@st.cache_data(show_spinner=False)
def load_data():
    return pd.read_csv('src/itl3_compare_data.csv'), pd.read_csv('src/itl3_compare_uk_data.csv')

async def main():
    st.set_page_config(layout="wide", page_icon="favicon.ico", page_title="ITL3 Compare")

    def img_to_base64(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    logo_base64 = img_to_base64("static/logo.png")
    figshare_base64 = img_to_base64("static/Figshare_logo.png")
    cc_base64 = img_to_base64("static/cc.xlarge.png")

    st.markdown(f"""
    <div style="
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 200w;
        margin: -45px -80px 10px -80px;
        background-color: #ffffff;
        padding: 10px 50px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.12);
        position: relative;
    ">
        <a href='https://lab.productivity.ac.uk/' target='_blank'>
            <img src='data:image/png;base64,{logo_base64}' style='height:30px;'>
        </a>
        <a href='https://doi.org/10.48420/30030220' target='_blank'>
            <img src='data:image/png;base64,{figshare_base64}' style='height:50px;'>
        </a>
    </div>
    """, unsafe_allow_html=True)

    # Initialise data
    all_data, uk_data = load_data()

    all_data['GVA/H volume'] = all_data.groupby("code")["GVA/H volume"].transform(
        lambda x: (x / x.loc[all_data.loc[x.index, "year"] == 2008].values[0]) * 100
    )
    uk_data['GVA/H volume'] = uk_data.groupby("code")["GVA/H volume"].transform(
        lambda x: (x / x.loc[uk_data.loc[x.index, "year"] == 2008].values[0]) * 100
    )

    driver = {
        'GVA per hour worked': ['Productivity measured as Gross Value Added per hour worked', '2023', '2004', '<a href="https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/labourproductivity/datasets/subregionalproductivitylabourproductivitygvaperhourworkedandgvaperfilledjobindicesbyuknuts2andnuts3subregions" target="_blank">Source</a>'],
        'Export Intensity': ['Exports as a percentage of GDP ', '2023', '2016', '<a href="https://www.ons.gov.uk/businessindustryandtrade/internationaltrade/datasets/subnationaltradeingoods" target="_blank">Source</a>'],
        'New Businesses': ['New firms as a percentage of total active firms', '2023', '2017', '<a href="https://www.ons.gov.uk/businessindustryandtrade/business/activitysizeandlocation/datasets/businessdemographyreferencetable" target="_blank">Source</a>'],
        'Low Skilled': ["Percentage of the working-age population with NVQ1/RQF1 or ‘no qualifications’", '2024', '2016', '<a href="https://www.nomisweb.co.uk/datasets/apsnew" target="_blank">Source</a>'],
        'High Skilled': ["Percentage of the working-age population with qualification at NVQ4+/RQF4+ level", '2024', '2012', '<a href="https://www.nomisweb.co.uk/datasets/apsnew" target="_blank">Source</a>'],
        'Active': ['Percentage of the working-age population active in employment', '2024', '2012', '<a href="https://www.nomisweb.co.uk/datasets/apsnew" target="_blank">Source</a>'],
        'Inactive due to Illness': ['Percentage of <i>inactive</i> working age population, inactive due to ill health', '2024', '2014', '<a href="https://www.nomisweb.co.uk/datasets/apsnew" target="_blank">Source</a>'],
        'Working Age': ['Percentage of the total population that are of working age (aged 16-64)', '2023', '2012', '<a href="https://www.nomisweb.co.uk/datasets/apsnew" target="_blank">Source</a>'],
        '5G connectivity': ['Percentage of outdoor areas with 5G service access from at least one mobile network operator', '2025', '2023', '<a href="https://www.ofcom.org.uk/research-and-data/multi-sector-research/infrastructure-research" target="_blank">Source</a>'],
        'Gigabit connectivity': ['Percentage of premises that have access to a gigabit connection', '2025', '2021', '<a href="https://www.ofcom.org.uk/research-and-data/multi-sector-research/infrastructure-research" target="_blank">Source</a>'],
        'GFCF per job': ['Gross fixed capital formation per job, total amount of investment in tangible and intangible assets', '2020', '2008', '<a href="https://www.ons.gov.uk/economy/regionalaccounts/grossdisposablehouseholdincome/datasets/experimentalregionalgrossfixedcapitalformationgfcfestimatesbyassettype" target="_blank">Source</a>'],
        'ICT per job': ['Total amount of investment in ICT equipment per job', '2020', '2008', '<a href="https://www.ons.gov.uk/economy/regionalaccounts/grossdisposablehouseholdincome/datasets/experimentalregionalgrossfixedcapitalformationgfcfestimatesbyassettype" target="_blank">Source</a>'],
        'Intangibles per job': ['Total amount of investment in intangible capital per job', '2020', '2008', '<a href="https://www.ons.gov.uk/economy/regionalaccounts/grossdisposablehouseholdincome/datasets/experimentalregionalgrossfixedcapitalformationgfcfestimatesbyassettype" target="_blank">Source</a>']
    }
    # Filter indicator
    indicators = driver.keys()

    st.components.v1.html("""
    <script>
        const style = document.createElement('style');
        style.textContent = `
            .stColumn {
                border: 1px solid #e0e0e0 !important;
                border-radius: 12px !important;
                padding: 18px !important;
                background-color: #ffffff !important;
                box-shadow: 0 4px 6px rgba(0,0,0,0.12) !important;
            }
            .stApp {
                background-color: #6b739c !important;
                min-width: 1500px !important;
            }
        `;
        window.parent.document.head.appendChild(style);
    </script>
    """, height=0)
    cols = st.columns([1,2,1])

    selected_indicator = 'GVA per hour worked'
    data = all_data[['name', 'year', selected_indicator]]
    
    # Filter region
    all_data = all_data.sort_values(by=['name', 'year'])
    code = list(all_data['code'].unique())
    itl3 = list(all_data['name'].unique())
    query_params = {k.lower(): v.upper() for k, v in st.query_params.items()}
    index_1 = 0
    
    if 'region_1' in query_params:
        if query_params['region_1'] in code:
            index_1 = code.index(query_params['region_1'])
    with cols[0]:
        selected_itl3_1 = st.selectbox("Select First ITL3 Region:", itl3, index=index_1)

    index_2 = 1
    if 'region_2' in query_params:
            if query_params['region_2'] in code:
                index_2 = code.index(query_params['region_2'])
    with cols[2]:
        selected_itl3_2 = st.selectbox("Select Second ITL3 Region:", itl3, index=index_2)

    all_data = all_data.drop(columns='code')
        
    #tasks = []
    # Create placeholders for the charts
    gauge_1_placeholder = cols[0].empty()
    time_series_placeholder = cols[1].empty()
    gauge_2_placeholder = cols[2].empty()
    spider_1_placeholder = cols[0].empty()
    spider_2_placeholder = cols[2].empty()
    # Calculate bounds as 2 standard deviations from the median (general bounds formula)
    median = data.loc[data['year'] == int(driver[selected_indicator][1]), selected_indicator].median()
    bounds = [median * 0.75, median * 1.25]
    # Ensure indicators are not below 0 and encompass each class
    bounds[0] = min(median * 0.85, max(0, bounds[0]))
    bounds[1] = max(median * 1.15, bounds[1])

    
    # Create a charts
    gauge_1 = visualisations.gauge(data, selected_itl3_1, selected_indicator, driver[selected_indicator][1], bounds)
    time_series = visualisations.time_series(all_data, [selected_itl3_1, selected_itl3_2], uk_data)
    gauge_2 = visualisations.gauge(data, selected_itl3_2, selected_indicator, driver[selected_indicator][1], bounds)
    spider_1 = visualisations.spider(all_data, indicators, selected_itl3_1, '#eb5e5e', driver)
    spider_2 = visualisations.spider(all_data, indicators, selected_itl3_2, '#9c4f8b', driver)
    
    # Animate charts
    # tasks.append(animate_gauge_async(gauge_1_placeholder, gauge_1, selected_itl3_1, 80, bounds))
    # tasks.append(animate_time_series_async(time_series_placeholder, time_series, data, selected_indicator, [selected_itl3_1, selected_itl3_2], 80))
    # tasks.append(animate_gauge_async(gauge_2_placeholder, gauge_2, selected_itl3_2, 80, bounds))
    # tasks.append(animate_spider_async(spider_1_placeholder, spider_1, selected_itl3_1, 80))
    # tasks.append(animate_spider_async(spider_2_placeholder, spider_2, selected_itl3_2, 80))
    gauge_1_placeholder.plotly_chart(gauge_1, use_container_width=True, key=f'gauge-{selected_itl3_1}-1-final')
    spider_1_placeholder.plotly_chart(spider_1, use_container_width=True, key=f'spider-{selected_itl3_1}-1-final')
    
    gauge_2_placeholder.plotly_chart(gauge_2, use_container_width=True, key=f'gauge-{selected_itl3_2}-2-final')
    spider_2_placeholder.plotly_chart(spider_2, use_container_width=True, key=f'spider-{selected_itl3_2}-2-final')

    time_series_placeholder.plotly_chart(time_series, use_container_width=True, key=f'time-series-final')
    
    carousel_items = ""
    # Convert Plotly bar charts to HTML
    for i, indicator in enumerate([ind for ind in list(indicators)[1:] if ind != 'Low Skilled']):
        bar = visualisations.bar(all_data, indicator, [selected_itl3_1, selected_itl3_2], driver[indicator][0])
        bar = bar.to_html(full_html=False, include_plotlyjs='cdn')
        # Set the first item as active
        active_class = "active" if i == 0 else ""
        carousel_items += f"""
        <div class="carousel-item {active_class}">
            {bar}
        </div>
        """
        
    # HTML for the carousel
    carousel_html = f"""
    <div id="carouselExample" class="carousel slide" data-bs-ride="carousel">
    <div class="carousel-inner">
        {carousel_items}  <!-- Python variable -->
    </div>
    <button class="carousel-control-prev" type="button" data-bs-target="#carouselExample" data-bs-slide="prev">
        <span class="carousel-control-prev-icon" aria-hidden="true"></span>
        <span class="visually-hidden">Previous</span>
    </button>
    <button class="carousel-control-next" type="button" data-bs-target="#carouselExample" data-bs-slide="next">
        <span class="carousel-control-next-icon" aria-hidden="true"></span>
        <span class="visually-hidden">Next</span>
    </button>
    </div>

    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>

    <style>
    /* Shrink the actual buttons */
    .carousel-control-prev,
    .carousel-control-next {{
        width: 50px;   /* reduce clickable width */
        height: 50px;  /* reduce clickable height */
        top: 50%;      /* center vertically */
        transform: translateY(-50%);
        background-color: rgba(0,0,0,0.5); /* optional */
        border-radius: 20%; /* makes it a circle */
    }}

    /* Style the arrow icons inside */
    .carousel-control-prev-icon,
    .carousel-control-next-icon {{
        width: 20px;
        height: 20px;
    }}
    </style>
    """
    with cols[1]:
        # Display the carousel in Streamlit
        st.components.v1.html(carousel_html, height=500)
    
    st.markdown(
    f"""
    <style>
    .bottom-right-image {{
        position: fixed;
        bottom: 10px;   /* distance from bottom */
        right: 10px;    /* distance from right */
        z-index: 1000;  /* keep it on top of other elements */
    }}
    </style>
    <div class="bottom-right-image">
        <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank">
            <img src='data:image/png;base64,{cc_base64}' style='height:30px;'>
        </a>
    </div>
    """,
    unsafe_allow_html=True
)

    
    # await asyncio.gather(*tasks)
    

if __name__ == '__main__':
    asyncio.run(main())