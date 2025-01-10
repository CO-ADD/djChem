import os
from pathlib import Path
import numpy as np
from django_rdkit.models import *
from django_rdkit.config import config
from django.conf import settings

from adjCHEM.constants import COMPOUND_SEP
import apputil.utils.data as djdata

# ==================================================================================
# Aggregation function
# ==================================================================================

# --------------------------------------------------------------------
def agg_Lst(x,sep=";"):
    return(djdata.join_lst(x,sep=sep))

# --------------------------------------------------------------------
def agg_DR(x):
    return(DR_Range(x))

# --------------------------------------------------------------------
def agg_Inhib(x):
    return(Value_Range(x,aggType='Mean',floatPrec=1))

#-----------------------------------------------------------------------------
# Summary Functions for Inhibition %
#-----------------------------------------------------------------------------
def Value_Range(lstValue,aggType='Mean',floatPrec=2,maxLst=10):
    npArr = np.array(lstValue)
    npArr = npArr[npArr != np.array(None)]
    df = {}
    if len(npArr) > 0:
        df['Min']    = f"{np.min(npArr):.{floatPrec}f}" 
        df['Max']    = f"{np.max(npArr):.{floatPrec}f}" 
        df['Median'] = f"{np.median(npArr):.{floatPrec}f}"
        df['Mean']   = f"{np.mean(npArr):.{floatPrec}f}"
        df['StDev']  = f"{np.std(npArr):.{floatPrec}f}"
        df['ValueList'] = djdata.limit_lst([round(x,floatPrec) for x in npArr],maxLst)
        df['StrList'] = "; ".join(f"{x:.{floatPrec}f}" for x in df['ValueList'])
        df['nValues'] = len(npArr)
        if len(npArr) == 1:
            if aggType == 'Mean':
                df['Range'] = df['Mean'] + " " + " (" + str(df['nValues']) + ")"
            else:
                df['Range'] = df['Median'] + " " + " (" + str(df['nValues']) + ")"
        elif len(npArr) == 2:
            df['Range'] = df['Min'] + "; " + df['Max'] + " (" + str(df['nValues']) + ")"
        else:
            if aggType == 'Mean':
                df['Range'] = df['Min'] + " [" + df['Mean'] + "] " + df['Max'] + " (" + str(df['nValues']) + ")"
            else:
                df['Range'] = df['Min'] + " [" + df['Median'] + "] " + df['Max'] + " (" + str(df['nValues']) + ")"
    else:
        df['Min'] = '-'
        df['Max'] = '-'
        df['Median'] ='-'
        df['Mean'] ='-'
        df['StDev'] = '-'
        df['StrList'] = '-'
        df['ValueList'] = []
        df['nValues'] = 0
        df['Range'] = '-'
    return(df)

#-----------------------------------------------------------------------------
# Summary Functions for Dose Response values - MIC CC50
#-----------------------------------------------------------------------------
def DR_Range(lstDR,maxLst=10):
    df = {}
    sortLst = DR2Sort_lst(lstDR)
    if len(sortLst) > 0:
        sortLst.sort()
        sortDR = Sort2DR_lst(sortLst)
        df['Min'] = sortDR[0]
        df['Max'] = sortDR[-1]
        df['Median'] =sortDR[(int((len(sortLst)-1)/2))]
        df['nDR'] = len(sortDR)
        df['nValues'] = len(sortDR)
        df['ValueList'] = djdata.limit_lst(sortDR,maxLst)
        df['DRList'] = "; ".join(df['ValueList'])

        if len(sortLst) == 1:
            df['Range'] = df['Median'] + " " + " (" + str(df['nDR']) + ")"
        elif len(sortLst) == 2:
            df['Range'] = df['Min'] + "; " + df['Max'] + " (" + str(df['nDR']) + ")"
        else:
            df['Range'] = df['Min'] + " [" + df['Median'] + "] " + df['Max'] + " (" + str(df['nDR']) + ")"
    else:
        df['Min'] = '-'
        df['Max'] = '-'
        df['Median'] ='-'
        df['nDR'] = 0
        df['nValues'] = 0
        df['ValueList'] = []
        df['Range'] = '-'
    return(df)

