from django.db import models

from rdkit import Chem
from django_rdkit import models
from model_utils import Choices
from sequences import Sequence
from django.core.validators import RegexValidator

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GistIndex

from django.core.validators import MaxValueValidator, MinValueValidator 
from django.db import transaction, IntegrityError
from django.utils.text import slugify
from django.contrib.auth.models import AbstractUser
import pgtrigger

from apputil.models import AuditModel, Dictionary, ApplicationUser
from apputil.utils.bio_data import pScore, ActScore_DR, ActScore_SC

from adjCHEM.constants import *

import logging
logger = logging.getLogger(__name__)

#=================================================================================================
class Assay(AuditModel):
    """
    List of Assays
    """
#=================================================================================================

    Choice_Dictionary = {
        'assay_type':'Assay_Type',
        'plate_size':'Plate_Size',
        'plate_material':'Plate_Material',
    }

    ID_SEQUENCE = 'Assay'
    ID_PREFIX = 'ASS'
    ID_PAD = 5

    assay_id = models.CharField(max_length=15, primary_key=True, verbose_name = "Assay ID")
    assay_code = models.CharField(max_length=50, blank=True, verbose_name = "Assay Code")
    assay_notes = models.CharField(max_length=150, blank=True, verbose_name = "Notes")
    assay_type = models.CharField(max_length=50, blank=True, verbose_name = "Assay Type")
    organism = models.CharField(max_length=50, blank=True, verbose_name = "Organism")
    strain = models.CharField(max_length=50, blank=True, verbose_name = "Strain")
    strain_notes = models.CharField(max_length=150, blank=True, verbose_name = "Strain")
    media = models.CharField(max_length=100, blank=True, verbose_name = "Media")
    plate_type = models.CharField(max_length=100, blank=True, verbose_name = "Plate type")
    readout = models.CharField(max_length=50, blank=True, verbose_name = "Readout")
    readout_dye = models.CharField(max_length=50, blank=True, verbose_name = "Readout Dye")
    source = models.CharField(max_length=50, blank=True, verbose_name = "Source")
    source_code = models.CharField(max_length=120, blank=True, verbose_name = "Source Code")
    reference = models.CharField(max_length=150, blank=True, verbose_name = "Reference")
    laboratory = models.CharField(max_length=50, blank=True, verbose_name = "Laboratory")

    class Meta:
        app_label = 'dcoadd'
        db_table = 'assay'
        ordering=['assay_id']
        indexes = [
            models.Index(name="ass_ty_idx", fields=['assay_type']),
            models.Index(name="ass_co_idx", fields=['assay_code']),
            models.Index(name="ass_org_idx", fields=['organism']),
            models.Index(name="ass_str_idx", fields=['strain']),
        ]

    def __str__(self):
        return f"{self.assay_id} {self.assay_code}"
    
    #------------------------------------------------
    @classmethod
    def get(cls,AssayID, SourceName=None, SourceCode=None,verbose=0):
        try:
            if SourceName and SourceCode:
                retInstance = cls.objects.get(source_code = SourceCode, source = SourceName)
            else:
                retInstance = cls.objects.get(assay_id=AssayID)
        except:
            if verbose:
                logger.warning(f"[Assay Not Found] {AssayID} or {SourceName} {SourceCode}")
            retInstance = None
        return(retInstance)

    #------------------------------------------------
    # def save(self, *args, **kwargs):
    #     if not self.assay_id:
    #         self.assay_id = self.next_id()
    #         if self.assay_id: 
    #             super(Assay, self).save(*args, **kwargs)
    #     else:
    #         super(Assay, self).save(*args, **kwargs) 

#=================================================================================================
class Source(AuditModel):
    """
    List of Data/Compound sources
    """
#=================================================================================================

    Choice_Dictionary = {
        'source_type':'Source_Type',
    }

    ID_SEQUENCE = 'Source'
    ID_PREFIX = 'SRC'
    ID_PAD = 5

    source_id = models.CharField(max_length=15,primary_key=True, verbose_name = "Assay ID")
    source_name = models.CharField(max_length=150, blank=True, verbose_name = "Name")
    source_type = models.ForeignKey(Dictionary, null=True, blank=True, verbose_name = "Type", on_delete=models.DO_NOTHING,
        db_column="source_type", related_name="%(class)s_source_type")
    organisation = models.CharField(max_length=150, blank=True, verbose_name = "Organisation")

    class Meta:
        app_label = 'dcoadd'
        db_table = 'source'
        ordering=['source_id']
        indexes = [
            models.Index(name="src_pn_idx", fields=['source_name']),
            models.Index(name="src_pt_idx", fields=['source_type']),
        ]


    #------------------------------------------------
    @classmethod
    def get(cls,SourceID, SourceName=None,verbose=0):
        try:
            if SourceName :
                retInstance = cls.objects.get(source_name = SourceName)
            else:
                retInstance = cls.objects.get(source_id=SourceID)
        except:
            if verbose:
                logger.warning(f"[Source Not Found] {SourceID} or {SourceName}")
            retInstance = None
        return(retInstance)

    #------------------------------------------------
    # def save(self, *args, **kwargs):
    #     if not self.source_id:
    #         self.source_id = self.next_id()
    #         if self.source_id: 
    #             super(Source, self).save(*args, **kwargs)
    #     else:
    #         super(Source, self).save(*args, **kwargs) 

#=================================================================================================
class Project(AuditModel):
    """
    List of Projects
    """
