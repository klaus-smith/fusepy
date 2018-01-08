# "Implement a Fuse Driver for Google Drive" from GNU/Linux Magazine HS N°90 by Sylvain Peyrefitte 
# As a Passionate I love to buy IT Reviews and try to reproduce interesting article like this one !

from __future__ import print_function
import httplib2
import os
import io
from errno import EROFS

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

from stat import S_IFDIR, S_IFREG

from fuse import FUSE, FuseOSError, Operations


try:
    import argparse
    
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/drive.metadata.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Drive API Python Quickstart'

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'drive-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to' + credential_path)
    return credentials

class GoogleDriveFS(Operations):
    def __init__(self):
        self.credentials = get_credentials()
        self.http = self.credentials.authorize(httplib2.Http())
        self.service = discovery.build('drive', 'v3', http=self.http, cache_discovery=False)
        self.items = {}
        self.fh = {}
        self.next_fh = 0
    
    def readdir(self, path, fh):
        results = self.service.files().list(fields="nextPageToken,files(id, name, size)").execute()
        self.items = dict([(item['name'], (item['id'], int(item.get('size') or '0'))) for item in results.get('files', [])])
	return ['.', '..'] + list(self.items.keys())

    def getattr(self, path, fh=None):
	if path == '/':
	    return dict(st_mode=(S_IFDIR | 0o755), st_nlink=2)
	if path[1:] not in self.items:
	    raise FuseOSError(EROFS)
        
        return dict(st_mode=(S_IFREG | 0o755), st_nlink=1, st_size=int(self.items[path[1:]][1]))

    def open(self, path, flags):
	if path[1:] not in self.items:
	    raise FuseOSError(EROFS)

	request = self.service.files().get_media(fileId=self.items[path[1:]][0])
	fh = io.BytesIO()
	downloader = http.MediaIoBaseDownload(fh, request)
	done = False
	while done is False:
	    status, done = downloader.next_chunk()

	fh_id = self.next_fh
	self.next_fh += 1
	self.fh[fh_id] = fh

	return fh_id

    def read(self, path, size, offset, fh):
	if fh not in self.fh:
	    raise FuseOSError(EROFS)
	self.fh[fh].seek(offset)
	return self.fh[fh].read(size)

def main():
    FUSE(GoogleDriveFS(), "/tmp/test-fuse", nothreads=True, foreground=True)

if __name__ == '__main__':
    main()
