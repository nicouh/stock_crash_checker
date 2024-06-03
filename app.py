import os
import dash
from dash import html, dcc
from fredapi import Fred
from dash.dependencies import Input, Output, State
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta

fred_api_key = os.environ.get('fred_api_key')
fred = Fred(api_key=fred_api_key)
end_date = datetime.today()
start_date = end_date - timedelta(days=5 * 365)
obs_window = '15y'
px_width = 620
px_height = 360


def get_data():
    # Fetch S&P 500 data
    sp500 = yf.Ticker("^GSPC")
    sp500_hist = sp500.history(period=obs_window)
    sp500_hist['SMA200'] = sp500_hist['Close'].rolling(window=200).mean()

    # Fetch VIX data
    vix = yf.Ticker("^VIX")
    vix_hist = vix.history(period=obs_window)

    # Fetch US unemployment claims
    unemployment_claims = fred.get_series('ICSA')
    unemployment_claims = pd.DataFrame(unemployment_claims, columns=['value'])
    unemployment_claims['SMA'] = unemployment_claims['value'].rolling(window=10).mean()
    unemployment_claims['steepness'] = unemployment_claims['SMA'].diff()

    # Fetch Federal Funds Rate data
    fed_funds_rate = fred.get_series('DFF')
    fed_funds_rate = pd.DataFrame(fed_funds_rate, columns=['value'])

    # Fetch US Treasury yield data
    series_ids = {'3 Mo': 'DGS3MO', '1 Yr': 'DGS1', '10 Yr': 'DGS10'}
    yield_data = pd.DataFrame()
    for maturity, series_id in series_ids.items():
        yield_data[maturity] = fred.get_series(series_id)

    # Drop rows with NaN values (incomplete dates)
    yield_data = yield_data[yield_data.index.year >= 1990]
    yield_data = yield_data.dropna()
    # yield_data['diff'] = yield_data['10 Yr'] - yield_data['1 Yr']
    yield_data['diff'] = yield_data['10 Yr'] - yield_data['3 Mo']

    return sp500_hist, vix_hist, unemployment_claims, fed_funds_rate, yield_data


def init_figs(sp500_hist, vix_hist, unemployment_claims, fed_funds_rate, yield_data,
              start_date, end_date, px_width, px_height):

    figs = {}
    # Initial figure definitions
    figs['sp500'] = {
        'data': [
            {'x': sp500_hist.index, 'y': sp500_hist['Close'], 'type': 'line', 'name': 'S&P 500'},
            {'x': sp500_hist.index, 'y': sp500_hist['SMA200'], 'type': 'line', 'name': 'SMA 200', 'line': {'width': 1.5}}
        ],
        'layout': {
            'title': 'S&P 500 and 200-Day SMA',
            'xaxis': {'range': [start_date, end_date]},
            'yaxis': {'range': [2000, 5500]},
            'width': px_width, 'height': px_height,
            'showlegend': False
        }
    }

    figs['vix'] = { #initial_vix_fig = {
        'data': [{'x': vix_hist.index, 'y': vix_hist['Close'], 'type': 'line', 'name': 'VIX'}],
        'layout': {
            'title': 'VIX',
            'xaxis': {'range': [start_date, end_date]},
            'yaxis': {'range': [0, 80]},
            'width': px_width, 'height': px_height
        }
    }

    figs['ue'] = { #initial_unemployment_fig = {
        'data': [
            {'x': unemployment_claims.index, 'y': unemployment_claims['value'], 'type': 'line', 'name': 'UEC'},
            {'x': unemployment_claims.index, 'y': unemployment_claims['SMA'], 'type': 'line', 'name': 'SMA', 'line': {'width': 1.3}}
        ],
        'layout': {
            'title': 'US Unemployment Claims and SMA 10 Weeks',
            'xaxis': {'range': [start_date, end_date]},
            'yaxis': {'range': [150000, 400000]},
            'width': px_width, 'height': px_height,
            'showlegend': False
        }
    }

    figs['fed_rates'] = {#initial_fed_funds_rate_fig = {
        'data': [{'x': fed_funds_rate.index, 'y': fed_funds_rate['value'], 'type': 'line', 'name': 'Fed Funds Rate'}],
        'layout': {'title': 'Federal Funds Rate',
                   'xaxis': {'range': [start_date, end_date]},
                   'yaxis': {'range': [0, 7]},
                   'width': px_width, 'height': px_height,
                   'showlegend': False
        }
    }

    figs['yields'] = {# initial_yield_fig = {
        'data': [{'x': yield_data.index, 'y': yield_data['diff'], 'type': 'line', 'name': 'Yield Data 3 Mo / 10 Yr'}],
        'layout': {'title': '3 Mo / 10 Yr Yield Data Curve',
                   'xaxis': {'range': [start_date, end_date]},
                   'yaxis': {'range': [-2.2, 2.2]},
                   'width': px_width, 'height': px_height,
                   'showlegend': False
        }
    }
    return figs