#=================================================================================================
    Choice_Dictionary = {
        'project_type':'Project_Type',
        'pub_status':'Pub_Status',
    }
    
    ID_SEQUENCE = 'Project'
    ID_PREFIX = 'PRJ'
    ID_PAD = 5

    project_id = models.CharField(max_length=15,primary_key=True, verbose_name = "Project ID")
    project_name = models.CharField(max_length=150, blank=True, verbose_name = "Name")
    project_type = models.ForeignKey(Dictionary, null=True, blank=True, verbose_name = "Type", on_delete=models.DO_NOTHING,
        db_column="project_type", related_name="%(class)s_project_type")
    
    organisation_name = models.CharField(max_length=150, blank=True, verbose_name = "Organisation")
    source_id = models.ForeignKey(Source, null=True, blank=True, verbose_name = "Source", on_delete=models.DO_NOTHING,
        db_column="source_id", related_name="%(class)s_source_id")
    compound_status = models.CharField(max_length=150, blank=True, verbose_name = "Compound Status")
    data_status = models.CharField(max_length=150, blank=True, verbose_name = "Data Status")
    pub_status = models.ForeignKey(Dictionary, null=True, blank=True, verbose_name = "Pub Status", on_delete=models.DO_NOTHING,
        db_column="pub_status", related_name="%(class)s_pub_statust")
    pub_date = models.DateField(null=True, blank=True,  editable=False, verbose_name="Published")

    class Meta:
        app_label = 'dcoadd'
        db_table = 'project'
        ordering=['project_id']
        indexes = [
            models.Index(name="prj_pn_idx", fields=['project_name']),
            models.Index(name="prj_pt_idx", fields=['project_type']),
            models.Index(name="prj_src_idx", fields=['source_id']),
        ]

    #------------------------------------------------
    def __str__(self) -> str:
        return f"{self.project_id}  {self.source_id}"

    #------------------------------------------------
    # def save(self, *args, **kwargs):
    #     if not self.project_id:
    #         self.project_id = self.next_id()
    #         if self.project_id: 
    #             super(Project, self).save(*args, **kwargs)
    #     else:
    #         super(Project, self).save(*args, **kwargs) 


#=================================================================================================
class Chem_Structure(AuditModel):
    """
    List of ChemStructure 
    """
