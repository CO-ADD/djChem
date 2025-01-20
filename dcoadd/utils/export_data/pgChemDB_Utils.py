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

#import django

ProgName = "getDataset"

# Logger ----------------------------------------------------------------
import logging
logger = logging.getLogger(__name__)

#-----------------------------------------------------------------------------

def openCoaddDB(User='coadd', Passwd='MtMaroon23',DataBase="coadd",verbose=1):
    dbPG = zSqlConnector.PostgreSQL()
    dbPG.open(User,Passwd,"imb-coadd-db.imb.uq.edu.au",DataBase,verbose=verbose)
    return(dbPG)

def openChemDB(User='chemdb', Passwd='chemdb',DataBase="chemdb",verbose=1):
    dbPG = zSqlConnector.PostgreSQL()
    dbPG.open(User,Passwd,"imb-coadd-db.imb.uq.edu.au",DataBase,verbose=verbose)
    return(dbPG)


#-----------------------------------------------------------------------------
def get_Projects(DataSet='Public', ProjectTypes=['CO-ADD'], test=0):
#-----------------------------------------------------------------------------

    qrySQL = """
        Select p.project_id, p.project_name, p.organisation_name, p.project_type, p.pub_date, p.pub_status
        From  coadd.project p
        Where 
        """

    sqlPrj = ','.join([f"'{p}'" for p in ProjectTypes])
    qrySQL += f" p.project_type in ({sqlPrj}) "

    if DataSet == 'Public':
        qrySQL += " and pub_status = 'Public' "

    if test>0:
        qrySQL += f" Fetch First {test} Rows Only "

    pgDB = openChemDB(verbose=0)
    qryDF = pd.DataFrame(pgDB.get_dict_list(qrySQL)).set_index('project_id')
    logger.info(f"[Project] {DataSet} {len(qryDF):_} ")
    pgDB.close()

    return(qryDF)

#-----------------------------------------------------------------------------
def get_Assays(DataSet='Public', ProjectTypes=['CO-ADD'], test=0):
#-----------------------------------------------------------------------------

    qrySQL = """
        Select a.assay_id, a.assay_code, a.sum_assay_code, a.assay_type, 
            a.organism, a.strain, a.strain_notes, 
            a.media, a.plate_type, a.readout, a.readout_dye
        From  coadd.assay a
        """

    sqlPrj = ','.join([f"'{p}'" for p in ProjectTypes])
    qrySQL += f" Where a.source in ({sqlPrj}) "

    # if DataSet == 'Public':
    #     qrySQL += " and pub_status = 'Public' "

    # if test>0:
    #     qrySQL += f" Fetch First {test} Rows Only "

    pgDB = openChemDB(verbose=0)
    qryDF = pd.DataFrame(pgDB.get_dict_list(qrySQL)).set_index('assay_id')
    logger.info(f"[Assay] {DataSet}: {len(qryDF):_} ")
    pgDB.close()

    return(qryDF)

#-----------------------------------------------------------------------------
def get_Structures(DataSet='Public', ProjectTypes=['CO-ADD','WADI'], test=0):
#-----------------------------------------------------------------------------

    qrySQL = """
        Select Distinct s.structure_id, s.structure_code, s.structure_name,
         s.structure_types, s.compound_type,
         s.mf, s.mw, s.natoms, s.nfrag, s.charge,
         s.hba, s.hbd, s.logp, s.tpsa, s.fractioncsp3, s.nrotbonds,
         s.nrings, s.narorings, s.nhetarorings, s.nhetaliphrings,
         s.atom_classes,
         s.smol
        From  coadd.chem_structure s
          left join coadd.compound c on c.structure_id = s.structure_id
           left join coadd.project p on p.project_id = c.project_id
        """
    pgDB = openChemDB(verbose=0)

    if DataSet == 'Public':
        qrySQL += " Where p.pub_status = 'Public' "

    if test>0:
        qrySQL += f" Fetch First {test} Rows Only "

    pgDB = openChemDB(verbose=0)
    #nEntries = pd.read_sql_query(qrySQL, pgDB.db).values[0, 0]
    qryDF = pd.DataFrame(pgDB.get_dict_list(qrySQL)).set_index('structure_id')
    logger.info(f"[Structure] {DataSet}: {len(qryDF):_} ")
    pgDB.close()


    return(qryDF)

