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
from pgChemDB_Utils import (openChemDB,
                            get_Projects, get_Assays, get_Compounds, get_Structures,
                            get_SingleConc_byStructure, get_SingleConc_byCompound,
                            get_DoseResponse_byStructure, get_DoseResponse_byCompound)

#import django

ProgName = "getDataset"

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
def get_pivGNMemb_SC():
#-----------------------------------------------------------------------------

    qrySQL = """
            Select structure_id, 
            Sa::float, Ec::float, EcLpxC::float, EcTolC::float,
            Pa::float, Pa5mex::float
        From (
                Select structure_id, 
                --ASS00001	Ec [25992]
                --ASS00004	Pa [27853]
                --ASS00005	Sa [43300]
                --ASS00006	Ec [lpxC]
                --ASS00007	Ec [tolC]
                --ASS00008	Pa [mexX]
                    max(inhibition_ave) filter (where assay_id = 'ASS00005') Sa,
                    max(inhibition_ave) filter (where assay_id = 'ASS00001') Ec,
                    max(inhibition_ave) filter (where assay_id = 'ASS00006') EcLpxC,
                    max(inhibition_ave) filter (where assay_id = 'ASS00007') EcTolC,
                    max(inhibition_ave) filter (where assay_id = 'ASS00004') Pa,
                    max(inhibition_ave) filter (where assay_id = 'ASS00008') Pa5mex
                from coadd.act_struct_sc 
                group by structure_id
            ) as s
        where s.Pa5mex is not null or s.EcLpxC is not null or s.EcTolC is not Null    
        """

