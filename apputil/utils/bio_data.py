import os
from pathlib import Path
import math
import numpy as np
from django_rdkit.models import *
from django_rdkit.config import config
from django.conf import settings

from adjCHEM.constants import COMPOUND_SEP
import apputil.utils.data as djdata

import logging
logger = logging.getLogger(__name__)

#-----------------------------------------------------------------------------
# Scoring Functions
#-----------------------------------------------------------------------------
ActScoreDR_Cutoff = {
    'Invalid':  {'Score':-1,'Code':'-','Desc':'wrong Data'},
    'Inactive': {'Score':0, 'Code':'I','Desc':'>'},
    'Partial':  {'Score':1, 'Code':'P','Desc':'> & >= 50%'},
    'LowActive':{'Score':2, 'Code':'L','Desc':'= & >32'},
    'Active':   {'Score':3, 'Code':'A','Desc':'= <= & <= 32/20', 'CutOff':{'uM':20,'ug/mL':32,'pct':50}},
    'Hit':      {'Score':4, 'Code':'H','Desc':'= <= & <= 16/10', 'CutOff':{'uM':10,'ug/mL':16,'pct':20}},
    'SuperHit': {'Score':5, 'Code':'S','Desc':'= <= & <= 2/1',   'CutOff':{'uM':1,'ug/mL':2,'pct':10}}
}

ActScoreSC_Cutoff = {
    'Invalid':  {'Score':-1,'Code':'-','Desc':'wrong Data'},
    'Inactive': {'Score':0, 'Code':'I','Desc':'Inhib <50 '},
    'Partial':  {'Score':1, 'Code':'P','Desc':'Inhib >50 & ZScore >= 2.5', 'CutOff': {'Inhib':50, 'ZScore':2.5}},
    'Active':   {'Score':3, 'Code':'A','Desc':'Inhib >80 & ZScore >= 3.5', 'CutOff':{'Inhib':80, 'ZScore':3.5}},
    'Unknown':  {'Score':0, 'Code':'S','Desc':'> & >= 50%'},
}

#-----------------------------------------------------------------------------
def ActType_SC(Inhib,ZScore=None,cutoff_Inhib={'A':80,'P':50},cutoff_Zscore={'A':3.5,'P':2.5}):
#-----------------------------------------------------------------------------
    actType = 'Invalid'

    if isinstance(Inhib,str):
        Inhib = float(Inhib)

    if ZScore: # With ZSCore as per CO-ADD
        if isinstance(ZScore,str):
            ZScore = float(ZScore)
        actType = 'Inactive'
        if Inhib >= cutoff_Inhib['P'] and ZScore >= cutoff_Zscore['P']:
            actType = 'Partial'
        if Inhib >= cutoff_Inhib['A'] and ZScore >= cutoff_Zscore['A']:
            actType = 'Active'
        if Inhib >= cutoff_Inhib['A'] and ZScore < cutoff_Zscore['P']:
            actType = 'Unknown'

    else: # Without ZSCore as per DoseResponse
        actType = 'Inactive'
        if Inhib >= cutoff_Inhib['P']:
            actType = 'Partial'
        if Inhib >= cutoff_Inhib['A']:
            actType = 'Active'
        return(actType)
#-----------------------------------------------------------------------------
def ActScore_SC(Inhib,ZScore=None,cutoff_Inhib={'A':80,'P':50},cutoff_Zscore={'A':3.5,'P':2.5}):
#-----------------------------------------------------------------------------
    _t = ActType_SC(Inhib,ZScore=ZScore,cutoff_Inhib=cutoff_Inhib,cutoff_Zscore=cutoff_Zscore)
    return(ActScoreSC_Cutoff[_t]['Score'])

