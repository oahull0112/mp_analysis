# -*- coding: utf-8 -*-
"""
Created on Fri Dec  3 17:41:26 2021

@author: Shaun

"""
import pandas as pd
import re

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdrivermanager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

import helper
from climb import MP_Climb
from climber import MP_Climber

LOCATION_DICT = {'Red River Gorge':'105841134', 'New River Gorge':'105855991',
                 'Yosemite':'105833388', 'Gunks':'105798167', 'Boulder Canyon':'105744222',
                 'Joshua Tree':'105720495', 'Eldorado Canyon':'105744246', 'Rumney':'105867829',
                 'Red Rocks':'105731932', 'Horseshoe Canyon':'105903004', 'Indian Creek':'105716763',
                 'Smith Rock':'105788989', 'Squamish':'105798170'}
SPORT_CRAGS = ['Rumney', 'New River Gorge', 'Red Rocks', 'Boulder Canyon',
               'Red River Gorge', 'Horseshoe Canyon', 'Smith Rock']
TRAD_CRAGS = ['Squamish', 'Joshua Tree', 'Eldorado Canyon', 'Yosemite', 'Gunks',
              'Indian Creek']

def test_main():
    for location in SPORT_CRAGS:
        location_code = LOCATION_DICT[location]
        print('Pulling Data for: ' + location)
        climb_data, climber_data = loop_through_areas(location_code, location, climb_filter=['Sport'])
    for location in TRAD_CRAGS:
        location_code = LOCATION_DICT[location]
        print('Pulling Data for: ' + location)
        climb_data, climber_data = loop_through_areas(location_code, location, climb_filter=['Trad'])

def loop_through_areas(location_code, location, climb_data=pd.DataFrame(), climber_data=pd.DataFrame(), pull_climber_data=True, climb_filter=['sport','trad','tr']):
    climb_filter = [i.title() for i in climb_filter]
    soup = helper.is_climb_url(get_mp_link(location_code, climb_filter))
    if soup:
        # currently the links generated by get_mp_link are broken
        # a link needs to be a "view all" link in order for this to work, otherwise this works:
        # int(css.find_all(class_='float-md-left')[0].get_text().split('Results 1 to ')[1].split()[2][0:-1])
        climb_total = int(soup.find_all(class_="float-md-left")[0].get_text().split('Results 1 to ')[1].split(' of')[0])
        if climb_total<1000:
            climb_data, climber_data = loop_through_climbs(soup, location, location_code, pull_climber_data, climb_total, climb_filter=climb_filter)
        else:
            soup_parent = helper.is_climb_url("https://www.mountainproject.com/area/" + location_code)
            if soup_parent:
                areas = soup_parent.find_all(class_="lef-nav-row")
                area_links = [i.find_all('a')[0] for i in areas]
                for area_link in area_links:
                    location_code = area_link.get('href').split('/')[4]
                    print(area_link.get('href').split('/')[5])
                    area_data, area_climber_data = loop_through_areas(location_code, location, climb_data, climber_data, pull_climber_data)
                    climb_data = helper.append_dataframes(climb_data, area_data)
                    climber_data = helper.append_dataframes(climber_data, area_climber_data)
                    climb_data.to_excel(location+'_climbs.xlsx')
                    climber_data.to_excel(location+'_climbers.xlsx')
        climb_data.to_excel(location+'_climbs.xlsx')
        climber_data.to_excel(location+'_climbers.xlsx')
    return climb_data, climber_data

