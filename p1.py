#!/usr/bin/env python

import json, requests, datetime, pickle, collections, csv, operator

URL_PREFIX = 'https://bitbucket.org/api/2.0/'
DEF_QUERY  = 2000

parameter = 'repositories'
per_page = '?pagelen=100'

json_response = requests.get(URL_PREFIX + parameter + per_page).json()
next_page = json_response['next']

users = {}
private = 0

cur_page = 1

# I had to edit extract_data()
# Previously, I had two dictionaries: one for users and one for repos
# But I realized repos are NOT guaranteed to be uniquely named, which is
# why we were getting fewer than we should've when searching.
# The 'full_name' in json_response IS guaranteed to be unique since it includes
# user's name, which is also guaranteed to be unique.
# So now there is only one main dict, users, which contains all info.
# users[username] is a nested dictionary and is just the names of that user's repos
# as the key, and the rest of the json_response dict as the value.
# Yes, triple-nested dictionaries.

def extract_data(repo):
    global users
    username, slash, reponame = repo['full_name'].partition('/')
    try:
        users[username][reponame] = repo
    except KeyError:
        users[username] = {}
        users[username][reponame] = repo

def get_next_page():
    global json_response
    items = json_response['values']
    for item in items:
        extract_data(item)
    json_response = requests.get(json_response['next']).json()

def query(num):
    global json_response
    global cur_page
    if num == 0:
        # Go until there is nothing left!
        while json_response.has_key('next'):
            if cur_page % 100 == 0:
                print 'On page', cur_page
            get_next_page()
            cur_page += 1
            for entry in range(len(json_response['values'])):
                if json_response['values'][entry]['created_on'][:13] == '2014-09-23T17':
                    print 'Found repos created up to 5pm 9/23/2014'
                    print 'Pages crawled:', cur_page
                    return
    else:
        for i in range(num):
            get_next_page()

# This is what the following lines do:
#  - Try to load a pickled file from the disk
#    - This is just a cache of the users previously found to save time. Delete these files to search again
#  - If the file is there, it just loads it
#  - If the file is NOT there, then it uses BitBucket's API to query DEF_QUERY number of pages
#    - After it does this, it will save a pickled version of the dictionary it generates to be used as cache above


try:
    users = pickle.load( open('./users_cache/users.p', 'r') )
    print '-- Using cached users --'
except IOError:
    print '-- Grabbing', DEF_QUERY, 'pages --'
    query(DEF_QUERY)
    pickle.dump( users, open('./users_cache/users.p', 'w') )
    print '-- Results cached --'

print 'Number of users found:', len(users.keys())
print 'Number of repos found:', sum([len(users[user].keys()) for user in users.keys()])
# Number of repos should be (number of queries) * (per_page)

# This loop gives us the languages from repos that have a specified language
# We can make a graph based on this, but mention that a lot of repos don't specify language

# Can you tell I like list comprehensions?
languages = [users[user][repo]['language'] for user in users.keys() for repo in users[user].keys() if users[user][repo]['language']]
lang_count = collections.Counter(languages)
writer = csv.writer(open('languages.csv', 'w'))
for key, value in lang_count.items():
    writer.writerow([key, value])

num_repos_per_user = [ len(users[user].keys()) for user in users.keys() ]
num_repos_count = collections.Counter(num_repos_per_user)
writer = csv.writer(open('num_repos.csv', 'w'))
for key, value in num_repos_count.items():
    writer.writerow([key, value])

print 'Number of repos'
for repo in num_repos_count.keys():
    print '{0:3} {1:4}'.format(repo, num_repos_count[repo])
print '----------------'

# This gets the years repos were created
# Then we get a count of how often each year was listed

year_created = [ users[user][repo]['created_on'][:4] for user in users.keys() for repo in users[user].keys() ]
year_count = collections.Counter(year_created)
f = open('year_created.csv', 'w')
writer = csv.writer(f)
for year in year_count.keys():
    writer.writerow([year, year_count[year]])
f.close()

print 'Year created'
for year in year_count.keys():
    print '{0:4} {1:4}'.format(year, year_count[year])
print '-----------------'

# Size of repo binned to 100MB

sizes = [ users[user][repo]['size'] for user in users.keys() for repo in users[user].keys() ]
sizes.sort()
binned_sizes = [size/100000000 for size in sizes]
sizes_dict = {}
for b in binned_sizes:
    if b < 10:
        try:
            sizes_dict[b] += 1
        except KeyError:
            sizes_dict[b] = 1
    else:
        try:
            sizes_dict[10] += 1
        except KeyError:
            sizes_dict[10] = 1

f = open('overall_sizes.csv', 'w')
writer = csv.writer(f)
for s in sizes_dict.keys():
    writer.writerow([s, sizes_dict[s]])
f.close()

print 'Overall size (100MB)'
for size in sizes_dict.keys():
    print '{0:3} {1:5}'.format(size, sizes_dict[size])
print '--------------'

lang_by_year = {}
for year in range(2008, 2013):
    lang_by_year[year] = [ users[user][repo]['language'] for user in users.keys() for repo in users[user].keys() if int(users[user][repo]['created_on'][:4]) == year ]

counted_lang_by_year = {}
for year in range(2008, 2013):
    counted_lang_by_year[year] = collections.Counter(lang_by_year[year])

for year in counted_lang_by_year.keys():
    print sorted(counted_lang_by_year[year].items(), key=operator.itemgetter(1))[::-1][1:10]
