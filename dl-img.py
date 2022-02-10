import json,os,datetime,re

def dl_img():
    img=[]
    day=input("请输入时间\n时间请勿早于2022-01-01\n格式:xxxx-xx-xx\n留空表示查看今日\n")
    if day=='':
        day=datetime.datetime.now().strftime('%Y-%m-%d')
        print(day)
    now_time=datetime.datetime.strptime(day,'%Y-%m-%d')
    yes_time=now_time+datetime.timedelta(days=-1)
    now_time_str=now_time.strftime('%Y-%m-%d')
    yes_time_str=yes_time.strftime('%Y-%m-%d')

    try:
        with open('/root/bing_img/'+yes_time_str+'/'+yes_time_str+'.json',"r") as log:
            json_data = json.load(log)
    except:
        json_data = {}
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
            print(str(index)+": https://www.bing.com"+img_url+"_UHD.jpg")
            index+=1

dl_img()

# def dl_img_2(day):
#     img=[]
#     now_time=datetime.datetime.strptime(day,'%Y-%m-%d')
#     yes_time=now_time+datetime.timedelta(days=-1)
#     now_time_str=now_time.strftime('%Y-%m-%d')
#     yes_time_str=yes_time.strftime('%Y-%m-%d')

#     try:
#         with open('/root/bing_img/'+yes_time_str+'/'+yes_time_str+'.json',"r") as log:
#             json_data = json.load(log)
#     except:
#         json_data = {}
#     for cc in json_data.keys():
#         img_url=json_data[cc][0]['urlbase']
#         img_io=re.search(r'R.*_',img_url,re.I).group()
#         img_io=img_io[2:-1:]
#         if not img_io in img:
#             img.append(img_io)

#     index=0
#     with open('/root/bing_img/'+now_time_str+'/'+now_time_str+'.json',"r") as log:
#         json_data = json.load(log)
#     for cc in json_data.keys():
#         img_url=json_data[cc][0]['urlbase']
#         img_io=re.search(r'R.*_',img_url,re.I).group()
#         img_io=img_io[2:-1:]
#         if not img_io in img:
#             img.append(img_io)
#             with open('/root/bing_img/readme.md',"a+") as log:
#                 log.write("!["+now_time_str+"-"+str(index)+"]("+"https://www.bing.com"+img_url+"_UHD.jpg)\n")
#             print(str(index)+": https://www.bing.com"+img_url+"_UHD.jpg")
#             index+=1

# for i in range(1,11):
#     day="2022-02-"+str(i)
#     with open('/root/bing_img/readme.md',"a+") as log:
#         log.write(day+"\n----------------\n")
#     dl_img_2(day)