def loop_through_climbs(soup, location, location_code, pull_climber_data, climb_total, constant_export=False, suppress_print=False, climb_filter=['sport','trad','tr']):
    climb_data = pd.DataFrame()
    climber_data = pd.DataFrame()
    link_list = []
    count=0

    for link in soup.find_all(href=re.compile("mountainproject.com/route/")):
        if not(link.get('href') is None) and (count<climb_total):
            count=count+1
            climb_soup = helper.is_climb_url(str(link.get('href'))) # 
            if climb_soup:
                route = MP_Climb(climb_soup)
                print(route.name)
                if pull_climber_data:
                    climber_data, link_list = get_ascent_data(route, climber_data,
                                                              link_list, location,
                                                              constant_export,
                                                              False, climb_filter=climb_filter)
                    checkpoint_climber_data(climber_data,
                climb_data = helper.append_dataframes(climb_data, route.to_df())
                if constant_export:
                    climb_data.to_excel(location+'_climbs_'+location_code+'.xlsx', index=False)
                if count>0 and count%50==0 and not suppress_print:
                    print('=====Climb Count: ' + str(count))
                    
    return climb_data, climber_data

def get_ascent_data(route, climber_data, link_list, location, constant_export, suppress_print, climb_filter=['sport','trad','tr']):
    
    climber_links = get_climber_links(route.ascents_link)
    
    climber_count=0
    for link in climber_links:
        if not (link in link_list):
            
            link_list = link_list + [link]
            name = link.get_text()
            #formatted_name = (re.search(r'>([^<]+)<', str(link))).group(1).lower().replace(' ','-')
            formatted_name = name.lower().replace(' ', '-')
            url = f'https://mountainproject.com{link.get('href')}/{formatted_name}/tick-export'

            climber_soup = helper.is_climb_url(url)
            climber_o = MP_Climber(climber_soup, name=name, location_filter=location, sport_definition=climb_filter)
            climber_data = helper.append_dataframes(climber_data, climber_o.to_df())
            climber_count=climber_count+1
            
            print(climber_o.name)
            
            if constant_export:
                climber_data.to_excel(location+'_climbers_temp.xlsx', index=False)
            if climber_count> 0 and climber_count%250==0 and not suppress_print:
                print('Climber Count: ' + str(climber_count) + ', ', end=' ')
                        
    return climber_data, link_list

def get_climber_links(url):
    
    ff_path = '/Users/oliviahull/geckodriver'
    
    cService = webdriver.FirefoxService(executable_path=ff_path)
    driver = webdriver.Firefox(service = cService)
    driver.get(url)
    driver.implicitly_wait(20)
    
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    tick_options = soup.find_all(class_="table table-striped")
    ticks = tick_options[3]
    climber_links = ticks.find_all(href=re.compile("/user/"))

    return climber_links

#def checkpoint_climbers

# returns the area list of climbs page
def get_mp_link(area_id, climb_filter=['sport','trad','tr']):
    climb_filter = [i.lower() for i in climb_filter]
    mp_link = "https://www.mountainproject.com/route-finder?&selectedIds=" + area_id
    if 'sport' in climb_filter:
        mp_link = mp_link + "&is_sport_climb=1"
    if 'trad' in climb_filter:
        mp_link = mp_link + "&is_trad_climb=1"
    if 'tr' in climb_filter or 'top rope' in climb_filter:
        mp_link = mp_link + "&is_top_rope=1"
    #Will search all rock climbs between 5.0 and 5.15d with any stars or pitches
    mp_link = mp_link + "&diffMaxrock=12400&diffMinrock=1000&sort1=area&sort2=rating&pitches=0&stars=0&type=rock&viewAll=1"
    return mp_link

def get_ascent_data_old(route, climber_data, link_list, location, constant_export, suppress_print, climb_filter=['sport','trad','tr']):
    climber_count=0
    route_soup = helper.is_climb_url(route.ascents_link) # this is the links to the ticks/opinions page for a climb
    if route_soup:
        #tick_options = route_soup.find_all(class_="table table-striped")
        if len(tick_options)>=4:
            ticks = tick_options[3]
            climber_links = ticks.find_all('a')
            for link in climber_links:
                if not (link in link_list):
                    link_list = link_list + [link]
                    climber_soup = helper.is_climb_url(link.get('href')+'/tick-export')
                    climber_o = MP_Climber(climber_soup, name=link.get_text(), location_filter=location, sport_definition=climb_filter)
                    climber_data = helper.append_dataframes(climber_data, climber_o.to_df())
                    climber_count=climber_count+1
                    if constant_export:
                        climber_data.to_excel(location+'_climbers_temp.xlsx', index=False)
                    if climber_count> 0 and climber_count%250==0 and not suppress_print:
                        print('Climber Count: ' + str(climber_count) + ', ', end=' ')
    return climber_data, link_list
