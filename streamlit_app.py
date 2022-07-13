import streamlit as st
import pandas as pd
import os
import json
from text_highlighter import text_highlighter
from streamlit.scriptrunner import get_script_run_ctx
from datetime import datetime


class UpdateDF:
    def __init__(self, rows):
        self.rows = rows
    def __call__(self):
        assert len(set(self.rows.number)) == 1
        df = st.session_state.df
        df = df[df.number != self.rows.iloc[0].number]
        st.session_state.df = pd.concat([df, pd.DataFrame(self.rows)])
        st.session_state.df.sort_values(['number'], inplace=True)
        st.session_state.updated = True


class DeleteExample:
    def __init__(self, number):
        self.number = number
    def __call__(self):
        df = st.session_state.df
        st.session_state.df = df[df.number != self.number]
        where_not_m1 = st.session_state.df.number != -1
        st.session_state.df['number'][where_not_m1] = range(len(st.session_state.df[where_not_m1]))
        st.session_state.updated = True


class StartAnns:
    def __init__(self, name, starting_anns):
        self.name = name
        self.starting_anns = starting_anns
    def __call__(self):
        st.session_state['name'] = self.name
        st.session_state['starting_anns'] = self.starting_anns
        if self.starting_anns == 'Start a new set':
            df = pd.DataFrame([], columns=['number', 'search terms', 'system', 'summary', 'labels', 'label names', 'studies', 'error_annotations'])
        else:
            df = pd.read_csv(
                os.path.join('annotations', self.starting_anns),
                converters={
                    'search terms': json.loads,
                    'summary': json.loads,
                    'labels': json.loads,
                    'label names': json.loads,
                    'studies': json.loads,
                    'error_annotations': json.loads,
                },
            )
        st.session_state['df'] = df
        st.session_state.updated = False


# Get session info
if 'session_id' not in st.session_state:
    st.session_state.session_id = get_script_run_ctx().session_id
    st.session_state.datetime = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
st.write('# Trialstreamer User Study')
st.write('Session start time: ' + st.session_state.datetime)
st.write('Session ID: ' + st.session_state.session_id)
# Get user name
if 'name' not in st.session_state:
    # Session name
    name = st.text_input('Enter your name:')
    # Get annotations
    if not os.path.exists('annotations'):
        os.mkdir('annotations')
    starting_anns = st.selectbox(
        'Please choose which annotations to start from and click \"Start Annotating\".', ['Start a new set'] + os.listdir('annotations'))
    st.button('Start Annotating', on_click=StartAnns(name, starting_anns), disabled=name=="")
    st.stop()
current_session_name = '%s_%s_%s' % (st.session_state.name, st.session_state.datetime, st.session_state.session_id)
name = st.session_state.name
df = st.session_state['df']
# Save Annotations
if st.session_state.updated and len(df) > 0:
    df_to_save = df.copy()
    for k in ['search terms', 'summary', 'labels', 'label names', 'studies', 'error_annotations']:
        df_to_save[k] = df_to_save[k].apply(json.dumps)
    df_to_save.to_csv(os.path.join('annotations', current_session_name + '.csv'), index=False)
elif os.path.exists(os.path.join('annotations', current_session_name + '.csv')):
    os.remove(os.path.join('annotations', current_session_name + '.csv'))
# Annotation Interface
st.write('Annotator: ' + name)
st.write('You have annotated **%i** instances. You have **%scompleted** the final questions.' % (len(df[df.number != -1]), '' if -1 in set(df.number) else 'not '))
with st.expander('All annotations'):
    st.write(df)
    st.write('##### WARNING: Be careful with the button below!')
    st.button('Revert All Annotation Edits from the Current Session', on_click=StartAnns(name, st.session_state.starting_anns))
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
        'annotator': name,
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
        st.write('##### Highlight Errors')
        st.write('As best you can tell using the punchlines, highlight anything that does not seem to be faithful to the studies. (You can remove a highlight by clicking on it.)')
        error_annotations = text_highlighter(
            ' '.join(instance_info['summary']), labels=['error']
        )
        error_annotations = {str(k): v for k, v in enumerate(error_annotations)}
        st.write('### Per Error Annotations')
        for i, error_ann in error_annotations.items():
            st.write('#### Error %s: %s' % (i, error_ann['text']))
            error_ann['error_confirmation'] = st.radio(
                'Can you confirm if this is an error using the interface?', options=['no', 'yes'],
                key='error_confirmation_%s_%i' % (i, number), horizontal=True)
            error_ann['error_insight'] = st.radio(
                'Does clicking on the words in this error provide insight as to where it came from?', options=['no', 'yes'],
                key='error_insight_%s_%i' % (i, number), horizontal=True)
        st.write('### Concluding questions')
        accuracy_assesment = st.radio('Rate the general accuray of the summary.', options=[1, 2, 3, 4, 5], key=number, horizontal=True,
            index=0 if current_rows is None else int(current_rows.iloc[0].accuracy_assesment)-1,
            format_func=likert_format)
        confidence_in_accuracy_assesment = st.radio('Rate how confident are you in your answer above?', options=[1, 2, 3, 4, 5], key=number, horizontal=True,
            index=0 if current_rows is None else int(current_rows.iloc[0].confidence_in_accuracy_assesment)-1,
            format_func=likert_format)
        rows = pd.DataFrame([dict(
            number=number,
            annotator=name,
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
