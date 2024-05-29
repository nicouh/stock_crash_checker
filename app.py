import os
import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta

fred_api_key = os.environ.get('fred_api_key')

end_date = datetime.today()
start_date = end_date - timedelta(days=5*365)
obs_window = '15y'
px_width = 650
px_heigth = 380

# Fetch S&P 500 data
sp500 = yf.Ticker("^GSPC")
sp500_hist = sp500.history(period=obs_window)
sp500_hist['SMA200'] = sp500_hist['Close'].rolling(window=200).mean()

# Fetch VIX data
vix = yf.Ticker("^VIX")
vix_hist = vix.history(period=obs_window)

# Fetch US unemployment claims
unemployment_claims_url = f'https://api.stlouisfed.org/fred/series/observations?series_id=ICSA&api_key={fred_api_key}&file_type=json'
response = requests.get(unemployment_claims_url)
unemployment_claims = pd.DataFrame(response.json()['observations'])
unemployment_claims['date'] = pd.to_datetime(unemployment_claims['date'])
unemployment_claims.set_index('date', inplace=True)
unemployment_claims['value'] = unemployment_claims['value'].astype(float)
unemployment_claims['SMA'] = unemployment_claims['value'].rolling(window=10).mean()
unemployment_claims['steepness'] = unemployment_claims['SMA'].diff()
ued_hist = unemployment_claims.copy()

# Initial figure definitions
initial_sp500_fig = {
    'data': [
        {'x': sp500_hist.index, 'y': sp500_hist['Close'], 'type': 'line', 'name': 'S&P 500'},
        {'x': sp500_hist.index, 'y': sp500_hist['SMA200'], 'type': 'line', 'name': 'SMA 200'}
    ],
    'layout': {
        'title': 'S&P 500 and 200-Day SMA',
        'xaxis': {'range': [start_date, end_date]},
        'width': px_width, 'height': px_heigth
    }
}

initial_vix_fig = {
    'data': [{'x': vix_hist.index, 'y': vix_hist['Close'], 'type': 'line', 'name': 'VIX'}],
    'layout': {
        'title': 'VIX',
        'xaxis': {'range': [start_date, end_date]},
        'yaxis': {'range': [0,80]},
        'width': px_width, 'height': px_heigth
    }
}

initial_unemployment_fig = {
    'data': [
        {'x': unemployment_claims.index, 'y': unemployment_claims['value'], 'type': 'line', 'name': 'UEC'},
        {'x': unemployment_claims.index, 'y': unemployment_claims['SMA'],   'type': 'line', 'name': 'SMA'}
    ],
    'layout': {
        'title': 'US Unemployment Claims and SMA 10 Weeks',
        'xaxis': {'range': [start_date, end_date]},
        'yaxis': {'range': [0,600000]},
        'width': px_width, 'height': px_heigth
    }
}

app = dash.Dash(__name__)

sp500_check = sp500_hist['SMA200'].iloc[-1] > sp500_hist['Close'].iloc[-1]
vix_check = vix_hist['Close'].iloc[-1] > 45
ue_check_abs = unemployment_claims['value'].iloc[-1] > 350000
ue_check_rel = unemployment_claims['steepness'].iloc[-1] > 600

text_check_sp500 = f"<span style='color:{'green' if not sp500_check else 'red'};'>{sp500_check}</span>"
text_check_vix = f"<span style='color:{'green' if not vix_check else 'red'};'>{vix_check}</span>"
text_check_ue_a = f"<span style='color:{'green' if not ue_check_abs else 'red'};'>{ue_check_abs}</span>"
text_check_ue_r = f"<span style='color:{'green' if not ue_check_rel else 'red'};'>{ue_check_rel}</span>"

