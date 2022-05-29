from cProfile import run
import pstats
from pyobigram.utils import sizeof_fmt,get_file_size,createID,nice_time
from pyobigram.client import ObigramClient,inlineQueryResultArticle
from MoodleClient import MoodleClient

from JDatabase import JsonDatabase
import zipfile
import os
import infos
import xdlink
import mediafire
import datetime
import time
import youtube
import NexCloudClient
from pydownloader.downloader import Downloader
from ProxyCloud import ProxyCloud
import ProxyCloud
import socket
import tlmedia
import S5Crypto
import asyncio
import aiohttp
from yarl import URL
import re
from draft_to_calendar import send_calendar

def sign_url(token: str, url: URL):
    query: dict = dict(url.query)
    query["token"] = token
    path = "webservice" + url.path
    return url.with_path(path).with_query(query)

def downloadFile(downloader,filename,currentBits,totalBits,speed,time,args):
    try:
        bot = args[0]
        message = args[1]
        thread = args[2]
        if thread.getStore('stop'):
            downloader.stop()
        downloadingInfo = infos.createDownloading(filename,totalBits,currentBits,speed,time,tid=thread.id)
        bot.editMessageText(message,downloadingInfo)
    except Exception as ex: print(str(ex))
    pass

def uploadFile(filename,currentBits,totalBits,speed,time,args):
    try:
        bot = args[0]
        message = args[1]
        originalfile = args[2]
        thread = args[3]
        downloadingInfo = infos.createUploading(filename,totalBits,currentBits,speed,time,originalfile)
        bot.editMessageText(message,downloadingInfo)
    except Exception as ex: print(str(ex))
    pass

def processUploadFiles(filename,filesize,files,update,bot,message,thread=None,jdb=None):
    try:
        bot.editMessageText(message,'🤜Preparando Para Subir☁...')
        evidence = None
        fileid = None
        user_info = jdb.get_user(update.message.sender.username)
        cloudtype = user_info['cloudtype']
        proxy = ProxyCloud.parse(user_info['proxy'])
        if cloudtype == 'moodle':
            client = MoodleClient(user_info['moodle_user'],
                                  user_info['moodle_password'],
                                  user_info['moodle_host'],
                                  user_info['moodle_repo_id'],
                                  proxy=proxy)
            loged = client.login()
            itererr = 0
            if loged:
                if user_info['uploadtype'] == 'evidence':
                    evidences = client.getEvidences()
                    evidname = str(filename).split('.')[0]
                    for evid in evidences:
                        if evid['name'] == evidname:
                            evidence = evid
                            break
                    if evidence is None:
                        evidence = client.createEvidence(evidname)

                originalfile = ''
                if len(files)>1:
                    originalfile = filename
                draftlist = []
                for f in files:
                    f_size = get_file_size(f)
                    resp = None
                    iter = 0
                    tokenize = False
                    if user_info['tokenize']!=0:
                       tokenize = True
                    while resp is None:
                          if user_info['uploadtype'] == 'evidence':
                             fileid,resp = client.upload_file(f,evidence,fileid,progressfunc=uploadFile,args=(bot,message,originalfile,thread),tokenize=tokenize)
                          elif user_info['uploadtype'] == 'draft':
                                fileid,resp = client.upload_file_draft(f,progressfunc=uploadFile,args=(bot,message,originalfile,thread),tokenize=tokenize)
                                draftlist.append(resp)
                          elif user_info['uploadtype'] == 'perfil':
                                fileid,resp = client.upload_file_perfil(f,progressfunc=uploadFile,args=(bot,message,originalfile,thread),tokenize=tokenize)
                                draftlist.append(resp)
                          elif user_info['uploadtype'] == 'blog':
                                fileid,resp = client.upload_file_blog(f,progressfunc=uploadFile,args=(bot,message,originalfile,thread),tokenize=tokenize)
                                draftlist.append(resp)
                          elif user_info['uploadtype'] == 'calendar':
                                fileid,resp = client.upload_file_calendar(f,progressfunc=uploadFile,args=(bot,message,originalfile,thread),tokenize=tokenize)
                                draftlist.append(resp)
                          iter += 1
                          if iter>=10:
                              break
                    os.unlink(f)
                if user_info['uploadtype'] == 'evidence':
                    try:
                        client.saveEvidence(evidence)
                    except:pass
                return draftlist
            else:
                bot.editMessageText(message,'❌Error En La Pagina❌')
        elif cloudtype == 'cloud':
            tokenize = False
            if user_info['tokenize']!=0:
               tokenize = True
            bot.editMessageText(message,'🤜Subiendo ☁ Espere Mientras... 😄')
            host = user_info['moodle_host']
            user = user_info['moodle_user']
            passw = user_info['moodle_password']
            remotepath = user_info['dir']
            client = NexCloudClient.NexCloudClient(user,passw,host,proxy=proxy)
            loged = client.login()
            if loged:
               originalfile = ''
               if len(files)>1:
                    originalfile = filename
               filesdata = []
               for f in files:
                   data = client.upload_file(f,path=remotepath,progressfunc=uploadFile,args=(bot,message,originalfile,thread),tokenize=tokenize)
                   filesdata.append(data)
                   os.unlink(f)
               return filesdata
        return None
    except Exception as ex:
        bot.editMessageText(message,f'❌Error {str(ex)}❌')