#=================================================================================================
    Choice_Dictionary = {
        'structure_type':'Structure_Type',
    }

    ID_SEQUENCE = 'ChemStructure'
    ID_PREFIX = 'CS'
    ID_PAD = 9

    structure_id = models.CharField(max_length=15, primary_key=True, verbose_name = "Structure ID")
    structure_code = models.CharField(max_length=15, blank=True, verbose_name = "Structure Code")
    structure_name = models.CharField(max_length=50, blank=True, verbose_name = "Structure Name")
    structure_types = ArrayField(models.CharField(max_length=15, null=True, blank=True), size=4, verbose_name = "Structure Types", 
                                      null=True, blank=True)
    atom_classes = ArrayField(models.CharField(max_length=15, null=True, blank=True), size=4, verbose_name = "Atom Classes", 
                                      null=True, blank=True)

    compound_type = models.ForeignKey(Dictionary, null=True, blank=True, verbose_name = "Type", on_delete=models.DO_NOTHING,
        db_column="compound_type", related_name="%(class)s_compound_type")

    smol = models.MolField(verbose_name = "MOL")	
    nfrag = models.PositiveSmallIntegerField(default=1, blank=True, verbose_name ="nFrag")
    charge = models.DecimalField(max_digits=10, decimal_places=2,  blank=True, verbose_name ="Charge")
    
    # Calculated by Trigger Function
    tfp2 = models.BfpField(null=True,blank=True,verbose_name = "Topological-Torsion FP")	
    ffp2 = models.BfpField(null=True,blank=True,verbose_name = "Feature Morgan FP (FCFP)")
    mfp2 = models.BfpField(null=True,blank=True,verbose_name = "Morgan FP (ECFP)")


    inchikey = models.CharField(max_length=50, blank=True,verbose_name ="InChiKey")
    mf = models.CharField(max_length=500, blank=True, verbose_name = "MF")
    mw = models.DecimalField(max_digits=12, decimal_places=3, default=0, blank=True, verbose_name ="MW")
    natoms = models.PositiveSmallIntegerField(default=0, blank=True, verbose_name ="nAtoms")
    hba = models.PositiveSmallIntegerField(default=0, blank=True, verbose_name ="HBond Acc")
    hbd = models.PositiveSmallIntegerField(default=0, blank=True, verbose_name ="HBond Don")
    logp = models.DecimalField(max_digits=9, decimal_places=2, default=0, blank=True, verbose_name ="logP")
    tpsa = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True, verbose_name ="tPSA")
    fractioncsp3 = models.DecimalField(max_digits=9, decimal_places=2, default=0, blank=True, verbose_name ="Sp3")
    nrotbonds = models.PositiveSmallIntegerField(default=0, blank=True, verbose_name ="nRotBond")
    nrings = models.PositiveSmallIntegerField(default=0, blank=True, verbose_name ="nRings")
    narorings = models.PositiveSmallIntegerField(default=0, blank=True, verbose_name ="nAroRings")
    nhetarorings = models.PositiveSmallIntegerField(default=0, blank=True, verbose_name ="nHetAroRings")
    nhetaliphrings = models.PositiveSmallIntegerField(default=0, blank=True, verbose_name ="nHetAliphRings")

    class Meta:
        app_label = 'dcoadd'
        db_table = 'chem_structure'
        ordering=['structure_id']
        indexes = [
            models.Index(name="cstruct_dcode_idx", fields=['structure_code']),
            models.Index(name="cstruct_inchi_idx", fields=['inchikey']),
            models.Index(name="cstruct_mf_idx", fields=['mf']),
            models.Index(name="cstruct_mw_idx", fields=['mw']),
            models.Index(name="cstruct_natoms_idx", fields=['natoms']),
            models.Index(name="cstruct_nfrag_idx", fields=['nfrag']),
            models.Index(name="cstruct_charge_idx", fields=['charge']),
            models.Index(name="cstruct_cmptyp_idx", fields=['compound_type']),
            GistIndex(name="cstruct_smol_idx",fields=['smol']),
            GistIndex(name="cstruct_ffp2_idx",fields=['ffp2']),
            GistIndex(name="cstruct_mfp2_idx",fields=['mfp2']),
            GistIndex(name="cstruct_tfp2_idx",fields=['tfp2'])
        ]
        triggers = [pgtrigger.Trigger(
                        name= "trigfunc_chemstruct_biu",
                        operation = pgtrigger.Insert | pgtrigger.Update,
                        when = pgtrigger.Before,
                        func = """
                                New.mfp2 := morganbv_fp(NEW.sMol);
                                New.ffp2 := featmorganbv_fp(NEW.sMol);
                                New.tfp2 := torsionbv_fp(NEW.sMol);
                                New.inchikey := mol_inchikey(NEW.sMol);
                                New.mw := mol_amw(NEW.sMol);
                                New.mf := mol_formula(NEW.sMol);
                                New.natoms := mol_numheavyatoms(NEW.sMol);
                                New.logp := mol_logp(NEW.sMol);
                                New.tpsa := mol_tpsa(NEW.sMol);
                                New.nrotbonds = mol_numrotatablebonds(NEW.sMol);
                                New.fractioncsp3 = mol_fractioncsp3(NEW.sMol);
                                New.hba = mol_hba(NEW.sMol);
                                New.hbd = mol_hbd(NEW.sMol);
                                New.nrings = mol_numrings(NEW.sMol);
                                New.narorings = mol_numaromaticrings(NEW.sMol);
                                New.nhetarorings = mol_numaromaticheterocycles(NEW.sMol);
                                New.nhetaliphrings = mol_numaliphaticheterocycles(NEW.sMol);
                                RETURN NEW;
                            """
                            )
                    ]

    #------------------------------------------------
    # def __str__(self) -> str:
    #     return f"{self.drug_id}"

    #------------------------------------------------
    def __repr__(self) -> str:
        return f"{self.structure_name} ({self.structure_id})"

    #------------------------------------------------
    @classmethod
    def get(cls, StructureID=None, StructureName=None, verbose=0):
    # Returns an instance by structure_id or structure_name
        try:
            if StructureID:
                retInstance = cls.objects.get(structure_id=StructureID)
            elif StructureName:
                retInstance = cls.objects.get(structure_name=StructureName)
            else:
                retInstance = None
        except:
            retInstance = None
            if verbose:
                if StructureID:
                    print(f"[Structure Not Found] {StructureID} ")
                elif StructureName:
                    print(f"[Structure Not Found] {StructureName} ")
        return(retInstance)

    @classmethod
    def get_bySmiles(cls,Smiles,verbose=0):
    # Returns an instance by smiles exact search
        try:
            retInstance = cls.objects.filter(smol__exact=Smiles).first()
        except:
            retInstance = None
            if verbose:
                print(f"[Structure Not Found] {Smiles} ")
        return(retInstance)

    #------------------------------------------------
    @classmethod
    def exists(cls,StructureID=None,StructureName=None,verbose=0):
    # Returns if an instance exists by drug_name or durg_id
        if StructureID:
            retValue = cls.objects.filter(structure_id=StructureID).exists()
        elif StructureName:
            retValue = cls.objects.filter(structure_name=StructureName).exists()
        else:
            retValue = False
        return(retValue)

    #------------------------------------------------
    @classmethod
    def exists_bySmiles(cls,Smiles,verbose=0):
    # Returns if an instance exists by drug_name or durg_id
        retValue = cls.objects.filter(smol__exact=Smiles).exists()
        return(retValue)

    #------------------------------------------------
    @classmethod
    def smiles2mol(cls,Smiles,verbose=0):
        try:
            xmol = Chem.MolFromSmiles(Smiles)
        except:
            xmol = None
            if verbose:
                print(f"[Invalid SMILES] {Smiles} ")
        return(xmol)

    #------------------------------------------------
    @classmethod
    def register_fromDict(cls,sDict,smiles_name='smiles',mol_name='mol',verbose=0):
        djchem = None
        if smiles_name in sDict:
            djchem = cls.get_bySmiles(sDict[smiles_name])
            if not djchem:
                djchem = cls()
                djchem.set_molecule(sDict[smiles_name])
        elif mol_name in sDict:
            djchem = cls.get_bySmiles(Chem.MolToSmiles(sDict[mol_name]))
            if not djchem:
                djchem = cls()
                djchem.smol = sDict[mol_name]

        if djchem:        
            for s in ['structure_code','structure_name']:
                if s in sDict:
                    setattr(djchem,s,sDict[s])

            validStatus = True
            djchem.init_fields()
            validDict = djchem.validate_fields()
            if validDict:
                validStatus = False
                for k in validDict:
                    print('[reg Chem_Structure] Warning',k,validDict[k])

            if validStatus:
                djchem.save()
                return(djchem)
            else:
                return(None)
        else:
            if verbose:
                print(f"[reg Chem_Structure] no {smiles_name} or {mol_name} in {sDict}")
            return(None)

    #------------------------------------------------
    def set_molecule(self,Smiles):
        self.smol = self.smiles2mol(Smiles,verbose=0) 

    #------------------------------------------------
    def set_properties(self):
        self.charge = Chem.GetFormalCharge(self.smol)
    #    self.mw = Chem.Descriptors.MolWt(self.smol)
    #    self.mf = Chem.rdMolDescriptors.CalcMolFormula(self.smol)
    
    #------------------------------------------------
    def get_smiles(self):
        return(Chem.MolToSmiles(self.smol))

    #------------------------------------------------
    def save(self, *args, **kwargs):
        if self.smol:
            self.set_properties()
            if not self.structure_id:
                self.structure_id = self.next_id()
                if self.structure_id: 
                    super(Chem_Structure, self).save(*args, **kwargs)
            else:
                super(Chem_Structure, self).save(*args, **kwargs)
        else: 
            print(f"[Not a valid Molecule] ")

