#
#
import os, sys
import datetime
import csv
import pandas as pd
import numpy as np
import configargparse
from pathlib import Path

from tqdm import tqdm
# from zUtils import zData

import django

# Logger ----------------------------------------------------------------
import logging
logTime= datetime.datetime.now()
logName = "Update_ActScore"
logFileName = os.path.join("log",f"x{logName}_{logTime:%Y%m%d_%H%M%S}.log")
logLevel = logging.INFO 

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="[%(name)-20s] %(message)s ",
    handlers=[logging.FileHandler(logFileName,mode='w'),logging.StreamHandler()],
#    handlers=[logging.StreamHandler()],
    level=logLevel)

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

    from dcoadd.models import (Project, Source, Chem_Structure, Compound, Assay,
                               Activity_Structure_DoseResponse, Activity_Structure_Inhibition)
    from apputil.utils.set_data import set_Dictionaries,set_dictFields
    from apputil.utils.bio_data import ActScore_DR, ActScore_SC


    # ----------------------------------------------------------------------------------------
    if 'Structure' in prgArgs.table :
        qryStr = Activity_Structure_DoseResponse.objects.all()
        nEntries = qryStr.count()
        logger.info(f" [{prgArgs.table}] Structures: {nEntries}")

        OutNumbers = {'Processed':0, 'Empty':0, 'Failed':0, 'New':0, 'Uploaded':0,}
        for djObj in tqdm(qryStr, desc='[ActStructDR]'):
            OutNumbers['Processed'] += 1

            djObj.set_actscores()

            validStatus = True
            validDict = djObj.validate_fields()
            if validDict:
                validStatus = False
                OutNumbers['Failed'] += 1
                logger.warning(f"{djObj} {validDict} ")

            if validStatus:
                if prgArgs.upload:
                    OutNumbers['Uploaded'] += 1
                    djObj.save(user=prgArgs.appuser)




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