def gen_text(sp500_hist, vix_hist, unemployment_claims, fed_funds_rate, yield_data):
    # Compute Checks
    checks = {}
    checks['sp500'] = sp500_hist['SMA200'].iloc[-1] > sp500_hist['Close'].iloc[-1]
    checks['vix'] = vix_hist['Close'].iloc[-1] > 45
    checks['ue_abs'] = unemployment_claims['value'].iloc[-1] > 350000
    checks['ue_rel'] = unemployment_claims['steepness'].iloc[-1] > 1000

    fed_funds_rate_filtered = fed_funds_rate.loc[pd.Timestamp('2020-01-01'):datetime.today()]
    fed_funds_rate_values = fed_funds_rate_filtered['value'].tolist()
    fed_funds_rate_max = max(fed_funds_rate_values)
    checks['fed_dec'] = fed_funds_rate_max - fed_funds_rate['value'].iloc[-1] > 0
    checks['yields_a'] = yield_data['diff'].values[-1] < 0

    yield_inv_dates = []
    for n, yield_dat in enumerate(yield_data['diff'][1:]):
        if yield_dat * yield_data['diff'].iloc[n - 1] < 0:
            yield_inv_dates.append(yield_data.index[n])
    days_since_crossing = (datetime.today() - yield_inv_dates[-1]).days
    checks['yields_b'] = days_since_crossing > 368.5  # 700+168+196+534+378+175+294+540+189+511 / 10

    text_check_sp500 = f"<span style='color:{'green' if not checks['sp500'] else 'red'};'>{checks['sp500']}</span>"
    text_check_vix = f"<span style='color:{'green' if not checks['vix'] else 'red'};'>{checks['vix']}</span>"
    text_check_ue_a = f"<span style='color:{'green' if not checks['ue_abs'] else 'red'};'>{checks['ue_abs']}</span>"
    text_check_ue_r = f"<span style='color:{'green' if not checks['ue_rel'] else 'red'};'>{checks['ue_rel']}</span>"
    text_check_fed = f"<span style='color:{'green' if not checks['fed_dec'] else 'red'};'>{checks['fed_dec']}</span>"
    text_check_y_a = f"<span style='color:{'green' if not checks['yields_a'] else 'red'};'>{checks['yields_a']}</span>"
    text_check_y_b = f"<span style='color:{'green' if not checks['yields_b'] else 'red'};'>{checks['yields_b']}</span>"

    # Generate Text
    text_content = f"""
        <h2 style="margin: 3px; padding: 3px;">Crash Check</h2>
        <table style="border-collapse: separate; border-spacing: 30px 0px; width: 85%;">
        <tr>
            <td><h4 style="margin: 2px; padding: 0;">Crash</h4></td>
            <td style="width: 40%;"><h4 style="margin: 2px; padding: 0;">condition</h4></td>
            <td><h4 style="margin: 2px; padding: 0;">value</h4></td>
            <td><h4 style="margin: 2px; padding: 0;">check</h4></td>
        </tr>
        <tr>
              <td>initiated</td>
              <td style="font-family: monospace; font-size: 11pt;">SP500 &lt; SMA200</td>
              <td>{checks['sp500']}</td>
              <td><b>{text_check_sp500}</b></td>
        </tr>
        <tr>
              <td>happened</td>
              <td style="font-family: monospace; font-size: 11pt;">&nbsp; VIX &gt; 45</td>
              <td>{round(vix_hist['Close'].iloc[-1], 2)}</td>
              <td><b>{text_check_vix}</b></td>
        </tr>
        <tr>
              <td>likely</td>
              <td style="font-family: monospace; font-size: 11pt; margin-left: 50px;">&nbsp;&nbsp;&nbsp;UE &gt; 350 k</td>
              <td>{unemployment_claims['value'].iloc[-1] / 1000} k</td>
              <td><b>{text_check_ue_a}</b></td>
        </tr>
        <tr>
              <td>likely</td>
              <td style="font-family: monospace; font-size: 11pt;">d/dt UE_sma &gt; 1000</td>
              <td>{unemployment_claims['steepness'].iloc[-1]}</td>
              <td><b>{text_check_ue_r}</b></td>
        </tr>
        <tr>
              <td>initiated</td>
              <td style="font-family: monospace; font-size: 11pt;">dec. FED rates</td>
              <td>{fed_funds_rate_max}/{fed_funds_rate['value'].iloc[-1]}</td>
              <td><b>{text_check_fed}</b></td>
        </tr>
            <tr>
              <td>initiated</td>
              <td style="font-family: monospace; font-size: 11pt;">yield inv., y(today) &lt; 0 </td>
              <td>{round(yield_data['diff'].values[-1], 2)} &lt; 0 </td>
              <td><b>{text_check_y_a}</b></td>
        </tr>
            <tr>
              <td>awaiting</td>
              <td style="font-family: monospace; font-size: 11pt;">days since inversion &gt; av.</td>
              <td>{days_since_crossing} > 368 </td>
              <td><b>{text_check_y_b}</b></td>
        </tr>
        </table>
        
        <font size="9pt">  
        
        Yield curve inversion occurred on {yield_inv_dates[-1].date()}, {days_since_crossing} d ago. <br>        
        Average of 368.5 days computed from [Game of Trades](https://www.linkedin.com/posts/game-of-trades_the-yield-curve-has-been-inverted-for-over-activity-7187517889917181954-3Z4k/), 
        see [here](https://media.licdn.com/dms/image/D4D12AQH4dBh2WkJ2NQ/article-cover_image-shrink_720_1280/0/1716201001189?e=1722470400&v=beta&t=EsDmRHHTCG9ulNUELC-jbIMSEovCnFT_2rkyrHT2pKs). 

        ({datetime.today().date()})
        
        </font>
    """
    #Notes: When the FED rates decrease again, a crash is likely to occur as the FED is trying to dampen negative
    #    effects of previously high rates. I.e. slowing down the economy has worked, a crash occurred, then they have
    #    to counteract.
    return text_content


