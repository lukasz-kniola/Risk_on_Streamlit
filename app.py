import streamlit as st
import requests, json, io
import pandas as pd
import numpy as np
from streamlit.state.session_state import SessionState

st.set_page_config(layout='wide')

# Session state Initialization
if 'file' not in st.session_state:
	st.session_state['file'] = None

if 'cols' not in st.session_state:
	st.session_state['cols'] = ["SITEID", "SEX", "AGE", "RACE", "COUNTRY", "HEIGHT", "WEIGHT", "BMI"]

if 'attempt' not in st.session_state:
	st.session_state['attempt'] = False

if 'multi' not in st.session_state:
	st.session_state['multi'] = 1

def risk_stats(ds, dsref, cols, multi=1):
    stats = {}
    ref = dsref.groupby(cols).size().reset_index().rename(columns={0: 'equiv_class'})
    d = pd.merge(ds, ref, how='left')
    d['risk'] = 1 / d['equiv_class']

    stats['Records'] = len(ds)
    stats['Average Risk'] = round(d.risk.mean() * multi, 5)
    stats['Maximum Risk'] = round(d.risk.max() * multi, 5)
    stats['Unique Records'] = int(d[d.risk == 1].risk.count())
    stats['Proportion Unique'] = round(stats['Unique Records'] / len(ds), 6)

    return {' '.join(sorted(cols)): stats}


def variants(dict):
    d = []
    for i in range(1, 2**len(dict)):
        d.append([
            x for j, x in enumerate(dict)
            if bin(i)[2:].zfill(len(dict))[j] == '1'
        ])
    return d


def test_all(ds, ref, vars, multi):
    risks = {}
    for variant in variants(vars):
        risks.update(risk_stats(ds, ref, variant, multi))
    return risks

def below_threshold(s):
    return ['background-color: lightgreen']*len(s) if s['Average Risk']<=0.09 else ['background-color: none']*len(s)

st.title('Calculate Risk of Re-identification')

st.sidebar.subheader("Select:")
menu = st.sidebar.radio("", options=["Input file", "Columns", "Risk of Attempt", "Calculate"])

# st.write(" ")
# if st.session_state.file is not None:
#     st.sidebar.write("File: ", st.session_state.file.name)
# else:
#     st.sidebar.write("File:")
# st.sidebar.write("Columns: ", ", ".join(st.session_state.cols))
# st.sidebar.write("Attempt risk: ", str(st.session_state.multi))

if menu == "Input file":
    st.header("Select input file")    
    st.session_state.file = st.file_uploader("Upload a DM dataset",type=['sas7bdat'])
    
elif menu == "Columns":
    st.header("Select columns")
        
    if st.session_state.file is not None:
        df = pd.read_sas(st.session_state.file, format="sas7bdat", encoding='iso-8859-1').fillna("#empty#")
        cols = {}

        for col in df.columns:            
            cols[col] = st.checkbox(col,True if col in st.session_state.cols else False)
        st.session_state.cols = [k for k,v in cols.items() if v]

    else:
        st.write("No file selected")

elif menu == "Risk of Attempt":
    st.header("Risk of attempt")
    attempt_risk = 1

    col1, col2 = st.columns(2)
    
    col1.subheader("Consider risk of attempt?")

    consider_attempt = col1.radio("", options=["No", "Yes"], index=int(st.session_state.attempt=='Yes'), key="attempt")

    if consider_attempt == "Yes":
        with col2:
            st.subheader("Context:")
            att_dsa = st.radio("Data Sharing Agreement", options=["Yes", "No"], index=0)
            att_ong = st.radio("Ongoing Trial", options=["Yes", "No"], index=1)
            att_rar = st.radio("Rare Disease", options=["Yes", "No"], index=1)
            att_acc = st.radio("Access Control", options=["Direct", "Secure Transfer", "Sandbox"], index=1)
            att_rel = st.radio("Relationship with Requestor", options=["None", "Previous", "Partner"], index=1)

            if att_dsa == "Yes":
                attempt_risk *= 0.5

            if att_ong == "Yes":
                attempt_risk *= 2.5

            if att_rar == "Yes":
                attempt_risk *= 1.33

            if att_acc == "Secure Transfer":
                attempt_risk *= 0.8
            elif att_acc == "Sandbox":
                attempt_risk *= 0.5

            if att_rel == "Previous":
                attempt_risk *= 0.8
            elif att_rel == "Partner":
                attempt_risk *= 0.4

            attempt_risk = round(attempt_risk, 4)

    st.session_state.multi = attempt_risk

    st.write("Risk of Attempt multiplier: ", attempt_risk )
    

elif menu == "Calculate":

    results = st.empty()

    if st.session_state.file is not None and st.session_state.cols is not []:
        df = pd.read_sas(st.session_state.file, format="sas7bdat", encoding='iso-8859-1').fillna("#empty#")
        
        risks = test_all(df, df, st.session_state.cols, st.session_state.multi)

        rr = pd.DataFrame.from_dict(risks, orient='index').sort_values(['Average Risk'])

        rrs = rr.style.apply(below_threshold, axis=1)
        results.table(rrs)

        for col in st.session_state.cols:
            st.subheader(col)    
            bc = df.groupby([col]).size().rename('Count')
            st.bar_chart(bc)


