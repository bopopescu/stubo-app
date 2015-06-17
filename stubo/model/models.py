from mongoengine import *
import logging
import hashlib
import json

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
            return ScenarioStub.objects(scenario=name).oder_by('stub.priority')
        else:
            return ScenarioStub.objects(scenario=self.name).order_by('stub.priority')

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
        """
        Counts stubs that belong to this scenario
        :rtype : Integer
        :param name: optional parameter Scenario name, skip it if you want to modify current initialized object
        :return: integer with stubs count
        """
        if name:
            # TODO: this fork should be removed after proper testing and name passing should not be allowed
            return ScenarioStub.objects(scenario=name).count()
        else:
            return ScenarioStub.objects(scenario=self.name).count()

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
                # try getting scenario name
                scenario_obj = Scenario.objects.get(name=name)
                self.get_pre_stubs(name).detele()
                self.get_stubs(name).delete()
                scenario_obj.delete()
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
            stubs_deleted = ScenarioStub.objects(Q(stub__recorded__lte=recorded) & Q(scenario=name)).delete()
            prestubs_deleted = PreScenarioStub.objects(Q(stub__recorded__lte=recorded) & Q(scenario=name)).delete()
            if not self.stub_count(name):
                Scenario.objects(name=name).delete()
        else:
            # get all stubs and pre stubs for this Scenario and filter based on recorded date and delete them
            stubs_deleted = ScenarioStub.objects(Q(stub__recorded__lte=recorded) & Q(scenario=self.name)).delete()
            prestubs_deleted = PreScenarioStub.objects(Q(stub__recorded__lte=recorded) & Q(scenario=self.name)).delete()
            # if no stubs remain for this scenario - delete scenario object
            if not self.stub_count():
                self.delete()
        msg = "Scenario Stubs deleted: %s. Pre Scenario Stubs deleted: %s." % (stubs_deleted, prestubs_deleted)
        log.debug(msg)

    def insert_stub(self, doc, stateful):
        from stubo.model.stub import Stub
        matchers = doc['stub'].contains_matchers()
        scenario = doc['scenario']

        stubs_cursor = self.get_stubs(scenario)
        if stubs_cursor.count():
            for stub in stubs_cursor:
                the_stub = Stub(stub['stub'], scenario)
                if matchers and matchers == the_stub.contains_matchers():
                    if not stateful and \
                                    doc['stub'].response_body() == the_stub.response_body():
                        msg = 'duplicate stub found, not inserting.'
                        log.warn(msg)
                        return msg
                    log.debug('In scenario: {0} found exact match for matchers:'
                              ' {1}. Perform stateful update of stub.'.format(scenario,
                                                                              matchers))
                    response = the_stub.response_body()
                    response.extend(doc['stub'].response_body())
                    the_stub.set_response_body(response)
                    self.db.scenario_stub.update(
                        {'_id': ObjectId(stub['_id'])},
                        {'$set' : {'stub' : the_stub.payload}})
                    return 'updated with stateful response'
        doc['stub'] = doc['stub'].payload
        status = self.db.scenario_stub.insert(doc)
        return 'inserted scenario_stub: {0}'.format(status)


class ScenarioStub(Document):
    scenario = StringField(required=True)
    stub = DynamicField()
    stub_hash = StringField(default=None)

    meta = {
        'indexes': [
            {'fields': ['scenario',
                        'stub_hash']}
        ],
        'ordering': ['+stub.recorded']
    }

    def __unicode__(self):
        return self.stub_hash

    def create_hash(self):
        """
        Creates a hash for dictionary (stub payload)
        :return: hash or None if it fails
        """
        try:
            stub_hash = hashlib.md5(json.dumps(self.stub, sort_keys=True)).hexdigest()
            self.stub_hash = stub_hash
            self.save()
            return stub_hash
        except Exception as e:
            log.warn("Failed to create stub hash: %s" % e)
            return None

    def get_hash(self):
        """
        Gets hash for current stub. If it doesn't exist - creates new one and returns. For new hash creation (after stub
        update) use create_hash() method.
        :return: md5 hash value of the stub, returns None if hash creation failed
        """
        if self.stub_hash is not None:
            return self.stub_hash
        else:
            return self.create_hash()


class PreScenarioStub(Document):
    scenario = StringField(required=True)
    stub = DynamicField()
    fingerprint = StringField(default=None)

    meta = {
        'indexes': [
            {'fields': ['scenario']}
        ],
        'ordering': ['+stub.recorded']
    }

    def __unicode__(self):
        return self.scenario

