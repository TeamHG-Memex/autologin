from scrapyd_api import ScrapydAPI
import traceback
import time

class ScrapydLoginFinderJob(object):

    def __init__(self, seed_url, username, password, db_name, use_formasaurus=True, scrapyd_host="localhost", scrapyd_port="6800", project="default", spider="login_finder"):

        scrapy_url = "http://" + scrapyd_host + ":" + str(scrapyd_port)
        self.scrapi = ScrapydAPI(scrapy_url)
        self.project = project
        self.spider = spider
        self.seed_url = seed_url
        self.username = username
        self.password = password
        self.db_name = db_name
        self.use_formasaurus = use_formasaurus
        print 'LoginFinderJob use formasaurus? %s' % self.use_formasaurus

    def schedule(self):

        self.job_id = self.scrapi.schedule(self.project, self.spider, seed_url = self.seed_url, username = self.username, password = self.password, db_name = self.db_name, use_formasaurus = self.use_formasaurus)

        return self.job_id

    def list_jobs(self):
        return self.scrapi.list_jobs(self.project)

    def get_state(self):

        try:
            self.job_id
        except:
            Exception("You must schedule a job before getting the state!")

        try:
            for job in self.scrapi.list_jobs(self.project)["running"]:
                print self.job_id, job["id"]
                if job["id"] == self.job_id:
                    return "Running"

            for job in self.scrapi.list_jobs(self.project)["pending"]:
                print self.job_id, job["id"]
                if job["id"] == self.job_id:
                    return "Pending"

        except:
            print "handled exception:"
            traceback.print_exc()
            return None

        return "Done"
    
    def block_until_done(self, timeout = 120):
        
        exec_time = 0
        while 1:
            exec_time += 1
            if exec_time == timeout:
                raise Exception("Timeout time reached for login_finder spider execution")

            time.sleep(1)
            state = self.get_state()
            if state == "Done":
                break

if __name__ == "__main__":

    slfj = ScrapydLoginFinderJob("https://github.com/", "actest1234", "passpasspass123")
    slfj.schedule()
    slfj.block_until_done()
    print "OK you're good to go"

