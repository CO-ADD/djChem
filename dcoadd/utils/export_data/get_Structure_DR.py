#
import os, sys
import datetime
import csv
from pathlib import Path
import pandas as pd
import numpy as np
import configargparse

import psycopg2

import logging
logLevel = logging.INFO 
logger = logging.getLogger(__name__)
logging.basicConfig(
    format="[%(name)-20s] %(message)s ",
    handlers=[logging.StreamHandler()],
    level=logLevel)


#-----------------------------------------------------------------------------
# PostgreSql Connector Class
#-----------------------------------------------------------------------------
class PostgreSqlConnector(object):

    def __init__(self):
        self.db = None
        self.cursor = None
        self.sql_type = None
        self.verbose = 1

    def open(self, username, password, hostname, database, verbose=1):
        try:
            self.config = {
                    'user': username,
                    'password': password,
                    'host': hostname,
                    'dbname': database,
                    'port' : 5432,
                    'raise_on_warnings': True
                    }

            self.db = psycopg2.connect(host=hostname, dbname=database, user=username, password=password)
        except psycopg2.OperationalError as e:
            logger.error(f"[PostgreSQL] Connection Error - {e}")
            raise
        self.verbose=verbose
        self.sql_type = "PostgreSQL"
        self.cursor = self.db.cursor()
        #self.cursor.execute('SET GLOBAL max_allowed_packet=500*1024*1024')
        self.user = username
        self.password = password
        self.hostname = hostname
        self.port = 5432
        self.database = database
        if self.verbose>0:
            logger.info(f"[PostgreSQL] {self.database}@{self.hostname}")

    def exec(self, sql, bindvars=None, commit=False):
        try:
            self.cursor.execute(sql, bindvars)
        except psycopg2.OperationalError as e:
            logger.error(f"[PostgreSQL] Execute Error {e}")
            raise
        if commit:
            self.db.commit()

    def close(self):
        try:
            #self.cursor.close()
            self.db.close()
        except psycopg2.connector.Error as e:
            pass
        if self.verbose>0:
            logger.info(f"[PostgreSQL] {self.database}@{self.hostname} [Closed] ")
            

    def nCount(self, sql, bindvars=None):
        """
        General method to return the first single column in a Select statement
          - to be used with "Select count(1) From ... "
        """
        self.exec(sql,bindvars=bindvars)
        new_Count = self.cursor.fetchone()[0]
        return new_Count

    def get_dict_list(self, sql, bindvars=None,upCase=False,lowCase=True):
        """
        Create a list, each item contains a dictionary outlined like:
        { "col1_name" : col1_data }
        Each item in the list is technically one row of data with named columns,
        represented as a dictionary object
        For example:
        list = [
            {"col1":1234567, "col2":1234, "col3":123456, "col4":BLAH},
            {"col1":7654321, "col2":1234, "col3":123456, "col4":BLAH}
            ]
            """
        self.exec(sql,bindvars=bindvars)
#        if self.cursor.rowcount > 0: DOES NOT Work for Oracle until cursor.fetchone() or cursor.fetchall()
        columns = [i[0] for i in self.cursor.description]
        new_list = []
        for row in self.cursor:
            row_dict = dict()
            for col in columns:
                if upCase:
                    row_dict[col.upper()] = row[columns.index(col)]
                elif lowCase:
                    row_dict[col.lower()] = row[columns.index(col)]
                else:
                    row_dict[col] = row[columns.index(col)]

            new_list.append(row_dict)
        return new_list


#----------------------------------------------------------------------------
def openChemDB(User='chemdb', Passwd='chemdb',DataBase="chemdb",verbose=1):
    dbPG = PostgreSqlConnector()
    dbPG.open(User,Passwd,"imb-coadd-db.imb.uq.edu.au",DataBase,verbose=verbose)
    return(dbPG)