text_content = f"""
    <h2 style="margin: 3px; padding: 3px;">Crash Check</h2>
    <table style="border-collapse: separate; border-spacing: 30px 0px; width: 80%;">
    <tr>
          <td><h4 style="margin: 2px; padding: 0;">Crash</h4></td>
        <td style="width: 40%;"><h4 style="margin: 2px; padding: 0;">condition</h4></td>
        <td><h4 style="margin: 2px; padding: 0;">value</h4></td>
          <td><h4 style="margin: 2px; padding: 0;">check</h4></td>
    </tr>
    <tr>
          <td>initiated</td>
          <td style="font-family: monospace; font-size: 11pt;">SP500 &lt; SMA200</td>
          <td></td>
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
          <td style="font-family: monospace; font-size: 11pt;">d/dt UE_sma &gt; 500</td>
          <td>{unemployment_claims['steepness'].iloc[-1]}</td>
          <td><b>{text_check_ue_r}</b></td>
    </tr>
    </table>
    
    ({end_date.date()})
"""

app.layout = html.Div([
    html.Div([
        dcc.Graph(id='sp500-graph', figure=initial_sp500_fig),
        dcc.Markdown(text_content, id='text-panel', style={'textAlign': 'left', 'paddingTop': '40px'}, dangerously_allow_html=True)
    ], style={'display': 'grid', 'grid-template-columns': '50% 50%', 'grid-template-rows': '50% 50%'}),
    html.Div([
        dcc.Graph(id='vix-graph', figure=initial_vix_fig),
        dcc.Graph(id='unemployment-graph', figure=initial_unemployment_fig)        
    ], style={'display': 'grid', 'grid-template-columns': '50% 50%', 'grid-template-rows': '50% 50%'})
])

@app.callback(
    [Output('sp500-graph', 'figure'),
     Output('vix-graph', 'figure'),
     Output('unemployment-graph', 'figure')],
    [Input('sp500-graph', 'relayoutData')],
    [State('sp500-graph', 'figure'),
     State('vix-graph', 'figure'),
     State('unemployment-graph', 'figure')],
)
def update_graphs(sp500_relayoutData, sp500_fig, vix_fig, unemployment_fig):
    ctx = dash.callback_context

    if not ctx.triggered or 'xaxis.range[0]' not in sp500_relayoutData:
        range_start, range_end = start_date, end_date
    else:
        range_start = pd.to_datetime(sp500_relayoutData['xaxis.range[0]'])
        range_end = pd.to_datetime(sp500_relayoutData['xaxis.range[1]'])

    if sp500_fig is None:
        sp500_fig = initial_sp500_fig
    if vix_fig is None:
        vix_fig = initial_vix_fig
    if unemployment_fig is None:
        unemployment_fig = initial_unemployment_fig

    # Update x-axis range
    sp500_fig['layout']['xaxis']['range'] = [range_start, range_end]
    vix_fig['layout']['xaxis']['range'] = [range_start, range_end]
    unemployment_fig['layout']['xaxis']['range'] = [range_start, range_end]

    # Convert datetime objects to timezone-naive
    vix_hist.index = vix_hist.index.tz_localize(None)
    ued_hist.index = ued_hist.index.tz_localize(None)

    # Update y-axis range for VIX
    vix_visible_data = vix_hist[(vix_hist.index >= range_start) & (vix_hist.index <= range_end)]
    if not vix_visible_data.empty:
        vix_min = 0.98 * vix_visible_data['Close'].min()
        vix_max = 1.02 * vix_visible_data['Close'].max()
        vix_fig['layout']['yaxis']['range'] = [vix_min, vix_max]

    # Update y-axis range for Unemployment Claims
    ued_visible_data = ued_hist[(ued_hist.index >= range_start) & (ued_hist.index <= range_end)]
    if not ued_visible_data.empty:
        ued_min = 0.98 * ued_visible_data['value'].min()
        ued_max = 1.02 * ued_visible_data['value'].max()
        unemployment_fig['layout']['yaxis']['range'] = [ued_min, ued_max]

    return sp500_fig, vix_fig, unemployment_fig

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    app.run_server(debug=True, host='0.0.0.0', port=port)