def processFile(update,bot,message,file,thread=None,jdb=None):
    file_size = get_file_size(file)
    getUser = jdb.get_user(update.message.sender.username)
    max_file_size = 1024 * 1024 * getUser['zips']
    file_upload_count = 0
    client = None
    findex = 0
    if file_size > max_file_size:
        compresingInfo = infos.createCompresing(file,file_size,max_file_size)
        bot.editMessageText(message,compresingInfo)
        zipname = str(file).split('.')[0] + createID()
        mult_file = zipfile.MultiFile(zipname,max_file_size)
        zip = zipfile.ZipFile(mult_file,  mode='w', compression=zipfile.ZIP_DEFLATED)
        zip.write(file)
        zip.close()
        mult_file.close()
        client = processUploadFiles(file,file_size,mult_file.files,update,bot,message,jdb=jdb)
        try:
            os.unlink(file)
        except:pass
        file_upload_count = len(zipfile.files)
    else:
        client = processUploadFiles(file,file_size,[file],update,bot,message,jdb=jdb)
        file_upload_count = 1
    bot.editMessageText(message,'🤜Preparando Archivo📄...')
    evidname = ''
    files = []
    if client:
        if getUser['cloudtype'] == 'moodle':
            if getUser['uploadtype'] == 'evidence':
                try:
                    evidname = str(file).split('.')[0]
                    txtname = evidname + '.txt'
                    evidences = client.getEvidences()
                    for ev in evidences:
                        if ev['name'] == evidname:
                           files = ev['files']
                           break
                        if len(ev['files'])>0:
                           findex+=1
                    client.logout()
                except:pass
            if getUser['uploadtype'] == 'draft' or getUser['uploadtype'] == 'blog' or getUser['uploadtype'] == 'calendar':
               for draft in client:
                   files.append({'name':draft['file'],'directurl':draft['url']})
        else:
            for data in client:
                files.append({'name':data['name'],'directurl':data['url']})
        bot.deleteMessage(message.chat.id,message.message_id)
        finishInfo = infos.createFinishUploading(file,file_size,max_file_size,file_upload_count,file_upload_count,findex)
        filesInfo = infos.createFileMsg(file,files)
        bot.sendMessage(message.chat.id,finishInfo+'\n'+filesInfo,parse_mode='html')
        if len(files)>0:
            txtname = str(file).split('/')[-1].split('.')[0] + '.txt'
            sendTxt(txtname,files,update,bot)
        try:
            import urllib
            user_info = jdb.get_user(update.message.sender.username)
            cloudtype = user_info['cloudtype']
            proxy = ProxyCloud.parse(user_info['proxy'])
            if cloudtype == 'moodle':
                client = MoodleClient(user_info['moodle_user'],
                                    user_info['moodle_password'],
                                    user_info['moodle_host'],
                                    user_info['moodle_repo_id'],
                                    proxy=proxy)
            host = user_info['moodle_host']
            user = user_info['moodle_user']
            passw = user_info['moodle_password']
            if getUser['uploadtype'] == 'calendar' or getUser['uploadtype'] == 'draft':
                nuevo = []
                #if len(files)>0:
                    #for f in files:
                        #url = urllib.parse.unquote(f['directurl'],encoding='utf-8', errors='replace')
                        #nuevo.append(str(url))
                fi = 0
                for f in files:
                    separator = ''
                    if fi < len(files)-1:
                        separator += '\n'
                    nuevo.append(f['directurl']+separator)
                    fi += 1
                urls = asyncio.run(send_calendar(host,user,passw,nuevo))
                loged = client.login()
                if loged:
                    token = client.userdata
                    modif = token['token']
                    client.logout()
                nuevito = []
                for url in urls:
                    url_signed = (str(sign_url(modif, URL(url))))
                    nuevito.append(url_signed)
                loco = '\n'.join(map(str, nuevito))
                fname = str(txtname)
                with open(fname, "w") as f:
                    f.write(str(loco))
                #fname = str(randint(100000000, 9999999999)) + ".txt"
                bot.sendMessage(message.chat.id,'Enlaces de Calendario👇')
                bot.sendFile(update.message.chat.id,fname)
            else:
                return
        except:
            bot.sendMessage(message.chat.id,'💢No se Puede Mover a Calendario💢')
    else:
        bot.editMessageText(message,'❌Error En La Pagina❌')