#-----------------------------------------------------------------------------
def ActType_DR(DR,DR_Unit,DMax=0, cutoffDR=ActScoreDR_Cutoff,cutoff_inhib=50):
#-----------------------------------------------------------------------------

    #print(f" {DR} {DR_Unit}")
    actType = 'Invalid'
    CmpdSep = '|'

    # Set initial values
    if DMax is None:
        DMax = 0
    prefix,val,_ = split_DR(DR)
    if CmpdSep in DR_Unit:
        _lst = list(DR_Unit.split(CmpdSep))
        _lst = list(map(str.strip, _lst))
        unit = _lst[0]
    else:
        unit = DR_Unit

    if (prefix == '=') or (prefix == '<'):
        actType = 'LowActive'
        if unit in cutoffDR['Active']['CutOff']:
            for a in ['Active','Hit','SuperHit']:
                if val <= cutoffDR[a]['CutOff'][unit]:
                    actType = a
    else:
        if DMax >= cutoff_inhib:
            actType = 'Partial'
        else:
            actType = 'Inactive'
    return(actType)

#-----------------------------------------------------------------------------
def ActScore_DR(DR,DR_Unit,DMax=0, cutoffDR=ActScoreDR_Cutoff,cutoff_inhib=50):
#-----------------------------------------------------------------------------
    _t = ActType_DR(DR,DR_Unit,DMax=DMax,cutoffDR=cutoffDR,cutoff_inhib=cutoff_inhib)
    return(cutoffDR[_t]['Score'])

#-----------------------------------------------------------------------------
# pScore -log DR
#-----------------------------------------------------------------------------
def pScore(DR,Unit,DMax,MW=0,gtShift=3,drMax2=40):
    prefix = '-'
    log_uM = 6
    prefix,val,_ = split_DR(DR)

    try:
        val = conv_Conc(val,Unit,'uM',MW)[0]
        if (prefix == '=') or (prefix == '<'):
            pScore = log_uM - math.log10(val)
        elif (prefix == '>'):
            if DMax is not None:
                if DMax >= drMax2:
                    gtShift = 2
            pScore = log_uM - math.log10(gtShift*val)
        else:
            pScore = 0
    except:
        pScore = -1
    return(round(pScore,2))

# ==================================================================================
# Converting concentration molar <-> g/mL
# ==================================================================================
def conv_Conc(conc,fromunit,tounit,mw=0):
    unitMolar = {'M':0, 'mM':-3, 'uM':-6, 'µM': -6, 'nM':-9,'pM':-12}
    unitGramLiter = {'mg/mL':0, 'ug/mL':-3, 'µg/mL':-3, 'ng/mL':-6, 'pg/mL':-9}

    mw = float(mw)

    if tounit in unitMolar:
        if fromunit in unitMolar:
            nconc = conc * 10**(unitMolar[fromunit]-unitMolar[tounit])
        elif fromunit in unitGramLiter:
            if mw > 0:
                nconc = 10**(unitGramLiter[fromunit]-unitMolar[tounit]) * conc / mw
            else:
                logger.error(f'Requires a molecular weight {mw:.2f}')
        else:
            logger.error(f'Wrong unit to convert from {fromunit}')

    elif tounit in unitGramLiter:
        if fromunit in unitGramLiter:
            nconc = conc * 10**(unitGramLiter[fromunit]-unitGramLiter[tounit])
        elif fromunit in unitMolar:
            if mw > 0:
                nconc = 10**(unitMolar[fromunit]-unitGramLiter[tounit]) * conc * mw
            else:
                logger.error(f'Requires a molecular weight {mw:.2f}')
        else:
            logger.error(f'Wrong unit to convert from {fromunit}')
    else:
        logger.error(f'Wrong unit to convert to {tounit}')
    return(nconc,tounit)


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
    return(SC_Range(x,aggType='Mean',floatPrec=1))

#-----------------------------------------------------------------------------
# Summary Functions for Inhibition %
#-----------------------------------------------------------------------------
def SC_Range(lstValue,aggType='Mean',floatPrec=2,maxLst=10):
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
def split_DR(strDR):
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
