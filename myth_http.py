import datetime
import BaseHTTPServer
import urllib
import cgi
import json
import MySQLdb
import re
import sys, traceback
from MythTV import MythDB
from StringIO import StringIO

class SimpleHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    frontend = None
    db = None

    def init_frontend(self):
       host = u'mythhostname' #yours here 
       passw = "sekret" #mysql password
       db = "mythconverg" #myth mysql database name
       user = "mythtv" #mysql username

       try: 
         database = MythDB(args=(('DBHostName',host),
                  ('DBName',db),
                  ('DBUserName',user),
                  ('DBPassword',passw),
                  ('DBPort',3306),
                  ('SecurityPin',0000)))   
         self.frontend = database.getFrontend(host)
         # can we do this just once somehow? fixme
         self.db = MySQLdb.connect(host="localhost", user=user, passwd=passw,db=db)
       except Exception as e:
         exc_type, exc_value, exc_traceback = sys.exc_info()
         traceback.print_exc(exc_traceback, file=sys.stdout)
         print "Couldn't connect to database",e


    def do_GET(self):
        if (self.frontend and self.db):
           print "ok"
        else:
           print "Nok"
           self.init_frontend()

        #self.send_header("Location", self.path + "/")
        #self.end_headers()
        #look for nowp request
        nowp = self.do_now_playing()
        self.send_response(200)
        self.end_headers()
        #print nowp.__class__
        #print nowp

#       print "PATH",self.path
      
        if (re.search("nowp",self.path)):
          #print "ok"

          if (re.search("html",self.path)):
            j = self.pp_html(nowp)
          else:      
            j = json.dumps(nowp)
          self.wfile.write(j)
        else:
          #print "Nok"
          self.wfile.write("nothing found")
       
### html
    def pp_html(self,dict):
       str = "<html><body>"
       for k in dict:
         v = dict[k]
         str = str +  "<p>%s - %s</p>" % (k,v)

       return str

####
# Get what is playing now
####

    def do_now_playing(self,force=False):

      results= {}
      if (self.frontend and self.db):
        output = self.frontend.sendQuery("location")
        #print output
        arr = output.rsplit(" ")
        #print len(arr)," ",str(arr)

        m = re.search('Playback', output)#if we are on guidegrid etc we don't want it

        if(m and len(arr)>10):                                          
          channel = arr[6]
          results["channum"]=arr[6]
          dt = arr[7]
          dtnow = datetime.datetime.now()
          dtnfmt = dtnow.strftime("%Y-%m-%d %H:%M:%S")
          results["datetime"]=dt

          cursor = self.db.cursor()
          q ="select title,starttime,callsign,programid from program,channel where program.chanid=channel.chanid and starttime <= '"+dtnfmt+"' and endtime > '"+dtnfmt+"' and program.chanid='"+channel+"' limit 1;"
          #print q
          cursor.execute(q)

          result = cursor.fetchall()
          if len(result)==0:
            print "No result for sql query - did you run mythfilldb or check EIT?"
          else:
            record = result[0] 
            print "RECORD",str(record)

            res2=""
            if (record!=""):
              secs = record[1]
              diff_secs=dtnow-secs
              print "SECS",secs,"dtnow",dtnow,"diff",diff_secs

              results["secs"]=diff_secs.seconds

              ch = record[2]
              ch = ch.lower()
              ch = ch.replace(" ","")
              results["channel"]=ch
              t = record[0]
              results["title"]=t
              crid = record[3]

            # should use the dns here
            # but instead we just try and fail if no data
              if (crid):
                 crid = "crid://"+crid
                 u = "http://services.notu.be/resolve?uri\[\]="+crid+"&noredirect=true"
                 #print "u",u
                 data = urllib.urlopen(u).read()
                 # parse the json, get 'p' (should be only one)
                 j = json.loads(data)
                 arr = j[1]
                 d = arr[0]
                 p = d["p"]
                 if (p):
                   pid = p.replace("http://www.bbc.co.uk/programmes/","")
                   pid = pid.replace("#programme","")
                   pid = pid.replace(".rdf","")
   
                   results["pid"]=pid

      return results

def test(HandlerClass = SimpleHTTPRequestHandler,
         ServerClass = BaseHTTPServer.HTTPServer):
    BaseHTTPServer.test(HandlerClass, ServerClass)


if __name__ == '__main__':
    test()


