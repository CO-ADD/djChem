#
import os, sys
import datetime
import csv
import pandas as pd
import numpy as np
import configargparse
from functools import reduce
from pathlib import Path

from tqdm import tqdm

from zSql import zSqlConnector

import django

# Logger ----------------------------------------------------------------
import logging
logTime= datetime.datetime.now()
logName = "Upload_ActCmpDR"
logFileName = os.path.join("log",f"x{logName}_{logTime:%Y%m%d_%H%M%S}.log")
logLevel = logging.INFO 

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="[%(name)-20s] %(message)s ",
    handlers=[logging.FileHandler(logFileName,mode='w'),logging.StreamHandler()],
#    handlers=[logging.StreamHandler()],
    level=logLevel)

#-----------------------------------------------------------------------------

def openCoaddDB(User='coadd', Passwd='MtMaroon23',DataBase="coadd",verbose=1):
    dbPG = zSqlConnector.PostgreSQL()
    dbPG.open(User,Passwd,"imb-coadd-db.imb.uq.edu.au",DataBase,verbose=verbose)
    return(dbPG)

#-----------------------------------------------------------------------------
def main(prgArgs,djDir):

    sys.path.append(djDir['djPrj'])
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "adjCHEM.settings")
    django.setup()

    logging.getLogger().addHandler(logging.FileHandler(logFileName,mode='w'))
    logger.info(f"Python         : {sys.version.split('|')[0]}")
    logger.info(f"Conda Env      : {os.environ['CONDA_DEFAULT_ENV']}")
    logger.info(f"LogFile        : {logFileName}")

    logger.info(f"Django         : {django.__version__}")
    logger.info(f"Django Folder  : {djDir['djPrj']}")
    logger.info(f"Django Data    : {djDir['dataDir']}")
    logger.info(f"Django Project : {os.environ['DJANGO_SETTINGS_MODULE']}")

    from dcoadd.models import (Project, Source, Chem_Structure, Compound, Assay,
                               Activity_Compound_DoseResponse)
    from apputil.utils.set_data import set_Dictionaries,set_dictFields
    from apputil.utils.bio_data import split_DR

    # ---------------------------------------------------------------------
    if prgArgs.table == 'ActCompoundDR':

        OutFile = f"Upload_{prgArgs.table}_Issues.xlsx"

        logger.info(f"[Upd_djCOADD] Table: {prgArgs.table}") 
        logger.info(f"[Upd_djCOADD] User:  {prgArgs.appuser}") 

        if int(prgArgs.test)>0:
            qryCmp = Compound.objects.all().values('compound_id')[:int(prgArgs.test)]
        else:    
            qryCmp = Compound.objects.all().values('compound_id')

        nEntries = qryCmp.count()
        logger.info(f" [{prgArgs.table}] Compounds: {nEntries}")

        entrySQL = """
                Select dr.cmpbatch_id, dr.sum_assay_id,
                    dr.n_assays, dr.n_actives, dr.act_types,  dr.act_score, dr.pscore,
                    dr.inhibit_max_ave,
                    dr.drval_type result_type, dr.drval_unit result_unit,
                    dr.drval_max result_max, dr.drval_min result_min, dr.drval_median result_median, dr.drval_unit result_unit,
                    dr.drval_std_geomean result_std_geomean, dr.drval_std_unit result_std_unit
                From  dsummary.sum_cmpbatch_dr dr
                """
        cpyFields = ['n_assays', 'n_actives','act_types', 'act_score','pscore','inhibit_max_ave',
                     'result_max', 'result_min', 'result_median',
                     'result_std_geomean',
                     'pub_date'
                ]
        dictFields = ['pub_status','result_unit','result_std_unit','result_type' ]

        SourceName = 'CO-ADD'
        djSource = Source.get(None,SourceName)

        if djSource is None:
            logger.error(f" Source {SourceName} not Found")

        else:
            OutNumbers = {'Processed':0, 'Empty':0, 'Failed':0, 'New':0, 'Uploaded':0,}
            OutDict = []

            pgDB = openCoaddDB(verbose=0)
            for e in tqdm(qryCmp, total= nEntries, desc=prgArgs.table):
                cid = e['compound_id']
                qrySQL = entrySQL + f" Where dr.cmpbatch_id = '{cid}' and dr.n_cmpbatches = 1 "
                df = pd.DataFrame(pgDB.get_dict_list(qrySQL))

                for idx,row in df.iterrows():
                    #print(row)
                    validStatus = True
                    NewEntry = False
                    djAssay = Assay.get(None,SourceName,row['sum_assay_id'])
                    djCompound = Compound.get(row['cmpbatch_id'])

                    if djAssay and djCompound and djSource: 
                        
                        djObj = Activity_Compound_DoseResponse.get(djCompound,djAssay,djSource)
                        if djObj is None:
                            NewEntry = True
                            djObj = Activity_Compound_DoseResponse()
                            djObj.compound_id  = djCompound
                            djObj.assay_id  = djAssay
                            djObj.source_id = djSource

                        set_dictFields(djObj,row,cpyFields)
                        set_Dictionaries(djObj,row,dictFields)

                        djObj.result_prefix, djObj.result_value,_ = split_DR(djObj.result_median)
                        djObj.set_actscores()

                        validStatus = True
                        djObj.init_fields()                        
                        validDict = djObj.validate_fields()
                        if validDict:
                            validStatus = False
                            OutNumbers['Failed'] += 1
                            row.update(validDict)
                            logger.warning(f"{djObj.compound_id} {validDict} ")
                            OutDict.append(row)

                        if validStatus:
                            if prgArgs.upload:
                                if NewEntry or prgArgs.overwrite:
                                    #print(f" {djObj.project_id}")
                                    OutNumbers['Uploaded'] += 1
                                    djObj.save(user=prgArgs.appuser)

                    else:
                        OutNumbers['Failed'] += 1
                        if djAssay is None:
                            row["Warning"] = f" Assay {row['sum_assay_id']} not Found in {SourceName}"
                            #logger.warning(f" {sid} Assay {row['sum_assay_id']} not Found in {SourceName}")
                        if djCompound is None:
                            row["Error"] = f" Compound  {cid} not Found"
                            logger.error(f" {cid} Compound not Found")
                        OutDict.append(row)

                OutNumbers['Processed'] += len(df)

        pgDB.close()
        if len(OutDict) > 0:
            logger.info(f"Writing Issues: {OutFile}")
            outDF = pd.DataFrame(OutDict)
            outDF.to_excel(OutFile)
        else:
            logger.info(f"No Issues")

        logger.info(f"{OutNumbers}")