#-----------------------------------------------------------------------------
# Doseresponse Sorting Functions 
#-----------------------------------------------------------------------------
def DR2Sort(strDR,zLength=4):
    if strDR[0] == '>':
        s3 = 'Z'
        s2 = strDR[1:]
    elif strDR[:2] == '<=':
        s3 = 'M'
        s2 = strDR[2:]
    else:
        s3 = 'A'
        s2 = strDR
    if s2.find('.') != -1:
        s1 = '0'*(zLength-len(s2[:s2.find('.')]))
    else:
        s1 = '0'*(zLength-len(s2))
    return(s1+s2+s3)

# --------------------------------------------------------------------
def Sort2DR(strSort,zLength=4):
    pF ={'M':'<=','Z':'>','A':''}
    d1 = pF[strSort[-1]]
    s1 = strSort[:-1].lstrip('0')
    if s1[0] == '.':
        s1 = '0'+s1
    return(d1+s1)

# --------------------------------------------------------------------
def DR2Sort_lst(lstDR,zLength=4):
    lstSort = []
    for i in lstDR:
        try:
            if COMPOUND_SEP in i:
                v = djdata.split_StrList(i,sep=COMPOUND_SEP) #split_lst
                v[0] = DR2Sort(str(v[0]),zLength=zLength)
                lstSort.append(COMPOUND_SEP.join(v))
                # print("okDR2Sort_lst")
            else:
                lstSort.append(DR2Sort(str(i),zLength=zLength))
        except Exception as err:
            print(f"drerror: {err} with {i}")

    return(lstSort)

# --------------------------------------------------------------------
def Sort2DR_lst(lstSort,zLength=4):
    lstDR = []
    for i in lstSort:
        try:
            if COMPOUND_SEP in i:
                v = djdata.split_StrList(i,sep=COMPOUND_SEP) #split_lst
                v[0] = Sort2DR(v[0],zLength=zLength)
                lstDR.append(COMPOUND_SEP.join(v))
                # print("okSort2DR_lst")
            else:
                lstDR.append(Sort2DR(i,zLength=zLength))
        except Exception as err:
            print(f"sortrerror: {err} with {i}")
    return(lstDR)

#-----------------------------------------------------------------------------
# Doseresponse Formating Functions
#-----------------------------------------------------------------------------
def split_XC50(strDR):
    fval = 0
    sval = 0
    prefix = '-'
    if isinstance(strDR,str):
        # Separate dr-string -> prefix and sval
        if '>' in strDR:
            sval = strDR[1:]
            prefix = '>'
        elif '<=' in strDR:
            sval = strDR[2:]
            prefix = '<'
        elif '<' in strDR:
            sval = strDR[1:]
            prefix = '<'
        elif 'nf' in strDR:
            sval = 0
            prefix = 'x'
        else:
            sval = strDR
            prefix = '='
        
        # Separate mixture -> 1st val into fval
        if isinstance(sval,str):
            if COMPOUND_SEP in sval:
                lval = djdata.split_StrList(sval,sep=COMPOUND_SEP)
                fval = djdata.to_num(lval[0])
            else:
                fval = djdata.to_num(sval)
        else:
            fval = sval

    if isinstance(strDR,float) or isinstance(strDR,int) :
            sval = strDR
            fval = djdata.to_num(strDR)
            prefix = '='

    return(prefix,fval,sval)

# --------------------------------------------------------------------
def split_DR(strDR):
    if strDR[0] == '>':
        p = '>'
        v = djdata.to_num(strDR[1:])
    elif strDR[:2] == '<=':
        p = '<='
        v = djdata.to_num(strDR[2:])
    else:
        p = '='
        v = djdata.to_num(strDR)
    return(p,v)

# --------------------------------------------------------------------
def format_DR(p,v):
    if isinstance(v,str):
        strVal = v
    else:
        if int(v) == v:
            strVal = f"{v}"
        elif v > 1000:
                strVal = f"{v:.0f}"
        elif v > 100:
                strVal = f"{v:.1f}"
        elif v > 10:
                strVal = f"{v:.2f}"
        else:
            strVal = f"{v:.3f}"

    if p == 'X':
        strVal = 'nf'
    elif p == '<=' or p == '>':
        strVal = p + strVal
    return(strVal)