#-------------------------------------------------------------------------------------------------
class Compound(AuditModel):
    """
    List of Compounds 
    """
#-------------------------------------------------------------------------------------------------
    Choice_Dictionary = {
        'compound_type':'Compound_Type',
        'pub_status':'Pub_Status',
    }

    ID_SEQUENCE = 'Compound'
    ID_PREFIX = 'CMP'
    ID_PAD = 9
    
    compound_id = models.CharField(max_length=15, primary_key=True, verbose_name = "Compound ID")
    compound_code = models.CharField(max_length=120, blank=True, verbose_name = "Code")
    compound_name = models.CharField(max_length=120, blank=True, verbose_name = "Name")
    compound_type = models.ForeignKey(Dictionary, null=True, blank=True, verbose_name = "Type", on_delete=models.DO_NOTHING,
        db_column="compound_type", related_name="%(class)s_compound_type")
    coadd_id = models.CharField(max_length=25, blank=True, verbose_name = "CO-ADD ID")
    
    project_id = models.ForeignKey(Project, null=True, blank=True, verbose_name = "Project ID", on_delete=models.DO_NOTHING,
        db_column="project_id", related_name="%(class)s_project_id")
    source_id = models.ForeignKey(Source, null=True, blank=True, verbose_name = "Source", on_delete=models.DO_NOTHING,
        db_column="source_id", related_name="%(class)s_source_id")
    structure_id = models.ForeignKey(Chem_Structure, null=True, blank=True, verbose_name = "Structure ID", on_delete=models.DO_NOTHING,
        db_column="structure_id", related_name="%(class)s_structure_id")

    std_status = models.CharField(max_length=10, blank=True, verbose_name = "Std Status")
    std_smiles = models.CharField(max_length=2048, blank=True, verbose_name = "Std Smiles")
    std_nfrag = models.SmallIntegerField(default=0, verbose_name = "Std nFrag")
    std_salt = models.CharField(max_length=100, blank=True, verbose_name = "Std Salt")
    std_ion = models.CharField(max_length=100, blank=True, verbose_name = "Std Ion")
    std_solvent = models.CharField(max_length=100, blank=True, verbose_name = "Std Solvent")
    std_metal = models.CharField(max_length=100, blank=True, verbose_name = "Std Metal")
    std_structure_type = models.CharField(max_length=400, blank=True, verbose_name = "Std Type")

    pub_status = models.ForeignKey(Dictionary, null=True, blank=True, verbose_name = "Pub Status", on_delete=models.DO_NOTHING,
        db_column="pub_status", related_name="%(class)s_pub_statust")
    pub_date = models.DateField(null=True, blank=True,  editable=False, verbose_name="Published")

    class Meta:
        app_label = 'dcoadd'
        db_table = 'compound'
        ordering=['compound_id']
        indexes = [
            models.Index(name="cmp_name_idx", fields=['compound_name']),
            models.Index(name="cmp_code_idx", fields=['compound_code']),
            models.Index(name="cmp_type_idx", fields=['compound_type']),
            models.Index(name="cmp_pid_idx", fields=['project_id']),
            models.Index(name="cmp_src_idx", fields=['source_id']),
            models.Index(name="cmp_str_idx", fields=['structure_id']),
            models.Index(name="cmp_sstat_idx", fields=['std_status']),
            models.Index(name="cmp_snfrag_idx", fields=['std_nfrag']),
            models.Index(name="cmp_sstyp_idx", fields=['std_structure_type']),
            models.Index(name="cmp_ssalt_idx", fields=['std_salt']),
            models.Index(name="cmp_smetal_idx", fields=['std_metal']),
            models.Index(name="cmp_pst_idx", fields=['pub_status']),
            
        ]

    #------------------------------------------------
    def __str__(self) -> str:
        return f"{self.compound_id}  {self.compound_code}"

    #------------------------------------------------
    @classmethod
    def get(cls,CompoundID,verbose=0):
    # Returns an instance by compound_id
        try:
            retInstance = cls.objects.get(compound_id=CompoundID)
        except:
            retInstance = None
            if verbose:
                print(f"[Compound Not Found] {CompoundID} ")
        return(retInstance)

    #------------------------------------------------
    @classmethod
    def exists(cls,CompoundID,verbose=0):
    # Returns if an instance exists by compound_id
        retValue = cls.objects.filter(compound_id=CompoundID).exists()
        return(retValue)