#==============================================================================
if __name__ == "__main__":

    print("-------------------------------------------------------------------")
    print("Running : ",sys.argv)
    print("-------------------------------------------------------------------")


    # ArgParser -------------------------------------------------------------
    prgParser = configargparse.ArgumentParser(prog='upload_Django_Data', 
                                description="Uploading data to adjCOADD from Oracle/Excel/CSV")
    prgParser.add_argument("-t",default=None,required=False, dest="table", action='store', help="Table to upload [CompoundID]")
    prgParser.add_argument("--upload",default=False,required=False, dest="upload", action='store_true', help="Upload data to dj Database")
    prgParser.add_argument("--overwrite",default=False,required=False, dest="overwrite", action='store_true', help="Overwrite existing data")
    prgParser.add_argument("--user",default='J.Zuegg',required=False, dest="appuser", action='store', help="AppUser to Upload data")
    prgParser.add_argument("--test",default=0,required=False, dest="test", action='store', help="Number of entries to test")
    prgParser.add_argument("--new",default=False,required=False, dest="new", action='store_true', help="Not migrated entries only")

#    prgParser.add_argument("-d","--directory",default=None,required=False, dest="directory", action='store', help="Directory or Folder to parse")
    prgParser.add_argument("--plate",default=None,required=False, dest="plateid", action='store', help="Single File to parse")
#    prgParser.add_argument("--db",default='Local',required=False, dest="database", action='store', help="Database [Local/Work/WorkLinux]")
#    prgParser.add_argument("-r","--runid",default=None,required=False, dest="runid", action='store', help="Antibiogram RunID")

    prgParser.add_argument("--django",default='Local',required=False, dest="django", action='store', help="Django configuration [Meran/Laptop/Work]")
    prgParser.add_argument("-c","--config",type=Path,is_config_file=True,help="Path to a configuration file ",)

    prgArgs = prgParser.parse_args()

    # Django -------------------------------------------------------------
    djDir = {}
    if prgArgs.django == 'Meran':
        djDir['djPrj'] = "D:/Code/zdjCode/djCHEM"
    #   uploadDir = "C:/Code/A02_WorkDB/03_Django/adjCOADD/utilities/upload_data/Data"
    #   orgdbDir = "C:/Users/uqjzuegg/The University of Queensland/IMB CO-ADD - OrgDB"
    elif prgArgs.django == 'Work':
        djDir['djPrj'] = "/home/uqjzuegg/xhome/Code/zdjCode/djChem"
        djDir['dataDir'] = "/home/uqjzuegg/xhome/Code/zdjCode/djChem/dcoadd/data"
    #     uploadDir = "C:/Data/A02_WorkDB/03_Django/adjCOADD/utilities/upload_data/Data"
    elif prgArgs.django == 'Laptop':
        djDir['djPrj'] = "C:/Code/zdjCode/djCHEM"
        djDir['dataDir'] = "C:/Code/zdjCode/djCHEM/dcoadd/data"

    if djDir:
        main(prgArgs,djDir)
        logger.info("-------------------------------------------------------------------")

#==============================================================================