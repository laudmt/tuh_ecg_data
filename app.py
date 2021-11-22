# -*- coding: utf-8 -*-

import glob
import pandas as pd
import plotly
import plotly.graph_objects as go
from plotly.subplots import make_subplots

input_directory = './data/bs_all/'
available_patients = glob.glob(input_directory + '*_data_file.csv')
available_patients.sort()

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output


app = dash.Dash(__name__, title='TUH ECG database exploration', external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css'])
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Br(),
    dcc.Link('Go to Overall stats', href='/page-2'),
    html.Br(),
    html.Div(id='page-content')
])

page_1_layout = html.Div([
    dcc.Dropdown(id='patient_dd',
                    options=[{'label': i, 'value': i} for i in available_patients],
                    value=available_patients[0]),
    html.Div(id='page-1-content'),
    html.Hr(),
    dcc.RadioItems(id='patient_exams', labelStyle={'display': 'inline-block'}),
    html.Hr(),
    dcc.Graph(id='indicator-graphic')
])

page_2_layout = html.Div([
    html.Div(id='page-2-content'),
    html.Hr(),
    dcc.Dropdown(id='window_type',
                    options=[{'label': 'window_type_120', 'value': 'window_type_120'},
                             {'label': 'window_type_180', 'value': 'window_type_180'},
                             {'label': 'window_type_240', 'value': 'window_type_240'},
                             {'label': 'window_type_300', 'value': 'window_type_300'}],
                    value='window_type_120'),
    html.Br(),
    dcc.Graph(id='indicator-graphic-2'),
    html.Br(),
    dcc.Textarea(id='definitions',
                 value='Various definitions of tachycardia :\n\nFC > 100 bpm\nFC > 120 bpm\ndelta FC > 10 bpm relative to pre critical state\ndelta FC > 15 bpm relative to pre critical state\nFC > basale state + 50 % basale state\nFC > basale state + 60 % basale state\nFC > basale state + 34 bpm',
                 style={'width' : '100%', 'height':150})
])

@app.callback(
    Output('patient_exams', 'options'),
    [Input('patient_dd', 'value')])
def set_slider_options(patient_input_file):
    df = pd.read_csv(patient_input_file)
    option_list = []
    for i in df.exam.unique():
        if df.loc[(df.exam == i) & (df.label > 0), 'label'].sum() > 0:
            option_list.append({'label': '* ' + i, 'value': i})
        else:
            option_list.append({'label': i, 'value': i})
    return option_list
    # return [{'label': i, 'value': i} for i in df.exam.unique()]

@app.callback(
    Output('patient_exams', 'value'),
    [Input('patient_exams', 'options')])
def set_slider_value(available_options):
    return available_options[0]['value']


@app.callback(
    Output('indicator-graphic', 'figure'),
    [Input('patient_dd', 'value')],
    [Input('patient_exams', 'value')])
def update_graph(patient_input_file, exam_name):
    df = pd.read_csv(patient_input_file)
    df.date = pd.to_datetime(df.date)
    ddf = df[df.exam == exam_name]
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True)

    fig.add_trace(go.Scatter(x=ddf['date'], y=ddf['hr'], mode='lines', name='signal', line=dict(color=plotly.colors.DEFAULT_PLOTLY_COLORS[0])), row=1, col=1)
    if not ddf.loc[ddf.window_type_120.astype(str).str.contains('_bs'), 'date'].empty:
        fig.add_trace(go.Scatter(x=ddf.loc[ddf.window_type_120.str.contains('_bs'), 'date'], y=ddf.loc[ddf.window_type_120.str.contains('_bs'), 'hr'], mode='markers', marker_color=plotly.colors.DEFAULT_PLOTLY_COLORS[1], connectgaps=False, name='before seizure'), row=1, col=1)
    if not ddf.loc[ddf.window_type_120.astype(str).str.contains('_basale'), 'date'].empty:
        fig.add_trace(go.Scatter(x=ddf.loc[ddf.window_type_120.str.contains('_basale'), 'date'], y=ddf.loc[ddf.window_type_120.str.contains('_basale'), 'hr'], mode='markers', marker_color=plotly.colors.DEFAULT_PLOTLY_COLORS[2], connectgaps=False, name='seizure basale'), row=1, col=1)
    if not ddf.loc[ddf.window_type_120.astype(str).str.contains('_s$'), 'date'].empty:
        fig.add_trace(go.Scatter(x=ddf.loc[ddf.window_type_120.str.contains('_s$'), 'date'], y=ddf.loc[ddf.window_type_120.str.contains('_s$'), 'hr'], mode='markers', marker_color=plotly.colors.DEFAULT_PLOTLY_COLORS[3], connectgaps=False, name='seizure'), row=1, col=1)
    fig.add_trace(go.Scatter(x=ddf['date'], y=ddf['label'], mode='lines', name='label',  line=dict(color=plotly.colors.DEFAULT_PLOTLY_COLORS[4])), row=2, col=1)

    return fig