#-------------------------------------------------------------------------------------------------
class Activity_Compound_Inhibition(AuditModel):
    """
    List of Summary Activity for each Structure
    """
#-------------------------------------------------------------------------------------------------
    Choice_Dictionary = {
        'result_type':'Result_Type',
        'pub_status':'Pub_Status',
    }


    ID_SEQUENCE = None

    #udi_key = models.CharField(max_length=24, unique=True, blank=False, verbose_name = "UDI")

    compound_id = models.ForeignKey(Compound, blank=False, verbose_name = "Compound ID", on_delete=models.DO_NOTHING,
        db_column="compound_id", related_name="%(class)s_compound_id")
    assay_id = models.ForeignKey(Assay, blank=False, verbose_name = "Assay", on_delete=models.DO_NOTHING,
        db_column="assay_id", related_name="%(class)s_assay_id")
    source_id = models.ForeignKey(Source, blank=False, verbose_name = "Source", on_delete=models.DO_NOTHING,
        db_column="source_id", related_name="%(class)s_source_id")

    # Activity Summary
    act_types = models.CharField(max_length=250, blank=True, verbose_name = "Active Tupes")
    n_assays = models.SmallIntegerField(default=-1, blank=True, verbose_name = "#Assay")
    n_actives = models.SmallIntegerField(default=-1, blank=True, verbose_name = "#Actives")
    act_score = models.DecimalField(default=-1, max_digits=10, decimal_places=2, verbose_name = "Act Score")

    result_type = models.ForeignKey(Dictionary, blank=False, verbose_name = "Result Type", on_delete=models.DO_NOTHING,
        db_column="result_type", related_name="%(class)s_result_type")

    inhibition_ave = models.DecimalField(default=-1, max_digits=9, decimal_places=3, verbose_name = "Inhibition Ave")
    inhibition_std = models.DecimalField(default=-1, max_digits=9, decimal_places=3, verbose_name = "Inhibition Std")
    inhibition_min = models.DecimalField(default=-1, max_digits=9, decimal_places=3, verbose_name = "Inhibition Min")
    inhibition_max = models.DecimalField(default=-1, max_digits=9, decimal_places=3, verbose_name = "Inhibition Max")
    mscore_ave = models.DecimalField(max_digits=9, decimal_places=3, verbose_name = "MScore Max")

    pub_status = models.ForeignKey(Dictionary, null=True, blank=True, verbose_name = "Pub Status", on_delete=models.DO_NOTHING,
        db_column="pub_status", related_name="%(class)s_pub_statust")
    pub_date = models.DateField(null=True, blank=True,  editable=False, verbose_name="Published")


    #------------------------------------------------
    class Meta:
        app_label = 'dcoadd'
        db_table = 'act_cmpd_sc'
        ordering=['compound_id']
        constraints = [
            models.UniqueConstraint(name='actcmpsc_pk_cst', fields=['compound_id', 'assay_id','source_id'], )
        ]        
        indexes = [
            models.Index(name="actcmpsc_cmp_idx", fields=['compound_id']),
            models.Index(name="actcmpsc_ass_idx", fields=['assay_id']),
            models.Index(name="actcmpsc_src_idx", fields=['source_id']),
            models.Index(name="actcmpsc_act_idx", fields=['act_score']),
            models.Index(name="actcmpsc_iave_idx", fields=['inhibition_ave']),
            models.Index(name="actcmpsc_mave_idx", fields=['mscore_ave']),
            models.Index(name="actcmpsc_rtyp_idx", fields=['result_type']),
            models.Index(name="actcmpsc_pst_idx", fields=['pub_status']),
        ]

    #------------------------------------------------
    @classmethod
    def get(cls,CompoundID, AssayID, SourceID,verbose=0):
        try:
            retInstance = cls.objects.get(compound_id = CompoundID, assay_id = AssayID, source_id= SourceID)
        except:
            if verbose:
                logger.warning(f"[ActCompoundSC Not Found] {CompoundID} {AssayID} {SourceID}")
            retInstance = None
        return(retInstance)

    #------------------------------------------------
    def set_actscores(self,ZScore=False,verbose=0):
        if ZScore:
            self.act_score = ActScore_SC(self.inhibition_ave,self.mscore_ave)
        else:
            self.act_score = ActScore_SC(self.inhibition_ave)

#-------------------------------------------------------------------------------------------------
class Activity_Compound_DoseResponse(AuditModel):
    """
    List of Single Conc (Inhibition) Activities 
    """
