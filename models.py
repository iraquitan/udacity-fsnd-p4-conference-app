# -*- coding: utf-8 -*-
"""
 * Project: udacity-fsnd-p4-conference-app
 * Author name: Iraquitan Cordeiro Filho
 * Author login: iraquitan
 * File: models
 * Date: 3/23/16
 * Time: 12:23 AM
"""
import httplib
import endpoints
from protorpc import messages
from google.appengine.ext import ndb


class Profile(ndb.Model):
    """Profile -- User profile object"""
    displayName = ndb.StringProperty()
    mainEmail = ndb.StringProperty()
    teeShirtSize = ndb.StringProperty(default='NOT_SPECIFIED')
    conferenceKeysToAttend = ndb.StringProperty(repeated=True)
    sessionsWishlist = ndb.StringProperty(repeated=True)


class ProfileMiniForm(messages.Message):
    """ProfileMiniForm -- update Profile form message"""
    displayName = messages.StringField(1)
    teeShirtSize = messages.EnumField('TeeShirtSize', 2)


class ProfileForm(messages.Message):
    """ProfileForm -- Profile outbound form message"""
    displayName = messages.StringField(2)
    mainEmail = messages.StringField(3)
    teeShirtSize = messages.EnumField('TeeShirtSize', 4)
    conferenceKeysToAttend = messages.StringField(5, repeated=True)
    sessionsWishlist = messages.StringField(6, repeated=True)


class TeeShirtSize(messages.Enum):
    """TeeShirtSize -- t-shirt size enumeration value"""
    NOT_SPECIFIED = 1
    XS_M = 2
    XS_W = 3
    S_M = 4
    S_W = 5
    M_M = 6
    M_W = 7
    L_M = 8
    L_W = 9
    XL_M = 10
    XL_W = 11
    XXL_M = 12
    XXL_W = 13
    XXXL_M = 14
    XXXL_W = 15


class Conference(ndb.Model):
    """Conference -- Conference object"""
    name = ndb.StringProperty(required=True)
    description = ndb.StringProperty()
    organizerUserId = ndb.StringProperty()
    topics = ndb.StringProperty(repeated=True)
    city = ndb.StringProperty()
    startDate = ndb.DateProperty()
    month = ndb.IntegerProperty()
    endDate = ndb.DateProperty()
    maxAttendees = ndb.IntegerProperty()
    seatsAvailable = ndb.IntegerProperty()


class ConferenceForm(messages.Message):
    """ConferenceForm -- Conference outbound form message"""
    name = messages.StringField(1)
    description = messages.StringField(2)
    organizerUserId = messages.StringField(3)
    topics = messages.StringField(4, repeated=True)
    city = messages.StringField(5)
    startDate = messages.StringField(6)
    month = messages.IntegerField(7, variant=messages.Variant.INT32)
    maxAttendees = messages.IntegerField(8, variant=messages.Variant.INT32)
    seatsAvailable = messages.IntegerField(9, variant=messages.Variant.INT32)
    endDate = messages.StringField(10)
    websafeKey = messages.StringField(11)
    organizerDisplayName = messages.StringField(12)


class ConferenceForms(messages.Message):
    """ConferenceForms -- multiple Conference outbound form message"""
    items = messages.MessageField(ConferenceForm, 1, repeated=True)


class ConferenceQueryForm(messages.Message):
    """ConferenceQueryForm -- Conference query inbound form message"""
    field = messages.StringField(1)
    operator = messages.StringField(2)
    value = messages.StringField(3)


class ConferenceQueryForms(messages.Message):
    """
    ConferenceQueryForms -- multiple ConferenceQueryForm inbound form message
    """
    filters = messages.MessageField(ConferenceQueryForm, 1, repeated=True)


class ConferenceDateRangeForm(messages.Message):
    """
    ConferenceDateRangeForm -- ConferenceDateRangeForm inbound form message
    """
    startDate = messages.StringField(1)
    endDate = messages.StringField(2)


class ConferenceAvailableForm(messages.Message):
    """
    ConferenceAvailableForm -- ConferenceAvailableForm inbound form message
    """
    month = messages.IntegerField(1)


class BooleanMessage(messages.Message):
    """BooleanMessage-- outbound Boolean value message"""
    data = messages.BooleanField(1)


class ConflictException(endpoints.ServiceException):
    """ConflictException -- exception mapped to HTTP 409 response"""
    http_status = httplib.CONFLICT


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    data = messages.StringField(1, required=True)


class Speaker(ndb.Model):
    """Speaker -- Please add a description"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()
    institution = ndb.StringProperty()
    creatorUserId = ndb.StringProperty()


class SpeakerForm(messages.Message):
    """SpeakerForm -- Please add a description"""
    name = messages.StringField(1, required=True)
    email = messages.StringField(2)
    institution = messages.StringField(3)
    creatorUserId = messages.StringField(4)
    websafeKey = messages.StringField(5)


class Session(ndb.Model):
    """Session -- Please add a description"""
    name = ndb.StringProperty(required=True)
    conferenceKey = ndb.StringProperty(required=True)
    speakerKey = ndb.StringProperty()
    highlights = ndb.StringProperty(repeated=True)
    duration = ndb.IntegerProperty()
    typeOfSession = ndb.StringProperty()
    date = ndb.DateProperty()
    startTime = ndb.TimeProperty()


class SessionForm(messages.Message):
    """SessionForm -- Please add a description"""
    name = messages.StringField(1, required=True)
    conferenceKey = messages.StringField(2)
    speakerKey = messages.StringField(3)
    highlights = messages.StringField(4, repeated=True)
    duration = messages.IntegerField(5, variant=messages.Variant.INT32)
    typeOfSession = messages.StringField(6)
    date = messages.StringField(7)
    startTime = messages.StringField(8)
    speakerName = messages.StringField(9)
    websafeKey = messages.StringField(10)


class SessionForms(messages.Message):
    """SessionForms -- multiple Session outbound form message"""
    items = messages.MessageField(SessionForm, 1, repeated=True)


class SessionByTypeForm(messages.Message):
    """SessionByTypeForm -- Session query inbound form message"""
    typeOfSession = messages.StringField(1)


class SessionQueryForm(messages.Message):
    """SessionQueryForm -- Session query inbound form message"""
    field = messages.StringField(1)
    operator = messages.StringField(2)
    value = messages.StringField(3)


class SessionQueryForms(messages.Message):
    """
    SessionQueryForms -- multiple SessionQueryForm inbound form message
    """
    filters = messages.MessageField(SessionQueryForm, 1, repeated=True)


class SpecificQueryForm(messages.Message):
    """
    SpecificQueryForm -- Specific query inbound form message
    """
    operator = messages.StringField(1)
    value = messages.StringField(2)


class LocationQueryForm(messages.Message):
    """
    LocationQueryForm -- Location query inbound form message
    """
    city = messages.StringField(1)
