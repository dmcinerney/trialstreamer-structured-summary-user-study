import streamlit as st
import pandas as pd
import os


#class UpdateDF:
#    def __init__(self, df, file, rows):
#        self.df = df
#        self.file = file
#        self.rows = rows
#
#    def __call__(self):
#        assert len(set(self.rows.number)) == 1
#        self.df = self.df[self.df.number != rows.iloc[0].number]
#        self.df = pd.concat([self.df, pd.DataFrame(self.rows)])
#        self.df.sort_values(['number', 'annotation_num'], inplace=True)
#        self.df.to_csv(self.file, index=False)
class UpdateDF:
    def __init__(self, rows):
        self.rows = rows
    def __call__(self):
        assert len(set(self.rows.number)) == 1
        df = st.session_state.df
        df = df[df.number != self.rows.iloc[0].number]
        st.session_state.df = pd.concat([df, pd.DataFrame(self.rows)])
        st.session_state.df.sort_values(['number', 'annotation_num'], inplace=True)


#class DeleteExample:
#    def __init__(self, df, file, number):
#        self.df = df
#        self.file = file
#        self.number = number
#
#    def __call__(self):
#        self.df = self.df[self.df.number != self.number]
#        self.df['number'] = range(len(self.df))
#        self.df.to_csv(self.file, index=False)
class DeleteExample:
    def __init__(self, number):
        self.number = number
    def __call__(self):
        df = st.session_state.df
        st.session_state.df = df[df.number != number]
        st.session_state.df['number'] = range(len(st.session_state.df))


st.write('# Trialstreamer User Study')
#if not os.path.exists('annotations'):
#    os.mkdir('annotations')
#files = os.listdir('annotations')
#options = ['Create new annotation set'] + [f.replace('.csv', '') for f in files]
#annotation_name = st.selectbox('Annotation Set:', options)
#if annotation_name == 'Create new annotation set':
#    annotation_name = st.text_input('Annotation Set Name:')
#    assert annotation_name != 'Create new annotation set'
#df_file = os.path.join('annotations', annotation_name + '.csv')
#if os.path.exists(df_file):
#    df = pd.read_csv(df_file)
#else:
#    df = pd.DataFrame([], columns=['number'])
if 'df' not in st.session_state.keys():
    st.session_state['df'] = pd.DataFrame([], columns=['number'])
df = st.session_state['df']
options = ['Add new example']
if len(df) > 0:
    options += sorted(list(set(df.number)))
fmt = lambda o: o if o not in set(df.number) else '%s: %s' % (o, df[df.number == o].iloc[0].search_terms)
number = st.selectbox('Example to edit/annotate:', options, format_func=fmt)
if number != 'Add new example':
    current_rows = df[df.number == number]
    st.write(current_rows)
    st.button('Delete', on_click=DeleteExample(number))
else:
    number = len(set(df.number))
    if number in df.number:
        current_rows = df[df.number == number]
    else:
        current_rows = None
info = st.text_input(
    'Paste the json automatically copied to your clipboard when you push the \"Copy info to clipboard\" button on the trialstreamer interface',
    key=number)
c1, c2, c3, c4 = st.columns(4)
with c1:
    relevance = st.radio('Rate the relevance of the summary to the given query.', options=[1, 2, 3, 4, 5], key=number)
rows = []
rows.append({
    'number': number,
    'info': info,
    'relevance': relevance,
})
rows = pd.DataFrame(rows)
#st.button('Submit', on_click=UpdateDF(df, df_file, rows))
st.button('Submit', on_click=UpdateDF(rows))
st.write(df)