#-------------------------------------------------------------------------------------------------
    Choice_Dictionary = {
        'result_unit':'Unit_Concentration',
        'result_std_unit':'Unit_Concentration',
        'result_type':'Result_Type',
        'pub_status':'Pub_Status',
    }

    ID_SEQUENCE = None

    #udi_key = models.CharField(max_length=24, unique=True, blank=False, verbose_name = "UDI")

    compound_id = models.ForeignKey(Compound, blank=False, verbose_name = "Compound ID", on_delete=models.DO_NOTHING,
        db_column="compound_id", related_name="%(class)s_compound_id")
    assay_id = models.ForeignKey(Assay, blank=False, verbose_name = "Assay", on_delete=models.DO_NOTHING,
        db_column="assay_id", related_name="%(class)s_assay_id")
    source_id = models.ForeignKey(Source, blank=False, verbose_name = "Source", on_delete=models.DO_NOTHING,
        db_column="source_id", related_name="%(class)s_source_id")


    # Activity Summary
    act_types = models.CharField(max_length=250, blank=True, verbose_name = "Active Types")
    n_assays = models.SmallIntegerField(default=-1, blank=True, verbose_name = "#Assay")
    n_actives = models.SmallIntegerField(default=-1, blank=True, verbose_name = "#Actives")
    act_score = models.DecimalField(default=-1, max_digits=10, decimal_places=2, verbose_name = "Act Score Ave")
    pscore = models.DecimalField(default=-1, max_digits=10, decimal_places=2, verbose_name = "pScore Ave")

    inhibit_max_ave = models.DecimalField(default=-1, max_digits=9, decimal_places=3, verbose_name = "Inhibition Max Ave")
    result_type = models.ForeignKey(Dictionary, blank=False, verbose_name = "Result Type", on_delete=models.DO_NOTHING,
        db_column="result_type", related_name="%(class)s_result_type")

    result_value = models.DecimalField(max_digits=9, decimal_places=2, default=0,verbose_name = "Result Value")
    result_prefix = models.CharField(max_length=25, blank=False, verbose_name = "Result Prefix")

    result_max    = models.CharField(max_length=20, blank=False, verbose_name = "Result Max")
    result_min    = models.CharField(max_length=20, blank=False, verbose_name = "Result Min")
    result_median = models.CharField(max_length=20, blank=False, verbose_name = "Result Median")

    result_unit = models.ForeignKey(Dictionary, blank=False, verbose_name = "Result Unit", on_delete=models.DO_NOTHING,
        db_column="result_unit", related_name="%(class)s_result_unit")

    result_std_geomean = models.CharField(max_length=20, blank=False, verbose_name = "Result Std GeoMean")
    result_std_unit = models.ForeignKey(Dictionary, blank=False, verbose_name = "Result Std Unit", on_delete=models.DO_NOTHING,
        db_column="result_std_unit", related_name="%(class)s_result_std_unit")

    pub_status = models.ForeignKey(Dictionary, null=True, blank=True, verbose_name = "Pub Status", on_delete=models.DO_NOTHING,
        db_column="pub_status", related_name="%(class)s_pub_statust")
    pub_date = models.DateField(null=True, blank=True,  editable=False, verbose_name="Published")


    class Meta:
        app_label = 'dcoadd'
        db_table = 'act_cmpd_dr'
        ordering=['compound_id']
        constraints = [
            models.UniqueConstraint(name='actcmpdr_pk_cst', fields=['compound_id', 'assay_id','source_id'], )
        ]        
        indexes = [
            models.Index(name="actcmpdr_cmp_idx", fields=['compound_id']),
            models.Index(name="actcmpdr_ass_idx", fields=['assay_id']),
            models.Index(name="actcmpdr_src_idx", fields=['source_id']),
            models.Index(name="actcmpdr_act_idx", fields=['act_score']),
            models.Index(name="actcmpdr_pscr_idx", fields=['pscore']),
            models.Index(name="actcmpdr_dmax_idx", fields=['inhibit_max_ave']),
            models.Index(name="actcmpdr_rtyp_idx", fields=['result_type']),
            models.Index(name="actcmpdr_rval_idx", fields=['result_value']),
            models.Index(name="actcmpdr_rpre_idx", fields=['result_prefix']),
            models.Index(name="actcmpdr_pst_idx", fields=['pub_status']),
        ]
    #------------------------------------------------
    @classmethod
    def get(cls,CompoundID, AssayID, SourceID,verbose=0):
        try:
            retInstance = cls.objects.get(compound_id = CompoundID, assay_id = AssayID, source_id= SourceID)
        except:
            if verbose:
                logger.warning(f"[ActCompoundSC Not Found] {CompoundID} {AssayID} {SourceID}")
            retInstance = None
        return(retInstance)

    #------------------------------------------------
    def set_actscores(self,verbose=0):
        self.act_score = ActScore_DR(self.result_median,self.result_unit.dict_value,DMax=self.inhibit_max_ave)
        self.pscore = pScore(self.result_std_geomean,self.result_std_unit.dict_value,self.inhibit_max_ave,MW=0,gtShift=3,drMax2=40)

#-------------------------------------------------------------------------------------------------
class Activity_Structure_DoseResponse(AuditModel):
    """
    List of Single Conc (Inhibition) Activities 
    """
