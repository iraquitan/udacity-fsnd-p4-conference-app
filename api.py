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
from protorpc import messages
from protorpc import message_types
from protorpc import remote

from google.appengine.api import urlfetch
from google.appengine.ext import ndb

from models import Profile, ConferenceForm, Conference, ConferenceQueryForms, \
    ConferenceForms
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
        """Copy relevant fields from Profile to ProfileForm."""
        # copy relevant fields from Profile to ProfileForm
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
        """Return user Profile from datastore, creating new one if
        non-existent."""
        # Get current user
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
        """Get user Profile and return to user, possibly updating it first."""
        # get user Profile
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
        """Return user profile."""
        return self._do_profile()

    @endpoints.method(ProfileMiniForm, ProfileForm,
                      path='profile', http_method='POST', name='saveProfile')
    def save_profile(self, request):
        """Update & return user profile."""
        return self._do_profile(request)

    # - - - Conference objects - - - - - - - - - - - - - - - - -

    @staticmethod
    def _copy_conference_to_form(conf, displayName):
        """Copy relevant fields from Conference to ConferenceForm."""
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
        """
        # preload necessary data items
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

        return request

    @endpoints.method(ConferenceForm, ConferenceForm, path='conference',
                      http_method='POST', name='createConference')
    def create_conference(self, request):
        """Create new conference."""
        return self._create_conference_object(request)

    @endpoints.method(ConferenceQueryForms, ConferenceForms,
                      path='queryConferences', http_method='POST',
                      name='queryConferences')
    def query_conferences(self, request):
        """query_conferences documentation"""
        conferences = Conference.query()

        # return individual ConferenceForm object per Conference
        return ConferenceForms(
            items=[self._copy_conference_to_form(conf, "")
                   for conf in conferences]
        )

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
                      path='getConferencesCreated', http_method='POST',
                      name='getConferencesCreated')
    def get_conferences_created(self, request):
        """get_conferences_created documentation"""
        # Make sure user is authenticated
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
                      path='filterPlayground', http_method='GET',
                      name='filterPlayground')
    def filter_playground(self, request):
        """filter_playground documentation"""
        q = Conference.query()

        # 1 - city equals to London
        q = q.filter(Conference.city == "London")

        # 2 - topic equals to Medical Innovations
        q = q.filter(Conference.topics == "Medical Innovations")

        # 3 - order by conference name
        q = q.order(Conference.name)
        # Return set of ConferenceForms per Conference
        return ConferenceForms(
            items=[self._copy_conference_to_form(conf, "")
                   for conf in q]
        )

# registers API
api = endpoints.api_server([ConferenceApi])
