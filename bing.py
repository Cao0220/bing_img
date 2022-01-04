import json
import requests
import os
import time

def get_img(cc):
    url='https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&cc='+cc
    json_data=requests.get(url).text
    data = json.loads(json_data)
    for i in data['images']:
        day=i["startdate"]
        day_for=day[0:4]+"-"+day[4:6]+"-"+day[6:8]
        img_url=i["urlbase"]
        # os.system("mkdir /root/bing_img/"+day_for+"/")
        os.system("cd /root/bing_img/"+day_for+"/ && wget https://www.bing.com"+img_url+"_UHD.jpg "+"-O "+cc+".jpg")
        with open('/root/bing_img/'+day_for+'/'+day_for+'.txt',"a+") as log:
            log.write(cc+": https://www.bing.com"+img_url+"_UHD.jpg\n")

def get_io(cc):
    global io
    url='https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&cc='+cc
    json_data=requests.get(url).text
    data = json.loads(json_data)
    cc_io=data['images']
    io[cc]=cc_io

os.system("mkdir /root/bing_img/"+time.strftime('%Y-%m-%d')+"/")

print('------------------------',time.strftime('%Y-%m-%d %a %H:%M:%S')+' bing.py','========================',sep='\n')

for i in ['de','cn','jp','us']:
    get_img(i)

io={}
for i in ['ar','at','au','be','br','ca','ch','cl','cn','de','dk','es','fi','fr','hk','ie','in','it','jp','kr','nl','no','nz','ph','pt','ru','se','sg','tw','uk']:
    get_io(i)
with open('/root/bing_img/'+time.strftime('%Y-%m-%d')+'/'+time.strftime('%Y-%m-%d')+'.json',"a+") as log:
    log.write(json.dumps(io, sort_keys=False, indent=4, ensure_ascii=False, separators=(',', ':')))

os.system('day=`date +%Y-%m-%d` && cd /root/bing_img/ && /usr/local/git/bin/git add . && /usr/local/git/bin/git commit -m $day &&/usr/local/git/bin/git push -u origin main')

