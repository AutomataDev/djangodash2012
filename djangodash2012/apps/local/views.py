from django.shortcuts import HttpResponse
from django.conf import settings
from django.db import IntegrityError

import flickrapi
import time
import urllib2,urllib
import simplejson

from core.models import Year,Image,Miracle

def parse(request):
    miracles = Miracle.objects.all()
    years = Year.objects.all()

    for miracle in miracles:
        parse_flickr(miracle)
        parse_google(miracle, years)
        parse_instagram(miracle)
    return HttpResponse()

def parse_flickr(miracle):
    flickr = flickrapi.FlickrAPI(settings.FLICKR_API)
    photos = flickr.walk(tag_mode='all',
        tags=miracle.flickr_tags,
        min_taken_date='2010-01-01',
        max_taken_date='2012-12-31',
        #                sort = 'interestingness-desc',
        per_page=500,
    )
    for photo in photos:
        secret = photo.get('secret')
        server = photo.get('server')
        id = photo.get('id')
        farm = photo.get('farm')
        size='z'
        url = r"""http://farm%s.staticflickr.com/%s/%s_%s_%s.jpg""" % (farm,server,id,secret,size)
        title = photo.get('title')

        create_image(miracle, Image.SERVICE_TYPES[1][0], url, title)
    time.sleep(2)
    return

def parse_google(miracle, years):
    for year in years:
        start = 0
        step = 4
        search_title = "%s in %s"%(miracle.google_tags, year.value)
        search_string = urllib.quote(search_title)

        #custom search feature request
        #service = build('customsearch', 'v1', developerKey=settings.GOOGLE_API)
        #request = service.list(q=tag, cx=settings.GOOGLE_PROJECT ,searchType='image')
        #result = request.execute()
        for start in xrange(start,20,step):
            url = ('https://ajax.googleapis.com/ajax/services/search/images?v=1.0&start=%i&q=%s'\
                   % (start,search_string))
            request = urllib2.Request(url, None, {'Referer': ''})
            response = urllib2.urlopen(request)
            results = simplejson.load(response)

            if results:
                for image in results['responseData']['results']:
                    title = image.get('titleNoFormatting')
                    create_image(miracle, Image.SERVICE_TYPES[2][0],image.get('url'), title)
            time.sleep(2)
    return

def parse_instagram(miracle):
    tag = miracle.instagram_tags
    count = 20
    next_url = 'https://api.instagram.com/v1/tags/%s/media/recent?count=%s&max_id=0&client_id=%s' % (tag, count, settings.INSTAGRAM_CLIENT_ID)
    for i in xrange(1, 8):
        request = urllib2.Request(next_url, None, {'Referer': ''})
        response = urllib2.urlopen(request)
        results = simplejson.load(response)

        if not results:
            break

        next_url = results['pagination']['next_url']

        for media in results['data']:
            url = media['images']['standard_resolution']['url']
            title = miracle.name
            if media['caption']:
                title = media['caption']['text']

            create_image(miracle, Image.SERVICE_TYPES[0][0], url, title)

        time.sleep(2)
    return

def create_image(miracle, type, url, title, year = None):
    try:
        new_image = Image()
        new_image.miracle = miracle
        new_image.type = type
        new_image.url = url
        new_image.title = title
        if year is not None:
            new_image.year = year
        new_image.save()
    except IntegrityError: #not unique
        pass
    return