#-------------------------------------------------------------------------------------------------
    Choice_Dictionary = {
        'result_unit':'Unit_Concentration',
        'result_std_unit':'Unit_Concentration',
        'result_type':'Result_Type',
        'pub_status':'Pub_Status',
    }

    ID_SEQUENCE = None

    #udi_key = models.CharField(max_length=24, unique=True, blank=False, verbose_name = "UDI")

    structure_id = models.ForeignKey(Chem_Structure, blank=False, verbose_name = "Structure ID", on_delete=models.DO_NOTHING,
        db_column="structure_id", related_name="%(class)s_structure_id")
    assay_id = models.ForeignKey(Assay, blank=False, verbose_name = "Assay", on_delete=models.DO_NOTHING,
        db_column="assay_id", related_name="%(class)s_assay_id")
    source_id = models.ForeignKey(Source, blank=False, verbose_name = "Source", on_delete=models.DO_NOTHING,
        db_column="source_id", related_name="%(class)s_source_id")

    # Activity Summary
    act_types = models.CharField(max_length=250, blank=True, verbose_name = "Active Types")
    n_assays = models.SmallIntegerField(default=-1, blank=True, verbose_name = "#Assay")
    n_actives = models.SmallIntegerField(default=-1, blank=True, verbose_name = "#Actives")
    act_score = models.DecimalField(default=-1, max_digits=10, decimal_places=2, verbose_name = "Act Score")
    pscore = models.DecimalField(default=-1, max_digits=10, decimal_places=2, verbose_name = "pScore")

    inhibit_max_ave = models.DecimalField(default=-1, max_digits=9, decimal_places=3, verbose_name = "Inhibition Max Ave")
    result_type = models.ForeignKey(Dictionary, blank=False, verbose_name = "Result Type", on_delete=models.DO_NOTHING,
        db_column="result_type", related_name="%(class)s_result_type")

    result_value = models.DecimalField(max_digits=9, decimal_places=2, default=0,verbose_name = "Result Value")
    result_prefix = models.CharField(max_length=25, blank=False, verbose_name = "Result Prefix")

    result_max    = models.CharField(max_length=20, blank=False, verbose_name = "Result Max")
    result_min    = models.CharField(max_length=20, blank=False, verbose_name = "Result Min")
    result_median = models.CharField(max_length=20, blank=False, verbose_name = "Result Median")

    result_unit = models.ForeignKey(Dictionary, blank=False, verbose_name = "Result Unit", on_delete=models.DO_NOTHING,
        db_column="result_unit", related_name="%(class)s_result_unit")

    result_std_geomean = models.CharField(max_length=20, blank=False, verbose_name = "Result Std GeoMean")
    result_std_unit = models.ForeignKey(Dictionary, blank=False, verbose_name = "Result Std Unit", on_delete=models.DO_NOTHING,
        db_column="result_std_unit", related_name="%(class)s_result_std_unit")

    pub_status = models.ForeignKey(Dictionary, null=True, blank=True, verbose_name = "Pub Status", on_delete=models.DO_NOTHING,
        db_column="pub_status", related_name="%(class)s_pub_statust")
    pub_date = models.DateField(null=True, blank=True,  editable=False, verbose_name="Published")


    class Meta:
        app_label = 'dcoadd'
        db_table = 'act_struct_dr'
        ordering=['structure_id']
        constraints = [
            models.UniqueConstraint(name='actstrdr_pk_cst', fields=['structure_id', 'assay_id','source_id'], )
        ]        
        indexes = [
            models.Index(name="actstrdr_sid_idx", fields=['structure_id']),
            models.Index(name="actstrdr_ass_idx", fields=['assay_id']),
            models.Index(name="actstrdr_src_idx", fields=['source_id']),
            models.Index(name="actstrdr_act_idx", fields=['act_score']),
            models.Index(name="actstrdr_pscr_idx", fields=['pscore']),
            models.Index(name="actstrdr_dmax_idx", fields=['inhibit_max_ave']),
            models.Index(name="actstrdr_rtyp_idx", fields=['result_type']),
            models.Index(name="actstrdr_rval_idx", fields=['result_value']),
            models.Index(name="actstrdr_rpre_idx", fields=['result_prefix']),
            models.Index(name="actstrdr_pst_idx", fields=['pub_status']),
        ]

    #------------------------------------------------
    @classmethod
    def get(cls,StructureID, AssayID, SourceID,verbose=0):
        try:
            retInstance = cls.objects.get(structure_id = StructureID, assay_id = AssayID, source_id= SourceID)
        except:
            if verbose:
                logger.warning(f"[ActStructureDR Not Found] {StructureID} {AssayID} {SourceID}")
            retInstance = None
        return(retInstance)
    
    #------------------------------------------------
    def set_actscores(self,verbose=0):
        self.act_score = ActScore_DR(self.result_median,self.result_unit.dict_value,DMax=self.inhibit_max_ave)
        self.pscore = pScore(self.result_std_geomean,self.result_std_unit.dict_value,self.inhibit_max_ave,MW=0,gtShift=3,drMax2=40)



#-------------------------------------------------------------------------------------------------
class Activity_Structure_Inhibition(AuditModel):
    """
    List of Summary Activity for each Structure
    """
