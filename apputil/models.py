import pandas as pd
import numpy as np
from sequences import Sequence
from asgiref.sync import sync_to_async

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.postgres.fields import ArrayField
from django.urls import reverse
from django import forms
from django.utils import timezone
import logging

#-------------------------------------------------------------------------------------------------
class ApplicationUser(AbstractUser):    
#-------------------------------------------------------------------------------------------------
    HEADER_FIELDS = {
        'name':'Name',
        'username':'Username', 
        'first_name':'First Name',  
        'last_name':'Last Name',
        'initials':'Initial',
        'email':'Email',
        'permission':'Permissions',
        'is_appuser':'AppUser',
        'is_active':'Active', 
        }

    username = models.CharField(unique=True, max_length=55, verbose_name='Username')                    # uqjzuegg 
    name = models.CharField(primary_key=True,  max_length=50, verbose_name='Name')                      # J.Zuegg
    initials = models.CharField(max_length=5, null=True, blank=True, verbose_name='Initials')           # JZG
    organisation = models.CharField(max_length=250, null=True, blank=True, verbose_name='Organisation') # University of Queensland
    department = models.CharField(max_length=250, null=True, blank=True, verbose_name='Department')     # Institute for Molecular Bioscience
    group = models.CharField(max_length=50, null=True, blank=True, verbose_name='Group')                # Blaskovich
    phone = models.CharField(max_length=25, null=True, blank=True, verbose_name='Name')                 # +61 7 344 62994
    permission = models.CharField(max_length=10, default = 'No', null=False, verbose_name='Permission') # application permissions .. Read, Write, Delete, Admin ..
    is_appuser=models.BooleanField(default=True,verbose_name='IsAppUser')

    #------------------------------------------------
    class Meta:
        db_table = 'app_user'
        ordering=['name']

    #------------------------------------------------  
    def __str__(self) -> str:
        return f"{self.name}" 

    #------------------------------------------------
    # Returns an User instance if found by name
    @classmethod
    def get(cls,UserName):
        try:
            retInstance = cls.objects.get(name=UserName)
        except:
            retInstance = None
        return(retInstance)

    #------------------------------------------------
    # Returns an User instance if found by name
    @classmethod
    def exists(cls,UserName):
        return cls.objects.filter(name=UserName).exists()

    # --------------------------------------------------------------------------
    def has_permission(self,strPermission) -> bool:
    #
    # Returns True/False if User has strPermission 
    #   checks if strPermission/self.permission in [Read, Write, Delete, Admin]
    # --------------------------------------------------------------------------
        _Permissions = {
            'Read':1,
            'Write':2,
            # 'Delete':3,
            'Admin':10,
        }
        if strPermission in _Permissions:
            if self.permission in _Permissions: 
                return(_Permissions[self.permission]>=_Permissions[strPermission])
            else:
                return(False)
        else:
            return(False)

    # --------------------------------------------------------------------------
    # get field names in postgres in the order provided by constants.py
    @classmethod
    def get_databasefields(self, fields=None):
        if fields:
            databasefields=fields.keys()
        else:
            databasefields=None
        return databasefields
    # # get field verbose or customized name in the order provided by constants.py

    @classmethod
    def get_fields(cls, fields=None):
        if fields is None:
            fields = cls.HEADER_FIELDS
        if fields:
            select_fields=[fields[f.name] for f in cls._meta.fields if f.name in fields.keys()]
        else:
            select_fields=None
        return select_fields


    # get field name in model Class in the order provided by constants.py
    @classmethod
    def get_modelfields(cls, fields=HEADER_FIELDS):
        if fields:
            model_fields=[f.name for f in cls._meta.fields if f.name in fields.keys()]
        else:
            model_fields=None
        return model_fields

#-------------------------------------------------------------------------------------------------
class AuditModel(models.Model):
    """
    An abstract base class model that provides audit informations 
    """