@app.callback(
    Output('indicator-graphic-2', 'figure'),
    [Input('window_type', 'value')])
def update_graph_2(window_type):
    df = pd.read_csv('./data/' + 'bs_{}_diff_file.csv'.format(window_type))
    
    fig = make_subplots(rows=4, cols=2,specs=[[{"type": "pie"}, {"type": "pie"}],
                                            [{"type": "xy"}, {"type": "pie"}],
                                            [{"type": "xy"}, {"type": "pie"}],
                                            [{"type": "xy"}, {"type": "pie"}]])
    fig.add_trace(go.Pie(values=df.loc[df.diff_type.str.contains('_s_ov100$'), 'diff_mean'].value_counts().values, labels=df.loc[df.diff_type.str.contains('_s_ov100$'), 'diff_mean'].value_counts().index, title='before seizure > 100'), row=1, col=1)
    fig.add_trace(go.Pie(values=df.loc[df.diff_type.str.contains('_s_ov120$'), 'diff_mean'].value_counts().values, labels=df.loc[df.diff_type.str.contains('_s_ov120$'), 'diff_mean'].value_counts().index, title='before seizure > 120'), row=1, col=2)
    fig.add_trace(go.Histogram(x=df.loc[df.diff_type.str.contains('_s$'), 'diff_mean'].values, name='before seizure - seizure basale'), row=2, col=1)
    df_tmp = df[df.diff_type.str.contains('_s$')]
    fig.add_trace(go.Pie(values=(df_tmp.diff_mean > 10).value_counts().values, labels=(df_tmp.diff_mean > 10).value_counts().index, title='s - basale > 10 bpm'), row=2, col=2)
    fig.add_trace(go.Histogram(x=df.loc[df.diff_type.str.contains('_s_0_r$'), 'diff_mean'].values, name='before seizure / whole basale'), row=3, col=1)
    df_tmp = df[df.diff_type.str.contains('_s_0_r$')]
    fig.add_trace(go.Pie(values=(df_tmp.diff_mean > 1.5).value_counts().values, labels=(df_tmp.diff_mean > 1.5).value_counts().index, title='s / basale > 1.5'), row=3, col=2)
    fig.add_trace(go.Histogram(x=df.loc[df.diff_type.str.contains('_s_0$'), 'diff_mean'].values, name='before seizure - whole basale'), row=4, col=1)
    df_tmp = df[df.diff_type.str.contains('_s_0$')]
    fig.add_trace(go.Pie(values=(df_tmp.diff_mean > 34).value_counts().values, labels=(df_tmp.diff_mean > 34).value_counts().index, title='s - basale > 34'), row=4, col=2)

    fig.update_layout(height=900, showlegend=True)
    return fig

# Index Page callback
@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/page-1':
        return page_1_layout
    elif pathname == '/page-2':
        return page_2_layout
    else:
        return page_1_layout
    
if __name__ == '__main__':
    app.run_server(debug=True, use_reloader=False)  # Turn off reloader if inside Jupyter