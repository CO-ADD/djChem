#
import pandas as pd
import logging
logger = logging.getLogger(__name__)

from apputil.utils.data import strList_to_List
from apputil.models import Dictionary
#

# dictList = ['project_name','project_comment',
#             ...
#             ]
# arrDict = {'screen_status': 'screen_status',                  # strList->List
#             'ora_contact_ids':['CONTACT_A_ID','CONTACT_B_ID'] # append.List
#            }
# dictFields = ['project_type','provided_container','stock_conc_unit',] # using Choice_Dictionary


#------------------------------------------------------------------------------------
def set_fkeyFields(djModel,rowDict, arrDict):
    valid = True
    for f in arrDict:
        if f in rowDict:
            _obj = arrDict[f].get(rowDict[f])
            if _obj is not None:
                setattr(djModel,f,_obj)
            else:
                valid = False
    return valid           
#------------------------------------------------------------------------------------
def set_arrayFields(djModel,rowDict, arrDict):
    for f in arrDict:
        #print("arrFields",f)
        if isinstance(arrDict[f],str):
            if pd.notnull(rowDict[arrDict[f]]):
                setattr(djModel,f,strList_to_List(str(rowDict[arrDict[f]])) )
                
        elif isinstance(arrDict[f],list):
            _list = []
            for l in arrDict[f]:
                if pd.notnull(rowDict[l]):
                    _list.append(rowDict[l])
            setattr(djModel,f,_list)
        
#------------------------------------------------------------------------------------
def set_dictFields(djModel,rowDict,dictList):
    for e in dictList:
        if e in rowDict:
            if pd.notnull(rowDict[e]):
                setattr(djModel,e,rowDict[e])

#------------------------------------------------------------------------------------
def set_Dictionaries(djModel,rowDict,dictFields):
    for d in dictFields:
        if d in rowDict:
            if pd.notnull(rowDict[d]):
                if d in djModel.Choice_Dictionary:
                    setattr(djModel,d,Dictionary.get(djModel.Choice_Dictionary[d],rowDict[d]))

#------------------------------------------------------------------------------------
def set_arrayDictionaries(djModel,rowDict,arrDict):
    for f in arrDict:
        _dict_list = []
        _ret_list  = []
        if isinstance(arrDict[f],str):
            if pd.notnull(rowDict[arrDict[f]]):
                if f in djModel.Choice_Dictionary:
                    _dict_list = strList_to_List(rowDict[arrDict[f]])
                
        elif isinstance(arrDict[f],list):
            for l in arrDict[f]:
                if pd.notnull(rowDict[l]):
                    _dict_list.append(rowDict[l])
        
        for l in _dict_list:
            _d = Dictionary.get(djModel.Choice_Dictionary[f],l)
            if _d:
                _ret_list.append(str(_d))
            
        if len(_ret_list)>0:
            setattr(djModel,f,_ret_list)


# if upload:
#    if overwrite:
#       save
#    elif newentry:
#       save

#------------------------------------------------------------------------------------
def set_Fields_fromDict(djModel,row,FieldList=[], ArrayDict={}, DictList=[],valLog=None):
    validStatus = True

    if len(FieldList)>0:
        set_dictFields(djModel,row,FieldList)
    if len(ArrayDict)>0:
        set_arrayFields(djModel,row,ArrayDict)     
    if len(DictList)>0:
        set_Dictionaries(djModel,row,DictList)
        
    djModel.clean_Fields()
    validDict = djModel.validate()
    if validDict:
        validStatus = False
        for k in validDict:
            if valLog:    
                valLog.add_log('Warning','',k,validDict[k],'-')
            else: 
                logger.warning(f"{k} - {validDict[k]}")
    return(validStatus)
