from mongoengine import *
import logging
from stubo.model.stub import Stub

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
        """
        Checks whether the stub doesn't exist in database and inserts it. If it does and stateful mode is set to True -
        updates current stub
        :param doc: Dictionary containing Stub object and scenario name
        :param stateful: True or False value to specify whether to update stub or not
        :return: message with status
        """
        # Getting matchers for current stub
        matchers = doc['stub'].contains_matchers()[0]

        # Getting Stubs for this Scenario with exact body pattern match
        matched_stub = ScenarioStub.objects(Q(scenario=self.name) &
                                            Q(matcher=matchers))
        # If there are matched stubs - check response body
        if matched_stub:
            # Q complex query returns a list, we only need one (and only) member
            matched_stub = matched_stub[0]
            the_stub = Stub(matched_stub['stub'], self.name)

            # Check whether stateful insert or not and whether response body matches
            if not stateful and the_stub.response_body() == matched_stub.response_body():
                msg = 'Duplicate stub found, not inserting.'
                log.warn(msg)
                return msg

            # 'stateful' True so extending response body
            log.debug('In scenario: {0} found exact match for matcher:'
                      ' {1}. Performing stateful update of stub.'.format(self.name, matchers))
            response = the_stub.response_body()
            response.extend(doc['stub'].response_body())
            the_stub.set_response_body(response)
            # Assigning new payload
            matched_stub['stub'] = the_stub.payload
            # Saving stub
            matched_stub.save()
            return 'updated with stateful response'
        else:
            # If no matches found - insert a new stub
            stub_obj = ScenarioStub(scenario=self.name, stub=doc['stub'].payload,
                                    matcher=matchers)
            stub_obj.save()
            return 'inserted scenario_stub: {0}'.format(stub_obj)


class Stub(Document):
    scenario = StringField(required=True)
    priority = IntField(default=None)
    recorded = StringField(default=None)

    # request - urlPath
    request_path = StringField(default=None)
    request_query_args = StringField(default=None)
    # previously stored in ScenarioStub.stub.request.bodyPatterns.contains
    contains_matchers = ListField(StringField(default=None))
    # previously stored in ScenarioStub.stub.request.bodyPatterns
    request_method = StringField(default=None)

    # args - dictionary for storing args
    args = DictField(default=None)

    # response
    response_body = StringField(default=None)
    response_headers = StringField(default=None)
    response_status = IntField(default=None)
    # delayPolicy
    delay_policy = DynamicField(default=None)

    module = DynamicField(default=None)

    meta = {
        'indexes': [
            {'fields': ['scenario', 'contains_matchers']}
        ],
        'ordering': ['+recorded']
    }

    def __unicode__(self):
        return self.scenario

    def space_used(self):
        return self.__len__()

    def number_of_matchers(self):
        return len(self.matchers or [])

    def host(self):
        try:
            return self.scenario.split(':')[0]
        except Exception as e:
            log.debug(e)
            return None



class ScenarioStub(Document):
    scenario = StringField(required=True)
    stub = DynamicField()
    # Matcher is used to quickly identify existing stubs during recording
    matcher = StringField(default=None)

    meta = {
        'indexes': [
            {'fields': ['scenario', 'matcher']}
        ],
        'ordering': ['+stub.recorded']
    }

    def __unicode__(self):
        return self.scenario or u''

    def response_body(self):
        """
        Gets Stub's response body
        :return: Body string or None if it doesn't exist
        """
        try:
            return dict(self.stub.items())['response']['body']
        except Exception as e:
            log.warn("Couldn't get body for stub witch matcher: %s. Error: %s" % (self.matcher, e))
            return None



class PreScenarioStub(Document):
    scenario = StringField(required=True)
    stub = DynamicField()

    meta = {
        'indexes': [
            {'fields': ['scenario']}
        ],
        'ordering': ['+stub.recorded']
    }

    def __unicode__(self):
        return self.scenario