#-----------------------------------------------------------------------------
def get_Compounds(DataSet='Public', ProjectTypes=['CO-ADD','WADI'], test=0):
#-----------------------------------------------------------------------------

    qrySQL = """
        Select distinct c.compound_id, c.compound_code, c.compound_name, c.compound_type, c.project_id,
            c.structure_id, c.std_status,
            c.std_structure_type, c.std_salt, c.std_ion, c.std_solvent, c.std_metal, c.std_nfrag
        From  coadd.compound c 
           left join coadd.project p on p.project_id = c.project_id
        """
    sqlPrj = ','.join([f"'{p}'" for p in ProjectTypes])
    qrySQL += f" Where p.project_type in ({sqlPrj}) "
   
    if DataSet == 'Public':
        qrySQL += " and p.pub_status in ('Public','MissingData') "

    if test>0:
        qrySQL += f" Fetch First {test} Rows Only "

    pgDB = openChemDB(verbose=0)

    qryDF = pd.DataFrame(pgDB.get_dict_list(qrySQL)).set_index('compound_id')
    logger.info(f"[Compounds] : {len(qryDF):_} ")

    pgDB.close()

    return(qryDF)

#-----------------------------------------------------------------------------
def get_SingleConc_byStructure(DataSet='Public', ProjectTypes=['CO-ADD','WADI'], test=0):
#-----------------------------------------------------------------------------

    qrySQL = """
        Select sc.structure_id, sc.assay_id, ass.assay_code, ass.sum_assay_code,
            sc.n_assays, sc.n_actives, sc.act_types, sc.act_score,
            sc.inhibition_ave, sc.inhibition_std, sc.mscore_ave
        From  coadd.act_struct_sc sc
          left join coadd.compound c on c.structure_id = sc.structure_id
           left join coadd.project p on p.project_id = c.project_id
          left join coadd.assay ass on sc.assay_id = ass.assay_id
        """

    sqlPrj = ','.join([f"'{p}'" for p in ProjectTypes])
    qrySQL += f" Where p.project_type in ({sqlPrj}) "
   
    if DataSet == 'Public':
        qrySQL += " and p.pub_status = 'Public' "

    if test>0:
        qrySQL += f" Fetch First {test} Rows Only "


    pgDB = openChemDB(verbose=0)
    qryDF = pd.DataFrame(pgDB.get_dict_list(qrySQL)).set_index('structure_id')
    logger.info(f"[ActData Structure SC] : {len(qryDF):_} ")
    pgDB.close()

    return(qryDF)

#-----------------------------------------------------------------------------
def get_SingleConc_byCompound(DataSet='Public', ProjectTypes=['CO-ADD','WADI'], test=0):
#-----------------------------------------------------------------------------

    qrySQL = """
        Select sc.compound_id, sc.assay_id, ass.assay_code, ass.sum_assay_code,
            sc.n_assays, sc.n_actives, sc.act_types, sc.act_score,
            sc.inhibition_ave, sc.inhibition_std, sc.mscore_ave
        From  coadd.act_cmpd_sc sc
          left join coadd.compound c on c.compound_id = sc.compound_id
           left join coadd.project p on p.project_id = c.project_id
          left join coadd.assay ass on sc.assay_id = ass.assay_id
        """

    sqlPrj = ','.join([f"'{p}'" for p in ProjectTypes])
    qrySQL += f" Where p.project_type in ({sqlPrj}) "
   
    if DataSet == 'Public':
        qrySQL += " and p.pub_status = 'Public' "

    if test>0:
        qrySQL += f" Fetch First {test} Rows Only "


    pgDB = openChemDB(verbose=0)
    qryDF = pd.DataFrame(pgDB.get_dict_list(qrySQL)).set_index('compound_id')
    logger.info(f"[ActData Compound SC] {DataSet}: {len(qryDF):_} ")
    pgDB.close()

    return(qryDF)


