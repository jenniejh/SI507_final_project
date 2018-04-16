
from bs4 import BeautifulSoup
import requests
import json
import secrets
import sqlite3
import csv
import plotly.plotly as py

########## Data Source ##########
# https://www.internationalstudent.com
# US universities

# https://maps.googleapis.com/maps/api/place/textsearch/json
# coordinate


########## Data Access and Storage ##########

# Set up caching for google coordinate and US schools
CACHE_FNAME_schools = 'cache_schools.json'
try:
    cache_file_schools = open(CACHE_FNAME_schools, 'r')
    cache_contents_schools = cache_file_schools.read()
    CACHE_DICTION_schools = json.loads(cache_contents_schools)
    cache_file_schools.close()
except:
    CACHE_DICTION_schools = {}

CACHE_FNAME_GOOGLE = 'cache_GOOGLE.json'
try:
    cache_file_GOOGLE = open(CACHE_FNAME_GOOGLE, 'r')
    cache_contents_GOOGLE = cache_file_GOOGLE.read()
    CACHE_DICTION_GOOGLE = json.loads(cache_contents_GOOGLE)
    cache_file_GOOGLE.close()
except:
    CACHE_DICTION_GOOGLE = {}


# Set up a class for school instances
class School:
    def __init__(self, name, student_total, student_international, faculty_total, tuition,
                 street, city, state, zipcode, locale, longitude, latitude):
        self.name = name
        self.student_total = student_total
        self.student_international = student_international
        self.faculty_total = faculty_total
        self.tuition = tuition
        self.street = street
        self.city = city
        self.state = state
        self.zipcode = zipcode
        self.locale = locale
        self.longitude = longitude
        self.latitude = latitude


# Get data from google caching and school caching

def get_unique_key(url):
    return url 

def params_unique_combination(baseurl, params_d, private_keys = [secrets.google_places_key]):
    alphabetized_keys = sorted(params_d.keys())
    res = []
    for k in alphabetized_keys:
        if k not in private_keys:
            res.append("{}-{}".format(k, params_d[k]))
    return baseurl + "_".join(res)

# define a funcition to fetch data from Web or the cache file
# input: an url
# return: a dictionary of web pages of US schools
def get_schools_using_cache(url):
    unique_ident = get_unique_key(url)

    if unique_ident in CACHE_DICTION_schools:
        print("Getting cached data...")
        return CACHE_DICTION_schools[unique_ident]
    
    else:
        print("Making a request for new data...")
        page = requests.get(url).text
        CACHE_DICTION_schools[unique_ident] = page
        dumped_json_cache = json.dumps(CACHE_DICTION_schools)
        fw = open(CACHE_FNAME_schools,"w")
        fw.write(dumped_json_cache)
        fw.close()
        return CACHE_DICTION_schools[unique_ident]


# define a funcition to fetch data from either Google API using text search (see the website for text search) or the cache file
# input: street, city, state of a school
# return: a dictionary of the information about the school
def get_coordinate_using_cache(street, city, state): 

    query = street + ", " + city + ", " + state
    
    base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params_d = {}
    params_d["query"] = query 
    params_d["key"] = secrets.google_places_key

    unique_ident = params_unique_combination(base_url, params_d)

    if unique_ident in CACHE_DICTION_GOOGLE:
        print("\n Getting cached data...")
        return CACHE_DICTION_GOOGLE[unique_ident]  

    else: 
        print("\n Making a request for the new data")
        resp = requests.get(base_url, params_d)  
        resp_text = resp.text
        CACHE_DICTION_GOOGLE[unique_ident] = json.loads(resp_text) # load it to a python dictionary CACHE_DICTION
            
        dumps_data = json.dumps(CACHE_DICTION_GOOGLE) # Meanwhile, dump the data to a json file 
        cache_file = open(CACHE_FNAME_GOOGLE, "w") # write the data to the cache file CACHE_FNAME thus we can retrieve and use it next time
        cache_file.write(dumps_data)
        cache_file.close()
        return CACHE_DICTION_GOOGLE[unique_ident]

