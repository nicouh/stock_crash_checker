# app.py
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import yfinance as yf
import pandas as pd
import requests

import os
fred_api_key = os.environ.get('fred_api_key')

obs_window='3y'

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

app = dash.Dash(__name__)

app.layout = html.Div([
    dcc.Graph(id='sp500-graph'),
    dcc.Graph(id='vix-graph'),
    dcc.Graph(id='unemployment-graph'),
])

@app.callback(
    [Output('sp500-graph', 'figure'),
     Output('vix-graph', 'figure'),
     Output('unemployment-graph', 'figure')],
    [Input('sp500-graph', 'id')]
)
def update_graphs(_):
    fig1 = {
        'data': [{'x': sp500_hist.index, 'y': sp500_hist['Close'], 'type': 'line', 'name': 'S&P 500'},
                 {'x': sp500_hist.index, 'y': sp500_hist['SMA200'], 'type': 'line', 'name': 'SMA 200'}],
        'layout': {'title': 'S&P 500 and 200-Day SMA'}
    }

    fig2 = {
        'data': [{'x': vix_hist.index, 'y': vix_hist['Close'], 'type': 'line', 'name': 'VIX'}],
        'layout': {'title': 'VIX'}
    }

    fig3 = {
        'data': [{'x': unemployment_claims.index, 'y': unemployment_claims['value'], 'type': 'line', 'name': 'US Unemployment Claims'}],
        'layout': {'title': 'US Unemployment Claims'}
    }

    return fig1, fig2, fig3

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    app.run_server(debug=True)
