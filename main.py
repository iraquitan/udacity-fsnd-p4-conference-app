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


app = webapp2.WSGIApplication([
    ('/crons/set_announcement', SetAnnouncementHandler),
], debug=True)
