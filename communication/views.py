'''This package contains views for the communication app.

So far this includes API calls for Twitter feeds and Google Calendar'''

import json
import urllib, urllib2
import datetime, time
import tweepy
import dateutil

from django.conf import settings
from django.shortcuts import render_to_response
from django.views.generic.base import View, TemplateView
from django.views.generic import ListView
from django.template import RequestContext
from django.contrib import messages

from communication.models import LabAddress, LabLocation

def generate_twitter_timeline(count):
    '''This function generates a timeline from a twitter username.

    This function requires a valid TWITTER_NAME as defined in localsettings.py.
    The function also requires an integer for the number of tweets as a second argument.
    It places a REST call to the Twitter API v1 (see https://dev.twitter.com/docs/api/1/get/statuses/user_timeline)
    It returns a dictionary containing information on the most recent tweets from that account (excluding replies).
    If twitter returns a HTTPError, an error message is returned.
    It is not currently in use and is only left here for reference purposes.
    '''

    auth = tweepy.OAuthHandler(settings.TWITTER_CONSUMER_KEY, settings.TWITTER_CONSUMER_SECRET)
    auth.set_access_token(settings.TWITTER_ACCESS_TOKEN, settings.TWITTER_ACCESS_TOKEN_SECRET)

    api = tweepy.API(auth)
    values = {'count':count, 'include_rts':'true'}
    params = urllib.urlencode(values)
    timeline = api.user_timeline(count=count)
    #for tweet in timeline:
    #    str_time = time.strptime(tweet['created_at'], "%a %b %d %H:%M:%S +0000 %Y")
    #    tweet['created_at_cleaned'] = datetime.datetime(*str_time[:6])
    return timeline
    
def facebook_status_request(type, max):
    '''This function takes a request url and token and returns deserialized data.
        
    It requires a type (general, milestones or posts) and a maximum number of entries to return
    '''
    values = {'access_token':settings.FACEBOOK_ACCESS_TOKEN}
    params = urllib.urlencode(values)
    request_url = 'https://graph.facebook.com/'+ settings.FACEBOOK_ID  + '/' + type + '?' + params    
    request = urllib2.Request(request_url)
    
    try:
        response = urllib2.urlopen(request)
    except urllib2.URLError, e:
        if e.code == 404:
            data = "Facebook API is not Available."
        else:
            #this is for a non-404 URLError.
            data = "Facebook API is not Available."
    except ValueError:
            data = "Facebook API is not Available."        
    else:
            #successful connection
            json_data = response.read()
            data = json.loads(json_data)
            return data       
    
def get_wikipedia_edits(username, count):
    '''This function gets the wikipedia edits for a particular user.
    
    This function takes a username argument and a count argument.
    It places a REST call to the Wikipedia API (see http://www.mediawiki.org/wiki/API).
    It returns a dictionary with the names of the edited articles.
    '''    
    values = {'ucuser':username, 
    'action':'query', 
    'list':'usercontribs', 
    'format':'json', 
    'uclimit':count,
    'ucnamespace':'0',
    'ucprop':'title|timestamp',
    'ucshow':'!minor'}
    params = urllib.urlencode(values)
    target_site = 'http://en.wikipedia.org/w/api.php?' + params
    response = urllib2.urlopen(target_site)
    json_response = response.read() #this reads the HTTP response
    pages = json.loads(json_response) 
    for edit in pages['query']['usercontribs']:
        str_time = time.strptime(edit['timestamp'], "%Y-%m-%dT%H:%M:%SZ")
        edit['timestamp_cleaned'] = datetime.datetime(*str_time[:6])    
    return pages

class TwitterView(TemplateView):
    '''This view class generates a page showing the twitter timeline for the lab twitter feed.
    
    This view uses the function :function:`~communication.utilities.twitter_oauth_req`.
    The default settings are to return 20 tweets including retweets but excluding replies.
    '''

    template_name = "twitter_timeline.html"
    
    def get_context_data(self, **kwargs):
        '''This function adds the google_calendar_id to the context.'''
        context = super(TwitterView, self).get_context_data(**kwargs)
        context['timeline'] = generate_twitter_timeline(50)
        context['screen_name'] = settings.TWITTER_NAME
        return context 
             
class GoogleCalendarView(TemplateView):
    '''This view renders a google calendar page.
    
    It can render a link to the iCalendar representation of the calendar.
    This view will also display the next few events.
    The calendar is generated by a widget
    Currently this only works for publicly shared Google Calendars.
    '''
    
    template_name = 'calendar.html'
    
    def get_context_data(self, **kwargs):
        '''This function adds the google_calendar_id to the context.'''
        context = super(GoogleCalendarView, self).get_context_data(**kwargs)
        context['google_calendar_id'] = settings.GOOGLE_CALENDAR_ID
        return context    
        
