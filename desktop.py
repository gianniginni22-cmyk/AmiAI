"""Desktop entry point with automatic HTTPS update check."""
import json, os, socket, subprocess, sys, threading, time, urllib.parse, urllib.request
from pathlib import Path
import uvicorn, webview
from app.main import app

APP_VERSION='0.7.3'
UPDATE_MANIFEST_URL=os.getenv('AMIGURUMI_UPDATE_MANIFEST','https://raw.githubusercontent.com/gianniginni22-cmyk/AmigurumiAI/main/update-manifest.json')

def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0)); return int(s.getsockname()[1])

def run_server(port):
    config=uvicorn.Config(app,host='127.0.0.1',port=port,log_level='warning',access_log=False)
    server=uvicorn.Server(config); server.install_signal_handlers=lambda:None; server.run()

def wait_ready(url,timeout=15):
    deadline=time.time()+timeout
    while time.time()<deadline:
        try:
            with urllib.request.urlopen(url,timeout=.5) as r:
                if r.status==200:return
        except Exception: time.sleep(.1)
    raise RuntimeError('Il server locale non è diventato disponibile.')

def version_tuple(v):
    try:return tuple(int(x) for x in v.split('.')[:4])
    except:return (0,)

def check_update():
    if not UPDATE_MANIFEST_URL: return None
    try:
        req=urllib.request.Request(UPDATE_MANIFEST_URL,headers={'User-Agent':'AmigurumiAI'})
        with urllib.request.urlopen(req,timeout=5) as r: m=json.load(r)
        latest=str(m.get('version','')).strip(); url=str(m.get('installer_url','')).strip(); sha=str(m.get('sha256','')).strip()
        parsed=urllib.parse.urlparse(url)
        if latest and parsed.scheme=='https' and parsed.netloc and version_tuple(latest)>version_tuple(APP_VERSION) and len(sha)==64 and all(c in '0123456789abcdefABCDEF' for c in sha):
            return latest,url,sha
    except Exception: return None
    return None

def start_update(info):
    latest,url,sha=info
    exe=Path(sys.executable).resolve().parent/'AmigurumiAI-Updater.exe'
    if not exe.exists(): return False
    subprocess.Popen([str(exe),url,sha,str(os.getpid())],close_fds=True)
    return True

def main():
    port=free_port(); threading.Thread(target=run_server,args=(port,),daemon=True).start(); wait_ready(f'http://127.0.0.1:{port}/api/health')
    info=check_update()
    if info and start_update(info):
        return
    window=webview.create_window('Amigurumi AI Designer',f'http://127.0.0.1:{port}/',width=1440,height=920,min_size=(1000,700),resizable=True)
    webview.start(debug=False)

if __name__=='__main__': main()