# define a function to get the coordinate of the school
# input: street, city, state of a school
# return a dictionary of coordinates
def get_coordinate(street, city, state):
    loc = get_coordinate_using_cache(street, city, state)
    dict_loc = {}
    if len(loc["results"]) >= 1:
        dict_loc["latitude"] = loc["results"][0]["geometry"]["location"]["lat"]
        dict_loc["longitude"] = loc["results"][0]["geometry"]["location"]["lng"] 
    else:
        pass
    return dict_loc 


# define a function to get the school information by scraping and crawling the web page
# input: state
# return: a list of school instances in the state
def get_schools(state):
    base_url = "https://www.internationalstudent.com"
    url = base_url + "/school-search/usa/" + state + "/?School%5BsearchProgram%5D=175" + "&School%5BsearchDegree%5D=4" 
    #limit all searches to Sociology with filter id 175
    # also limit all searches to doctorate degree with filter id 4
    
    page = get_schools_using_cache(url)
    soup = BeautifulSoup(page, "html.parser")
    
    # get the total number of web pages in this state
    try:
        num_page = int(soup.find(class_="summary").string[-1])
    except:
        num_page = 0
    
    school_list =[]
    if num_page > 0:
        for page in range(num_page):
            page_index = page+1
            url_update = base_url + "/school-search/usa/" + state + "/?School%5BsearchProgram%5D=175" + "&School%5BsearchDegree%5D=4" + "&School_page=" + str(page_index)
            
            page_update = get_schools_using_cache(url_update)
            soup_update = BeautifulSoup(page_update, "html.parser")
            
            schools = soup_update.find_all(class_="col text-secondary") # 25 schools on each page
            
            for i in schools:
                try:
                    school_name = i.find(class_="font-bitter text-left text-danger mb-2 mb-lg-0").string # get the school name
                    school_more = i.find(class_="col text-center order-sm-3")
                    school_url = school_more.find("a")["href"]
                    school_url_comp = base_url + school_url # url for a specific school

                    page_school = get_schools_using_cache(school_url_comp)
                    soup_school = BeautifulSoup(page_school, "html.parser")
                    
                    try:
                        student = soup_school.find(id="yw0")
                        stu_info = student.find_all(class_="f-12")
                        try:
                            stu_total = stu_info[0].string # get the total number of students in the school
                        except:
                            stu_total = None

                        try:
                            stu_international = stu_info[3].string # get the total number of international students in the school
                        except:
                            stu_international = None
                    except: # no information about students
                        stu_total = None
                        stu_international = None

                    try:
                        faculty = soup_school.find(id="yw1")
                        fac_info = faculty.find_all(class_="f-12")
                        fac_total = fac_info[0].string # get the total number of faculty in the school
                    except:
                        fac_total = None # no information about faculty

                    try:
                        tuition = soup_school.find(class_="blue").string.strip()[15:] # get the total amount of tuition 
                    except:
                        tuition = None # no information about tuition

                    loc = soup_school.find(class_= "f-12 mt-2") # get the information about the location of the school
                    try:
                        street = loc.contents[0].strip() # street name
                    except:
                        street = None

                    try:
                        city = loc.contents[2].strip().split(",")[0] # city name
                    except:
                        city = None

                    try:
                        state = loc.contents[2].strip().split(",")[1].split()[0] # state name
                        zipcode = loc.contents[2].strip().split(",")[1].split()[1][:5] # zipcode
                    except:
                        state = None
                        zipcode = None

                    try:
                        loc_info = soup_school.find(id="school-info-contact")
                        loc_info_more = loc_info.find(class_="mb-3")
                        locale = loc_info_more.contents[5].strip().split(":")[0] # type of the location such as city, town, rural, suburb, etc.
                    except:
                        locale = None

                    try:
                        coor = get_coordinate(street, city, state) # coordinate
                        longitude = coor["longitude"]
                        latitude = coor["latitude"]
                    except:
                        longitude = None
                        latitude = None

                    school_ins = School(school_name, stu_total, stu_international, fac_total, tuition,
                                        street, city, state, zipcode, locale, longitude, latitude) # create a school instance

                    school_list.append(school_ins) # append the instance to the list of schools
                except: # for schools that don't have any information
                    pass
    else:
        pass
    return school_list