#==============================================================================
def main(prgArgs):

    runTime= datetime.datetime.now()

    drSQL = """
            select distinct act.structure_id, 
                    act.result_type, act.assay_id, ass.assay_code, 
                    act.n_assays, act.result_min, act.result_median, act.result_max, act.result_unit, 
                    act.result_std_geomean, act.result_std_unit, act.inhibit_max_ave,
                    act.act_score, act.pscore,
                    cs.nfrag, cs.charge, cs.mf, cs.mw, cs.natoms, cs.hba, cs.hbd, 
                    cs.logp, cs.tpsa, cs.fractioncsp3, cs.nrotbonds, 
                    cs.nrings, cs.narorings, cs.nhetarorings, cs.nhetaliphrings,
                    cs.smol 
            from coadd.act_struct_dr act 
            left join coadd.compound c on c.structure_id = act.structure_id
            left join coadd.project p on p.project_id = c.project_id
            left join coadd.assay ass on ass.assay_id = act.assay_id
            left join coadd.source s on s.source_id = act.source_id
            left join coadd.chem_structure cs  on cs.structure_id = act.structure_id
            where p.pub_status = 'Public' 
            and s.source_name = 'CO-ADD'
            and cs.nfrag = 1            
            """
    
    Tables = {
        'HEK293': 'HEK293 [Res]',
        'Sa': 'Sa [43300]',
        'EcTolC': 'Ec [tolC]',
        'EcLpxC': 'Ec [lpxC]',
        'Ec': 'Ec [25992]',
        'Kp': 'Kp [700603]',
        'Ab': 'Ab [19606]',
        'Pa': 'Pa [27853]',
        'PaMexX': 'Pa [mexX]',
        'Ca': 'Ca [90028]',
        'Cn': 'Cn [208821]',
    }

    if prgArgs.table in Tables:

        dataVersion = 'Public'
        fileName = f'COADD_Public_{prgArgs.table}_MIC'
        dirName = './'

        qrySQL = drSQL + f" and ass.assay_code = '{Tables[prgArgs.table]}'"

        pgDB = openChemDB()
        logger.info(f"[CO-ADD Data] Table  : {prgArgs.table}") 
        logger.info(f"[CO-ADD Data] Version: {dataVersion}") 

        logger.info(f"[CO-ADD Data] getting {prgArgs.table} .. ")
        DF = pd.DataFrame(pgDB.get_dict_list(qrySQL))
        logger.info(f"[CO-ADD Data] {prgArgs.table} with {len(DF)} entries ")

        csvFileName = os.path.join(dirName,f"{fileName}_{runTime:%Y%m%d}.csv")
        xlsFileName = os.path.join(dirName,f"{fileName}_{runTime:%Y%m%d}.xlsx")

        logger.info(f"[CO-ADD Data] Writing {csvFileName} ")
        DF.to_csv(csvFileName)
        logger.info(f"[CO-ADD Data] Writing {xlsFileName} ")
        DF.to_excel(xlsFileName)

        pgDB.close()


#==============================================================================
if __name__ == "__main__":

    print("-------------------------------------------------------------------")
    print(f"Python         : {sys.version.split('|')[0]}")
    print(f"Conda Env      : {os.environ['CONDA_DEFAULT_ENV']}")
    print("-------------------------------------------------------------------")

    # ArgParser -------------------------------------------------------------
    prgParser = configargparse.ArgumentParser(prog='get CO-ADD Dataset', 
                                description="Export CO-ADD Dataset into Excel/CSV")
    prgParser.add_argument("-t",default=None,required=True, dest="table", action='store', help="Table to get [Options: Sa, Ec, EcTolC, ...]")

    try:
        prgArgs = prgParser.parse_args()
    except:
        prgParser.print_help()
        print("- EXIT -----------------------------------------------------------")

        sys.exit(0)

    if prgArgs:
        main(prgArgs)
        print("- DONE -----------------------------------------------------------")
#==============================================================================

