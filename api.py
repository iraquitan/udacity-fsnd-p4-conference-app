# -*- coding: utf-8 -*-
"""
 * Project: udacity-fsnd-p4-conference-app
 * Author name: Iraquitan Cordeiro Filho
 * Author login: iraquitan
 * File: api
 * Date: 3/23/16
 * Time: 1:24 AM
"""
from datetime import datetime
import json
import os
import time

import endpoints
from google.appengine.api import taskqueue
from google.appengine.ext.ndb import get_multi
from protorpc import messages
from protorpc import message_types
from protorpc import remote

from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from google.appengine.api import memcache

from models import Profile, ConferenceForm, Conference, ConferenceQueryForms, \
    ConferenceForms, BooleanMessage, ConflictException, StringMessage, \
    SessionForm, Session
from models import ProfileMiniForm
from models import ProfileForm
from models import TeeShirtSize

from settings import WEB_CLIENT_ID
from utils import get_user_id

EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID

DEFAULTS = {
    "city": "Default City",
    "maxAttendees": 0,
    "seatsAvailable": 0,
    "topics": ["Default", "Topic"],
}

OPERATORS = {
    'EQ': '=',
    'GT': '>',
    'GTEQ': '>=',
    'LT': '<',
    'LTEQ': '<=',
    'NE': '!='
}

FIELDS = {
    'CITY': 'city',
    'TOPIC': 'topics',
    'MONTH': 'month',
    'MAX_ATTENDEES': 'maxAttendees',
}

CONF_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_REQUEST = endpoints.ResourceContainer(
    SessionForm,
    websafeConferenceKey=messages.StringField(1),
)

MEMCACHE_ANNOUNCEMENTS_KEY = "RECENT ANNOUNCEMENTS"
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


@endpoints.api(name='conference',
               version='v1',
               allowed_client_ids=[WEB_CLIENT_ID, API_EXPLORER_CLIENT_ID],
               scopes=[EMAIL_SCOPE])
