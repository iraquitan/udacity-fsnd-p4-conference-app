# PROJECT 4 - Conference App with Google App Engine
A project for a conference app, where users can sign up with their Google accounts and update their profile info. Logged in users can also create and delete their own conferences, and attend to conferences with seats available. Project using Google App Engine and features like task queues to send confirmation email when conference is created, and cron job to updated announcement of conferences that are almost sold out. Application running in the cloud in this [LINK](https://udacity-scalable-app-1238.appspot.com/)

## Table of contents
* [Requirements](#requirements)
* [Quick start](#quick-start)
* [Design choices for Sessions and Speakers](#design-choices-for-sessions-and-speakers)
* [Query Problem](#query-problem)
* [Additional Queries](#additional-queries)
* [Creator](#creator)
* [License](#license)

## Requirements
* Python 2.7
* Git
* [App Engine SDK for Python](https://cloud.google.com/appengine/downloads/#Google_App_Engine_SDK_for_Python)

## Quick start
* Clone this repo `git clone https://github.com/iraquitan/udacity-fsnd-p4-conference-app.git conference-app`.
* Change to the `/conference-app` directory.
* Go to [Google Developers Console](https://console.developers.google.com/) and create a new project.
* Update `your-user-id` in **app.yaml** with your new project application ID.
* Go to [Google Developers Console](https://console.developers.google.com/), and over **credentials**, configure _OAUTH consent screen_ with the name of the application.
* Create a new _OAUTH Client ID_ credential for _Web application_.
    * In __Authorized JavaScript origins__ add `https://your-app-id.appspot.com` and `http://localhost:8080` if you are using port 8080.
    * In __Authorized redirect URIs__ add `https://your-app-id.appspot.com/oauth2callback` and `http://localhost:8080/oauth2callback` if you are using port 8080.
* Update `your-web-client-id` in **settings.py** with your web client ID that looks like this: `your-web-client-id.apps.googleusercontent.com`.	
* Update `CLIENT_ID` in Oauth2Provider, located in **static/js/app.js** with your web client ID that looks like this: `your-web-client-id.apps.googleusercontent.com`.
* To test locally, you can use the `**GoogleAppEngineLauncher SDK** utility or use command line as follows:
    * `$ dev_appserver.py ./` if you are currently in the project folder.
    * Then head to `http://localhost:8080` to see the application running.
    * Or to `http://localhost:8080/_ah/api/explorer` to see the API endpoints of the running application.
* To deploy, you can use the **GoogleAppEngineLauncher SDK** utility or use command line as follows:
    * `$ appcfg.py -A YOUR_PROJECT_ID -V v1 update ./` if you are currently in the project folder.
    * Then head to `https://your-app-id.appspot.com` to see the application running in the cloud.
    * Or to `https://your-app-id.appspot.com/_ah/api/explorer` to see the API endpoints of the application running in the cloud.

## Design choices for Sessions and Speakers
* Speaker:
    * Speakers are implemented as an entity.
    * Speakers have the following fields:
        * Field Name | Property Type | Aditional Info
          ---------- | ------------- | --------------
          name | ndb.StringProperty(required=True) | Used in POST form
          email | ndb.StringProperty() | Used in POST form
          institution | ndb.StringProperty() | Used in POST form
          creatorUserId | ndb.StringProperty() | Used internally when created
* Session:
    * Sessions are entities that stores the websafe keys of Conference and Speaker (if it have one).
    * To add a Session with speaker, you must first add a Speaker, and use his `websafeKey` in the Session `speakerKey` field.
    * Sessions have the following fields:
        * Field Name | Property Type | Aditional Info
          ---------- | ------------- | --------------
          name | ndb.StringProperty(required=True) | Used in POST form
          conferenceKey | ndb.StringProperty(required=True) | Querystring arguments passed through ResourceContainer
          speakerKey | ndb.StringProperty() | Used in POST form
          highlights | ndb.StringProperty(repeated=True) | Used in POST form
          duration | ndb.IntegerProperty() | Used in POST form
          typeOfSession | ndb.StringProperty() | Used in POST form
          date | ndb.DateProperty() | Used in POST form
          startTime | ndb.TimeProperty() | Used in POST form

## Query Problem
* Problem:
    * The problem is that in the query for all non-workshop before 7pm, there are two fields that need an inequality: `startTime` and `typeOfSession`. One way I think to solve this query is performing then separately and then get the intersection of both results.
* Solution:
    * To achieve the desired query result, I performed the two queries separately and stored the resulted sessions websafe keys in two different lists. Then I used the bultin python set type with the intersection method to get the keys that are in both lists. Then I used the ndb.get_multi method to retrieve all desired keys at once.
    * The solution is implemented in the `queryConferenceSessionsProblem` API endpoint.

## Additional Queries
* `getSessionsByDuration`: This API endpoint returns all Sessions given by a specific duration and operator (EQ: ==, LT: <, LTEQ: <=, GT: >, GTEQ: >=, NE: !=) across all Conferences.
* `getSessionsByLocation`: This endpoint gets all Sessions given by a specific city across all Conferences.
* `getConferencesByDateRange`: This endpoint returns all Conferences starting at a date range (**startDate** and **endDate**) in the format YYYY-mm-dd.
* `getConferencesAvailableByMonth`: This endpoint returns all Conferences with seats available by a given month.


## Creator
**Iraquitan Cordeiro Filho**
* <https://github.com/iraquitan>
* <https://www.linkedin.com/in/iraquitan>
* <https://twitter.com/iraquitan_filho>

## License
The contents of this repository are covered under the [MIT License](LICENSE).