# Getting all the data
sp500_hist, vix_hist, unemployment_claims, fed_funds_rate, yield_data = get_data()

# Initialize figs and generate text
initial_figs = init_figs(sp500_hist, vix_hist, unemployment_claims, fed_funds_rate,
                         yield_data, start_date, end_date, px_width, px_height)

text_content = gen_text(sp500_hist, vix_hist, unemployment_claims, fed_funds_rate,
                        yield_data)

# Start App
app = dash.Dash(__name__)

# HTML Layout
app.layout = html.Div([
    html.Div([
        dcc.Graph(id='sp500-graph', figure=initial_figs['sp500']),
        dcc.Markdown(text_content, id='text-panel', style={'textAlign': 'left', 'paddingTop': '40px'},
                     dangerously_allow_html=True)
    ], style={'display': 'grid', 'grid-template-columns': '50% 50%', 'grid-template-rows': '50% 50%'}),
    html.Div([
        dcc.Graph(id='vix-graph', figure=initial_figs['vix']),
        dcc.Graph(id='unemployment-graph', figure=initial_figs['ue'])
    ], style={'display': 'grid', 'grid-template-columns': '50% 50%', 'grid-template-rows': '50% 50%'}),
    html.Div([
        dcc.Graph(id='fed-funds-rate-graph', figure=initial_figs['fed_rates']),
        dcc.Graph(id='yield-data-graph', figure=initial_figs['yields'])
    ], style={'display': 'grid', 'grid-template-columns': '50% 50%', 'grid-template-rows': '50% 50%'})
])