class ConferenceApi(remote.Service):
    """Conference API v0.1"""

    # - - - Profile objects - - - - - - - - - - - - - - - - - - -

    @staticmethod
    def _copy_profile_to_form(prof):
        """
        Copy relevant fields from Profile to ProfileForm.

        Args:
            prof: The Profile object.

        Returns:
            A ProfileForm object with relevant fields from Profile
        """
        pf = ProfileForm()
        for field in pf.all_fields():
            if hasattr(prof, field.name):
                # convert t-shirt string to Enum; just copy others
                if field.name == 'teeShirtSize':
                    setattr(pf, field.name,
                            getattr(TeeShirtSize, getattr(prof, field.name)))
                else:
                    setattr(pf, field.name, getattr(prof, field.name))
        pf.check_initialized()
        return pf

    @staticmethod
    def _get_profile_from_user():
        """
        Return user Profile from datastore, creating new one if non-existent.

        Returns:
            A Profile object from current user

        Raises:
            endpoints.UnauthorizedException: An error if current user is not
            logged in.
        """
        user = endpoints.get_current_user()
        if not user:
            # Raise unauthorized exception if user not logged in
            raise endpoints.UnauthorizedException('Authorization required')

        # Generate a new key of kind Profile from user id
        p_key = ndb.Key(Profile, get_user_id(user))

        # Get profile from Datastore
        profile = p_key.get()

        # Create profile with current user info if profile is not stored
        if not profile:
            profile = Profile(
                key=p_key,
                displayName=user.nickname(),
                mainEmail=user.email()
            )
            profile.put()
        return profile  # return Profile

    def _do_profile(self, save_request=None):
        """
        Get user Profile and return to ProfileForm, possibly updating it first.
        If save_request is not None, update and put Profile to Datastore.

        Args:
            save_request: A request with fields to update.

        Returns:
            A ProfileForm with
        """
        prof = self._get_profile_from_user()

        # if save_request, process user-modifiable fields
        if save_request:
            for field in ('displayName', 'teeShirtSize'):
                if hasattr(save_request, field):
                    val = getattr(save_request, field)
                    if val:
                        setattr(prof, field, str(val))
            # Put profile to Datastore
            prof.put()
        # return ProfileForm
        return self._copy_profile_to_form(prof)

    @endpoints.method(message_types.VoidMessage, ProfileForm,
                      path='profile', http_method='GET', name='getProfile')
    def get_profile(self, request):
        """
        API endpoint to return current user profile.

        Args:
            request: The request sent to this API endpoint.

        Returns:
            A ProfileForm with the current user Profile.
        """
        return self._do_profile()

    @endpoints.method(ProfileMiniForm, ProfileForm,
                      path='profile', http_method='POST', name='saveProfile')
    def save_profile(self, request):
        """
        API endpoint to update & return user Profile.

        Args:
            request: The request sent to this API endpoint.

        Returns:
            A ProfileForm with the current user Profile updated by request.
        """
        return self._do_profile(request)

    # - - - Conference objects - - - - - - - - - - - - - - - - -

    @staticmethod
    def _copy_conference_to_form(conf, displayName):
        """
        Copy relevant fields from Conference to ConferenceForm.

        Args:
            conf: The Conference object.
            displayName: The name of the conference organizer.

        Returns:
            A ConferenceForm with relevant Conference fields.
        """
        cf = ConferenceForm()
        for field in cf.all_fields():
            if hasattr(conf, field.name):
                # convert Date to date string; just copy others
                if field.name.endswith('Date'):
                    setattr(cf, field.name, str(getattr(conf, field.name)))
                else:
                    setattr(cf, field.name, getattr(conf, field.name))
            elif field.name == "websafeKey":
                setattr(cf, field.name, conf.key.urlsafe())
        if displayName:
            setattr(cf, 'organizerDisplayName', displayName)
        cf.check_initialized()
        return cf

    @staticmethod
    def _create_conference_object(request):
        """
        Create or update Conference object, returning ConferenceForm/request.

        Args:
            request: The request sent to this API endpoint.

        Returns:
            Updated request.

        Raises:
            endpoints.UnauthorizedException: An error if current user is not
            logged in.
            endpoints.BadRequestException: An error if request does not have a
            name field. This field is required.
        """
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = get_user_id(user)

        if not request.name:
            raise endpoints.BadRequestException(
                "Conference 'name' field required")

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name) for field in
                request.all_fields()}
        del data['websafeKey']
        del data['organizerDisplayName']

        # add default values for those missing (both data model & outbound
        # Message)
        for df in DEFAULTS:
            if data[df] in (None, []):
                data[df] = DEFAULTS[df]
                setattr(request, df, DEFAULTS[df])

        # convert dates from strings to Date objects; set month based on start
        # date
        if data['startDate']:
            data['startDate'] = datetime.strptime(data['startDate'][:10],
                                                  "%Y-%m-%d").date()
            data['month'] = data['startDate'].month
        else:
            data['month'] = 0
        if data['endDate']:
            data['endDate'] = datetime.strptime(data['endDate'][:10],
                                                "%Y-%m-%d").date()

        # set seatsAvailable to be same as maxAttendees on creation
        # both for data model & outbound Message
        if data["maxAttendees"] > 0:
            data["seatsAvailable"] = data["maxAttendees"]
            setattr(request, "seatsAvailable", data["maxAttendees"])

        # make Profile Key from user ID
        p_key = ndb.Key(Profile, user_id)
        # allocate new Conference ID with Profile key as parent
        c_id = Conference.allocate_ids(size=1, parent=p_key)[0]
        # make Conference key from ID
        c_key = ndb.Key(Conference, c_id, parent=p_key)
        data['key'] = c_key
        data['organizerUserId'] = request.organizerUserId = user_id

        # create Conference & return (modified) ConferenceForm
        Conference(**data).put()

        # creation of Conference & return (modified) ConferenceForm
        Conference(**data).put()
        # send email to organizer confirming
        taskqueue.add(params={'email': user.email(),
                              'conferenceInfo': repr(request)},
                      url='/tasks/send_confirmation_email'
                      )
        return request

    @endpoints.method(ConferenceForm, ConferenceForm, path='conference',
                      http_method='POST', name='createConference')
    def create_conference(self, request):
        """
        API endpoint to create new conference and stores it to Datastore.

        Args:
            request: The request sent to this API endpoint.

        Returns:
            Updated request.
        """
        return self._create_conference_object(request)

    def _get_query(self, request):
        """
        Return formatted query from the submitted filters.

        Args:
            request: The request sent to this API endpoint.

        Returns:
            A query object after applying the filters.
        """
        q = Conference.query()
        inequality_filter, filters = self._format_filters(request.filters)

        # If exists, sort on inequality filter first
        if not inequality_filter:
            q = q.order(Conference.name)
        else:
            q = q.order(ndb.GenericProperty(inequality_filter))
            q = q.order(Conference.name)

        for filtr in filters:
            if filtr["field"] in ["month", "maxAttendees"]:
                filtr["value"] = int(filtr["value"])
            formatted_query = ndb.query.FilterNode(filtr["field"],
                                                   filtr["operator"],
                                                   filtr["value"])
            q = q.filter(formatted_query)
        return q

    @staticmethod
    def _format_filters(filters):
        """
        Parse, check validity and format user supplied filters.

        Args:
            filters:

        Returns:
            A tuple with the inequality field, if used, and with the filters
            formatted.

        Raises:
            endpoints.BadRequestException: An error if filter contains invalid
            field or operator.
            endpoints.BadRequestException: An error if more than one field is
            using inequality operators.
        """
        formatted_filters = []
        inequality_field = None

        for f in filters:
            filtr = {field.name: getattr(f, field.name) for field in
                     f.all_fields()}

            try:
                filtr["field"] = FIELDS[filtr["field"]]
                filtr["operator"] = OPERATORS[filtr["operator"]]
            except KeyError:
                raise endpoints.BadRequestException(
                    "Filter contains invalid field or operator.")

            # Every operation except "=" is an inequality
            if filtr["operator"] != "=":
                # check if inequality operation has been used in previous
                # filters disallow the filter if inequality was performed on
                # a different field before track the field on which the
                # inequality operation is performed
                if inequality_field and inequality_field != filtr["field"]:
                    raise endpoints.BadRequestException(
                        "Inequality filter is allowed on only one field.")
                else:
                    inequality_field = filtr["field"]

            formatted_filters.append(filtr)
        return inequality_field, formatted_filters

    @endpoints.method(ConferenceQueryForms, ConferenceForms,
                      path='queryConferences', http_method='POST',
                      name='queryConferences')
    def query_conferences(self, request):
        """
        API endpoint to query and return all conferences in the Datastore.

        Args:
            request: The request sent to this API endpoint.

        Returns:
            A set of ConferenceForms per conference.
        """
        conferences = self._get_query(request)

        # return individual ConferenceForm object per Conference
        return ConferenceForms(
            items=[self._copy_conference_to_form(conf, "")
                   for conf in conferences]
        )

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
                      path='getConferencesCreated', http_method='POST',
                      name='getConferencesCreated')
    def get_conferences_created(self, request):
        """
        API endpoint to query and return all conferences created by current
        user.

        Args:
            request: The request sent to this API endpoint.

        Returns:
            A set of ConferenceForms per conference.

        Raises:
            endpoints.UnauthorizedException: An error if current user is not
            logged in.
        """
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException("Authorization required.")

        # Make profile key
        p_key = ndb.Key(Profile, get_user_id(user))
        # Create ancestor query for this user
        conferences = Conference.query(ancestor=p_key)
        # Get user profile and display name
        profile = p_key.get()
        display_name = getattr(profile, 'displayName')
        # Return set of ConferenceForms per Conference
        return ConferenceForms(
            items=[self._copy_conference_to_form(conf, display_name)
                   for conf in conferences]
        )

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
                      path='conferences/attending',
                      http_method='GET', name='getConferencesToAttend')
    def get_conferences_to_attend(self, request):
        """
        Get list of conferences that user has registered for.

        Args:
            request: The request sent to this API endpoint.

        Returns:
            ConferenceForms of conferences user has registered.
        """
        # get user profile
        profile = self._get_profile_from_user()
        # get conferenceKeysToAttend from profile.
        ckta = profile.conferenceKeysToAttend
        # to make a ndb key from websafe key you can use:
        # ndb.Key(urlsafe=my_websafe_key_string)
        array_of_keys = [ndb.Key(urlsafe=ck) for ck in ckta]
        # fetch conferences from datastore.
        conferences = get_multi(array_of_keys)

        # return set of ConferenceForm objects per Conference
        return ConferenceForms(items=[self._copy_conference_to_form(conf, "")
                                      for conf in conferences]
                               )

    @endpoints.method(CONF_GET_REQUEST, ConferenceForm,
                      path='conference/{websafeConferenceKey}',
                      http_method='GET', name='getConference')
    def get_conference(self, request):
        """
        Return requested conference (by websafeConferenceKey).

        Args:
            request: The request sent to this API endpoint.

        Returns:
            A ConferenceForm whti the requested conference.

        Raises:
            endpoints.NotFoundException: An error if conference not found
        """
        # get Conference object from request; bail if not found
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: {}'.format(
                    request.websafeConferenceKey))
        prof = conf.key.parent().get()
        # return ConferenceForm
        return self._copy_conference_to_form(conf,
                                             getattr(prof, 'displayName'))

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
                      path='filterPlayground', http_method='GET',
                      name='filterPlayground')
    def filter_playground(self, request):
        """
        API endpoint to test query with property filters.

        Args:
            request: The request sent to this API endpoint.

        Returns:
            A set of ConferenceForms per conference.
        """
        q = Conference.query()

        # 1 - city equals to London
        q = q.filter(Conference.city == "London")

        # 2 - topic equals to Medical Innovations
        q = q.filter(Conference.topics == "Medical Innovations")

        # 3 - order by conference name
        q = q.order(Conference.name)

        # 4 - month equals to June
        q = q.filter(Conference.month == 6)

        # Return set of ConferenceForms per Conference
        return ConferenceForms(
            items=[self._copy_conference_to_form(conf, "")
                   for conf in q]
        )

    # - - - Registration - - - - - - - - - - - - - - - - - - - -

    @ndb.transactional(xg=True)
    def _conference_registration(self, request, reg=True):
        """
        Register or unregister user for selected conference.

        Args:
            request: The request sent to this API endpoint.
            reg (bool): True to register and False to unregister.

        Returns:
            A BooleanMessage of the final status of the transaction.

        Raises:
            endpoints.NotFoundException: An error if conference not found.
            ConflictException: If user already registered for the conference.
            ConflictException: If no seats available for the conference.
        """
        prof = self._get_profile_from_user()  # get user Profile

        # check if conf exists given websafeConfKey
        # get conference; check that it exists
        wsck = request.websafeConferenceKey
        conf = ndb.Key(urlsafe=wsck).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wsck)

        # register
        if reg:
            # check if user already registered otherwise add
            if wsck in prof.conferenceKeysToAttend:
                raise ConflictException(
                    "You have already registered for this conference")

            # check if seats avail
            if conf.seatsAvailable <= 0:
                raise ConflictException(
                    "There are no seats available.")

            # register user, take away one seat
            prof.conferenceKeysToAttend.append(wsck)
            conf.seatsAvailable -= 1
            retval = True

        # unregister
        else:
            # check if user already registered
            if wsck in prof.conferenceKeysToAttend:

                # unregister user, add back one seat
                prof.conferenceKeysToAttend.remove(wsck)
                conf.seatsAvailable += 1
                retval = True
            else:
                retval = False

        # write things back to the datastore & return
        prof.put()
        conf.put()
        return BooleanMessage(data=retval)

    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
                      path='conference/{websafeConferenceKey}',
                      http_method='POST', name='registerForConference')
    def register_for_conference(self, request):
        """
        Register user for selected conference.

        Args:
            request: The request sent to this API endpoint.

        Returns:
            A BooleanMessage of the final status of the transaction.
        """
        return self._conference_registration(request)

    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
                      path='conference/{websafeConferenceKey}/unregister',
                      http_method='POST', name='unregisterFromConference')
    def unregister_from_conference(self, request):
        """
        Unregister user for selected conference.

        Args:
            request: The request sent to this API endpoint.

        Returns:
            A BooleanMessage of the final status of the transaction.
        """
        return self._conference_registration(request, reg=False)

    # - - - Announcements - - - - - - - - - - - - - - - - - - - -

    @staticmethod
    def _cache_announcement():
        """
        Create Announcement & assign to memcache; used by memcache cron job &
        putAnnouncement().

        Returns:
            A string with the announcement. Empty string if no conference found
            or string with conferences almost sold out.
        """
        confs = Conference.query(ndb.AND(
            Conference.seatsAvailable <= 5,
            Conference.seatsAvailable > 0)
        ).fetch(projection=[Conference.name])

        if confs:
            # If there are almost sold out conferences,
            # format announcement and set it in memcache
            announcement = '%s %s' % (
                'Last chance to attend! The following conferences '
                'are nearly sold out:',
                ', '.join(conf.name for conf in confs))
            memcache.set(MEMCACHE_ANNOUNCEMENTS_KEY, announcement)
        else:
            # If there are no sold out conferences,
            # delete the memcache announcements entry
            announcement = ""
            memcache.delete(MEMCACHE_ANNOUNCEMENTS_KEY)

        return announcement

    @endpoints.method(message_types.VoidMessage, StringMessage,
                      path='conference/announcement/get',
                      http_method='GET', name='getAnnouncement')
    def get_announcement(self, request):
        """Return Announcement from memcache."""
        # return an existing announcement from Memcache or an empty string.
        announcement = memcache.get(MEMCACHE_ANNOUNCEMENTS_KEY)
        if not announcement:
            announcement = ""
        return StringMessage(data=announcement)

    # - - - Sessions - - - - - - - - - - - - - - - - - - - -

    @staticmethod
    def _copy_session_to_form(session):
        """
        Copy relevant fields from Session to SessionForm.

        Args:
            session: The Session object.

        Returns:
            A SessionForm with relevant Session fields.
        """
        ss = SessionForm()
        for field in ss.all_fields():
            if hasattr(session, field.name):
                # convert Date to date string; just copy others
                if field.name == 'date':
                    setattr(ss, field.name, str(getattr(session, field.name)))
                elif field.name == 'startTime':
                    setattr(ss, field.name, str(getattr(session, field.name)))
                else:
                    setattr(ss, field.name, getattr(session, field.name))
        ss.check_initialized()
        return ss

    def _create_session_object(self, request):
        if not request.name:
            raise endpoints.BadRequestException(
                "Session 'name' field required")

        # get Conference object from request; bail if not found
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: {}'.format(
                    request.websafeConferenceKey))
        owner_prof = conf.key.parent().get()
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException("Authorization required.")
        user_id = get_user_id(user)
        if owner_prof.mainEmail != user_id:
            raise endpoints.UnauthorizedException(
                "Only the conference organizer can create sessions.")

        # copy SessionForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name) for field in
                request.all_fields()}

        # convert dates from strings to Date objects and startTime to Time
        # objects
        if data['date']:
            data['date'] = datetime.strptime(data['date'][:10],
                                             "%Y-%m-%d").date()
        if data['startTime']:
            data['startTime'] = datetime.strptime(data['startTime'],
                                                  "%H:%M").time()

        c_key = ndb.Key(urlsafe=request.websafeConferenceKey)
        # allocate new Session ID with Conference key as parent
        s_id = Session.allocate_ids(size=1, parent=c_key)[0]
        # make Session key from ID
        s_key = ndb.Key(Session, s_id, parent=c_key)

        data['key'] = s_key
        request.conferenceId = request.websafeConferenceKey
        data['conferenceId'] = request.conferenceId
        del data['websafeConferenceKey']

        # create Session & return (modified) SessionForm
        sess = Session(**data)
        sess.put()

        return self._copy_session_to_form(sess)

    @endpoints.method(SESSION_REQUEST, SessionForm,
                      path='conference/{websafeConferenceKey}/addsession',
                      http_method='POST', name='createSession')
    def create_session(self, request):
        """create_session documentation"""
        return self._create_session_object(request)


# registers API
api = endpoints.api_server([ConferenceApi])
