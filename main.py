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


class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.response.write('Hello world!')


app = webapp2.WSGIApplication([
    ('/', MainHandler)
], debug=True)
