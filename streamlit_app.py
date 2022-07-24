import math
import streamlit as st
import pandas as pd
import os
import json
from text_highlighter import text_highlighter
from streamlit.scriptrunner import get_script_run_ctx
from datetime import datetime
import zipfile
import os
import psycopg2
from sqlalchemy import create_engine, inspect


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
        if self.name == "":
            st.session_state['name_error'] = 'You need to enter a name.'
            return
        if 'name_error' in st.session_state:
            del st.session_state['name_error']
        self.name = self.name.replace(' ', '_')
        st.session_state['name'] = self.name
        st.session_state['starting_anns'] = self.starting_anns
        if self.starting_anns == 'Start a new set':
            df = pd.DataFrame([], columns=['number', 'search terms', 'system', 'summary', 'labels', 'label names', 'studies', 'error_annotations',
                'annotator', 'has aspects', 'readability', 'relevance', 'recall', 'accuracy', 'confidence_in_accuracy', 'template_preference', 'template'])
        else:
#            df = pd.read_csv(
#                os.path.join('annotations', self.starting_anns),
#                converters={
#                    'search terms': json.loads,
#                    'summary': json.loads,
#                    'labels': json.loads,
#                    'label names': json.loads,
#                    'studies': json.loads,
#                    'error_annotations': json.loads,
#                },
#            )
            df = pd.read_sql_table(self.starting_anns, st.session_state.sqlalchemy_conn)
            for k in ['search terms', 'summary', 'labels', 'label names', 'studies', 'error_annotations']:
                df[k] = df[k].apply(json.loads)
        st.session_state['df'] = df
        st.session_state.updated = False


def download_all_anns_button():
    table_names = st.session_state.inspector.get_table_names(schema='public')
    if len(table_names) > 0:
        if not os.path.exists('annotations'):
            os.mkdir('annotations')
        for table in table_names:
            pd.read_sql_table(table, st.session_state.sqlalchemy_conn).to_csv('annotations/%s.csv' % table, index=False)
        with zipfile.ZipFile('annotations.zip', 'w') as f:
            for table in table_names:
                f.write('annotations/%s.csv' % table)
#    if os.path.exists('annotations.zip') and len(os.listdir('annotations')) > 0:
        with open('annotations.zip', 'rb') as f:
            st.download_button(
                label='Download All Annotations',
                data=f,
                file_name='all_annotations.zip',
                mime='application/zip'
            )
    else:
        st.download_button('Download All Annotations', '', disabled=True)


def stop():
    st.session_state.sqlalchemy_conn.close()
    st.stop()


#    dialect = 'postgresql'
#    user = 'postgres'
#    password = 'postgres'
#    host = 'localhost'
#    database = 'jered'
#    DATABASE_URL = '%s://%s:%s@%s/%s' % (dialect, user, password, host, database)
DATABASE_URL = os.environ['DATABASE_URL']
DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://')
if 'sqlalchemy_db' not in st.session_state:
    #st.write(DATABASE_URL)
    st.session_state.sqlalchemy_db = create_engine(DATABASE_URL)
    st.session_state.inspector = inspect(st.session_state.sqlalchemy_db)
    st.session_state.sqlalchemy_conn = st.session_state.sqlalchemy_db.connect()
    if 'session_info' not in st.session_state.inspector.get_table_names(schema='public'):
        session_info = pd.DataFrame([], columns=['session_id', 'annotator', 'datetime', 'starting_anns'])
        session_info.to_sql('session_info', st.session_state.sqlalchemy_conn, index=False)
else:
    st.session_state.sqlalchemy_conn = st.session_state.sqlalchemy_db.connect()
# Get session info
if 'session_id' not in st.session_state:
    st.session_state.session_id = get_script_run_ctx().session_id.replace('-', '_')
    st.session_state.datetime = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
st.write('# Trialstreamer User Study')
st.write('Session start time: ' + st.session_state.datetime)
st.write('Session ID: ' + st.session_state.session_id)
if not os.path.exists('annotations'):
    os.mkdir('annotations')