#-------------------------------------------------------------------------------------------------
    # object status -> indicated by number in database:
    DELETED   = -9
    INVALID   = -1
    UNDEFINED =  0
    VALID     =  1
    CONFIRMED =  2

    OWNER           = "djChem" # Defaut username
    

    # VALID_STATUS 0: Valid (New or Update) to save, -1: Invalid unable to save, 1: Valid no update required 

    VALID_STATUS    = False
    HEADER_FIELDS   = {}
    CARDS_FIELDS   = {}

    ID_SEQUENCE = "General"
    ID_PREFIX = "AAA"
    ID_PAD = 6

    astatus = models.IntegerField(verbose_name = "Status", default = 0, db_index = True, editable=False)
    acreated_at = models.DateTimeField(null=False, editable=False, verbose_name="Created at")
    aupdated_at = models.DateTimeField(null=True,  editable=False, verbose_name="Updated at")
    adeleted_at = models.DateTimeField(null=True,  editable=False, verbose_name="Deleted at",)
    acreated = models.ForeignKey(ApplicationUser, null=False, verbose_name = "Created by", 
        related_name="%(class)s_acreated_by", editable=False, on_delete=models.DO_NOTHING)
    aupdated = models.ForeignKey(ApplicationUser, null=True,  verbose_name = "Updated by", 
        related_name="%(class)s_aupdated_by", editable=False, on_delete=models.DO_NOTHING)
    adeleted = models.ForeignKey(ApplicationUser, null=True,  verbose_name = "Deleted by", 
        related_name="%(class)s_adeleted_by", editable=False, on_delete=models.DO_NOTHING)

    #------------------------------------------------
    class Meta:
        abstract = True
        ordering=['-acreated_at']
    
        #------------------------------------------------
    def __str__(self) -> str:
        return f"{self.pk}"
    #------------------------------------------------
    def __repr__(self) -> str:
        # return f"{self.__name__}: {self.pk}"
        return f"{self.pk}"

    #------------------------------------------------
    @classmethod
    def get(cls,pkID,verbose=0):
        try:
            retInstance = cls.objects.get(pk=pkID)
        except:
            if verbose:
                print(f"[{cls.__name__} Not Found] {pkID} ")
            retInstance = None
        return(retInstance)
    #------------------------------------------------
    @classmethod
    def exists(cls,pkID,verbose=0):
        return cls.objects.filter(pk=pkID).exists()

   #------------------------------------------------
    @classmethod
    def str_id(cls,clsNo) -> str:
        return(f"{cls.ID_PREFIX}{clsNo:0{cls.ID_PAD}d}")

    #------------------------------------------------
    @classmethod
    def next_id(cls) -> str:
        cls_IDSq=Sequence(cls.ID_SEQUENCE)
        cls_nextNo = next(cls_IDSq)
        cls_strID = cls.str_id(cls_nextNo)
        while cls.objects.filter(pk=cls_strID).exists():
            cls_nextNo = next(cls_IDSq)
            cls_strID = cls.str_id(cls_nextNo)
        return(cls_strID)    

    #------------------------------------------------
    def delete(self,**kwargs):
        appuser=kwargs.get("user")
        kwargs.pop("user",None)
        if appuser is None:
            appuser = ApplicationUser.objects.get(name=self.OWNER)

        self.astatus = self.DELETED
        self.adeleted_id = appuser
        self.adeleted_at = timezone.now()
        super(AuditModel,self).save(**kwargs)

    #------------------------------------------------
    def save(self, *args, **kwargs):
        #
        # Checks for application user
        #
        appuser=kwargs.get("user")
        kwargs.pop("user",None)
        if appuser is None:
            appuser = ApplicationUser.objects.get(name=self.OWNER)

        if not self.acreated_id:
            self.acreated_id = appuser
            self.acreated_at = timezone.now()       
        else:	
            self.aupdated_id = appuser
            self.aupdated_at = timezone.now()

        #
        # Checks if a clean=True is requested
        #   Default, via forms is False, but can be set via scripts/API
        #  
        modelClean=kwargs.get("clean")  
        kwargs.pop("clean",None)
        if modelClean:
            self.full_clean()

        #
        # Checks for PK
        #
        if not self.pk:
            self.pk = self.next_id()
            if self.pk: 
                super(AuditModel, self).save(*args, **kwargs)
        else:
            super(AuditModel, self).save(*args, **kwargs) 

    #------------------------------------------------
    def validate_fields(self,**kwargs):
    #
    # Validates the instance using full_clean
    # 
        retValid = {}
        try:
            self.full_clean(**kwargs)
        except ValidationError as e:
            for key in e.message_dict:
                _field = self._meta.get_field(key)
                #print(f"{key} PK:{_field.primary_key},Null:{_field.null},Blank:{_field.blank}")
                errMsgList = e.message_dict[key]
                retMsg = []
                for errMsg in errMsgList:
                    #print(f"[Validate] {key} -- {errMsg}")
        
                    if not _field.primary_key:
                        if 'This field cannot be null.' == errMsg: 
                            if not _field.null:
                                retMsg.append(errMsg)
                        elif 'This field cannot be blank.' == errMsg:
                            if not _field.blank:
                                retMsg.append(errMsg)
                        elif 'Ensure that there are no more than' in errMsg:
                            if _field.get_internal_type() != 'DecimalField':
                                retMsg.append(errMsg)
                        else:
                            retMsg.append(errMsg)

                if len(retMsg) > 0 :
                    retValid[key] = "; ".join(retMsg)
                #print(len(e.message_dict[key]))
                # if e.message_dict[key] == ['This field cannot be null.']:
                #     if not self._meta.get_field(key).null:
                #         retValid[key] = ", ".join(e.message_dict[key])
                # elif e.message_dict[key] == ['This field cannot be blank.']:
                #     if not self._meta.get_field(key).blank:
                #         retValid[key] = ", ".join(e.message_dict[key])
                # else:
                #     retValid[key] = ", ".join(e.message_dict[key])
        return(retValid)
             
    #------------------------------------------------
    def init_fields(self, default_Char="", default_Integer=0, default_Decimal=0.0):
        #
        # Sets 'None' fields in the instance according to Django guidelines 
        #   sets CharField    to "" (empty) or 'default' 
        #   sets IntegerField to 0 or 'default'
        #   sets DecimalField to 0.0 or 'default'
        #
            clFields = {}
            for field in self._meta.get_fields(include_parents=False):
                fType = field.get_internal_type()
                if fType == "IntegerField":
                    if hasattr(self,field.name):
                        if getattr(self,field.name) is None:
                            defValue = default_Integer
                            fDict = field.deconstruct()[3]
                            if 'default' in fDict:
                                defValue = fDict['default']
                            setattr(self,field.name,defValue)
                            clFields[field.name]=defValue
                if fType == "DecimalField":
                    if hasattr(self,field.name):
                        if getattr(self,field.name) is None:
                            defValue = default_Decimal
                            fDict = field.deconstruct()[3]
                            if 'default' in fDict:
                                defValue = fDict['default']
                            setattr(self,field.name,defValue)
                            clFields[field.name]=defValue
                elif fType == "CharField":
                    if hasattr(self,field.name):
                        if getattr(self,field.name) is None:
                            defValue = default_Char
                            fDict = field.deconstruct()[3]
                            if 'default' in fDict:
                                defValue = fDict['default']
                            setattr(self,field.name,defValue)
                            clFields[field.name]=defValue
            return(clFields)