#-------------------------------------------------------------------------------------------------
    Choice_Dictionary = {
        'result_type':'Result_Type',
        'pub_status':'Pub_Status',
    }


    ID_SEQUENCE = None

    #udi_key = models.CharField(max_length=24, unique=True, blank=False, verbose_name = "UDI")

    structure_id = models.ForeignKey(Chem_Structure, blank=False, verbose_name = "Structure ID", on_delete=models.DO_NOTHING,
        db_column="structure_id", related_name="%(class)s_structure_id")
    assay_id = models.ForeignKey(Assay, blank=False, verbose_name = "Assay", on_delete=models.DO_NOTHING,
        db_column="assay_id", related_name="%(class)s_assay_id")
    source_id = models.ForeignKey(Source, blank=False, verbose_name = "Source", on_delete=models.DO_NOTHING,
        db_column="source_id", related_name="%(class)s_source_id")

    # Activity Summary
    act_types = models.CharField(max_length=250, blank=True, verbose_name = "Active Tupes")
    n_assays = models.SmallIntegerField(default=-1, blank=True, verbose_name = "#Assay")
    n_actives = models.SmallIntegerField(default=-1, blank=True, verbose_name = "#Actives")
    act_score = models.DecimalField(default=-1, max_digits=10, decimal_places=2, verbose_name = "Act Score")

    result_type = models.ForeignKey(Dictionary, blank=False, verbose_name = "Result Type", on_delete=models.DO_NOTHING,
        db_column="result_type", related_name="%(class)s_result_type")

    inhibition_ave = models.DecimalField(default=-1, max_digits=9, decimal_places=3, verbose_name = "Inhibition Ave")
    inhibition_std = models.DecimalField(default=-1, max_digits=9, decimal_places=3, verbose_name = "Inhibition Std")
    inhibition_min = models.DecimalField(default=-1, max_digits=9, decimal_places=3, verbose_name = "Inhibition Min")
    inhibition_max = models.DecimalField(default=-1, max_digits=9, decimal_places=3, verbose_name = "Inhibition Max")
    mscore_ave = models.DecimalField(max_digits=9, decimal_places=3, verbose_name = "MScore Max")

    pub_status = models.ForeignKey(Dictionary, null=True, blank=True, verbose_name = "Pub Status", on_delete=models.DO_NOTHING,
        db_column="pub_status", related_name="%(class)s_pub_statust")
    pub_date = models.DateField(null=True, blank=True,  editable=False, verbose_name="Published")


    #------------------------------------------------
    class Meta:
        app_label = 'dcoadd'
        db_table = 'act_struct_sc'
        ordering=['structure_id']
        constraints = [
            models.UniqueConstraint(name='actstrsc_pk_cst', fields=['structure_id', 'assay_id','source_id'], )
        ]        
        indexes = [
            models.Index(name="actstrsc_sid_idx", fields=['structure_id']),
            models.Index(name="actstrsc_ass_idx", fields=['assay_id']),
            models.Index(name="actstrsc_src_idx", fields=['source_id']),
            models.Index(name="actstrsc_act_idx", fields=['act_score']),
            models.Index(name="actstrsc_iave_idx", fields=['inhibition_ave']),
            models.Index(name="actstrsc_mave_idx", fields=['mscore_ave']),
            models.Index(name="actstrsc_rtyp_idx", fields=['result_type']),
            models.Index(name="actstrsc_pst_idx", fields=['pub_status']),
        ]

    #------------------------------------------------
    @classmethod
    def get(cls,StructureID, AssayID, SourceID,verbose=0):
        try:
            retInstance = cls.objects.get(structure_id = StructureID, assay_id = AssayID, source_id= SourceID)
        except:
            if verbose:
                logger.warning(f"[ActStructureSC Not Found] {StructureID} {AssayID} {SourceID}")
            retInstance = None
        return(retInstance)

    #------------------------------------------------
    def set_actscores(self,ZScore=False,verbose=0):
        if ZScore:
            self.act_score = ActScore_SC(self.inhibition_ave,self.mscore_ave)
        else:
            self.act_score = ActScore_SC(self.inhibition_ave)

# #-------------------------------------------------------------------------------------------------
# class Testplate(AuditModel):
#     """
#     List of Testplate for unique identifier of data point 
#     """
# #-------------------------------------------------------------------------------------------------
#     Choice_Dictionary = {
#         'readout_type':'Readout_Type',
#         'plate_quality':'Plate_Quality',
#     }
    
#     ID_SEQUENCE = 'Testplate'
#     ID_PREFIX = 'TPW'
#     ID_PAD = 5

#     testplate_id = models.CharField(max_length=15,primary_key=True, verbose_name = "Project ID")
#     assay_id = models.ForeignKey(Assay, null=True, blank=True, verbose_name = "Assay", on_delete=models.DO_NOTHING,
#         db_column="assay_id", related_name="%(class)s_assay_id")
#     source_id = models.ForeignKey(Source, null=True, blank=True, verbose_name = "Source", on_delete=models.DO_NOTHING,
#         db_column="source_id", related_name="%(class)s_source_id")
#     source_code = models.CharField(max_length=150, blank=True, verbose_name = "Source Code")

#     readout_type = models.ForeignKey(Dictionary, null=True, blank=True, verbose_name = "Readout Type", on_delete=models.DO_NOTHING,
#         db_column="readout_type", related_name="%(class)s_readout_type")
#     plate_size = models.CharField(max_length=25, blank=True, verbose_name = "Plate Size")
#     plate_material = models.CharField(max_length=25, blank=True, verbose_name = "Plate Material")

#     positive_control = ArrayField(models.DecimalField(max_digits=7, decimal_places=2),size=4)
#     negative_control = ArrayField(models.DecimalField(max_digits=7, decimal_places=2),size=4)
#     sample_stats = ArrayField(models.DecimalField(max_digits=7, decimal_places=2),size=4)
#     edge_stats = ArrayField(models.DecimalField(max_digits=7, decimal_places=2),size=2)
#     zfactor = models.DecimalField(max_digits=7, decimal_places=2)
#     plate_qc = models.DecimalField(max_digits=7, decimal_places=2)
#     plate_quality = models.ForeignKey(Dictionary, null=True, blank=True, verbose_name = "Plate Quality", on_delete=models.DO_NOTHING,
#         db_column="plate_quality", related_name="%(class)s_plate_quality")

#     class Meta:
#         app_label = 'dcoadd'
#         db_table = 'testplate'
#         ordering=['testplate_id']
#         indexes = [
#             models.Index(name="tpw_ass_idx", fields=['assay_id']),
#             models.Index(name="tpw_src_idx", fields=['source_id']),
#         ]

#     #------------------------------------------------
#     # def save(self, *args, **kwargs):
#     #     if not self.testplate_id:
#     #         self.testplate_id = self.next_id()
#     #         if self.testplate_id: 
#     #             super(Testplate, self).save(*args, **kwargs)
#     #     else:
#     #         super(Testplate, self).save(*args, **kwargs) 

