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
        where_not_m1 = st.session_state.df.number != -1
        st.session_state.df['number'][where_not_m1] = range(len(st.session_state.df[where_not_m1]))


st.write('# Trialstreamer User Study')
if 'df' not in st.session_state.keys():
    st.session_state['df'] = pd.DataFrame([], columns=['number', 'search terms', 'system'])
df = st.session_state['df']
st.write('You have annotated **%i** instances. You have **%scompleted** the final questions.' % (len(df[df.number != -1]), '' if -1 in df.number else 'not '))
with st.expander('All annotations'):
    st.write(df)
st.download_button('Download CSV', st.session_state.df.to_csv(index=False), file_name='annotations.csv')
options = ['Add new example', 'Final questions']
if len(df) > 0:
    options += sorted(list(set(df[df.number != -1].number)))
def get_ann_title(o):
   if o not in set(df.number):
       return o
   search_terms = df[df.number == o].iloc[0]['search terms']
   return 'Pop: %s, Int: %s (%s)' % (search_terms['population'], search_terms['intervention'], df[df.number == o].iloc[0]['system'])
number = st.selectbox('Example to edit/annotate:', options, format_func=get_ann_title)
if number == 'Final questions':
    current_rows = df[df.number == -1]
    if len(current_rows) == 0:
        current_rows = None
    systems = list(set(df.system[~df.system.isna()]))
    systems_to_index = {system: i for i, system in enumerate(systems)}
    if len(systems) < 2:
        st.error('You cannot perform concluding questions until you have annotated instances on multiple systems.')
        st.stop()
    preferred_summaries = st.radio('Which system produced the best summaries?', options=systems, key='preferred_summaries',
        index=0 if current_rows is None else systems_to_index[current_rows.iloc[0].preferred_summaries])
    preferred_interface = st.radio('Which interface do you prefer?', options=systems, key='preferred_interface',
        index=0 if current_rows is None else systems_to_index[current_rows.iloc[0].preferred_interface])
    rows = pd.DataFrame([{
        'number': -1,
        'preferred_summaries': preferred_summaries,
        'preferred_interface': preferred_interface,
    }])
    st.button('Submit', on_click=UpdateDF(rows))
    if current_rows is not None:
        st.button('Delete', on_click=DeleteExample(-1))
else:
    if number != 'Add new example':
        current_rows = df[df.number == number]
    else:
        number = len(set(df[df.number != -1].number))
        assert number not in df.number
        current_rows = None
    if current_rows is None:
        value = ""
    else:
        value = json.dumps(
            {k: current_rows.iloc[0][k] for k in ['system', 'search terms', 'summary', 'labels', 'label names', 'studies']}, indent=4)
    instance_info = st.text_area(
        'Paste the json automatically copied to your clipboard when you push the \"Copy info to clipboard\" button on the trialstreamer interface',
        value=value,
        key=number,
        disabled=current_rows is not None)
    if instance_info != "":
        try:
            instance_info = json.loads(instance_info)
        except json.decoder.JSONDecodeError as e:
            st.error("Error decoding json")
            st.stop()
        assert 'population' in instance_info['search terms']
        assert 'intervention' in instance_info['search terms']
        assert len(instance_info['search terms']) == 2
        st.write('## Population: %s, Intervention: %s (%s)' % (
            instance_info['search terms']['population'], instance_info['search terms']['intervention'],
            instance_info['system']))
        st.write('**Summary:** ' + ' '.join(instance_info['summary']))
        st.write('### Initial questions')
        likert_format = lambda x: '1 (worst)' if x == 1 else '5 (best)' if x == 5 else x
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.write('##### Readability')
            readability = st.radio('Rate the readability of the summary (i.e. general fluency, coherency, sensability).', options=[1, 2, 3, 4, 5],
                format_func=likert_format,
                index=0 if current_rows is None else int(current_rows.iloc[0].readability)-1,
                key='readability_%s' % number)
        with c2:
            st.write('##### Relevance')
            relevance = st.radio('Rate the relevance of the summary to the given query (i.e. precision).', options=[1, 2, 3, 4, 5],
                format_func=likert_format,
                index=0 if current_rows is None else int(current_rows.iloc[0].relevance)-1,
                key='relevance_%s' % number)
        with c3:
            st.write('##### Recall')
            recall = st.radio('Rate how well the summary includes all the important aspects of the studies (i.e. recall).', options=[1, 2, 3, 4, 5],
                format_func=likert_format,
                index=0 if current_rows is None else int(current_rows.iloc[0].recall)-1,
                key='recall_%s' % number)
        with c4:
            st.write('##### Faithfulness')
            faithfulness = st.radio(
                'As best you can tell using the punchlines, rate how well the summary faithfully reflects the studies (i.e. does not contain hallucinations).',
                options=[1, 2, 3, 4, 5],
                format_func=likert_format,
                index=0 if current_rows is None else int(current_rows.iloc[0].faithfulness)-1,
                key='faithfulness_%s' % number)
        st.write('As best you can tell using the punchlines, highlight anything that does not seem to be faithful to the studies.')
        error_annotations = text_highlighter(
            ' '.join(instance_info['summary']), labels=['error']
        )
        st.write('### Per Error Annotations')
        for i, error_ann in enumerate(error_annotations):
            st.write('#### Error %i: %s' % (i, error_ann['text']))
            error_ann['error_confirmation'] = st.radio(
                'Can you confirm if this is an error using the interface?', options=['no', 'yes'],
                key='error_confirmation_%i_%i' % (i, number), horizontal=True)
            error_ann['error_insight'] = st.radio(
                'Does clicking on the words in this error provide insight as to where it came from?', options=['no', 'yes'],
                key='error_insight_%i_%i' % (i, number), horizontal=True)
        st.write('### Concluding questions')
        accuracy_assesment = st.radio('Rate the general accuray of the summary.', options=[1, 2, 3, 4, 5], key=number, horizontal=True,
            index=0 if current_rows is None else int(current_rows.iloc[0].accuracy_assesment)-1,
            format_func=likert_format)
        confidence_in_accuracy_assesment = st.radio('Rate how confident are you in your answer above?', options=[1, 2, 3, 4, 5], key=number, horizontal=True,
            index=0 if current_rows is None else int(current_rows.iloc[0].confidence_in_accuracy_assesment)-1,
            format_func=likert_format)
        rows = pd.DataFrame([dict(
            number=number,
            **instance_info,
            readability=readability,
            relevance=relevance,
            recall=recall,
            faithfulness=faithfulness,
            error_annotations=error_annotations,
            accuracy_assesment=accuracy_assesment,
            confidence_in_accuracy_assesment=confidence_in_accuracy_assesment,
        )])
        st.button('Submit', on_click=UpdateDF(rows))
        if current_rows is not None:
            st.button('Delete', on_click=DeleteExample(number))