#-----------------------------------------------------------------------------
def get_pivData_SC():
#-----------------------------------------------------------------------------

    qrySQL = """
            Select structure_id, 
                Sa_inhavg::float, 
                Ec_inhavg::float, EcLpxC_inhavg::float, EcTolC_inhavg::float,
                Kp_inhavg::float, Ab_inhavg::float,
                Pa_inhavg::float, Pa5mex_inhavg::float,
                Ca_inhavg::float, Cn_inhavg::float
            From 
            (
            Select structure_id, 
            --	ASS00011	HEK293 [Res]
            --	ASS00001	Ec [25992]
            --	ASS00002	Kp [700603]
            --	ASS00003	Ab [19606]
            --	ASS00004	Pa [27853]
            --	ASS00005	Sa [43300]
            --	ASS00006	Ec [lpxC]
            --	ASS00007	Ec [tolC]
            --	ASS00008	Pa [mexX]
            --	ASS00009	Ca [90028]
            --	ASS00010	Cn [208821]
            --	ASS00012	hRBC
                avg(inhibition_ave) filter (where assay_id = 'ASS00005') Sa_inhavg,
                avg(inhibition_ave) filter (where assay_id = 'ASS00001') Ec_inhavg,
                avg(inhibition_ave) filter (where assay_id = 'ASS00006') EcLpxC_inhavg,
                avg(inhibition_ave) filter (where assay_id = 'ASS00007') EcTolC_inhavg,
                avg(inhibition_ave) filter (where assay_id = 'ASS00002') Kp_inhavg,
                avg(inhibition_ave) filter (where assay_id = 'ASS00003') Ab_inhavg,
                avg(inhibition_ave) filter (where assay_id = 'ASS00004') Pa_inhavg,
                avg(inhibition_ave) filter (where assay_id = 'ASS00008') Pa5mex_inhavg,
                avg(inhibition_ave) filter (where assay_id = 'ASS00009') Ca_inhavg,
                avg(inhibition_ave) filter (where assay_id = 'ASS00010') Cn_inhavg
            from coadd.act_struct_sc 
            Group by structure_id
            ) as s
        """


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

        if prgArgs.dataset == 'Public':
            BaseName = f'COADD_{prgArgs.dataset}2024'
        elif prgArgs.dataset == 'Current':
            BaseName = f'COADD_{prgArgs.dataset}{logTime:%Y%m%d}'
        else:
            BaseName = f'COADD_{logTime:%Y%m%d%H%M}'

        if prgArgs.outdir:
            if not os.path.exists(prgArgs.outdir):
                os.makedirs(prgArgs.outdir)
            BaseName = os.path.join(prgArgs.outdir,BaseName)

        # Projects
        dfProject = get_Projects(DataSet=prgArgs.dataset,test=int(prgArgs.test))
        csvFile = os.path.join(f'{BaseName}_Projects.csv.gz')
        logger.info(f'[Project] --> {csvFile}')
        dfProject.to_csv(csvFile,compression='gzip')

        # Assays
        dfAssay = get_Assays()
        csvFile = os.path.join(f'{BaseName}_Assays.csv.gz')
        logger.info(f'[Assay] --> {csvFile}')
        dfAssay.to_csv(csvFile,compression='gzip')
        # cidDF = get_Compound_ID(DataSet=prgArgs.dataset,test=int(prgArgs.test))

        # Structure
        dfStructure = get_Structures(DataSet=prgArgs.dataset,test=int(prgArgs.test))
        csvFile = os.path.join(f'{BaseName}_Structures.csv.gz')
        logger.info(f'[Structure] --> {csvFile}')
        dfStructure.to_csv(csvFile,compression='gzip')

        dfStructure = get_Compounds(DataSet=prgArgs.dataset,test=int(prgArgs.test))
        csvFile = os.path.join(f'{BaseName}_Compounds.csv.gz')
        logger.info(f'[Compound] --> {csvFile}')
        dfStructure.to_csv(csvFile,compression='gzip')

        # SC Data
        dfSC = get_SingleConc_byStructure(DataSet=prgArgs.dataset,test=int(prgArgs.test))
        csvFile = os.path.join(f'{BaseName}_SingleConc_byStructure.csv.gz')
        logger.info(f'[SC Structure] --> {csvFile}')
        dfSC.to_csv(csvFile,compression='gzip')

        dfSC = get_SingleConc_byCompound(DataSet=prgArgs.dataset,test=int(prgArgs.test))
        csvFile = os.path.join(f'{BaseName}_SingleConc_byCompound.csv.gz')
        logger.info(f'[SC Compound] --> {csvFile}')
        dfSC.to_csv(csvFile,compression='gzip')

        # DR Data
        dfDR = get_DoseResponse_byStructure(DataSet=prgArgs.dataset,test=int(prgArgs.test))
        csvFile = os.path.join(f'{BaseName}_DR_DoseResponse_byStructure.csv.gz')
        logger.info(f'[DR Structure] --> {csvFile}')
        dfDR.to_csv(csvFile,compression='gzip')

        dfDR = get_DoseResponse_byCompound(DataSet=prgArgs.dataset,test=int(prgArgs.test))
        csvFile = os.path.join(f'{BaseName}_DR_DoseResponse_byCompound.csv.gz')
        logger.info(f'[DR Compound] --> {csvFile}')
        dfDR.to_csv(csvFile,compression='gzip')


        # Excel Output
        # xlsFile = os.path.join(f'{BaseName}_byStructure.xlsx')
        # logger.info(f'[ActData by Structure] --> {xlsFile}')
        # with pd.ExcelWriter(xlsFile) as writer:
        #    dfStructure.to_excel(writer, sheet_name='Structures')
        #    dfAssay.to_excel(writer, sheet_name='Assays')
        #    dfSC.to_excel(writer, sheet_name='SC')
        #    dfDR.to_excel(writer, sheet_name='DR')

        # Pivot Data
        # logger.info(f'[SC Structure] : Pivot')
        # pivSC = dfSC.pivot_table(index=['structure_id'],columns=['assay_code'],values=['inhibition_ave','act_score'],aggfunc='mean')

        # pivSC.columns = [" - ".join(a[::-1]) for a in pivSC.columns.to_flat_index()]
        # csvFile = os.path.join(f'{BaseName}_SC_Pivot_byStructure.csv.gz')
        # logger.info(f'[SC Structure] --> {csvFile}')
        # pivSC.to_csv(csvFile,compression='gzip')

        # print(scPIV.columns)
        # _asscode = list(set([c[1] for c in scPIV.columns]))
        # print(f"[_asscode] {_asscode}")
        # _neworder = scPIV.columns.reindex(_asscode, level=1)
        # print(f" [_neworder] {_neworder}")
        # scPIV = scPIV.reindex(columns=_neworder[0])


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