#-----------------------------------------------------------------------------
def get_DoseResponse_byStructure(DataSet='Public', ProjectTypes=['CO-ADD','WADI'], test=0):
#-----------------------------------------------------------------------------

    qrySQL = """
        Select dr.structure_id, dr.assay_id, ass.assay_code, ass.sum_assay_code,
            dr.result_type,
            dr.n_assays, dr.n_actives, dr.act_types, dr.act_score, dr.pscore,
            dr.result_median, dr.result_unit, dr.result_std_geomean, dr.result_std_unit, dr.inhibit_max_ave
        From  coadd.act_struct_dr dr
          left join coadd.compound c on c.structure_id = dr.structure_id
           left join coadd.project p on p.project_id = c.project_id
          left join coadd.assay ass on dr.assay_id = ass.assay_id
        """

    sqlPrj = ','.join([f"'{p}'" for p in ProjectTypes])
    qrySQL += f" Where p.project_type in ({sqlPrj}) "
   
    if DataSet == 'Public':
        qrySQL += " and p.pub_status = 'Public' "

    if test>0:
        qrySQL += f" Fetch First {test} Rows Only "


    pgDB = openChemDB(verbose=0)
    qryDF = pd.DataFrame(pgDB.get_dict_list(qrySQL)).set_index('structure_id')
    logger.info(f"[ActData Structure DR] : {len(qryDF):_} ")
    pgDB.close()

    return(qryDF)

#-----------------------------------------------------------------------------
def get_DoseResponse_byCompound(DataSet='Public', ProjectTypes=['CO-ADD','WADI'], test=0):
#-----------------------------------------------------------------------------

    qrySQL = """
        Select dr.compound_id, dr.assay_id, ass.assay_code, ass.sum_assay_code,
            dr.result_type,
            dr.n_assays, dr.n_actives, dr.act_types, dr.act_score, dr.pscore,
            dr.result_median, dr.result_unit, dr.result_std_geomean, dr.result_std_unit, dr.inhibit_max_ave
        From  coadd.act_cmpd_dr dr
          left join coadd.compound c on c.compound_id = dr.compound_id
           left join coadd.project p on p.project_id = c.project_id
          left join coadd.assay ass on dr.assay_id = ass.assay_id
        """

    sqlPrj = ','.join([f"'{p}'" for p in ProjectTypes])
    qrySQL += f" Where p.project_type in ({sqlPrj}) "
   
    if DataSet == 'Public':
        qrySQL += " and p.pub_status = 'Public' "

    if test>0:
        qrySQL += f" Fetch First {test} Rows Only "


    pgDB = openChemDB(verbose=0)
    qryDF = pd.DataFrame(pgDB.get_dict_list(qrySQL)).set_index('compound_id')
    logger.info(f"[ActData Compound DR] {DataSet}: {len(qryDF):_} ")
    pgDB.close()

    return(qryDF)


#-----------------------------------------------------------------------------
def apply_sc_gnmemb(s,iCutoff=25):
#-----------------------------------------------------------------------------
    
    GNDict = {
        'EcTolC': ['Ec_sc_inhib','EcTolC_sc_inhib'],
        'EcLpxC': ['Ec_sc_inhib','EcLpxC_sc_inhib'],
        'PaMexX': ['Pa_sc_inhib','PaMexX_sc_inhib'],
        }
    
    for k in GNDict.keys():
        if not np.isnan(s[GNDict[k][1]]) and not np.isnan(s[GNDict[k][0]]):
            if (s[GNDict[k][1]] - s[GNDict[k][0]]) > iCutoff:
                # Efflux
                s[f'{k}_sc_efflux'] = 1
            else:
                # Penetrate
                s[f'{k}_sc_efflux'] = 0
                
    return(s)


#-----------------------------------------------------------------------------
def apply_dr_gnmemb(s,pCutoff=0.2):
#-----------------------------------------------------------------------------

    GNDict = {
        'EcTolC': ['Ec_dr_pscore','EcTolC_dr_pscore'],
        'EcLpxC': ['Ec_dr_pscore','EcLpxC_dr_pscore'],
        'PaMexX': ['Pa_dr_pscore','PaMexX_dr_pscore'],
        }
    
    for k in GNDict.keys():
        if not np.isnan(s[GNDict[k][1]]) and not np.isnan(s[GNDict[k][0]]):
            if (s[GNDict[k][1]] - s[GNDict[k][0]]) > pCutoff:
                # Efflux
                s[f'{k}_dr_efflux'] = 1
            else:
                # Penetrate
                s[f'{k}_dr_efflux'] = 0
                
    return(s)