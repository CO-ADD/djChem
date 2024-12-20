#
# Database Router 
#

from django.conf import settings

#--------------------------------------------------------------------------
# General Router Class 
#  relying on Models having
#   class Meta:
#       app_label = "<db-route>"
#
#--------------------------------------------------------------------------
class DatabaseRouter(object):
#--------------------------------------------------------------------------
    #
    # Settings for Routes
    #   add corresponding router based on app_label 
    #
    route_app_labels = {
        'default': {'auth', 'contenttypes','apputil'},
        'dcoadd': {'dcoadd'},
        }

    def db_for_read(self, model, **hints):
        for dbroute in self.route_app_labels:
            if model._meta.app_label in self.route_app_labels[dbroute]:
                return dbroute
        return None

    def db_for_write(self, model, **hints):
        for dbroute in self.route_app_labels:
            if model._meta.app_label in self.route_app_labels[dbroute]:
                return dbroute
        return None

    def allow_relation(self, obj1, obj2, **hints):
        for dbroute in self.route_app_labels:
            if (
                obj1._meta.app_label in self.route_app_labels[dbroute] or
                obj2._meta.app_label in self.route_app_labels[dbroute]
            ):
                return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        for dbroute in self.route_app_labels:
            if app_label in self.route_app_labels[dbroute]:
                return db == dbroute
        return None