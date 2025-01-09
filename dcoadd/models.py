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
#from apputil.utils.data import strList_to_List
#from dcollab.models import Collab_Group, Collab_User
#from dchem.models import Chem_Structure
from adjCHEM.constants import *


#=================================================================================================
class Chem_Structure(AuditModel):
    """
    List of Chemical Structures
    """
#=================================================================================================

    Choice_Dictionary = {
        'structure_type':'Structure_Type',
    }

    ID_SEQUENCE = 'ChemStructure'
    ID_PREFIX = 'CCS'
    ID_PAD = 9

    structure_id = models.CharField(max_length=15, primary_key=True, verbose_name = "Structure ID")
    structure_code = models.CharField(max_length=15, blank=True, verbose_name = "Structure Code")
    structure_name = models.CharField(max_length=50, blank=True, verbose_name = "Structure Name")
    structure_type = models.ForeignKey(Dictionary, null=True, blank=True, verbose_name = "Type", on_delete=models.DO_NOTHING,
        db_column="structure_type", related_name="%(class)s_structuretype")
    smol = models.MolField(verbose_name = "MOL")	
    tfp2 = models.BfpField(null=True,blank=True,verbose_name = "Topological-Torsion FP")	
    ffp2 = models.BfpField(null=True,blank=True,verbose_name = "Feature Morgan FP (FCFP)")
    mfp2 = models.BfpField(null=True,blank=True,verbose_name = "Morgan FP (ECFP)")

    nfrag = models.PositiveSmallIntegerField(default=1, blank=True, verbose_name ="nFrag")
    charge = models.DecimalField(max_digits=10, decimal_places=2,  blank=True, verbose_name ="Charge")
    
    # Calculated by Trigger Function
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
        ordering=['structure_name']
        indexes = [
            models.Index(name="cstruct_dname_idx", fields=['structure_name']),
            models.Index(name="cstruct_dcode_idx", fields=['structure_code']),
            models.Index(name="cstruct_inchi_idx", fields=['inchikey']),
            models.Index(name="cstruct_mf_idx", fields=['mf']),
            models.Index(name="cstruct_mw_idx", fields=['mw']),
            models.Index(name="cstruct_natoms_idx", fields=['natoms']),
            models.Index(name="cstruct_nfrag_idx", fields=['nfrag']),
            models.Index(name="cstruct_charge_idx", fields=['charge']),
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
    def __repr__(self) -> str:
        return f"{self.structure_name} ({self.structure_id})"

    #------------------------------------------------
    @classmethod
    def get(cls,StructureID=None,StructureName=None,verbose=0):
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
            djchem.clean_Fields()
            validDict = djchem.validate()
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
        self.mw = Chem.Descriptors.MolWt(self.smol)
        self.mf = Chem.rdMolDescriptors.CalcMolFormula(self.smol)
    
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
    def __repr__(self) -> str:
        return f"{self.project_id}  {self.source_id}"

    #------------------------------------------------
    # def save(self, *args, **kwargs):
    #     if not self.project_id:
    #         self.project_id = self.next_id()
    #         if self.project_id: 
    #             super(Project, self).save(*args, **kwargs)
    #     else:
    #         super(Project, self).save(*args, **kwargs) 


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
    def __repr__(self) -> str:
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

    #------------------------------------------------
    # def save(self, *args, **kwargs):
    #     if not self.compound_id:
    #         self.compound_id = self.next_id()
    #         if self.compound_id:
    #             super(Compound, self).save(*args, **kwargs)
    #     else:
    #         super(Compound, self).save(*args, **kwargs) 


#-------------------------------------------------------------------------------------------------
class Activity_DoseResponse(AuditModel):
    """
    List of Single Conc (Inhibition) Activities 
    """
#-------------------------------------------------------------------------------------------------
    Choice_Dictionary = {
        'conc_unit':'Unit_Concentration',
        'conc_type':'Conc_Type',
        'result_type':'Result_Type',
        'result_unit':'Unit',
        'data_quality':'Data_Quality',
        'pub_status':'Pub_Status',
    }

    udi_key = models.CharField(max_length=24, unique=True, blank=False, verbose_name = "UDI")

    compound_id = models.ForeignKey(Compound, blank=False, verbose_name = "Compound ID", on_delete=models.DO_NOTHING,
        db_column="compound_id", related_name="%(class)s_compound_id")
    assay_id = models.ForeignKey(Assay, blank=False, verbose_name = "Assay", on_delete=models.DO_NOTHING,
        db_column="assay_id", related_name="%(class)s_assay_id")
    source_id = models.ForeignKey(Source, blank=False, verbose_name = "Source", on_delete=models.DO_NOTHING,
        db_column="source_id", related_name="%(class)s_source_id")
    
    result_type = models.ForeignKey(Dictionary, blank=False, verbose_name = "Result Type", on_delete=models.DO_NOTHING,
        db_column="result_type", related_name="%(class)s_result_type")
        
    result_str = models.CharField(max_length=24, blank=False, verbose_name = "Result ")
    result_value = models.DecimalField(max_digits=9, decimal_places=2, default=0,verbose_name = "Result Value")
    result_unit = models.ForeignKey(Dictionary, blank=False, verbose_name = "Result Unit", on_delete=models.DO_NOTHING,
        db_column="result_unit", related_name="%(class)s_result_unit")
    result_conc_type = models.ForeignKey(Dictionary, null=True, blank=True, verbose_name = "Conc Type", on_delete=models.DO_NOTHING,
        db_column="conc_type", related_name="%(class)s_conc_type")
    
    dmax = models.DecimalField(max_digits=9, decimal_places=2, default=0,verbose_name = "DMax")
    act_score = models.DecimalField(max_digits=9, decimal_places=2, default=-1,verbose_name = "Act Score")
    p_score = models.DecimalField(max_digits=9, decimal_places=2, default=-1,verbose_name = "pScore")
    data_quality = models.ForeignKey(Dictionary, null=True, blank=True, verbose_name = "Result Type", on_delete=models.DO_NOTHING,
        db_column="data_quality", related_name="%(class)s_data_quality")

    class Meta:
        app_label = 'dcoadd'
        db_table = 'act_doseresponse'
        ordering=['compound_id']
        indexes = [
            models.Index(name="adr_cmp_idx", fields=['compound_id']),
            models.Index(name="adr_ass_idx", fields=['assay_id']),
            models.Index(name="adr_src_idx", fields=['source_id']),
            models.Index(name="adr_rty_idx", fields=['result_type']),
            models.Index(name="adr_act_idx", fields=['act_score']),
            models.Index(name="adr_dqc_idx", fields=['data_quality']),
        ]

#-------------------------------------------------------------------------------------------------
class Activity_SingleConc(AuditModel):
    """
    List of Single Conc (Inhibition) Activities 
    """
#-------------------------------------------------------------------------------------------------
    Choice_Dictionary = {
        'conc_unit':'Unit_Concentration',
        'conc_type':'Conc_Type',
        'result_type':'Result_Type',
        'result_unit':'Unit',
        'data_quality':'Data_Quality',
        'pub_status':'Pub_Status',
    }

    udi_key = models.CharField(max_length=24, unique=True, blank=False, verbose_name = "UDI")

    compound_id = models.ForeignKey(Compound, blank=False, verbose_name = "Compound ID", on_delete=models.DO_NOTHING,
        db_column="compound_id", related_name="%(class)s_compound_id")
    assay_id = models.ForeignKey(Assay, blank=False, verbose_name = "Assay", on_delete=models.DO_NOTHING,
        db_column="assay_id", related_name="%(class)s_assay_id")
    source_id = models.ForeignKey(Source, blank=False, verbose_name = "Source", on_delete=models.DO_NOTHING,
        db_column="source_id", related_name="%(class)s_source_id")
    
    result_type = models.ForeignKey(Dictionary, blank=False, verbose_name = "Result Type", on_delete=models.DO_NOTHING,
        db_column="result_type", related_name="%(class)s_result_type")
    
    conc = models.DecimalField(max_digits=9, decimal_places=2, default=0,verbose_name = "Conc")
    conc_unit = models.ForeignKey(Dictionary, null=True, blank=True, verbose_name = "Conc Unit", on_delete=models.DO_NOTHING,
        db_column="conc_unit", related_name="%(class)s_conc_unit")
    conc_type = models.ForeignKey(Dictionary, null=True, blank=True, verbose_name = "Conc Type", on_delete=models.DO_NOTHING,
        db_column="conc_type", related_name="%(class)s_conc_type")
    
    result_value = models.DecimalField(max_digits=9, decimal_places=2, default=0,verbose_name = "Result Value")
    result_unit = models.ForeignKey(Dictionary, blank=False, verbose_name = "Result Unit", on_delete=models.DO_NOTHING,
        db_column="result_unit", related_name="%(class)s_result_unit")
    
    zscore = models.DecimalField(max_digits=9, decimal_places=2, default=0,verbose_name = "ZScore")
    act_score = models.DecimalField(max_digits=9, decimal_places=2, default=-1,verbose_name = "Act Score")
    data_quality = models.ForeignKey(Dictionary, null=True, blank=True, verbose_name = "Result Type", on_delete=models.DO_NOTHING,
        db_column="data_quality", related_name="%(class)s_data_quality")

    class Meta:
        app_label = 'dcoadd'
        db_table = 'act_singleconc'
        ordering=['compound_id']
        indexes = [
            models.Index(name="asc_cmp_idx", fields=['compound_id']),
            models.Index(name="asc_ass_idx", fields=['assay_id']),
            models.Index(name="asc_src_idx", fields=['source_id']),
            models.Index(name="asc_rty_idx", fields=['result_type']),
            models.Index(name="asc_act_idx", fields=['act_score']),
            models.Index(name="asc_dqc_idx", fields=['data_quality']),
        ]

#-------------------------------------------------------------------------------------------------
class Testplate(AuditModel):
    """
    List of Testplate for unique identifier of data point 
    """
#-------------------------------------------------------------------------------------------------
    Choice_Dictionary = {
        'readout_type':'Readout_Type',
        'plate_quality':'Plate_Quality',
    }
    
    ID_SEQUENCE = 'Testplate'
    ID_PREFIX = 'TPW'
    ID_PAD = 5

    testplate_id = models.CharField(max_length=15,primary_key=True, verbose_name = "Project ID")
    assay_id = models.ForeignKey(Assay, null=True, blank=True, verbose_name = "Assay", on_delete=models.DO_NOTHING,
        db_column="assay_id", related_name="%(class)s_assay_id")
    source_id = models.ForeignKey(Source, null=True, blank=True, verbose_name = "Source", on_delete=models.DO_NOTHING,
        db_column="source_id", related_name="%(class)s_source_id")
    source_code = models.CharField(max_length=150, blank=True, verbose_name = "Source Code")

    readout_type = models.ForeignKey(Dictionary, null=True, blank=True, verbose_name = "Readout Type", on_delete=models.DO_NOTHING,
        db_column="readout_type", related_name="%(class)s_readout_type")
    plate_size = models.CharField(max_length=25, blank=True, verbose_name = "Plate Size")
    plate_material = models.CharField(max_length=25, blank=True, verbose_name = "Plate Material")

    positive_control = ArrayField(models.DecimalField(max_digits=7, decimal_places=2),size=4)
    negative_control = ArrayField(models.DecimalField(max_digits=7, decimal_places=2),size=4)
    sample_stats = ArrayField(models.DecimalField(max_digits=7, decimal_places=2),size=4)
    edge_stats = ArrayField(models.DecimalField(max_digits=7, decimal_places=2),size=2)
    zfactor = models.DecimalField(max_digits=7, decimal_places=2)
    plate_qc = models.DecimalField(max_digits=7, decimal_places=2)
    plate_quality = models.ForeignKey(Dictionary, null=True, blank=True, verbose_name = "Plate Quality", on_delete=models.DO_NOTHING,
        db_column="plate_quality", related_name="%(class)s_plate_quality")

    class Meta:
        app_label = 'dcoadd'
        db_table = 'testplate'
        ordering=['testplate_id']
        indexes = [
            models.Index(name="tpw_ass_idx", fields=['assay_id']),
            models.Index(name="tpw_src_idx", fields=['source_id']),
        ]

    #------------------------------------------------
    # def save(self, *args, **kwargs):
    #     if not self.testplate_id:
    #         self.testplate_id = self.next_id()
    #         if self.testplate_id: 
    #             super(Testplate, self).save(*args, **kwargs)
    #     else:
    #         super(Testplate, self).save(*args, **kwargs) 