@app.callback(
    [Output('sp500-graph', 'figure'),
     Output('vix-graph', 'figure'),
     Output('unemployment-graph', 'figure'),
     Output('fed-funds-rate-graph', 'figure'),
     Output('yield-data-graph', 'figure')],
    [Input('sp500-graph', 'relayoutData')],
    [State('sp500-graph', 'figure'),
     State('vix-graph', 'figure'),
     State('unemployment-graph', 'figure'),
     State('fed-funds-rate-graph', 'figure'),
     State('yield-data-graph', 'figure')],
)
def update_graphs(sp500_relayoutData, sp500_fig, vix_fig, unemployment_fig, fed_funds_rate_fig, yield_fig):
    ctx = dash.callback_context

    if not ctx.triggered or 'xaxis.range[0]' not in sp500_relayoutData:
        range_start, range_end = start_date, end_date
    else:
        range_start = pd.to_datetime(sp500_relayoutData['xaxis.range[0]'])
        range_end = pd.to_datetime(sp500_relayoutData['xaxis.range[1]'])

    if sp500_fig is None:
        sp500_fig = initial_figs['sp500']
    if vix_fig is None:
        vix_fig = initial_figs['vix']
    if unemployment_fig is None:
        unemployment_fig = initial_figs['ue']
    if fed_funds_rate_fig is None:
        fed_funds_rate_fig = initial_figs['fed_rates']
    if yield_fig is None:
        yield_fig = initial_figs['yields']

    # Update x-axis range
    sp500_fig['layout']['xaxis']['range'] = [range_start, range_end]
    vix_fig['layout']['xaxis']['range'] = [range_start, range_end]
    unemployment_fig['layout']['xaxis']['range'] = [range_start, range_end]
    fed_funds_rate_fig['layout']['xaxis']['range'] = [range_start, range_end]
    yield_fig['layout']['xaxis']['range'] = [range_start, range_end]

    # Convert datetime objects to timezone-naive
    vix_hist.index = vix_hist.index.tz_localize(None)
    unemployment_claims.index = unemployment_claims.index.tz_localize(None)
    fed_funds_rate.index = fed_funds_rate.index.tz_localize(None)
    yield_data['diff'].index = yield_data['diff'].index.tz_localize(None)

    # Update y-axis range for VIX
    vix_visible_data = vix_hist[(vix_hist.index >= range_start) & (vix_hist.index <= range_end)]
    if not vix_visible_data.empty:
        vix_min = 0.98 * vix_visible_data['Close'].min()
        vix_max = 1.02 * vix_visible_data['Close'].max()
        vix_fig['layout']['yaxis']['range'] = [vix_min, vix_max]

    # Update y-axis range for Unemployment Claims
    ued_visible_data = unemployment_claims[
        (unemployment_claims.index >= range_start) & (unemployment_claims.index <= range_end)]
    if not ued_visible_data.empty:
        ued_min = 0.98 * ued_visible_data['value'].min()
        ued_max = 1.02 * ued_visible_data['value'].max()
        unemployment_fig['layout']['yaxis']['range'] = [ued_min, ued_max]

    # Update y-axis to autorange for Federal Funds Rate
    fed_funds_visible_data = fed_funds_rate[(fed_funds_rate.index >= range_start) & (fed_funds_rate.index <= range_end)]
    if not fed_funds_visible_data.empty:
        fed_funds_min = 0.98 * fed_funds_visible_data['value'].min()
        fed_funds_max = 1.02 * fed_funds_visible_data['value'].max()
        fed_funds_rate_fig['layout']['yaxis']['range'] = [fed_funds_min, fed_funds_max]

    # Update y-axis to auto range for Yield Data
    yields_visible_data = yield_data['diff'][
        (yield_data['diff'].index >= range_start) & (yield_data['diff'].index <= range_end)]
    if not yields_visible_data.empty:
        yield_funds_min = 0.98 * yields_visible_data.values.min()
        yield_funds_max = 1.02 * yields_visible_data.values.max()
        yield_fig['layout']['yaxis']['range'] = [yield_funds_min, yield_funds_max]

    return sp500_fig, vix_fig, unemployment_fig, fed_funds_rate_fig, yield_fig


if __name__ == '__main__':
    #app.run_server(debug=True)
    port = int(os.environ.get('PORT', 8050))
    app.run_server(debug=True, host='0.0.0.0', port=port)