def ddl(update,bot,message,url,file_name='',thread=None,jdb=None):
    downloader = Downloader()
    file = downloader.download_url(url,progressfunc=downloadFile,args=(bot,message,thread))
    if not downloader.stoping:
        if file:
            processFile(update,bot,message,file,jdb=jdb)

def sendTxt(name,files,update,bot):
                txt = open(name,'w')
                fi = 0
                for f in files:
                    separator = ''
                    if fi < len(files)-1:
                        separator += '\n'
                    txt.write(f['directurl']+separator)
                    fi += 1
                txt.close()
                bot.sendFile(update.message.chat.id,name)
                os.unlink(name)

def onmessage(update,bot:ObigramClient):
    try:
        thread = bot.this_thread
        username = update.message.sender.username
        tl_admin_user = os.environ.get('tl_admin_user')

        #set in debug
        tl_admin_user = 'DRP96'

        jdb = JsonDatabase('database')
        jdb.check_create()
        jdb.load()

        user_info = jdb.get_user(username)
        #if username == tl_admin_user or user_info:
        if username == tl_admin_user or user_info:  # validate user
            if user_info is None:
                #if username == tl_admin_user:
                if username == tl_admin_user:
                    jdb.create_admin(username)
                else:
                    jdb.create_user(username)
                user_info = jdb.get_user(username)
                jdb.save()
        else:
            mensaje = "❌No tienes Acceso❌.❌ Por favor Contacta con mi Programador @Wachu985❌\n"
            #mensaje = 'EL Bot está en MANTENIMIENTO'
            intento_msg = "💢El usuario @"+username+ " ha intentado usar el bot sin permiso💢"
            bot.sendMessage(update.message.chat.id,mensaje)
            bot.sendMessage(958475767,intento_msg)
            return
        


        msgText = ''
        try: msgText = update.message.text
        except:pass

        # comandos de admin
        if '/adduser' in msgText:
            isadmin = jdb.is_admin(username)
            if isadmin:
                try:
                    user = str(msgText).split(' ')[1]
                    jdb.create_user(user)
                    jdb.save()
                    msg = '😃Genial @'+user+' ahora tiene acceso al bot👍'
                    bot.sendMessage(update.message.chat.id,msg)
                except:
                    bot.sendMessage(update.message.chat.id,'❌Error en el comando /adduser username❌')
            else:
                bot.sendMessage(update.message.chat.id,'❌No Tiene Permiso❌')
            return
        if '/banuser' in msgText:
            isadmin = jdb.is_admin(username)
            if isadmin:
                try:
                    user = str(msgText).split(' ')[1]
                    if user == username:
                        bot.sendMessage(update.message.chat.id,'❌No Se Puede Banear Usted❌')
                        return
                    jdb.remove(user)
                    jdb.save()
                    msg = '🦶Fuera @'+user+' Baneado❌'
                    bot.sendMessage(update.message.chat.id,msg)
                except:
                    bot.sendMessage(update.message.chat.id,'❌Error en el comando /banuser username❌')
            else:
                bot.sendMessage(update.message.chat.id,'❌No Tiene Permiso❌')
            return
        if '/getdata' in msgText:
            isadmin = jdb.is_admin(username)
            if isadmin:
                bot.sendMessage(update.message.chat.id,'Base De Datos👇')
                bot.sendFile(update.message.chat.id,'database.jdb')
            else:
                bot.sendMessage(update.message.chat.id,'❌No Tiene Permiso❌')
            return
        # end

        # comandos de usuario
        if '/tutorial' in msgText:
            tuto = open('tuto.txt','r')
            bot.sendMessage(update.message.chat.id,tuto.read())
            tuto.close()
            return
        if '/info' in msgText:
            getUser = user_info
            if getUser:
                statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                bot.sendMessage(update.message.chat.id,statInfo)
                return
        if '/zips' in msgText:
            getUser = user_info
            if getUser:
                try:
                   size = int(str(msgText).split(' ')[1])
                   getUser['zips'] = size
                   jdb.save_data_user(username,getUser)
                   jdb.save()
                   msg = '😃Genial los zips seran de '+ sizeof_fmt(size*1024*1024)+' las partes👍'
                   bot.sendMessage(update.message.chat.id,msg)
                except:
                   bot.sendMessage(update.message.chat.id,'❌Error en el comando /zips size❌')
                return
        if '/account' in msgText:
            try:
                account = str(msgText).split(' ',2)[1].split(',')
                user = account[0]
                passw = account[1]
                getUser = user_info
                if getUser:
                    getUser['moodle_user'] = user
                    getUser['moodle_password'] = passw
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo)
            except:
                bot.sendMessage(update.message.chat.id,'❌Error en el comando /account user,password❌')
            return
        if '/host' in msgText:
            try:
                cmd = str(msgText).split(' ',2)
                host = cmd[1]
                getUser = user_info
                if getUser:
                    getUser['moodle_host'] = host
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo)
            except:
                bot.sendMessage(update.message.chat.id,'❌Error en el comando /host moodlehost❌')
            return
        if '/repoid' in msgText:
            try:
                cmd = str(msgText).split(' ',2)
                repoid = int(cmd[1])
                getUser = user_info
                if getUser:
                    getUser['moodle_repo_id'] = repoid
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo)
            except:
                bot.sendMessage(update.message.chat.id,'❌Error en el comando /repo id❌')
            return
        if '/tokenize_on' in msgText:
            try:
                getUser = user_info
                if getUser:
                    getUser['tokenize'] = 1
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo)
            except:
                bot.sendMessage(update.message.chat.id,'❌Error en el comando /tokenize state❌')
            return
        if '/tokenize_off' in msgText:
            try:
                getUser = user_info
                if getUser:
                    getUser['tokenize'] = 0
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo)
            except:
                bot.sendMessage(update.message.chat.id,'❌Error en el comando /tokenize state❌')
            return
        if '/cloud' in msgText:
            try:
                cmd = str(msgText).split(' ',2)
                repoid = cmd[1]
                getUser = user_info
                if getUser:
                    getUser['cloudtype'] = repoid
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo)
            except:
                bot.sendMessage(update.message.chat.id,'❌Error en el comando /cloud (moodle or cloud)❌')
            return
        if '/uptype' in msgText:
            try:
                cmd = str(msgText).split(' ',2)
                type = cmd[1]
                getUser = user_info
                if getUser:
                    getUser['uploadtype'] = type
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo)
            except:
                bot.sendMessage(update.message.chat.id,'❌Error en el comando /uptype (typo de subida (evidence,draft,blog))❌')
            return
        if '/proxy' in msgText:
            try:
                cmd = str(msgText).split(' ',2)
                proxy = cmd[1]
                getUser = user_info
                if getUser:
                    getUser['proxy'] = proxy
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo)
            except:
                if user_info:
                    user_info['proxy'] = ''
                    statInfo = infos.createStat(username,user_info,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo)
            return
        if '/gen' in msgText:
            pass
        if '/dir' in msgText:
            try:
                cmd = str(msgText).split(' ',2)
                repoid = cmd[1]
                getUser = user_info
                if getUser:
                    getUser['dir'] = repoid + '/'
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo)
            except:
                bot.sendMessage(update.message.chat.id,'❌Error en el comando /dir folder❌')
            return
        if '/cancel_' in msgText:
            try:
                cmd = str(msgText).split('_',2)
                tid = cmd[1]
                tcancel = bot.threads[tid]
                msg = tcancel.getStore('msg')
                tcancel.store('stop',True)
                time.sleep(3)
                bot.editMessageText(msg,'❌Tarea Cancelada❌')
            except Exception as ex:
                print(str(ex))
            return
        #end

        message = bot.sendMessage(update.message.chat.id,'🕰Procesando🕰...')

        thread.store('msg',message)

        if '/start' in msgText:
            start_msg = 'Bot          : TGUploaderPro v7.0\n'
            start_msg+= 'Desarrollador: @Unk980929\n'
            start_msg+= 'Guia         : https://nube.reduc.edu.cu/index.php/s/L9WMzC56ZgTZo6b/download/Tutorial%20R%C3%A1pido%20.mp4\n'
            start_msg+= 'Uso          :Envia Enlaces De Descarga y Archivos Para Procesar (Configure Antes De Empezar , Vea El /tutorial)\n'
            bot.editMessageText(message,start_msg)
        elif '/token' in msgText:
            message2 = bot.editMessageText(message,'Obteniendo Token...')
            try:
                proxy = ProxyCloud.parse(user_info['proxy'])
                client = MoodleClient(user_info['moodle_user'],
                                      user_info['moodle_password'],
                                      user_info['moodle_host'],
                                      user_info['moodle_repo_id'],proxy=proxy)
                loged = client.login()
                if loged:
                    token = client.userdata
                    modif = token['token']
                    bot.editMessageText(message2,'Su Token es: '+modif)
                    client.logout()
                else:
                    bot.editMessageText(message2,'La Moodle '+client.path+' No tiene Token')
            except Exception as ex:
                bot.editMessageText(message2,'La Moodle '+client.path+' No tiene Token o revise la Cuenta')
        elif '/files' == msgText and user_info['cloudtype']=='moodle':
             proxy = ProxyCloud.parse(user_info['proxy'])
             client = MoodleClient(user_info['moodle_user'],
                                   user_info['moodle_password'],
                                   user_info['moodle_host'],
                                   user_info['moodle_repo_id'],proxy=proxy)
             loged = client.login()
             if loged:
                 files = client.getEvidences()
                 filesInfo = infos.createFilesMsg(files)
                 bot.editMessageText(message,filesInfo)
                 client.logout()
             else:
                bot.editMessageText(message,'❌Error y Causas🧐\n1-Revise su Cuenta\n2-Servidor Desabilitado: '+client.path)
        elif '/txt_' in msgText and user_info['cloudtype']=='moodle':
             findex = str(msgText).split('_')[1]
             findex = int(findex)
             proxy = ProxyCloud.parse(user_info['proxy'])
             client = MoodleClient(user_info['moodle_user'],
                                   user_info['moodle_password'],
                                   user_info['moodle_host'],
                                   user_info['moodle_repo_id'],proxy=proxy)
             loged = client.login()
             if loged:
                 evidences = client.getEvidences()
                 evindex = evidences[findex]
                 txtname = evindex['name']+'.txt'
                 sendTxt(txtname,evindex['files'],update,bot)
                 client.logout()
                 bot.editMessageText(message,'TxT Aqui👇')
             else:
                bot.editMessageText(message,'❌Error y Causas🧐\n1-Revise su Cuenta\n2-Servidor Desabilitado: '+client.path)
             pass
        elif '/del_' in msgText and user_info['cloudtype']=='moodle':
            findex = int(str(msgText).split('_')[1])
            proxy = ProxyCloud.parse(user_info['proxy'])
            client = MoodleClient(user_info['moodle_user'],
                                   user_info['moodle_password'],
                                   user_info['moodle_host'],
                                   user_info['moodle_repo_id'],
                                   proxy=proxy)
            loged = client.login()
            if loged:
                evfile = client.getEvidences()[findex]
                client.deleteEvidence(evfile)
                client.logout()
                bot.editMessageText(message,'Archivo Borrado 🦶')
            else:
                bot.editMessageText(message,'❌Error y Causas🧐\n1-Revise su Cuenta\n2-Servidor Desabilitado: '+client.path)
        elif 'http' in msgText:
            url = msgText
            ddl(update,bot,message,url,file_name='',thread=thread,jdb=jdb)
        else:
            #if update:
            #    api_id = os.environ.get('api_id')
            #    api_hash = os.environ.get('api_hash')
            #    bot_token = os.environ.get('bot_token')
            #    
                # set in debug
            #    api_id = 18693993
            #    api_hash = '382ee6b53bdd0df66a52ea9779c62424'
            #    bot_token = '5320526209:AAFappqvXHMwP9KZYD-bawUCIVWaEN4l8vw'

            #    chat_id = int(update.message.chat.id)
            #    message_id = int(update.message.message_id)
            #    import asyncio
            #    asyncio.run(tlmedia.download_media(api_id,api_hash,bot_token,chat_id,message_id))
            #    return
            bot.editMessageText(message,'😵No se pudo procesar😵')
    except Exception as ex:
           print(str(ex))
  

def main():
    bot_token = os.environ.get('bot_token')

    #set in debug
    bot_token = '5320526209:AAFappqvXHMwP9KZYD-bawUCIVWaEN4l8vw'

    bot = ObigramClient(bot_token)
    bot.onMessage(onmessage)
    #bot.sendMessage(,'🚨 MoodleWachu Bot Iniciado 🚨\n                @wachu_bot')
    print('Bot Iniciado')
    bot.run()
    asyncio.run()

if __name__ == '__main__':
    try:
        main()
    except:
        main()
