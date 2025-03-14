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
logName = "Upload_Assay_Xlsx"
logFileName = os.path.join("log",f"x{logName}_{logTime:%Y%m%d_%H%M%S}.log")
logLevel = logging.INFO 

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="[%(name)-20s] %(message)s ",
#    handlers=[logging.FileHandler(logFileName,mode='w'),logging.StreamHandler()],
    handlers=[logging.StreamHandler()],
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

    logger.info(f"Python         : {sys.version.split('|')[0]}")
    logger.info(f"Conda Env      : {os.environ['CONDA_DEFAULT_ENV']}")
    #logger.info(f"LogFile        : {logFileName}")

    logger.info(f"Django         : {django.__version__}")
    logger.info(f"Django Folder  : {djDir['djPrj']}")
    logger.info(f"Django Data    : {djDir['dataDir']}")
    logger.info(f"Django Project : {os.environ['DJANGO_SETTINGS_MODULE']}")

    from dcoadd.models import Project, Source, Chem_Structure, Compound
    from apputil.utils.set_data import set_Dictionaries,set_dictFields

    # ---------------------------------------------------------------------
    if prgArgs.table == 'Compound':

        OutFile = "UploadCompound_Issues.xlsx"

        logger.info(f"[Upd_djCOADD] Table: {prgArgs.table}") 
        logger.info(f"[Upd_djCOADD] User:  {prgArgs.appuser}") 

        cmpSQL = """
                Select c.compound_id, c.compound_code, compound_name, compound_type,
                    project_id, b.structure_id,
                    std_status,  std_smiles, std_nfrag, std_salt, std_ion, std_solvent, std_metal, std_structure_type,
                    pub_status, pub_date
                From  dsample.coadd_compound c
                    Left Join dsample.cmpbatch b on c.compound_id = b.cmpbatch_id 
                """
    
        qryPrj = Project.objects.all().values('project_id')

        nEntries = qryPrj.count()
        logger.info(f" [{prgArgs.table}] Projects: {nEntries}")

        OutNumbers = {'Processed':0,'New Entry':0, 'Upload Entries':0,'Empty Entries':0}
        OutDict = []

        cpyFields = ['compound_code', 'compound_name',
                     'std_status', 'std_smiles','std_nfrag','std_salt','std_salt','std_solvent','std_metal','std_structure_type',
                     'pub_date'
                     ]
        dictFields = ['compound_type','pub_status']
        replaceValues = {'pub_status':{'Portal':'Reported','Processed':'MissingData'},
    }

        # -----------------------------------------
        pgDB = openCoaddDB(verbose=0)
        for e in tqdm(qryPrj, total= nEntries, desc=prgArgs.table):

            pid = e['project_id']
            qrySQL = cmpSQL + f" Where c.project_id = '{pid}' "
            df = pd.DataFrame(pgDB.get_dict_list(qrySQL))

            if len(df)>0:
                for k in replaceValues:
                    df[k].replace(replaceValues[k],inplace=True)

                for idx,row in df.iterrows():
                    NewEntry = False
                    #print(f" {row}")
                    djObj = Compound.get(row['compound_id'])
                    if djObj is None:
                        NewEntry = True
                        djObj = Compound()
                        djObj.compound_id = row['compound_id']
                    djObj.project_id = Project.get(pid)
                    djObj.source_id = Source.get('CO-ADD')
                    djObj.structure_id = Chem_Structure.get(row['structure_id'])
                    #djObj.coadd_id = row['structure_id']

                    set_dictFields(djObj,row,cpyFields)

                    set_Dictionaries(djObj,row,dictFields)

                    validStatus = True
                    djObj.init_fields()
                    validDict = djObj.validate_fields()
                    if validDict:
                        validStatus = False
                        row.update(validDict)
                        logger.warning(f"{djObj.structure_id} {validDict} ")
                        OutDict.append(row)

                    if validStatus:
                        if prgArgs.upload:
                            if NewEntry or prgArgs.overwrite:
                                #print(f" {djObj.project_id}")
                                OutNumbers['Upload Entries'] += 1
                                djObj.save(user=prgArgs.appuser)


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
        print("-------------------------------------------------------------------")

#==============================================================================