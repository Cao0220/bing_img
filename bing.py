import json,requests,os,time,re,datetime,random

def dl_img():
    img=[]

    now_time=datetime.datetime.now()
    yes_time=now_time+datetime.timedelta(days=-1)
    now_time_str=now_time.strftime('%Y-%m-%d')
    yes_time_str=yes_time.strftime('%Y-%m-%d')
    with open('/root/bing_img/'+yes_time_str+'/'+yes_time_str+'.json',"r") as log:
        json_data = json.load(log)
    for cc in json_data.keys():
        img_url=json_data[cc][0]['urlbase']
        img_io=re.search(r'R.*_',img_url,re.I).group()
        img_io=img_io[2:-1:]
        if not img_io in img:
            img.append(img_io)

    index=0
    with open('/root/bing_img/'+now_time_str+'/'+now_time_str+'.json',"r") as log:
        json_data = json.load(log)
    for cc in json_data.keys():
        img_url=json_data[cc][0]['urlbase']
        img_io=re.search(r'R.*_',img_url,re.I).group()
        img_io=img_io[2:-1:]
        if not img_io in img:
            img.append(img_io)
            os.system("cd /root/bing_img/"+now_time_str+"/ && wget https://www.bing.com"+img_url+"_UHD.jpg "+"-O "+str(index)+".jpg")
            with open('/root/bing_img/readme.md',"a+") as log:
                log.write("!["+now_time_str+"-"+str(index)+"]("+"https://www.bing.com"+img_url+"_UHD.jpg)\n")
            # print("cd /root/bing_img/"+now_time_str+"/ && wget https://www.bing.com"+img_url+"_UHD.jpg "+"-O "+str(index)+".jpg")
            index+=1

def get_io(cc):
    global io
    url='https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&video=1&cc='+cc
    json_data=requests.get(url).text
    data = json.loads(json_data)
    cc_io=data['images']
    io[cc]=cc_io

os.system("mkdir /root/bing_img/"+time.strftime('%Y-%m-%d')+"/")

print('------------------------',time.strftime('%Y-%m-%d %a %H:%M:%S')+' bing.py','========================',sep='\n')
with open('/root/bing_img/readme.md',"a+") as log:
    log.write(datetime.datetime.now().strftime('%Y-%m-%d')+"\n----------------\n")

io={}
for i in ['ar','at','au','be','br','ca','ch','cl','cn','de','dk','es','fi','fr','hk','ie','in','it','jp','kr','nl','no','nz','ph','pt','ru','se','sg','tw','uk']:
    get_io(i)

with open('/root/bing_img/'+time.strftime('%Y-%m-%d')+'/'+time.strftime('%Y-%m-%d')+'.json',"a+") as log:
    log.write(json.dumps(io, sort_keys=False, indent=4, ensure_ascii=False, separators=(',', ':')))

dl_img()

# time.sleep(random.randint(0,21600))
os.system('day=`date +%Y-%m-%d` && cd /root/bing_img/ && /usr/bin/git add . && /usr/bin/git commit -m $day &&/usr/bin/git push -u origin main')

