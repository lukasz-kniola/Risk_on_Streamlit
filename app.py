import streamlit as st
import requests, json, io
import pandas as pd
import numpy as np

st.set_page_config(layout='wide')

def risk_stats(ds, dsref, cols):
    stats = {}
    ref = dsref.groupby(cols).size().reset_index().rename(columns={0: 'equiv_class'})
    d = pd.merge(ds, ref, how='left')
    d['risk'] = 1 / d['equiv_class']

    stats['Records'] = len(ds)
    stats['Average Risk'] = round(d.risk.mean(), 5)
    stats['Maximum Risk'] = round(d.risk.max(), 5)
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


def test_all(ds, ref, vars):
    risks = {}
    for variant in variants(vars):
        risks.update(risk_stats(ds, ref, variant))
    return risks

st.title('Calculate Risk of Re-identification')

st.header("Risk of attempt")

att_dsa = st.radio("Data Sharing Agreement", options=["Yes", "No"], index=0)
att_ong = st.radio("Ongoing Trial", options=["Yes", "No"], index=1)
att_rar = st.radio("Rare Disease", options=["Yes", "No"], index=1)
att_acc = st.radio("Access Control", options=["Direct", "Secure Transfer", "Sandbox"], index=1)
att_rel = st.radio("Relationship with Requestor", options=["None", "Previous", "Partner"], index=1)

attempt_risk = 1
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

st.write("Risk of Attempt multiplier: ", attempt_risk )

results = st.empty()

file = st.sidebar.file_uploader("Upload a DM dataset",type=['sas7bdat'])

if file is not None:
    dm = pd.read_sas(file, format="sas7bdat", encoding='iso-8859-1').fillna("#empty#")

    st.sidebar.subheader("Columns:") 
    
    cols = {}
    for col in dm.columns:
        cols[col] = st.sidebar.checkbox(col,True if col in ["SITEID", "SEX", "AGE", "RACE", "COUNTRY", "HEIGHT", "WEIGHT", "BMI"] else False)
    selectedCols = [k for k,v in cols.items() if v]

    if selectedCols != []:
        if st.button("Calculate"):
        
            risks = test_all(dm, dm, selectedCols)

            rr = pd.DataFrame.from_dict(risks, orient='index')
            rr.sort_values(['Average Risk'])

            results.table(rr)

            for col in selectedCols:
                st.subheader(col)    
                bc = dm.groupby([col]).size().rename('Count')
                st.bar_chart(bc)


