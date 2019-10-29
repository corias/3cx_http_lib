## 3CX HTTP(S) API REQUESTS LIB
import csv, json, logging, os, requests
from datetime import datetime
# REMOVE HTTPS WARNINGS
import warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning
warnings.simplefilter('ignore',InsecureRequestWarning)

class threecx:

    # INITIALIZE
    def __init__ (self, url, username, password):
        self.url = url
        self.username = username
        self.password = password
        self.login_path = '/api/login'
        self.extensions_path = '/api/ExtensionList/export?'
        self.records_path = '/api/RecordingList/'
        self.record_download_path = '/api/RecordingList/Download'
        self.headers = {
            'Content-Type': 'application/json;charset=utf-8',
        }   
    # GET PHONE NUMBER FROM TEXT FIELD
    def tonumber(self, text):
        number = int(str(int(''.join(list(filter(str.isdigit, text)))))[:11])
        return number
    # FIND IF EXTENSION IS INTERNAL
    def isinternal(self, text):
        number = self.tonumber(text)
        if number < 10000: #4 DIGIT NUMBER MAXIMUM
            return True
        else:
            return False

    # PRINT TO STDOUT AND TO LOG AT THE SAME TIME
    def printlog(inputstring, loglevel=''):
        if loglevel == 'error':
            logging.error(inputstring)
        elif loglevel == 'warning':
            logging.warning(inputstring)
        elif loglevel == 'debug':
            logging.debug(inputstring)
        else:
            logging.info(inputstring)
        print(inputstring)
    
    # AUTHORIZE ON 3CX
    def auth (self):
        auth_data = {
            "Username": self.username,
            "Password": self.password
        }
        login_url = self.url + self.login_path
        try:
            auth = requests.post(login_url, data = str(auth_data), verify = False, headers=self.headers)
            if auth.status_code == 200:
                self.cookies = auth.cookies
                return True
            else:
                logging.error('Auth failed with code ' + str(auth.status_code))
                self.cookies = ''
                return False
        except:
            return False
    
    # DOWNLOAD EXTENSIONS CSV
    def download_extensions (self, targetpath):
        extensions_url = self.url + self.extensions_path
        getfile = requests.get(extensions_url, verify = False, cookies = self.cookies, stream = True)
        if getfile.status_code == 200:
            with open(targetpath, 'wb') as file:
                for chunk in getfile:
                    file.write(chunk)
        else:
            logging.error('Download failed with code ' + str(getfile.status_code))

    # GET 3CX RECORDS COUNT
    def get_records_count (self):
        count = 0
        recordslist_url = self.url + self.records_path
        getrecordscount = requests.get(recordslist_url, verify = False, cookies = self.cookies)
        if getrecordscount.status_code == 200:
            recordscount_json = json.loads(getrecordscount.text)
            count = recordscount_json['TotalRowsCount']
            logging.info('Found ' + str(count) + ' records on PBX')
        else:
            logging.error('Failed to get records count with code ' + getrecordscount.status_code)
        return count

    # GET ONE PAGE OF 3CX RECORDS
    def get_records_page (self, start, count):
        recordslist_url = self.url + self.records_path + '?count=' + str(count) + '&start=' + str(start)
        getrecordslist = requests.get(recordslist_url, verify = False, cookies = self.cookies)
        records_out = []
        if getrecordslist.status_code == 200:
            recordslist_json = json.loads(getrecordslist.text)['list']
            for record in recordslist_json:
                record_out = {
                    'Id' : record['Id'],
                    'Date' : record['Date'],
                    'From' : record['Participants'][0],
                    'To' : record['Participants'][1]
                    }
                records_out.append(record_out)
        else:
            logging.info('Failed to get records list with code ' + getrecordslist.status_code)
        return records_out


    # GET ALL RECORDS
    def get_all_records (self):
        count = self.get_records_count()
        records = []
        # PAGE BY PAGE INPUT
        hop = 1000
        shift = 0
        while shift < count:
            logging.info('Reading records '+ str(shift) + "-" + str(shift+hop) + "...")
            records_tmp = self.get_records_page(shift, hop)
            records.extend(records_tmp)
            shift = shift + hop
        #records = get_records_page(0, count)
        return records

    # GET RECORD PAGE WITH SPECIFIC DATE
    def get_records_page_by_date(self, start, count, targetdate):
        recordslist_url = self.url + self.records_path + '?count=' + str(count) + '&start=' + str(start)
        getrecordslist = requests.get(recordslist_url, verify = False, cookies = self.cookies)
        records_out = []
        dtt = datetime (int(targetdate.split('-')[0]), int(targetdate.split('-')[1]), int(targetdate.split('-')[2]))
        if getrecordslist.status_code == 200:
            recordslist_json = json.loads(getrecordslist.text)['list']
            date_ok = True
            for record in recordslist_json:
                # DEFINE IF DATE IS IN RANGE
                record_out = {}
                record_date = record['Date']
                record_date = record_date.split('T')[0]
                record_time = record['Date'].split('T')[1].split('.')[0]
                rtt = datetime (int(record_date.split('-')[0]), int(record_date.split('-')[1]), int(record_date.split('-')[2]))
                if record_date == targetdate:
                    record_out = {
                        'Id' : record['Id'],
                        'Date' : record_date + '_' + record_time,
                        'From' : record['Participants'][0],
                        'To' : record['Participants'][1]
                        }
                    
                elif rtt < dtt:
                    date_ok = False
                    break
                else:
                    # DATE IS OUT OF RANGE
                    #logging.info('Skip')
                    a = 1
                records_out.append(record_out)
        else:
            logging.error('Failed to get records list with code ' + getrecordslist.status_code)
        return records_out

    # GET ALL RECORDS WITH SPECIFIC DATE
    def get_all_records_by_date(self, targetdate):
        count = self.get_records_count()
        records=[]
        hop = 1000
        shift = 0
        while shift < count:
            logging.info('Reading records '+ str(shift) + "-" + str(shift+hop) + "...")
            records_tmp = self.get_records_page_by_date(shift, hop, targetdate)
            #print(str(len(records_tmp)))
            records.extend(records_tmp)
            shift = shift + hop
            if len(records_tmp) < hop:
                break
        logging.info('Found ' + str(len(records)) + ' records for this date')
        return records

    # DOWNLOAD SINGLE RECORD
    def download_record(self, record_id, filepath):
        record_download_url = self.url + self.record_download_path + "?file=" + str(record_id)
        file_exists = os.path.isfile(filepath)
        if not file_exists:
            try:
                getfile = requests.get(record_download_url, verify = False, cookies = self.cookies, stream=True, allow_redirects=False)
            except:
                print('Download failed with status code ' + str(getfile.status_code))
            if getfile.status_code == 200:
                getfile.raise_for_status()
                with open(filepath, 'wb') as file:
                    for chunk in getfile.iter_content(chunk_size=8192):
                        if chunk:
                            file.write(chunk)
                    logging.info('Download complete')
                    print('Download complete')
            elif getfile.status_code == 302:
                logging.error('Download failed with redirect code 302. This happens when call record does not exist on 3CX HDD')
                print('Download failed with redirect code 302. This happens when call record does not exist on 3CX HDD')
                norecord_path = filepath.replace('.wav','.NORECORD')
                #print (norecord_path)
                #os.mknod(norecord_path)
                with open(norecord_path, 'wb') as file:
                    file.close() # Kolkhoz
            else:
                logging.error('Download failed with status code ' + str(getfile.status_code))
                print('Download failed with status code ' + str(getfile.status_code))
        else:
            logging.warning('File already exists')

    # DOWNLOAD RECORDS FROM LIST
    def download_records_list(self, records, output_folder):
        direction = 'UNKNOWN'
        #print(output_folder)
        for record in records:
            if str(record) != "{}":
                date_time = record ['Date']
                raw_from = record ['From']
                raw_to = record ['To']
                record_id = record ['Id']
                onlytime = str(date_time.replace(':', '').replace('-','')).split("+")[0]
                #print('Buggy time: ' + onlytime)

                # GET YEAR AND CHECK IF YEAR FOLDER EXISTS
                yearfolder = output_folder + date_time.split('_')[0].split('-')[0] + "\\"
                if not os.path.isdir(yearfolder):
                    os.mkdir(yearfolder)
                mdfolder = yearfolder + date_time.split('_')[0].split('-')[1] + '-' + date_time.split('_')[0].split('-')[2] + "\\"
                if not os.path.isdir(mdfolder):
                    os.mkdir(mdfolder)
                
                # FIND IF SOME EXTENSION IS INTERNAL AND SET DIRECTION
                ext_from = self.tonumber(raw_from)
                ext_to = self.tonumber(raw_to)
                if self.isinternal(raw_from):
                      subfolder = str(ext_from).zfill(3)
                      direction = "OUT"
                elif self.isinternal(raw_to):
                    subfolder = str(ext_to).zfill(3)
                    direction = "IN"
                else:
                    subfolder = 'Other'
                if not os.path.isdir(mdfolder + subfolder):
                    os.mkdir(mdfolder + subfolder)
                # GENERATE FILENAME
                filename = str(record_id) + "_" + direction + "_" + onlytime + '_' + str(ext_from).zfill(3) + "_" + str(ext_to).zfill(3) + ".wav"
            
                #CHECK IF FILE EXIST
                filepath = mdfolder + subfolder + "\\" + filename
                if not os.path.isfile(filepath):
                    logging.info('Downloading ' + filepath + "...")#
                    print('Downloading ' + filepath + '...')#
                    self.download_record(record_id, filepath)
                else:
                    logging.info('Skipping (file exists) ' + filepath + "...")#
                    print('Skipping (file exists) ' + filepath + '...')#
                print('\r')#
