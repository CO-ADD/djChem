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

from pgChemDB_Utils import (openChemDB, get_SingleConc_byStructure, get_SingleConc_byCompound,
                            get_DoseResponse_byStructure, get_DoseResponse_byCompound,
                            apply_sc_gnmemb, apply_dr_gnmemb)
#import django

ProgName = "getCombinedDataset"

# Logger ----------------------------------------------------------------
import logging
logTime= datetime.datetime.now()
logFileName = os.path.join("log",f"x{ProgName}_{logTime:%Y%m%d_%H%M%S}.log")

logging.basicConfig(
    format="[%(name)-20s] %(message)s ",
#    handlers=[logging.FileHandler(logFileName,mode='w'),logging.StreamHandler()],
    handlers=[logging.StreamHandler()],
    level=logging.INFO )
logger = logging.getLogger(__name__)

#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
def main(prgArgs):

    logger.info(f"Python         : {sys.version.split('|')[0]}")
    logger.info(f"Conda Env      : {os.environ['CONDA_DEFAULT_ENV']}")
    logger.info(f"LogFile        : {logFileName}")

    # if prgArgs.outdir is None:
    #     PubDir = 'C:/Data/COADD/DataSet'
    # else:
    #     PubDir = prgArgs.outdir
    # if not os.path.exists(PubDir):
    #     os.makedirs(PubDir)

    # ---------------------------------------------------------------------
    if prgArgs.dataset in ['Public','Current']:

        BaseName = f'COADD_{prgArgs.dataset}'

        IndexCol = 'structure_id'
        ColumnsCol = 'sum_assay_code'

        # SC Data ----------------------------------------------------------------------------------------
        dfSC = get_SingleConc_byStructure(DataSet=prgArgs.dataset,test=int(prgArgs.test))
        SC_AssayCodes = list(dfSC[ColumnsCol].unique())

        logger.info(f'[SumData by Structure] SC Pivot ')
        pivSCF    = dfSC.pivot_table(index=IndexCol,columns=ColumnsCol,values=['inhibition_ave','act_score'], aggfunc='max' )
        logger.info(f'[SumData by Structure] SC Pivot --> {len(pivSCF)}')
        _colnames = []
        for col_idx in pivSCF.columns.to_flat_index():
            if 'act_score' in col_idx:
                _colnames.append(f"{col_idx[1]}_sc_act")
            elif 'inhibition_ave' in col_idx:
                _colnames.append(f"{col_idx[1]}_sc_inh")
            else:
                _colnames.append(f"{col_idx[1]}_sc_xx")
        pivSCF.columns = _colnames

        # DR Data ----------------------------------------------------------------------------------------
        dfDR = get_DoseResponse_byStructure(DataSet=prgArgs.dataset,test=int(prgArgs.test))
        DR_AssayCodes = list(dfDR[ColumnsCol].unique())

        logger.info(f'[SumData by Structure] DR Pivot ')
        pivDRF = dfDR.pivot_table(index=IndexCol,columns=ColumnsCol,values=['inhibit_max_ave','act_score','pscore'], aggfunc='max' )
        pivDRS = dfDR.pivot_table(index=IndexCol,columns=ColumnsCol,values=['result_std_geomean'], aggfunc=lambda x: x[0] )
        logger.info(f'[SumData by Structure] DR Pivot --> {len(pivDRF)}')
        
        _colnames = []
        for col_idx in pivDRF.columns.to_flat_index():
            if 'act_score' in col_idx:
                _colnames.append(f"{col_idx[1]}_dr_act")
            elif 'inhibit_max_ave' in col_idx:
                _colnames.append(f"{col_idx[1]}_dr_inh")
            elif 'pscore' in col_idx:
                _colnames.append(f"{col_idx[1]}_dr_psc")
            else:
                _colnames.append(f"{col_idx[1]}_dr_xx")
        pivDRF.columns = _colnames

        logger.info(f'[SumData by Structure] DR Add GN-Memb ')
        pivDRF = pivDRF.apply(apply_sc_gnmemb,axis=1)

        _colnames = []
        for col_idx in pivDRS.columns.to_flat_index():
            if 'result_std_geomean' in col_idx:
                _colnames.append(f"{col_idx[1]}_dr_res")
            else:
                _colnames.append(f"{col_idx[1]}_dr_xx")
        pivDRS.columns = _colnames

        # Merge PivTable ----------------------------------------------------------------------------------------
        logger.info(f'[SumData by Structure] Merge Pivot ')
        pivStruct = pd.merge(left=pivSCF, right=pivDRF, how= 'outer', on='structure_id')
        pivStruct = pd.merge(left=pivStruct, right=pivDRS, how= 'outer', on='structure_id')

        # Add Properties  ----------------------------------------------------------------------------------------
        

        # Output ----------------------------------------------------------------------------------------
        pivStruct = pivStruct.reindex(sorted(pivStruct.columns), axis=1) 

        logger.info(f'[SumData by Structure] SC: {len(pivSCF)} + DR: {len(pivDRF)} --> {len(pivStruct)}')
        csvFile = os.path.join(f'{BaseName}_byStructure.csv.gz')
        logger.info(f'[SumData by Structure] --> {csvFile}')
        pivStruct.to_csv(csvFile,compression='gzip')

        xlsFile = os.path.join(f'{BaseName}_byStructure.xlsx')
        logger.info(f'[SumData by Structure] --> {xlsFile}')
        with pd.ExcelWriter(xlsFile) as writer:
           pivStruct.to_excel(writer, sheet_name='Structures')

#==============================================================================
if __name__ == "__main__":

    print("-------------------------------------------------------------------")
    print("Running : ",sys.argv)
    print("-------------------------------------------------------------------")


    # ArgParser -------------------------------------------------------------
    prgParser = configargparse.ArgumentParser(prog='upload_Django_Data', 
                                description="Uploading data to adjCOADD from Oracle/Excel/CSV")
    prgParser.add_argument("-c","--dataset", default='Public',required=True, dest="dataset", action='store', help="Dataset")
    prgParser.add_argument("-o","--outdir",default=None,required=False, dest="outdir", action='store', help="Output Directory or Folder")
#    prgParser.add_argument("--upload",default=False,required=False, dest="upload", action='store_true', help="Upload data to dj Database")
#    prgParser.add_argument("--overwrite",default=False,required=False, dest="overwrite", action='store_true', help="Overwrite existing data")
#    prgParser.add_argument("--user",default='J.Zuegg',required=False, dest="appuser", action='store', help="AppUser to Upload data")
    prgParser.add_argument("--test",default=0,required=False, dest="test", action='store', help="Number of entries to test")
#    prgParser.add_argument("--new",default=False,required=False, dest="new", action='store_true', help="Not migrated entries only")

#    prgParser.add_argument("-d","--directory",default=None,required=False, dest="directory", action='store', help="Directory or Folder to parse")
#    prgParser.add_argument("--plate",default=None,required=False, dest="plateid", action='store', help="Single File to parse")
#    prgParser.add_argument("--db",default='Local',required=False, dest="database", action='store', help="Database [Local/Work/WorkLinux]")
#    prgParser.add_argument("-r","--runid",default=None,required=False, dest="runid", action='store', help="Antibiogram RunID")

    # prgParser.add_argument("--django",default='Local',required=False, dest="django", action='store', help="Django configuration [Meran/Laptop/Work]")
    # prgParser.add_argument("-c","--config",type=Path,is_config_file=True,help="Path to a configuration file ",)

    prgArgs = prgParser.parse_args()

    if prgArgs:
        main(prgArgs)
        logger.info("-------------------------------------------------------------------")

#==============================================================================