class WikipedaEditsView(View):  
    '''This view class generates a page showing the wikipedia edits for a user.
    '''

    def get(self, request, *args, **kwargs):
        '''This sets the GET function for WikipediaEditsView.'''
        try: 
            pages = get_wikipedia_edits(settings.WIKIPEDIA_USERNAME,50)
            return render_to_response('wikipedia_edits.html',
            {'pages':pages,'username':settings.WIKIPEDIA_USERNAME},
             mimetype='text/html',
             context_instance=RequestContext(request))
        except urllib2.HTTPError:
            messages.error(request, 'No Response from Wikipedia.  Are you sure that %s is a valid username?' % settings.WIKIPEDIA_USERNAME)	    
            return render_to_response('wikipedia_edits.html',
            {'username':settings.WIKIPEDIA_USERNAME},
             mimetype='text/html',
             context_instance=RequestContext(request))
             
class LabRulesView(TemplateView):
    '''This view gets the lab rules markdown and displays this file.
    
    This file must be supplied in LAB_RULES_FILE in localsettings.py
    The template will markup this file and display it as formatted HTML.
    If this file is not provided or is unavailable, an error will be displayed.
    '''
    
    template_name = 'lab_rules.html'
    
    def get_context_data(self, **kwargs):
        '''This function provides the context which is passed to this view.
        
        It will check if the markdown file is available, download it and pass  it to the template.
        If there is no markdown file, then it will generate a no file presented note.'''
        context = super(LabRulesView, self).get_context_data(**kwargs)
        request = urllib2.Request(settings.LAB_RULES_FILE)
        try:
            response = urllib2.urlopen(request)
        except urllib2.URLError, e:
            if e.code == 404:
                lab_rules = "Lab Rules File is not Available."
            else:
                #this is for a non-404 URLError.
                lab_rules = "Lab Rules File is not Available."
        except ValueError:
            lab_rules = "Lab Rules File is not Available."        
        else:
             #successful connection
             lab_rules = response.read()         
        context['lab_rules'] = lab_rules
        context['lab_rules_source'] = settings.LAB_RULES_FILE
        return context 
    
class PublicationPolicyView(TemplateView):
    '''This view gets the publication policy markdown and displays this file.
    
    This file must be supplied in PUBLICATION_POLICY_FILE in localsettings.py
    The template will markup this file and display it as formatted HTML.
    If this file is not provided or is unavailable, an error will be displayed.
    '''
    
    template_name = 'publication_policy.html'
    
    def get_context_data(self, **kwargs):
        '''This function provides the context which is passed to this view.
        
        It will check if the markdown file is available, download it and pass  it to the template.
        If there is no markdown file, then it will generate a no file presented note.'''
        context = super(PublicationPolicyView, self).get_context_data(**kwargs)
        request = urllib2.Request(settings.PUBLICATION_POLICY_FILE)
        try:
            response = urllib2.urlopen(request)
        except urllib2.URLError, e:
            if e.code == 404:
                publication_policy = "Publication Policy File is not Available."
            else:
                #this is for a non-404 URLError.
                publication_policy = "Publication Policy File is not Available."
        except ValueError:
            publication_policy = "Publication Policy File is not Available."        
        else:
             #successful connection
             publication_policy = response.read()         
        context['publication_policy'] = publication_policy
        context['publication_policy_source'] = settings.PUBLICATION_POLICY_FILE
        return context

class FeedDetailView(TemplateView):
    '''This view redirects to a template describing RSS feeds.'''
    
    template_name = "feed_details.html"   
    
    def get_context_data(self, **kwargs):
        '''This function adds the google_calendar_id to the context.'''
        context = super(FeedDetailView, self).get_context_data(**kwargs)
        context['google_calendar_id'] = settings.GOOGLE_CALENDAR_ID
        context['wikipedia_username'] = settings.WIKIPEDIA_USERNAME
        return context 
        
class NewsView(TemplateView):
    '''This view parses the facebook feed and presents it as laboratory news.
    '''
    
    template_name = "lab_news.html"
    
    def get_context_data(self, **kwargs):
        '''This function adds milestones and posts to the context.'''
                                              
        context = super(NewsView, self).get_context_data(**kwargs)
        context['statuses'] = facebook_status_request('statuses', 100)
        context['links'] = facebook_status_request('links', 10)
        milestones = facebook_status_request('milestones', 10)
        for milestone in milestones['data']:
            milestone['start_time_cleaned'] = dateutil.parser.parse(milestone['start_time'])
        context['milestones'] = milestones
        return context 
        
class ContactView(ListView):
    '''This view provides lab-contact information.'''
    
    template_name = "contact.html"
    model = LabAddress  
    
class LabLocationView(ListView):
    '''This view provides location information.
    
    Its passes the location_list parameter when the /location view is requested.
    '''
    
    template_name = "location.html"
    model = LabLocation                                            
