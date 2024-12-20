#
from django.core.validators import RegexValidator

#
# -adjdCHEM Settings ---------------------------------------------------

SAMPLE_SEP = "_"
SAMPLEBATCH_SEP = "_"
COMPOUND_SEP = '|'

AlphaNumeric = RegexValidator(r'^[0-9a-zA-Z]*$', 'Only alphanumeric characters are allowed.')
