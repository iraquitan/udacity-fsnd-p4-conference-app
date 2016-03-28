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

from models import Profile
from models import ProfileMiniForm
from models import ProfileForm
from models import TeeShirtSize

from settings import WEB_CLIENT_ID
from utils import get_user_id

EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID

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
                      path='profile', http_method='GET', name='get_profile')
    def get_profile(self, request):
        """Return user profile."""
        return self._do_profile()

    @endpoints.method(ProfileMiniForm, ProfileForm,
                      path='profile', http_method='POST', name='save_profile')
    def save_profile(self, request):
        """Update & return user profile."""
        return self._do_profile(request)


# registers API
api = endpoints.api_server([ConferenceApi])