# Get user name
if 'name' not in st.session_state:
    download_all_anns_button()
    with st.form('Start Session'):
        # Session name
        if 'name_error' in st.session_state:
            st.error(st.session_state.name_error)
        name = st.text_input('Enter your name:')
        # Get annotations
#        starting_anns = st.selectbox(
#            'Please choose which annotations to start from and click \"Start Annotating\".', ['Start a new set'] + os.listdir('annotations'))
        session_info = pd.read_sql_table('session_info', st.session_state.sqlalchemy_conn)
        tables = {r.session_id: '%s - %s' % (r.annotator, r.datetime) for i, r in session_info.iterrows()}
        starting_anns = st.selectbox(
            'Please choose which annotations to start from and click \"Start Annotating\".', ['Start a new set'] + list(tables.keys()),
            format_func=lambda x: tables[x] if x != 'Start a new set' else x)
        submitted = st.form_submit_button('Start Annotation Session')
    if submitted:
        StartAnns(name, starting_anns)()
        st.experimental_rerun()
    stop()
#current_session_name = '%s__%s__%s' % (st.session_state.name, st.session_state.datetime, st.session_state.session_id)
#current_session_name = current_session_name[:63]
current_session_name = st.session_state.session_id
name = st.session_state.name
df = st.session_state['df']
# Save Annotations
if st.session_state.updated and len(df) > 0:
    df_to_save = df.copy()
    for k in ['search terms', 'summary', 'labels', 'label names', 'studies', 'error_annotations']:
        df_to_save[k] = df_to_save[k].apply(json.dumps)
#    df_to_save.to_csv(os.path.join('annotations', current_session_name + '.csv'), index=False)
    # update session annotations
    df_to_save.to_sql(current_session_name, st.session_state.sqlalchemy_conn, index=False, if_exists='replace')
    # update session info
    session_info = pd.read_sql_table('session_info', st.session_state.sqlalchemy_conn)
    if current_session_name not in set(session_info.session_id):
        session_info = pd.concat([
            session_info,
            pd.DataFrame([{
                'session_id': current_session_name,
                'annotator': name,
                'datetime': st.session_state.datetime,
                'starting_anns': st.session_state.starting_anns,
            }])
        ])
        session_info.to_sql('session_info', st.session_state.sqlalchemy_conn, index=False, if_exists='replace')
#    with zipfile.ZipFile('annotations.zip', 'w') as f:
#        for root, directories, files in os.walk('annotations'):
#            for file in files:
#                f.write(os.path.join(root, file))
#elif os.path.exists(os.path.join('annotations', current_session_name + '.csv')):
#    os.remove(os.path.join('annotations', current_session_name + '.csv'))
else:
    session_info = pd.read_sql_table('session_info', st.session_state.sqlalchemy_conn)
    if current_session_name in set(session_info.session_id):
        # drop session table
        psycopg_conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = psycopg_conn.cursor()
        cursor.execute('''DROP TABLE %s''' % current_session_name)
        psycopg_conn.commit()
        psycopg_conn.close()
        # update session info
        session_info = session_info[session_info.session_id != current_session_name]
        session_info.to_sql('session_info', st.session_state.sqlalchemy_conn, index=False, if_exists='replace')
download_all_anns_button()
# Annotation Interface
st.write('Annotator: ' + name)
st.write('You have annotated **%i** instances. You have **%scompleted** the final questions.' % (len(df[df.number != -1]), '' if -1 in set(df.number) else 'not '))
with st.expander('All annotations'):
    st.write(df)
    st.warning('WARNING: Be careful with the button below!')
    st.button('Revert All Annotation Edits from the Current Session', on_click=StartAnns(name, st.session_state.starting_anns))
st.download_button('Download Session Annotations', st.session_state.df.to_csv(index=False), file_name='session_annotations.csv')
options = ['Add New Annotation', 'Final Questions']
if len(df) > 0:
    options += sorted(list(set(df[df.number != -1].number)))