# Create a list of school instances from all US states
schools_list_all = []
with open('us census bureau regions and divisions.csv') as statesCSVFile: # open a csv file which contains all US states
                                                                          # with this command, the file will be automatically closed after opening it
        d_states = csv.reader(statesCSVFile) 
        for row in d_states:
            if row[0] != "State":
                school_state = get_schools(row[0]) # row[0] is the state name
                schools_list_all = schools_list_all + school_state # append the school instances in the state to the original
print(len(schools_list_all))


# write the data into a CSV
outfile = open("schools_output.csv","w")
outfile.write('"Name","StudentTotal","InternationalStudentTotal","FacultyTotal","Tuition","Street","City","State","Zipcode","Locale","longitude","latitude"\n') # note: don't put space after each comma
for i in schools_list_all:
    outfile.write('"{}","{}","{}","{}","{}","{}","{}","{}","{}","{}","{}","{}"\n'.format(i.name, i.student_total, 
                    i.student_international, i.faculty_total, i.tuition, i.street, i.city, i.state, i.zipcode, i.locale, i.longitude, i.latitude))
outfile.close()


# Create an SQLite database called schoolinfo.db
def create_db():
    try: 
        conn = sqlite3.connect('schoolinfo.db')
        cur = conn.cursor()
    except Exception as e: # Print an error message if it fails.
        print(e)

    # clear out the database
    statement = '''
        DROP TABLE IF EXISTS 'Schools';
    '''
    cur.execute(statement)

    statement = '''
        DROP TABLE IF EXISTS 'States';
    '''
    cur.execute(statement)

    conn.commit()


    # Create two tables: Schools and States
    create_table_schools = '''
        CREATE TABLE "Schools" (
            'Id' INTEGER PRIMARY KEY AUTOINCREMENT,
            'Name' TEXT,
            'StudentTotal' INTEGER,
            'InternationalStudentTotal' INTEGER,
            'FacultyTotal' INTEGER,
            'Tuition' INTEGER,
            'Street' TEXT,
            'City' TEXT,
            'State' TEXT,
            'StateId' INTEGER,
            'Zipcode' TEXT,
            'Locale' TEXT,
            'Longitude' NUMERIC,
            'Latitude' NUMERIC
        );
    '''
    cur.execute(create_table_schools)
    conn.commit()

    create_table_states = '''
        CREATE TABLE "States" (
            'Id' INTEGER PRIMARY KEY AUTOINCREMENT,
            'State' TEXT,
            'StateCode' TEXT,
            'Region' TEXT,
            'Division' TEXT
        );
    '''
    cur.execute(create_table_states)
    conn.commit()
    conn.close()


# Populates using csv files of schools and states
def populate_db():

    # Connect to DB
    conn = sqlite3.connect('schoolinfo.db')
    cur = conn.cursor()

    # open the json file of countries
    with open('us census bureau regions and divisions.csv') as statesCSVFile: 
        d_states = csv.reader(statesCSVFile) 
        for row in d_states:
            # Insert the values to the table
            if row[0] != 'State': # Don't insert the first row
                insert_states = '''
                    INSERT INTO States
                    VALUES (?,?,?,?,?)
                '''
                values_states = (None, row[0], row[1], row[2], row[3])
                cur.execute(insert_states, values_states)
                conn.commit()

    with open('schools_output.csv') as schoolsCSVFile: 
        d_schools = csv.reader(schoolsCSVFile) 
        for row in d_schools:
            # Insert the values to the table
            if row[0] != 'Name': # Don't insert the first row
                insert_schools = '''
                    INSERT INTO Schools
                    SELECT ?,?,?,?,?,?,?,?,?,S.Id,?,?,?,?
                    FROM States AS S
                    WHERE S.State = ?
                '''
                values_schools = (None, row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9],row[10],row[11],row[7])
                cur.execute(insert_schools, values_schools)
                conn.commit()     
    conn.close()
    # ignore those schools with no clear state information....??? Must be wrong

create_db()
populate_db()

########## Data Processing ##########









