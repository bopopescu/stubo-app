from mongoengine import *
import logging


log = logging.getLogger(__name__)


class Scenario(Document):
    name = StringField(required=True)

    meta = {
        'indexes': [
            {'fields': ['name']}
        ]
    }

    def __unicode__(self):
        return self.name

    def get_stubs(self, name=None):
        """
        Gets all scenario_stub objects from the database for the current initialized objects. If a name is passed -
        gets stubs for that particular scenario. Name passing parameter will become redundant and is only implemented
        here for compatibility.
        :rtype : List
        :param name: optional parameter Scenario name, skip it if you want to modify current initialized object
        :return: a list of stubs
        """
        if name:
            # TODO: this fork should be removed after proper testing and name passing should not be allowed
            return ScenarioStub.objects.filter(scenario=name).oder_by('stub.priority')
        else:
            return ScenarioStub.objects.filter(scenario=self.name).order_by('stub.priority')

    def get_pre_stubs(self, name=None):
        """
        Gets all pre_scenario_stub objects from the database for the current initialized objects. If a name is passed -
        gets pre stubs for that particular scenario. Name passing parameter will become redundant and is only implemented
        here for compatibility.
        :rtype : List
        :param name: optional parameter Scenario name, skip it if you want to modify current initialized object
        :return: a list of pre stubs
        """
        if name:
            # TODO: this fork should be removed after proper testing and name passing should not be allowed
            return PreScenarioStub.objects.filter(scenario=name).oder_by('stub.priority')
        else:
            return PreScenarioStub.objects.filter(scenario=self.name).order_by('stub.priority')

    def stub_count(self, name=None):
        # TODO: this could be transformed to parameter instead of function
        """
        Counts stubs that belong to this scenario
        :rtype : Integer
        :param name: optional parameter Scenario name, skip it if you want to modify current initialized object
        :return: integer with stubs count
        """
        if name:
            # TODO: this fork should be removed after proper testing and name passing should not be allowed
            return ScenarioStub.objects.filter(scenario=name).count()
        else:
            return ScenarioStub.objects.filter(scenario=self.name).count()

    def insert_pre_stub(self, name=None, stub=None):
        """
        Inserts pre scenario stub
        :param name: optional parameter Scenario name, skip it if you want to modify current initialized object
        :param stub: stub payload
        :return:
        """
        if name:
            # TODO: this fork should be removed after proper testing and name passing should not be allowed
            pre_scenario_obj = PreScenarioStub(scenario=name,
                                               stub=stub.payload)
        else:
            pre_scenario_obj = PreScenarioStub(scenario=self.name,
                                               stub=stub.payload)

        inserted_object = PreScenarioStub.objects.insert(pre_scenario_obj)
        msg = "Stub inserted. Scenario: %s" % inserted_object.scenario
        # return 'inserted pre_scenario_stub: {0}'.format(inserted_object)
        log.debug(msg)
        return msg

    def remove_all(self, name=None):
        """
        Deletes stubs and pre stubs that are related to this Scenario object
        :param name: optional parameter Scenario name, skip it if you want to modify current initialized object
        :return: True if delete was successful, False if object does not exist.
        """
        if name:
            # TODO: this fork should be removed after proper testing and name passing should not be allowed
            try:
                Scenario.objects.get(name=name)
                self.get_pre_stubs(name).detele()
                self.get_stubs(name).delete()
                return True
            except DoesNotExist:
                msg = "Scenario not found, couldn't delete it. Scenario name: %s" % name
                log.warn(msg)
                return False
        else:
            self.get_pre_stubs().detele()
            self.get_stubs().delete()
            self.delete()
            return True

    def remove_all_older_than(self, name, recorded):
        """
        Removes all stubs and pre stubs of current or specified Scenario. If after deletion Scenario doesn't have any
        more stubs or pre stubs - Scenario gets deleted as well.
        :param name: optional parameter Scenario name, skip it if you want to modify current initialized object
        :param recorded: yyyy-mm-dd
        """

        if name:
            # TODO: this fork should be removed after proper testing and name passing should not be allowed
            stubs_deleted = ScenarioStub.objects(Q(stub__recorded__gte=recorded) & Q(scenario=name)).delete()
            prestubs_deleted = PreScenarioStub.objects(Q(stub__recorded__gte=recorded) & Q(scenario=name)).delete()
            msg = "Scenario Stubs deleted: %s. Pre Scenario Stubs deleted: %s." % (stubs_deleted, prestubs_deleted)
            log.debug(msg)
            if not self.stub_count(name):
                Scenario.objects(name=name).delete()
        else:
            stubs_deleted = ScenarioStub.objects(Q(stub__recorded__gte=recorded) & Q(scenario=self.name)).delete()
            prestubs_deleted = PreScenarioStub.objects(Q(stub__recorded__gte=recorded) & Q(scenario=self.name)).delete()
            msg = "Scenario Stubs deleted: %s. Pre Scenario Stubs deleted: %s." % (stubs_deleted, prestubs_deleted)
            log.debug(msg)
            if not self.stub_count(name):
                self.delete()


class ScenarioStub(Document):
    scenario = StringField(required=True)
    stub = DynamicField()

    meta = {
        'indexes': [
            {'fields': ['scenario']}
        ]
    }

    def __unicode__(self):
        return self.scenario


class PreScenarioStub(Document):
    scenario = StringField(required=True)
    stub = DynamicField()

    meta = {
        'indexes': [
            {'fields': ['scenario']}
        ]
    }

    def __unicode__(self):
        return self.scenario
