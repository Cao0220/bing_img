import json,os,time,re

def dl_img():
    img=[]
    index=0
    with open('/root/bing_img/'+time.strftime('%Y-%m-%d')+'/'+time.strftime('%Y-%m-%d')+'.json',"r") as log:
        json_data = json.load(log)
    for cc in json_data.keys():
        img_url=json_data[cc][0]['urlbase']
        img_io=re.search(r'R.*_',img_url,re.I).group()
        img_io=img_io[2:-1:]
        if not img_io in img:
            img.append(img_io)
            os.system("cd /root/bing_img/"+time.strftime('%Y-%m-%d')+"/ && wget https://www.bing.com"+img_url+"_UHD.jpg "+"-O "+str(index)+".jpg")
            index+=1

dl_img()