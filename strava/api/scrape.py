import requests
from bs4 import BeautifulSoup


class WebSession(object):

    user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.52 Safari/537.17'
    headers = None
    cookies = None
    
    def __init__(self):
        pass
        
    @property
    def default_headers(self):
        return {'User-Agent': self.user_agent}
    
    @property
    def authenticated(self):
        # XXX: This is not actually a good test.
        return self.cookies is not None
    
    def login(self, username, password):
    
        headers = {}
        headers['User-Agent'] = self.user_agent
        
        r = requests.get('https://www.strava.com/login', headers=headers)
        soup = BeautifulSoup(r.text)
        
        token_name = soup.find('meta', attrs=dict(name="csrf-param"))['content']
        token_value = soup.find('meta', attrs=dict(name="csrf-token"))['content']
        
        r = requests.post('https://www.strava.com/session',
                          params={'email': username, 'password': password, 'plan': '', token_name: token_value},
                          cookies=r.cookies,
                          headers=headers)
        
        soup = BeautifulSoup(r.text)
        if not soup.title.string.startswith('Strava | Home'):
            raise RuntimeError("Login failed")
        
        self.cookies = r.cookies
    

    def export_gpx(self, id):
        """
        Export a ride as GPX. 
        
        (requires authentication -- and premium acct)
        """
        if not self.authenticated:
            raise RuntimeError("Requires authentication.")
        
        # http://app.strava.com/activities/:id/export_gpx
        r = requests.get('http://app.strava.com/activities/{id}/export_gpx'.format(id=id),
                         cookies=self.cookies,
                         headers=self.default_headers)
        content = r.content
        print(content[:1024])
        

    
