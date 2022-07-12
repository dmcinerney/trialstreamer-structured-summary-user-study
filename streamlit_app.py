import streamlit as st
import pandas as pd
import os
import json
from text_highlighter import text_highlighter


class UpdateDF:
    def __init__(self, rows):
        self.rows = rows
    def __call__(self):
        assert len(set(self.rows.number)) == 1
        df = st.session_state.df
        df = df[df.number != self.rows.iloc[0].number]
        st.session_state.df = pd.concat([df, pd.DataFrame(self.rows)])
        st.session_state.df.sort_values(['number'], inplace=True)


class DeleteExample:
    def __init__(self, number):
        self.number = number
    def __call__(self):
        df = st.session_state.df
        st.session_state.df = df[df.number != self.number]
        st.session_state.df['number'] = range(len(st.session_state.df[st.session_state.df != -1]))


st.write('# Trialstreamer User Study')
if 'df' not in st.session_state.keys():
    st.session_state['df'] = pd.DataFrame([], columns=['number'])
df = st.session_state['df']
options = ['Add new example', 'Final questions']
if len(df) > 0:
    options += sorted(list(set(df[df.number != -1].number)))
fmt = lambda o: o if o not in set(df[df.number != -1].number) else '%s: %s' % (o, df[df.number == o].iloc[0].instance_info['search terms'])
number = st.selectbox('Example to edit/annotate:', options, format_func=fmt)
if number == 'Final questions':
    current_rows = df[df.number == -1]
    st.write(current_rows)
    if len(current_rows) > 0:
        st.button('Delete', on_click=DeleteExample(-1))
    preferred_summaries = st.radio('Which system produced the best summaries?', options=['System A', 'System B'], key=number)
    preferred_interface = st.radio('Which interface do you prefer?', options=['System A', 'System B'], key=number)
    rows = pd.DataFrame([{
        'number': -1,
        'preferred_summaries': preferred_summaries,
        'preferred_interface': preferred_interface,
    }])
    st.button('Submit', on_click=UpdateDF(rows))
else:
    if number != 'Add new example':
        current_rows = df[df.number == number]
        st.write(current_rows)
        st.button('Delete', on_click=DeleteExample(number))
    else:
        number = len(set(df[df.number != -1].number))
        if number in df.number:
            current_rows = df[df.number == number]
        else:
            current_rows = None
    instance_info = st.text_input(
        'Paste the json automatically copied to your clipboard when you push the \"Copy info to clipboard\" button on the trialstreamer interface',
        key=number)
    if instance_info != "":
        instance_info = json.loads(instance_info)
        st.write('Search terms:')
        st.write(instance_info['search terms'])
        st.write(instance_info['system'] + ' summary: ' + ' '.join(instance_info['summary']))
        st.write('### Initial questions')
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            readability = st.radio('Rate the readability of the summary (i.e. general fluency, coherency, sensability).', options=[1, 2, 3, 4, 5], key=number)
        with c2:
            relevance = st.radio('Rate the relevance of the summary to the given query (i.e. precision).', options=[1, 2, 3, 4, 5], key=number)
        with c3:
            recall = st.radio('Rate how well the summary includes all the important aspects of the studies (i.e. recall).', options=[1, 2, 3, 4, 5], key=number)
        with c4:
            faithfullness = st.radio('As best you can tell using the punchlines, rate how well the summary faithfully reflects the studies (i.e. does not contain hallucinations).', options=[1, 2, 3, 4, 5], key=number)
        st.write('As best you can tell using the punchlines, highlight anything that does not seem to be faithful to the studies.')
        error_annotations = text_highlighter(
            ' '.join(instance_info['summary']), labels=['error']
        )
        st.write('### Per Error Annotations')
        for i, error_ann in enumerate(error_annotations):
            st.write('#### Error %i: %s' % (i, error_ann['text']))
            st.write('Can you confirm if this is an error using the interface?')
            error_ann['error_confirmation'] = st.checkbox('yes', key='error_confirmation_%i_%i' % (i, number))
            st.write('Does clicking on the words in this error provide insight as to where it came from?')
            error_ann['error_insight'] = st.checkbox('yes', key='error_insight_%i_%i' % (i, number))
        st.write('### Concluding questions')
        st.write('Do you think the summary is accurate?')
        accuracy_assesment = st.checkbox('yes', key=number)
        confidence_in_accuracy_assesment = st.radio('Rate how confident are you in your answer above?', options=[1, 2, 3, 4, 5], key=number)
        rows = pd.DataFrame([{
            'number': number,
            'instance_info': instance_info,
            'readability': readability,
            'relevance': relevance,
            'recall': recall,
            'faithfullness': faithfullness,
            'error_annotations': error_annotations,
            'accuracy_assesment': accuracy_assesment,
            'confidence_in_accuracy_assesment': confidence_in_accuracy_assesment,
        }])
        st.button('Submit', on_click=UpdateDF(rows))
st.write(df)
st.download_button('Download CSV', st.session_state.df.to_csv(index=False), file_name='annotations.csv')
