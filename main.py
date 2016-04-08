# -*- coding: utf-8 -*-
"""
 * Project: udacity-fsnd-p4-conference-app
 * Author name: Iraquitan Cordeiro Filho
 * Author login: iraquitan
 * File: main
 * Date: 3/23/16
 * Time: 12:15 AM
"""
import webapp2
from google.appengine.api import app_identity
from google.appengine.api import mail
from api import ConferenceApi


class SetAnnouncementHandler(webapp2.RequestHandler):
    def get(self):
        """Set Announcement in Memcache."""
        announcement = ConferenceApi._cache_announcement()
        self.response.write(announcement)


class SendConfirmationEmailHandler(webapp2.RequestHandler):
    def post(self):
        """Send email confirming Conference creation."""
        mail.send_mail(
            'noreply@%s.appspotmail.com' % (
                app_identity.get_application_id()),     # from
            self.request.get('email'),                  # to
            'You created a new Conference!',            # subj
            'Hi, you have created the following '       # body
            'conference:\r\n\r\n%s' % self.request.get(
                'conferenceInfo')
        )


class CheckFeaturedSpeakerHandler(webapp2.RedirectHandler):
    def post(self):
        featured_speaker = ConferenceApi._check_speaker(
            self.request.get('speakerKey'),
            self.request.get('sessionKey')
        )

app = webapp2.WSGIApplication([
    ('/crons/set_announcement', SetAnnouncementHandler),
    ('/tasks/send_confirmation_email', SendConfirmationEmailHandler),
    ('/tasks/check_featured_speaker', CheckFeaturedSpeakerHandler),
], debug=True)