#-------------------------------------------------------------------------------------------------
class Dictionary(AuditModel):
#-------------------------------------------------------------------------------------------------
    HEADER_FIELDS = {
        'dict_value':'Value', 
        'dict_class':'Class',  
        'dict_desc':'Description',
        'dict_sort':'Order',
        'dict_app' :'Application',  
    }
    
    dict_value =models.CharField(primary_key=True, unique=True, max_length=50, verbose_name = "Value"  )
    dict_class= models.CharField(max_length=30, verbose_name = "Class")
    dict_app= models.CharField(max_length=30, verbose_name = "Application")
    dict_desc = models.CharField(max_length=140, blank=True, verbose_name = "Description")
    dict_sort = models.IntegerField(default=0, verbose_name = "Order")
   
    #------------------------------------------------
    class Meta:
        app_label = 'apputil'
        db_table = 'app_dictionary'
        ordering=['dict_class','dict_value']
        indexes = [
            models.Index(name="dict_class_idx",fields=['dict_class']),
        ]
    #------------------------------------------------
    def __str__(self) -> str:
        return f"{self.dict_value}  {self.dict_class}"


    def __repr__(self) -> str:
        return f"{self.dict_value}|{self.dict_desc} {self.dict_class}"
        #return f"[{self.dict_class}] {self.dict_value} ({self.dict_desc})"

    def strtml(self)-> str:
        return f"{self.dict_value} <small class='not-visible'> {self.dict_desc} </small>"

    #------------------------------------------------
    @classmethod
    def get(cls,DictClass,DictValue=None,DictDesc=None,verbose=1):
    #
    # Returns a Dictionary instance if found 
    #    by dict_value
    #    by dict_desc (set dict_value = None)
    #
        if DictValue:
            try:
                retDict = cls.objects.get(dict_value=DictValue, dict_class=DictClass)
            except:
                if verbose:
                    print(f"[Dict Value Not Found] {DictValue} {DictClass}")
                retDict = None
        elif DictDesc:
            try:
                retDict = cls.objects.get(dict_desc=DictDesc, dict_class=DictClass)
            except:
                if verbose:
                    print(f"[Dict Desc Not Found] {DictDesc} {DictClass}")
                retDict = None
        else:
            retDict = None
        return(retDict)

    #------------------------------------------------
    @classmethod
    def exists(cls,DictClass,DictValue=None,DictDesc=None,verbose=1):
    #
    # Returns if Dictionary instance exists
    #    by dict_value
    #    by dict_desc (set dict_value = None)
    #
        if DictValue:
            retValue = cls.objects.filter(dict_value=DictValue, dict_class=DictClass).exists()
        elif DictDesc:
            retValue = cls.objects.filter(dict_desc=DictDesc, dict_class=DictClass).exists()
        else:
            retValue = False
        return(retValue)

    #------------------------------------------------
    @classmethod
    #
    # Returns the objects based on the default filter for dict_class= and aStatus>=0
    #
    def get_filterobj(cls,DictClass,showDeleted=False):
        if showDeleted:
            return cls.objects.filter(dict_class=DictClass)
        else:
            return cls.objects.filter(dict_class=DictClass, astatus__gte=0)

    #------------------------------------------------
    @classmethod
    #
    # Returns Dictionary entries for a DictClass as Choices
    #
    def get_aschoices(cls, DictClass, showDesc = True, sep = " | ", emptyChoice= ('--', ' <empty> ')):
        dictList = None
        choices=(emptyChoice,)
        # comment on initial migrations
        dictList=Dictionary.objects.filter(dict_class=DictClass).values('dict_value', 'dict_desc', 'dict_sort')
        if dictList:
            sortedlist = sorted(dictList, key=lambda d: d['dict_sort']) 
            if sortedlist:
                choices_values=tuple([tuple(d.values()) for d in sortedlist])
                if showDesc:
                    choices=tuple((a[0], a[0]+sep+a[1]) for a in choices_values)
                else:
                    choices=tuple((a[0], a[0]) for a in choices_values)
        return choices