search_term_names = {'population': 'Population', 'intervention': 'Intervention', 'outcome': 'Outcome'}
shortened_search_term_names = {'population': 'Pop', 'intervention': 'Int', 'outcome': 'Out'}
def get_ann_title(o):
    if o not in set(df.number):
        return o
    search_terms = df[df.number == o].iloc[0]['search terms']
    template = df[df.number == o].iloc[0]['template']
    template_addon = ' with template' if template == template and template is not None else ''
    search_term_string = ', '.join(['%s: %s' % (v, search_terms[k]) for k, v in shortened_search_term_names.items() if k in search_terms.keys()])
    return '%i. %s (%s%s)' % (o, search_term_string, df[df.number == o].iloc[0]['system'], template_addon)
number = st.selectbox('Example to edit/annotate:', options, format_func=get_ann_title)
if number == 'Final Questions':
    st.write('### Final Questions')
    current_rows = df[df.number == -1]
    if len(current_rows) == 0:
        current_rows = None
    systems = list(set(df.system[~df.system.isna()]))
    systems_to_index = {system: i for i, system in enumerate(systems)}
    if len(systems) < 2:
        st.error('You cannot perform concluding questions until you have annotated instances on multiple systems.')
        stop()
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
    st.write('### Instance Annotation')
    if number != 'Add New Annotation':
        current_rows = df[df.number == number]
    else:
        number = len(set(df[df.number != -1].number))
        assert number not in set(df.number), number
        current_rows = None
    if current_rows is None:
        value = ""
    else:
        def df_to_json_python_objects(k):
            element = current_rows.iloc[0][k]
            if k == 'has aspects':
                element = bool(element)
            if k == 'template' and element != element:
                return None
            return element
        value = json.dumps(
            {k: df_to_json_python_objects(k)
             for k in ['system', 'has aspects', 'search terms', 'summary', 'labels', 'label names', 'studies', 'template']}, indent=4)
    instance_info = st.text_area(
        'Paste the json automatically copied to your clipboard when you push the \"Copy info to clipboard\" button on the trialstreamer interface',
        value=value,
        key=number,
        disabled=current_rows is not None)
    if instance_info == "":
        stop()
    try:
        instance_info = json.loads(instance_info)
    except json.decoder.JSONDecodeError as e:
        st.error("Error decoding json")
        stop()
    for k in instance_info['search terms'].keys():
        assert k in search_term_names.keys(), k
    assert len(instance_info['search terms']) >= 2
    has_template = 'template' in instance_info and instance_info['template'] is not None
    if has_template:
        assert instance_info['has aspects']
        st.warning("Warning: You are annotating a template summary. If you have not done so yet, you should annotate the \"General Summary\" first and then come back to the template summary.")
    st.markdown("""
        <style>
        .bigger-font {
            font-size:24px !important;
        }
        .big-font {
            font-size:18px !important;
        }
        </style>
        """, unsafe_allow_html=True)
    template_addon = ' with template' if has_template else ''
    search_term_string = ', '.join(['%s: %s' % (v, instance_info['search terms'][k]) for k, v in search_term_names.items() if k in instance_info['search terms'].keys()])
    st.markdown('<p class="bigger-font">%i. %s <b>(%s%s)</b></p>' % (
        number, search_term_string,
        instance_info['system'], template_addon), unsafe_allow_html=True)
    st.write('<p class="big-font">Summary: <b>%s</b></p>' % ' '.join(instance_info['summary']), unsafe_allow_html=True)
    if has_template:
        st.write('<p class="big-font">Template: <b>%s</b></p>' % instance_info['template'], unsafe_allow_html=True)
    likert_format = lambda x: '1 (worst)' if x == 1 else '5 (best)' if x == 5 else x
    c1, c2, c3 = st.columns(3)
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
    st.write('##### Highlight Errors')
    st.write('As best you can tell using the _punchlines_, highlight anything that does not seem to be faithful to the studies. (You can remove a highlight by clicking on it.)')
    st.write('_Punchlines_: Snippets extracted from the studies and displayed in the “Overview” section of the interface.')
    with st.container():
        error_annotations = text_highlighter(
            ' '.join(instance_info['summary']), labels=[''], annotations=[] if current_rows is None else list(current_rows.iloc[0].error_annotations.values())
        )
    st.markdown("""
        <style>
        div[data-testid="stVerticalBlock"] div div[data-testid="stVerticalBlock"] div.element-container iframe{
            padding-left: 7px;
            border-left: 7px solid lightgrey;
        }
        </style>
        """, unsafe_allow_html=True)
    error_annotations = {str(k): v for k, v in enumerate(error_annotations)}
    st.write('##### Per Error Annotations')
    if len(error_annotations) == 0:
        st.warning("You currently have not highlighted any errors above. Once you do, you will see additional questions here for each error.")
    elif instance_info['has aspects']:
        st.markdown('<p><b>Note:</b> The interface you are annotating associates aspects with each generated word which are shown when a word is clicked, so we have <b>2</b> questions per error.</p>', unsafe_allow_html=True)
    num_rows = math.ceil(len(error_annotations) / 4)
    rows = [st.columns(4) for _ in range(num_rows)]
    st.markdown("""
        <style>
        .summ-error {
            font-size:16px !important;
        }
        </style>
        """, unsafe_allow_html=True)
    no_yes_options = ['no', 'yes']
    no_yes_index = {k: i for i, k in enumerate(no_yes_options)}
    for i, error_ann in error_annotations.items():
        with rows[int(i) // 4][int(i) % 4]:
            st.markdown('<p class="summ-error">Error %s: <text style="color: red"><b>%s</b></text></p>' % (i, error_ann['text']), unsafe_allow_html=True)
            error_ann['error_confirmation'] = st.radio(
                'Can you confirm if this is an error using the interface?', options=no_yes_options,
                key='error_confirmation_%s_%i' % (i, number), horizontal=True, index=0 if 'error_confirmation' not in error_ann else no_yes_index[error_ann['error_confirmation']])
            if instance_info['has aspects']:
                error_ann['error_insight'] = st.radio(
                    'Does clicking on the words in this error provide insight as to where it came from?', options=no_yes_options,
                    key='error_insight_%s_%i' % (i, number), horizontal=True, index=0 if 'error_insight' not in error_ann else no_yes_index[error_ann['error_insight']])
    st.write('##### Overall Accuracy')
    accuracy = st.radio(
        'As best you can tell, rate how well the summary accurately reflects the studies (i.e. does not contain hallucinations and remains factual).',
        options=[1, 2, 3, 4, 5],
        format_func=likert_format,
        index=0 if current_rows is None else int(current_rows.iloc[0].accuracy)-1,
        key='accuracy_%s' % number, horizontal=True)
#    st.write('Above you rated the accuracy of the summary at a **%i** out of 5.' % accuracy)
    st.write('##### Confidence in Accuracy Assesment')
    confidence_in_accuracy = st.radio('Now rate how confident you are in your assesment of the accuracy.', options=[1, 2, 3, 4, 5], key=number, horizontal=True,
        index=0 if current_rows is None else int(current_rows.iloc[0].confidence_in_accuracy)-1,
        format_func=likert_format)
    if has_template:
        st.write('##### Extra Template Summary Question')
        template_preference = st.radio('Do you prefer this template summary over the original (\"General Summary\")?', options=no_yes_options, key=number, horizontal=True,
            index=0 if current_rows is None else no_yes_index[current_rows.iloc[0].template_preference])
    else:
        template_preference = None
    rows = pd.DataFrame([dict(
        number=number,
        session=current_session_name,
        **instance_info,
        readability=readability,
        relevance=relevance,
        recall=recall,
        error_annotations=error_annotations,
        accuracy=accuracy,
        confidence_in_accuracy=confidence_in_accuracy,
        template_preference=template_preference,
    )])
    st.button('Submit', on_click=UpdateDF(rows))
    if current_rows is not None:
        st.button('Delete', on_click=DeleteExample(number))
stop()
