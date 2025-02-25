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

    # ---------------------------------------------------------------------
    if prgArgs.dataset in ['Public','Reported','Current'] and prgArgs.index in ['Structure','Compound']:

        if prgArgs.dataset in ['Public','Reported']:
            BaseName = f'COADD_{prgArgs.dataset}2024_{logTime:%Y%m%d}'
        elif prgArgs.dataset == 'Current':
            BaseName = f'COADD_{prgArgs.dataset}_{logTime:%Y%m%d}'
        else:
            BaseName = f'COADD_{logTime:%Y%m%d%H%M}'

        if prgArgs.outdir:
            if not os.path.exists(prgArgs.outdir):
                os.makedirs(prgArgs.outdir)
            BaseName = os.path.join(prgArgs.outdir,BaseName)

        logger.info(f"[SumData by {prgArgs.index}] Getting Data ")
        if prgArgs.index == 'Structure':
            IndexCol = 'structure_id'
            dfSC = get_SingleConc_byStructure(DataSet=prgArgs.dataset,test=int(prgArgs.test))
            dfDR = get_DoseResponse_byStructure(DataSet=prgArgs.dataset,test=int(prgArgs.test))

        elif prgArgs.index == 'Compound':
            IndexCol = 'compound_id'
            dfSC = get_SingleConc_byCompound(DataSet=prgArgs.dataset,test=int(prgArgs.test))
            dfDR = get_DoseResponse_byCompound(DataSet=prgArgs.dataset,test=int(prgArgs.test))
        else:
            IndexCol = None

        ColumnsCol = 'sum_assay_code'

        # SC Data ----------------------------------------------------------------------------------------
        SC_AssayCodes = list(dfSC[ColumnsCol].unique())

        logger.info(f"[SumData by {prgArgs.index}] SC Pivot ")
        pivSCF    = dfSC.pivot_table(index=IndexCol,columns=ColumnsCol,values=['inhibition_ave','act_score'], aggfunc='max' )
        logger.info(f"[SumData by {prgArgs.index}] SC Pivot --> {len(pivSCF):_}")
        _colnames = []
        for col_idx in pivSCF.columns.to_flat_index():
            if 'act_score' in col_idx:
                _colnames.append(f"{col_idx[1]}_sc_act")
            elif 'inhibition_ave' in col_idx:
                _colnames.append(f"{col_idx[1]}_sc_inhib")
            else:
                _colnames.append(f"{col_idx[1]}_sc_xx")
        pivSCF.columns = _colnames

        # DR Data ----------------------------------------------------------------------------------------
        DR_AssayCodes = list(dfDR[ColumnsCol].unique())

        logger.info(f'[SumData by {prgArgs.index}] DR Pivot ')
        pivDRF = dfDR.pivot_table(index=IndexCol,columns=ColumnsCol,values=['inhibit_max_ave','act_score','pscore'], aggfunc='max' )
        pivDRS = dfDR.pivot_table(index=IndexCol,columns=ColumnsCol,values=['result_std_geomean'], aggfunc=lambda x: x.iloc[0] )
        logger.info(f"[SumData by {prgArgs.index}] DR Pivot --> {len(pivDRF):_}")
        
        _colnames = []
        for col_idx in pivDRF.columns.to_flat_index():
            if 'act_score' in col_idx:
                _colnames.append(f"{col_idx[1]}_dr_act")
            elif 'inhibit_max_ave' in col_idx:
                _colnames.append(f"{col_idx[1]}_dr_inhib")
            elif 'pscore' in col_idx:
                _colnames.append(f"{col_idx[1]}_dr_pscore")
            else:
                _colnames.append(f"{col_idx[1]}_dr_xx")
        pivDRF.columns = _colnames

        _colnames = []
        for col_idx in pivDRS.columns.to_flat_index():
            if 'result_std_geomean' in col_idx:
                _colnames.append(f"{col_idx[1]}_dr_result")
            else:
                _colnames.append(f"{col_idx[1]}_dr_xx")
        pivDRS.columns = _colnames

        # Merge PivTable ----------------------------------------------------------------------------------------
        logger.info(f"[SumData by {prgArgs.index}] Merge Pivot ")
        pivData = pd.merge(left=pivSCF, right=pivDRF, how= 'outer', on=IndexCol)
        pivData = pd.merge(left=pivData, right=pivDRS, how= 'outer', on=IndexCol)

        # Add Properties  ----------------------------------------------------------------------------------------
        logger.info(f"[SumData by {prgArgs.index}] Columns: {list(pivData.columns)}")
        logger.info(f"[SumData by {prgArgs.index}] SC Add GN-Memb ")
        pivData = pivData.apply(apply_sc_gnmemb,axis=1)
        logger.info(f"[SumData by {prgArgs.index}] DR Add GN-Memb ")
        pivData = pivData.apply(apply_dr_gnmemb,axis=1)
        
        # Output ----------------------------------------------------------------------------------------
        pivData = pivData.reindex(sorted(pivData.columns), axis=1) 

        logger.info(f"[SumData by {prgArgs.index}] SC: {len(pivSCF):_} + DR: {len(pivDRF):_} --> {len(pivData):_}")
        logger.info(f"[SumData by {prgArgs.index}] Columns: {list(pivData.columns)}")
        csvFile = os.path.join(f"{BaseName}_Merged_by{prgArgs.index}.csv.gz")
        logger.info(f"[SumData by {prgArgs.index}] --> {csvFile}")
        pivData.to_csv(csvFile,compression='gzip')

        # xlsFile = os.path.join(f"{BaseName}_by{prgArgs.index}.xlsx")
        # logger.info(f"[SumData by {prgArgs.index}] --> {xlsFile}")
        # with pd.ExcelWriter(xlsFile) as writer:
        #    pivData.to_excel(writer, sheet_name={prgArgs.index})

        # if prgArgs.dataset == 'Current' and prgArgs.upload:
        #     for idx, row in tqdm(pivData.iterrows(), total=len(pivData), desc = 'Upload pivData'):
        #         i = 1

#==============================================================================
if __name__ == "__main__":

    print("-------------------------------------------------------------------")
    print("Running : ",sys.argv)
    print("-------------------------------------------------------------------")


    # ArgParser -------------------------------------------------------------
    prgParser = configargparse.ArgumentParser(prog='upload_Django_Data', 
                                description="Uploading data to adjCOADD from Oracle/Excel/CSV")
    prgParser.add_argument("-c","--dataset", default='Public',required=True, dest="dataset", action='store', help="Dataset [Public/Reported/Current]")
    prgParser.add_argument("-i","--index", default='Structure',required=True, dest="index", action='store', help="by Index [Structure/Compound]")
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

    try:
        prgArgs = prgParser.parse_args()
    except:
        prgParser.print_help()
        print("- EXIT -----------------------------------------------------------")

        sys.exit(0)

    if prgArgs:
        main(prgArgs)
        logger.info("-------------------------------------------------------------------")

#==============================================================================