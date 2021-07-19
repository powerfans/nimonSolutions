#!/usr/bin/python3
# nextract_plus for InfluxDB and Grafana graphs
import hmc_topo as hmc
import time
import sys
import json
from xml.dom.minidom import parse

from pyecharts import options as opts
from pyecharts.charts import Graph

nversion = 35
measures = 0

# Don't switch debug or saveJSON to True if running via crontab
debug = True  # debug - make sure you have a debuf sub-directory
saveJSON = True  # save the line protocol JSON records to file "nextract.json
if saveJSON:
    JSONfile = open("nextract_plus.json", "w")
    JSONfile.write("nextract_plus.json\n")
saveInflux = False  # switch off access to InfluxDB

# Uncomment ONE of these ONLY
# mode="hardcode"    # Use the setting below
# mode="hmc"          # Use the setting below but overwrite the HMC hostname
# from the first command line arguement
mode = "file"  # The first command line argument is a JSON config filename

# EXAMPLE JSON CONFIG FILE.
# All lines are needed is not needed use ""
# Remove the hashes (#)
# {
# "hmc_hostname": "hmc15",
# "hmc_username": "pcmadmin",
# "hmc_password": "pcm123panda123sausages!",
# "ihostname": "ultraviolet.acme.com",
# "iport": 8086,
# "iusername": "debbie",
# "ipassword": "bladerunner808$$",
# "idbname": "nextractplus"
# }

# HMC details
# hmc_hostname="hmc42"
# hmc_username="nigel"
# hmc_password="SECRET"

# Influx details
# ihostname="influx.domain.com"     # server hostname or IP address
# iport=8086             # port
# iusername=""           # username
# ipassword=""           # password
# idbname="nextractplus" # database/bucket name

errorlist = set()

if mode == "hmc":
    if len(sys.argv) == 2:  # two including the program name entry [0]
        hmc_hostname = sys.argv[1]
    else:
        print("Stopping: Missing hostname arguement on the command line")
        sys.exit(666)

if mode == "file":
    if len(sys.argv) == 2:  # two including the program name entry [0]
        filename = sys.argv[1]
    else:
        print("Stopping: Missing config filename on the command line")
        sys.exit(667)

    try:
        with open(filename) as auth_file:
            auth = json.load(auth_file)
    except:
        print("Problem loading %s file." % (filename))
        sys.exit(668)

    try:
        hmc_hostname = auth['hmc_hostname']
        hmc_username = auth['hmc_username']
        hmc_password = auth['hmc_password']
        ihostname = auth['ihostname']
        iport = auth['iport']
        iusername = auth['iusername']
        ipassword = auth['ipassword']
        idbname = auth['idbname']
    except:
        print("Problem understanding %s file JSON format" % (filename))
        print(auth)
        sys.exit(669)

if debug:
    print("hmc:" + hmc_hostname + " user:" + hmc_username + " pass:" + hmc_password)
    print("Influx:" + ihostname + " user:" + iusername + " pass:" + ipassword)
    print("Influx port:" + str(iport) + " db:" + idbname)

if saveInflux:
    from influxdb import InfluxDBClient

    client = InfluxDBClient(ihostname, iport, iusername, ipassword, idbname)


def extract_data(data):
    "fix json by removing arrays of only one item "
    fields = {}
    for key, value in data.items():
        if key == "bridgedAdapters":
            continue
        if key == "transmittedBytes":
            continue
        try:
            fields[key] = float(value[0])
        except:
            fields[key] = value
    return fields


print("-> nextract_plus version %d saving JSON=%r Influx=%r" % (nversion, saveJSON, saveInflux))
print("-> Logging on to %s as hmc_username %s" % (hmc_hostname, hmc_username))
hmc = hmc.HMC(hmc_hostname, hmc_username, hmc_password)

print("-> Get Preferences")  # returns XML text
prefstripped = hmc.get_stripped_preferences_pcm()
if debug:
    hmc.save_to_file("server_perferences.xml", prefstripped)

print("-> Parse Preferences")
serverlist = hmc.parse_prefs_pcm(prefstripped)  # returns a list of dictionaries one per Server
perflist = []
all_true = True
print("-> ALL servers:")
for num, server in enumerate(serverlist):
    if server['lterm'] == 'true' and server['agg'] == 'true':
        todo = "- OK"
        perflist.append(server)
    else:
        todo = "- remove"
    print('-> Server name=%-16s agg=%-5s longterm=%-5s %s '
          % (server['name'], server['agg'], server['lterm'], todo))

print("-> Servers with Perf Stats")
seapdjsonlist = []
seavdjsonlist = []
lparjsonlist = []
alljsonlist = []
vscsijsonlist = []
npivjsonlist = []
for count, server in enumerate(perflist, start=1):  # just loop the servers with stats
    print('')

    #   if server['name'] == 'server_with_no_VIOS':
    #      print("Skipping server %s as it has no VIOS" % (server['name']))
    #      continue

    print('--> Server=%d Name=%s - Requesting the data ...' % (count, server['name']))
    starttime = time.time()
    filelist = hmc.get_filenames_server(server['atomid'], server['name'])  # returns XML of filename(s)
    neworkbridge =  hmc.get_filenames_NetworkBridge(server['atomid'],server['name'])
    Serverprofile = hmc.get_filenames_Serverprofile(server['atomid'],server['name'])
    endtime = time.time()
    print("---> Received %d file(s) in %.2f seconds" % (len(filelist), endtime - starttime))

    if debug:
        for num, file in enumerate(filelist, start=1):  # loop around the files
            filename = file['filename']
            print('---> Server=%s File=%d %s' % (server['name'], num, filename))

    if debug:
        hmc.set_debug(True)  # Warning this generated large files in the debug sub directory

    for num, file in enumerate(filelist, start=1):  # loop around the files
        filename = file['filename']
        data = hmc.get_stats(file['url'], filename, server['name'])  # returns JSON stats

        if filename[:13] == "ManagedSystem":  # start of the filename tells you if server or LPAR
            filename2 = filename.replace('.json', '.JSON')
            if debug:
                print('ManagedSystem Saving to file:%s' % (filename2))
                hmc.save_json_txt_to_file(filename2, data)
            # ____
            # / ___|  ___ _ ____   _____ _ __
            # \___ \ / _ \ '__\ \ / / _ \ '__|
            # ___) |  __/ |   \ V /  __/ |
            # |____/ \___|_|    \_/ \___|_|

            jdata = json.loads(data)
            info = jdata["systemUtil"]["utilInfo"]
            servername = info['name']
            serveruuid = info['uuid']
            serversn = info['mtms'].split('*')[1]
            serverjson = ""+'{"servername":"' + servername + '","serversn":"' + serversn + '","serveruuid":"' + serveruuid + '"'
            print("----> Server Name=%s MTM + Serial Number=%s" % (servername, info['mtms']))
            print("----> Server Date=%s start=%s end=%s" % (
            info['startTimeStamp'][:10], info['startTimeStamp'][11:19], info['endTimeStamp'][11:19]))
            print("----> Server DataType=%s Interval=%s seconds" % (info['metricType'], info['frequency']))
            if debug:
                print("Info dictionary:")
                print(info)

            utilSamplesArray = jdata['systemUtil']['utilSamples']

            # Create InfluxDB measurements and pump them in
            if debug:
                print("Server stats: %s" % (servername))

            entry = []
            vioslist = []
            for sample in utilSamplesArray:
                timestamp = sample['sampleInfo']['timeStamp']

                try:
                    fields = extract_data(sample['systemFirmwareUtil'])
                    fields['mtm'] = info['mtms']
                    fields['name'] = servername
                    fields['APIversion'] = info['version']
                    fields['metric'] = info['metricType']
                    fields['frequency'] = info['frequency']
                    fields['nextract'] = str(nversion)

                    data = {'measurement': 'server_details', 'time': timestamp,
                            'tags': {'servername': servername},
                            'fields': fields}
                    entry.append(data)
                except:
                    if debug: print("no system_details")

                try:
                    data = {'measurement': 'server_processor', 'time': timestamp,
                            'tags': {'servername': servername},
                            'fields': extract_data(sample['serverUtil']['processor'])}
                    entry.append(data)
                except:
                    if debug: print("no serverUtil-processor")

                try:
                    data = {'measurement': 'server_memory', 'time': timestamp,
                            'tags': {'servername': servername},
                            'fields': extract_data(sample['serverUtil']['memory'])}
                    entry.append(data)
                except:
                    if debug: print("no serverUtil-mem")

                try:
                    data = {'measurement': 'server_physicalProcessorPool', 'time': timestamp,
                            'tags': {'servername': servername},
                            'fields': extract_data(sample['serverUtil']['physicalProcessorPool'])}
                    entry.append(data)
                except:
                    if debug: print("no serverUtil-physicalProcessorPool")

                try:
                    arr = sample['serverUtil']['sharedMemoryPool']
                    for pool in arr:
                        data = {'measurement': 'server_sharedMemoryPool', 'time': timestamp,
                                'tags': {'servername': servername, 'pool': pool['id']},
                                'fields': extract_data(pool)}
                        entry.append(data)
                except:
                    if debug: print("no serverUtil-sharedMemoryPool")

                try:
                    for pool in sample['serverUtil']['sharedProcessorPool']:
                        data = {'measurement': 'server_sharedProcessorPool', 'time': timestamp,
                                'tags': {'servername': servername, 'pool': pool['id'], 'poolname': pool['name']},
                                'fields': extract_data(pool)}
                        entry.append(data)
                except:
                    if debug: print("no serverUtil-sharedProcessorPool")

                try:
                    for adapter in sample['serverUtil']['network']['sriovAdapters']:
                        for adaptport in adapter['physicalPorts']:
                            data = {'measurement': 'server_sriov', 'time': timestamp,
                                    'tags': {'servername': servername,
                                             'port': adaptport['id'],
                                             'location': adaptport['physicalLocation']},
                                    'fields': extract_data(adaptport)}
                            entry.append(data)
                except:
                    if debug: print("no server_sriov")

                try:
                    for HEA in sample['serverUtil']['network']['HEAdapters']['physicalPorts']:
                        for HEAport in HEA:
                            data = {'measurement': 'server_HEAport', 'time': timestamp,
                                    'tags': {'servername': servername,
                                             'port': HEAport['id'],
                                             'location': HEAport['physicalLocation']},
                                    'fields': extract_data(HEAport)}
                            entry.append(data)
                except:
                    if debug: print("no serverUtil-net-HEAport")

                # __   _(_) ___  ___
                # \ \ / / |/ _ \/ __|
                # \ V /| | (_) \__ \
                #  \_/ |_|\___/|___/
                try:
                    vios_array = sample['viosUtil']

                    try:
                        for vios in vios_array:
                            data = {'measurement': 'vios_details', 'time': timestamp,
                                    'tags': {'servername': servername, 'viosname': vios['name']},
                                    'fields': {'viosid': vios['id'], 'viosname': vios['name'],
                                               'viosstate': vios['state'], 'affinityScore': vios['affinityScore'],
                                               'viosuuid':vios['uuid']}}
                            entry.append(data)
                            vioslist.append({'viosname': vios['name'],'viosuuid':vios['uuid']})
                            if debug: print("vioslist add "+ vios['uuid'] )
                    except:
                        if debug: print("no VIOS_details")

                    try:
                        for vios in vios_array:
                            data = {'measurement': 'vios_memory', 'time': timestamp,
                                    'tags': {'servername': servername, 'viosname': vios['name']},
                                    'fields': extract_data(vios['memory'])}
                            entry.append(data)
                    except:
                        if debug: print("no VIOS memory")

                    try:
                        for vios in vios_array:
                            data = {'measurement': 'vios_processor',
                                    'time': sample['sampleInfo']['timeStamp'],
                                    'tags': {'servername': servername, 'viosname': vios['name']},
                                    'fields': extract_data(vios['processor'])}
                            entry.append(data)
                    except:
                        if debug: print("no VIOS processor")

                    # Networks
                    try:
                        for vios in vios_array:
                            length = len(vios['network']['clientLpars'])
                            data = {'measurement': 'vios_network_lpars', 'time': timestamp,
                                    'tags': {'servername': servername, 'viosname': vios['name']},
                                    'fields': {'clientlpars': length}}
                            entry.append(data)
                    except:
                        if debug: print("no VIOS network lpar count")

                    try:
                        for vios in vios_array:
                            for adapt in vios['network']['genericAdapters']:
                                data = {'measurement': 'vios_network_generic', 'time': timestamp,
                                        'tags': {'servername': servername, 'viosname': vios['name'],
                                                 'id': adapt['id'], 'location': adapt['physicalLocation']},
                                        'fields': extract_data(adapt)}
                                entry.append(data)
                    except:
                        if debug: print("no VIOS vios_network_gen")

                    try:
                        for vios in vios_array:
                            for adapt in vios['network']['sharedAdapters']:
                                data = {'measurement': 'vios_network_shared', 'time': timestamp,
                                        'tags': {'servername': servername, 'viosname': vios['name'],
                                                 'id': adapt['id'], 'location': adapt['physicalLocation']},
                                        'fields': extract_data(adapt)}
                                entry.append(data)
                    except:
                        if debug: print("no VIOS vios_network_shared")

                    try:
                        for vios in vios_array:
                            for adapt in vios['network']['virtualEthernetAdapters']:
                                data = {'measurement': 'vios_network_virtual', 'time': timestamp,
                                        'tags': {'servername': servername, 'viosname': vios['name'],
                                                 'location': adapt['physicalLocation'],
                                                 'vswitchid': adapt['vswitchId'],
                                                 'vlanid': adapt['vlanId']},
                                        'fields': extract_data(adapt)}
                                entry.append(data)
                    except:
                        if debug: print("no VIOS vios_network_virtual")

                    try:
                        for vios in vios_array:
                            for adapt in vios['network']['sriovLogicalPorts']:
                                data = {'measurement': 'vios_network_sriov', 'time': timestamp,
                                        'tags': {'servername': servername, 'viosname': vios['name'],
                                                 'location': adapt['physicalLocation'],
                                                 'physicalPortId': adapt['physicalPortId']},
                                        'fields': extract_data(adapt)}
                                entry.append(data)
                    except:
                        if debug: print("no VIOS vios_network_sriov")

                    # Storage
                    try:
                        for vios in vios_array:
                            length = len(vios['storage']['clientLpars'])
                            data = {'measurement': 'vios_storage_lpars', 'time': timestamp,
                                    'tags': {'servername': servername, 'viosname': vios['name']},
                                    'fields': {'clientlpars': length}}
                            entry.append(data)
                    except:
                        if debug: print("no VIOS storage lpar count")

                    try:
                        for vios in vios_array:
                            for adapt in vios['storage']['genericVirtualAdapters']:
                                data = {'measurement': 'vios_storage_virtual', 'time': timestamp,
                                        'tags': {'servername': servername, 'viosname': vios['name'],
                                                 'id': adapt['id'], 'location': adapt['physicalLocation']},
                                        'fields': extract_data(adapt)}
                                entry.append(data)
                    except:
                        if debug: print("no VIOS vios_storage_virtual")

                    try:
                        for vios in vios_array:
                            for adapt in vios['storage']['genericPhysicalAdapters']:
                                data = {'measurement': 'vios_storage_physical', 'time': timestamp,
                                        'tags': {'servername': servername, 'viosname': vios['name'],
                                                 'id': adapt['id'], 'location': adapt['physicalLocation']},
                                        'fields': extract_data(adapt)}
                                entry.append(data)
                    except:
                        if debug: print("no VIOS vios_storage_physical")

                    try:
                        for vios in vios_array:
                            for adapt in vios['storage']['fiberChannelAdapters']:
                                data = {'measurement': 'vios_storage_FC', 'time': timestamp,
                                        'tags': {'servername': servername, 'viosname': vios['name'],
                                                 'id': adapt['id'], 'location': adapt['physicalLocation']},
                                        'fields': extract_data(adapt)}
                                entry.append(data)
                    except:
                        if debug: print("no VIOS vios_storage_FC")

                    try:
                        for vios in vios_array:
                            for adapt in vios['storage']['sharedStoragePools']:
                                data = {'measurement': 'vios_storage_SSP', 'time': timestamp,
                                        'tags': {'servername': servername, 'viosname': vios['name'],
                                                 'id': adapt['id']},
                                        'fields': extract_data(adapt)}
                                entry.append(data)
                    except:
                        if debug: print("no VIOS vios_storage_SSP")
                except:
                    if debug: print("no VIOS at all")

            vioslist_new = []
            for vios in vioslist:
                if debug: print("vioslist not empty")
                if vios not in vioslist_new:
                    if debug: print("vioslist_new add "+ vios['viosname'])
                    vioslist_new.append(vios)

            for vios in vioslist_new:
                if debug: print("vioslist_new not empty，vios: "+ vios['viosname'])
                vios_xml = hmc.get_filenames_VIOS(vios['viosuuid'], vios['viosname'])
                ####遍历xml抓取信息
                DOMTree = parse("debug/"+"VIOS-" + vios['viosname'] + "-" + vios['viosuuid']+ "-filenames" + ".xml")
                booklist = DOMTree.documentElement
                #获取SEA
                sealist = booklist.getElementsByTagName('SharedEthernetAdapter')

                viosjson = ',"VIOS":"' + vios['viosname'] + '"'
                vdnum = 0

                deviceName = ""

                for i in range(len(sealist)):
                    sea = sealist[i].getElementsByTagName('BackingDeviceChoice')
                    device = sealist[i].getElementsByTagName('DeviceName')
                    seaName = ""
                    pdjson = ""
                    for j in  range(len(device)):
                        if(device[j].getAttribute("kb") == "CUD"):
                            if debug: print("seaName:" + device[j].toxml())
                            seaName = device[j].childNodes[0].nodeValue
                    if debug: print("viosjson:" + viosjson)
                    for j in range(len(sea)):
                        physicalDevice = sea[j].getElementsByTagName('EthernetBackingDevice')
                        for o in range(len(physicalDevice)):
                            pdName = physicalDevice[o].getElementsByTagName('DeviceName')[0].childNodes[0].nodeValue
                            pdlocation = ""
                            print("-->"+pdName+",PhysicalLocation:" + str(len(physicalDevice[o].getElementsByTagName('PhysicalLocation'))))
                            ethernetAdpterjson = ""
                            if(len(physicalDevice[o].getElementsByTagName('PhysicalLocation'))!=0):
                                pdlocation = physicalDevice[o].getElementsByTagName('PhysicalLocation')[0].childNodes[0].nodeValue
                            else:
                                linkAggregation = hmc.get_filenames_Link(vios['viosuuid'], vios['viosname'])
                                DOMTree2 = parse(
                                    "debug/" + "Link-" + vios['viosname'] + "-" + vios['viosuuid'] + "-filenames" + ".xml")
                                booklist2 = DOMTree2.documentElement
                                if booklist2.getElementsByTagName('DeviceName')[0].getAttribute("kb") == "CUR" :
                                    deviceName = booklist2.getElementsByTagName('DeviceName')[0].childNodes[0].nodeValue
                                    backupAdapter = booklist2.getElementsByTagName('BackupAdapter')[0].childNodes[0].nodeValue
                                if deviceName == pdName :
                                    ioAdapterList = booklist2.getElementsByTagName('IOAdapterChoice')
                                    for m in range(len(ioAdapterList)):
                                        print("-->ioAdapterList:" + ioAdapterList[m].toxml())
                                        ethernetAdpter = ioAdapterList[m].getElementsByTagName('DeviceName')[0].childNodes[0].nodeValue
                                        ethernetAdpterjson = ethernetAdpterjson + ',"ethernetAdpter'+str(m) +'":"'+ethernetAdpter+'"'
                            if(ethernetAdpterjson!=""):
                                print("-->ethernetAdpterjson:"+ ethernetAdpterjson)
                                pdjson = pdjson + ',"pdName' + str(o) + '":"' + pdName +'"'+ ethernetAdpterjson + ',"backupAdapter":"'+ backupAdapter+'"'
                            else:
                                pdjson = pdjson + ',"pdName' + str(o) + '":"' + pdName + '","pdlocation' + str(o) + '":"' + pdlocation + '"'
                            print("-->pdjson:" + pdjson)
                    #viosjson = viosjson + ',"seaname":"' + seaName + '"'
                    seaname_json = ',"SEA'+str(i)+ '":"'+seaName +'"'
                    vdjson = ""
                    virtualDeviceList = sealist[i].getElementsByTagName('TrunkAdapter')
                    for k in range(len(virtualDeviceList)):
                        vdName = virtualDeviceList[k].getElementsByTagName('DeviceName')[0].childNodes[0].nodeValue
                        vdlocation = virtualDeviceList[k].getElementsByTagName('LocationCode')[0].childNodes[0].nodeValue
                        vlanID = virtualDeviceList[k].getElementsByTagName('PortVLANID')[0].childNodes[0].nodeValue
                        #vdjson = vdjson + ',"vdName'+ str(k) + '":"' + vdName + '","vdlocation' + str(k) + '":"' + vdlocation + '","vlanID' + str(k) + '":"' + vlanID + '"'
                        vdjson = ',"vdName' + str(k) + '":"' + vdName + '","vlanID":"' + vlanID + '"'
                        #seavdjson = serverjson + viosjson + pdjson + seaname_json + vdjson + ',"vdnum":"' + str(vdnum) + '"}'
                        seavdjson = serverjson + viosjson + pdjson + seaname_json + vdjson + '}'
                        seavdjsonlist.append(seavdjson)
                        seajson = serverjson + viosjson + pdjson + seaname_json + '}'
                        seapdjsonlist.append(seavdjson)
                        vdnum = k+1

                ###获取vscsi
                print("*****vsci******:")
                vscsilist = booklist.getElementsByTagName('VirtualSCSIMapping')

                if len(vscsilist) != 0 :
                    for i in range(len(vscsilist)):
                        print("vscsilist_len:" + str(len(vscsilist))+",num:"+str(i)+",vios:"+vios['viosname'])
                        serverAdapter = vscsilist[i].getElementsByTagName('ServerAdapter')[0]
                        vscsiServerAdapterName = serverAdapter.getElementsByTagName('AdapterName')[0].childNodes[0].nodeValue
                        #vscsipdName = server.getElementsByTagName('BackingDeviceName')[0].childNodes[0].nodeValue
                        storagelist = vscsilist[i].getElementsByTagName('Storage')
                        localPartitionID =""
                        if len(storagelist) != 0 :
                            for j in range(len(storagelist)):
                                print(storagelist[j].toxml())
                                temp = storagelist[j].getElementsByTagName('PhysicalVolume')
                                if len(temp) != 0:
                                    storage = temp[0].getElementsByTagName('VolumeName')[0].childNodes[0].nodeValue
                                print("storagelist_len:" + str(len(storagelist)) + ",num:" + str(
                                    j) + ",storage:" + storage)
                            targetDevice =  vscsilist[i].getElementsByTagName('TargetDevice')[0].getElementsByTagName('TargetName')[0].childNodes[0].nodeValue
                            clientAdapterlist = vscsilist[i].getElementsByTagName('ClientAdapter')
                            if len(clientAdapterlist)!= 0 :
                                localPartitionID = vscsilist[i].getElementsByTagName('ClientAdapter')[0].getElementsByTagName('LocalPartitionID')[0].childNodes[0].nodeValue
                            vscsijson = '{"servername":"' + servername + '","serversn":"' + serversn + '","serveruuid":"' + serveruuid + '","VIOS":"' + vios['viosname'] + '","VSCSI_Server":"'+vscsiServerAdapterName+'","Disk":"'+storage+'","targetDevice":"'+targetDevice+'","ID":"'+localPartitionID+'"}'
                            print("--->vscsijson_org:"+ vscsijson)
                        else:
                            vscsijson = '{"servername":"' + servername + '","serversn":"' + serversn + '","serveruuid":"' + serveruuid + '","VIOS":"' + \
                                        vios[
                                            'viosname'] + '","VSCSI_Server":"' + vscsiServerAdapterName +'","ID":"'+localPartitionID+'"}'

                        vscsijsonlist.append(vscsijson)


                ###获取NPIV
                print("*****NPIV******:")
                npivlist = booklist.getElementsByTagName('VirtualFibreChannelMapping')

                if len(npivlist) != 0 :
                    for i in range(len(npivlist)):
                            print("npivlist_len:" + str(len(npivlist))+",num:"+str(i)+",vios:"+vios['viosname'])
                            serverAdapter = npivlist[i].getElementsByTagName('ServerAdapter')[0]
                            npivServerAdapterName = serverAdapter.getElementsByTagName('AdapterName')[0].childNodes[0].nodeValue
                            #vscsipdName = server.getElementsByTagName('BackingDeviceName')[0].childNodes[0].nodeValue
                            physicalPort = serverAdapter.getElementsByTagName('PhysicalPort')
                            portName = physicalPort[0].getElementsByTagName('PortName')[0].childNodes[0].nodeValue
                            locationCode = physicalPort[0].getElementsByTagName('LocationCode')[0].childNodes[0].nodeValue
                            clientAdapterlist = npivlist[i].getElementsByTagName('ClientAdapter')
                            localPartitionID = ""
                            if len(clientAdapterlist)!= 0 :
                                localPartitionID = \
                                npivlist[i].getElementsByTagName('ClientAdapter')[0].getElementsByTagName(
                                    'LocalPartitionID')[0].childNodes[0].nodeValue
                            npivjson = '{"servername":"' + servername + '","serversn":"' + serversn + '","serveruuid":"' + serveruuid + '","VIOS":"' + vios['viosname'] +'","portName":"'+portName+'","locationCode":"'+locationCode+ '","NPIV_Server":"'+npivServerAdapterName+'","ID":"'+localPartitionID+'"}'
                            print("--->npivjson_org:"+ npivjson)
                            npivjsonlist.append(npivjson)


            #if debug: print("seajson : " + serverjson + viosjson )


                    # if debug: print("VIOS ID " + SharedEthernetAdapterList)


            #for num, vios in enumerate(vios_xml, start=1):
            #    if debug: print("LW VIOS NAME " + vios['filename'])

        # _     ____   _    ____
        # | |   |  _ \ / \  |  _ \
        # | |   | |_) / _ \ | |_) |
        # | |___|  __/ ___ \|  _ <
        # |_____|_| /_/   \_\_| \_\

        if filename[:16] == "LogicalPartition":
            if debug:
                filename2 = filename + ".xml"
                print('----> Server=%s Filenames XML File=%d bytes=%d name=%s'
                      % (server['name'], num, len(data), filename2))
                hmc.save_to_file(filename2, data)
                print('----> LPAR on Server=%s Filenames XML File=%d bytes=%d' % (server['name'], num, len(data)))
            filename3, url = hmc.get_filename_from_xml(data)
            # some old HMC versions return duff filenames
            if filename3 == "":
                continue
            if url == "":
                continue
            LPARstats = hmc.get_stats(url, filename3, "LPARstats")
            LogicalPartitionProfileUUID = filename3[17:53]
            print('---> LogicalPartitionProfileUUID ' +  LogicalPartitionProfileUUID)
            LogicalPartitionProfile = hmc.get_filenames_LogicalPartitionProfile(LogicalPartitionProfileUUID,"LPAR")
            if debug:
                filename3 = filename3.replace('.json', '.JSON')
                print('---> Save readable JSON File=%d bytes=%d name=%s' % (num, len(LPARstats), filename3))
                hmc.save_json_txt_to_file(filename3, LPARstats)

            jdata = json.loads(LPARstats)
            servername = jdata["systemUtil"]["utilInfo"]['name']  # name of server
            lparname = jdata["systemUtil"]["utilSamples"][0]['lparsUtil'][0]['name']
            lparid = jdata["systemUtil"]["utilSamples"][0]['lparsUtil'][0]['uuid']
            print('----> LPAR=%s' % (lparname))

            for sample in jdata['systemUtil']['utilSamples']:
                errors = 0
                samplestatus = sample['sampleInfo']['status']
                sampletime = sample['sampleInfo']['timeStamp']
                if samplestatus != 0:
                    errmsg = "None"
                    errId = "None"
                    uuid = "None"
                    reportedBy = "None"

                    try:
                        errmsg = sample['sampleInfo']['errorInfo'][0]['errMsg']
                        errId = sample['sampleInfo']['errorInfo'][0]['errId']
                        uuid = sample['sampleInfo']['errorInfo'][0]['uuid']
                        reportedBy = sample['sampleInfo']['errorInfo'][0]['reportedBy']
                    except:
                        print("Error State non-zero but there is no error messages . . . continuing")

                    errors += 1
                    e_before = len(errorlist)
                    error = "%s%d%s%s%s" % (servername, samplestatus, errId, reportedBy, errmsg)
                    errorlist.add(error)
                    e_after = len(errorlist)
                    if e_before != e_after:  # ie the error was added so its new so print it
                        print("ERROR Server=%s LPAR=%s: Status=%d errId=%s From=%s\nERROR Description=%s\n"
                              % (servername, lparname, samplestatus, errId, reportedBy, errmsg))

                for lpar in sample['lparsUtil']:

                    try:
                        data = {'measurement': 'lpar_details', 'time': sampletime,
                                'tags': {'servername': servername, 'lparname': lparname},
                                'fields': {
                                    "id": lpar['id'],
                                    "name": lpar['name'],
                                    "state": lpar['state'],
                                    "type": lpar['type'],
                                    "osType": lpar['osType'],
                                    "affinityScore": lpar['affinityScore']}}
                        entry.append(data)
                    except:
                        if debug: print("no lpar_details %s %s %s" % (servername, lparname, sampletime))

                    try:
                        data = {'measurement': 'lpar_processor', 'time': sampletime,
                                'tags': {'servername': servername, 'lparname': lparname},
                                'fields': extract_data(lpar['processor'])}
                        entry.append(data)
                    except:
                        if debug: print("no lpar_processor%s %s %s" % (servername, lparname, sampletime))

                    try:
                        data = {'measurement': 'lpar_memory', 'time': sampletime,
                                'tags': {'servername': servername, 'lparname': lparname},
                                'fields': extract_data(lpar['memory'])}
                        entry.append(data)
                    except:
                        if debug: print("no lpar_memory %s %s %s" % (servername, lparname, sampletime))

                    if debug: print("LPAR state = |%s| %s %s %s" % (lpar['state'], servername, lparname, sampletime))
                    if lpar['state'] == "Not Activated":
                        continue  # Skip the below as they are only available for state=Active LPARs

                    # Networks
                    try:
                        for net in lpar['network']['virtualEthernetAdapters']:
                            try:
                                data = {'measurement': 'lpar_net_virtual', 'time': sampletime,
                                        'tags': {'servername': servername, 'lparname': lparname,
                                                 'location': net['physicalLocation'],
                                                 'vlanId': net['vlanId'],
                                                 'vswitchId': net['vswitchId']},
                                        'fields': extract_data(net)}
                                entry.append(data)
                                lparjson = "{server:" + servername + "},{lparname:" + lparname + "},{lparid:" + lparid + "},{vlanId:" + \
                                           net['vlanId'] + "},{location" + net['physicalLocation'] + "}"
                                if debug: print("lparjson:"+lparjson)
                                lparjsonlist.append(lparjson)

                            except:
                                if debug: print("no lpar_net_virtual")
                    except:
                        if debug: print("no lpar_net_virtual %s %s %s" % (servername, lparname, sampletime))

                    try:
                        for net in lpar['network']['sriovLogicalPorts']:
                            if debug: print(net)
                            try:
                                data = {'measurement': 'lpar_network_sriov', 'time': sampletime,
                                        'tags': {'servername': servername, 'lparname': lparname,
                                                 'location': net['physicalLocation'],
                                                 'physicalPortId': net['physicalPortId']},
                                        'fields': extract_data(net)}
                                entry.append(data)
                                if debug: print(data)
                            except:
                                if debug: print("no lpar_network_sriov")
                    except:
                        if debug: print("no lpar_network_sriov %s %s %s" % (servername, lparname, sampletime))

                    # Storage
                    try:
                        for store in lpar['storage']['genericVirtualAdapters']:
                            try:
                                data = {'measurement': 'lpar_storage_virtual', 'time': sampletime,
                                        'tags': {'servername': servername, 'lparname': lparname,
                                                 'id': store['id'],
                                                 'location': net['physicalLocation'],
                                                 'viosId': store['viosId']},
                                        'fields': extract_data(store)}
                                entry.append(data)
                            except:
                                if debug: print("no lpar_storage_virtual")
                    except:
                        if debug: print("no lpar_storage_virtual %s %s %s" % (servername, lparname, sampletime))

                    try:
                        for store in lpar['storage']['virtualFiberChannelAdapters']:
                            try:
                                data = {'measurement': 'lpar_storage_vFC', 'time': sampletime,
                                        'tags': {'servername': servername, 'lparname': lparname,
                                                 'location': store['physicalLocation'],
                                                 'viosId': store['viosId']},
                                        'fields': extract_data(store)}
                                entry.append(data)
                            except:
                                if debug: print("no lpar_storage_vFC")
                    except:
                        if debug: print("no lpar_storage_vFC %s %s %s" % (servername, lparname, sampletime))
        for lparjson in lparjsonlist:
            if debug: print(" lparjson: " + lparjson)


        # for a in range(len(seavdjsonlist)):
        #     if debug: print(" seajson: " + seavdjsonlist[a])
        #     seavddata = json.loads(seavdjsonlist[a])
        #     servername = seavddata['servername']
        #     serveruuid = seavddata['serveruuid']
        #     try:
        #         DOMTree = parse("debug/" + "Profile-" + servername + "-" + serveruuid + "-filenames" + ".xml")
        #         booklist = DOMTree.documentElement
        #         # 获取SEA
        #         lparlist = booklist.getElementsByTagName('entry')
        #     except:
        #         continue
        #     for b in range(int(seavddata['vdnum'])):
        #         for i in range(len(lparlist)):
        #             lparuuid = lparlist[i].getElementsByTagName('id')[0].childNodes[0].nodeValue
        #             lparid = lparlist[i].getElementsByTagName('PartitionID')[0].childNodes[0].nodeValue
        #             lparname = lparlist[i].getElementsByTagName('PartitionName')[0].childNodes[0].nodeValue
        #             print('---> LogicalPartitionProfileUUID ' + lparuuid)
        #             LogicalPartitionProfile = hmc.get_filenames_LogicalPartitionProfile(lparuuid,"LPAR")
        #             DOMTree2 = parse("debug/" + "LogicalPartitionProfile-LPAR-" + lparuuid + "-filenames" + ".xml")
        #             booklist2 = DOMTree2.documentElement
        #             vlanid = booklist2.getElementsByTagName('PortVLANID')[0].childNodes[0].nodeValue
        #             if(vlanid == seavddata['vlanID'+str(b)]):
        #                 string = seajsonlist[a]
        #                 length = int(len(string))-1
        #                 #if debug: print(" str: " + string + "\n"+str(len(string)))
        #                 alljson = seajsonlist[a][:length] + ',"vdName":"'+seavddata['vdName'+str(b)]+',"vdlocation":"'+ seavddata['vdlocation'+str(b)]+'",vlanid":"'+vlanid+'","lparid":"'+lparid+'","lparname":"'+lparname+'","lparuuid":"'+lparuuid+'"}'
        #                 #if debug: print(" alljson: " + alljson)
        #                 alljsonlist.append(alljson)

        #     if debug: print(" servername: " + servername)
        #
        #     if debug: print(" seajson: " + seajson)

        # PUSH TO INFLUXDB FOR EACH FILE if more than 25000 lines of data ready
        if len(entry) > 25000:
            print("Adding %d records to InfluxDB for Server=%s" % (len(entry), servername))
            measures = measures + len(entry)
            if saveInflux:
                client.write_points(entry)
            if saveJSON:
                for item in entry:
                    JSONfile.write(str(item) + "\n")
            entry = []  # empty the list

    # PUSH TO INFLUXDB FOR EACH SERVER
    if len(entry) > 0:
        if saveInflux:
            client.write_points(entry)
        print("Added %d records to InfluxDB for Server=%s" % (len(entry), servername))
        measures = measures + len(entry)
        if saveJSON:
            for item in entry:
                JSONfile.write(str(item) + "\n")

##SEA
for a in range(len(seavdjsonlist)):
    if debug: print(" seajson: " + seavdjsonlist[a])
    seavddata = json.loads(seavdjsonlist[a])
    servername = seavddata['servername']
    serveruuid = seavddata['serveruuid']
    DOMTree = parse("debug/" + "Profile-" + servername + "-" + serveruuid + "-filenames" + ".xml")
    booklist = DOMTree.documentElement
    # 获取SEA
    lparlist = booklist.getElementsByTagName('entry')
    for i in range(len(lparlist)):
        lparuuid = lparlist[i].getElementsByTagName('id')[0].childNodes[0].nodeValue
        lparid = lparlist[i].getElementsByTagName('PartitionID')[0].childNodes[0].nodeValue
        lparname = lparlist[i].getElementsByTagName('PartitionName')[0].childNodes[0].nodeValue
        print('---> servername'+servername+'-->LogicalPartitionProfileUUID ' + lparuuid )
        LogicalPartitionProfile = hmc.get_filenames_LogicalPartitionProfile(lparuuid,"LPAR")
        DOMTree2 = parse("debug/" + "LogicalPartitionProfile-LPAR-" + lparuuid + "-filenames" + ".xml")
        booklist2 = DOMTree2.documentElement
        vlan =booklist2.getElementsByTagName('PortVLANID')
        if len(vlan)==0 : continue
        vlanid = booklist2.getElementsByTagName('PortVLANID')[0].childNodes[0].nodeValue
        print('---> servername' + servername + '-->LogicalPartitionProfileUUID ' + lparuuid + '-->vlanid:'+ vlanid + ',vlanid'+':'+seavddata['vlanID'])
        if(vlanid == seavddata['vlanID']):
            string = seapdjsonlist[a]
            length = int(len(string))-1
            #if debug: print(" str: " + string + "\n"+str(len(string)))
            #alljson = seajsonlist[a][:length] + ',"vdName":"'+seavddata['vdName'+str(b)]+'","vdlocation":"'+ seavddata['vdlocation'+str(b)]+'","vlanid":"'+vlanid+'","lparid":"'+lparid+'","lparname":"'+lparname+'","lparuuid":"'+lparuuid+'"}'
            alljson = seapdjsonlist[a][:length] +',"VIOC":"' + lparname + '","ID":"'+lparid + '"}'
            alljsonlist.append(alljson)
            print("-----alljsonpd:" + alljson)
            #length = int(seavdjsonlist[a].rfind("vdnum"))-2
            #alljson = seavdjsonlist[a][:length] + ',"ID":"'+lparid+ '","Name":"' + lparname + '"}'
            #alljson = seavdjsonlist[a][:length] + ',"ID":"' + lparid + ',"Name":"' + lparname + '(' + lparid + ')' + '"}'
            #print("-----alljsonvd:" + alljson)
            #alljsonlist.append(alljson)
            #if debug: print(" alljson: " + alljson)


###VSCSI
for a in range(len(vscsijsonlist)):
    if debug: print("vscsijson: " + vscsijsonlist[a])
    vscsidata = json.loads(vscsijsonlist[a])
    servername = vscsidata['servername']
    serveruuid = vscsidata['serveruuid']
    DOMTree = parse("debug/" + "Profile-" + servername + "-" + serveruuid + "-filenames" + ".xml")
    booklist = DOMTree.documentElement
    # 获取SEA
    lparlist = booklist.getElementsByTagName('entry')
    print ("lparlist_length:"+str(len(lparlist)))
    for i in range(len(lparlist)):
        if debug: print(" vscsijson_org: " + vscsijsonlist[a])
        print("lparxml:"+ lparlist[i].toxml())
        lparuuid = lparlist[i].getElementsByTagName('id')[0].childNodes[0].nodeValue
        lparid = lparlist[i].getElementsByTagName('PartitionID')[0].childNodes[0].nodeValue
        lparname = lparlist[i].getElementsByTagName('PartitionName')[0].childNodes[0].nodeValue
        print("-->vscsi-->localPartitionID:"+ vscsidata['ID'] +",lparid:"+lparid)
        if vscsidata['ID'] == lparid :
            length = vscsijsonlist[a].rfind("ID")
            vscsijsonlist[a] = vscsijsonlist[a][:length-2] + ',"VIOC":"'+lparname+'","ID":"'+ lparid + '"}'
    if vscsidata['ID'] == "":
        length = vscsijsonlist[a].rfind("ID")
        vscsijsonlist[a] = vscsijsonlist[a][:length-2]+'}'
    if debug: print("vscsijson_final: " + vscsijsonlist[a])

###NPIV
for a in range(len(npivjsonlist)):
    if debug: print("npivjson: " + npivjsonlist[a])
    npivdata = json.loads(npivjsonlist[a])
    servername = npivdata['servername']
    serveruuid = npivdata['serveruuid']
    DOMTree = parse("debug/" + "Profile-" + servername + "-" + serveruuid + "-filenames" + ".xml")
    booklist = DOMTree.documentElement
    # 获取SEA
    lparlist = booklist.getElementsByTagName('entry')
    for i in range(len(lparlist)):
        if debug: print(" vscsijson_org: " + npivjsonlist[a])
        lparuuid = lparlist[i].getElementsByTagName('id')[0].childNodes[0].nodeValue
        lparid = lparlist[i].getElementsByTagName('PartitionID')[0].childNodes[0].nodeValue
        lparname = lparlist[i].getElementsByTagName('PartitionName')[0].childNodes[0].nodeValue
        if npivdata['ID'] == lparid :
            length = npivjsonlist[a].rfind("ID")
            npivjsonlist[a] = npivjsonlist[a][:length-2] + ',"VIOC":"'+lparname+'","ID":"'+ lparid + '"}'
    if npivdata['ID'] == "":
        length = npivjsonlist[a].rfind("ID")
        npivjsonlist[a] = npivjsonlist[a][:length-2]+'}'
    if debug: print("npivjson_final: " + npivjsonlist[a])




##去重
alljsonlist_new = []
for alljson in alljsonlist:
    if alljson not in vioslist_new:
        alljsonlist_new.append(alljson)

vscsijsonlist_new = []
for vscsijson in vscsijsonlist:
    if vscsijson not in vscsijsonlist_new:
        vscsijsonlist_new.append(vscsijson)

npivjsonlist_new = []
for npivjson in npivjsonlist:
    if npivjson not in npivjsonlist_new:
        npivjsonlist_new.append(npivjson)


##SEA
graphnode = ""
servername = ""
servername2 = ""
strlist=[]
graphnodelist=[]
num = 0
for alljson in alljsonlist_new:
    if debug: print(" alljson: " + alljson)
    length = len(alljsonlist_new)-1
    jsondata = json.loads(alljson)
    servername = jsondata['servername']
    items = jsondata.items()
    string = ""
    if debug: print(
        " -->servername: " + servername + ",servername2:" + servername2 + ",num:" + str(num) + ",len:" + str(length))
    if (servername != servername2 and servername2 != "") or num == length:
        if debug: print(" graphnode: " + graphnode)
        graphnodelist.append(graphnode[:len(graphnode)-1])
        strlist = []
        graphnode = ""
    for key,value in items:
        string = key + ':'+ value
        if string not in strlist:
            strlist.append(string)
    graphnode=""
    for str2 in strlist:
        if str2.rfind('servername') != -1 or str2.rfind('serversn') != -1 or str2.rfind('vdName') != -1 or str2.rfind('pdName') != -1 or str2.rfind('ethernetAdpter') != -1 or str2.rfind('VIOC') != -1:
            graphnode = graphnode + str2 + "\n"
        else:
            graphnode = graphnode + str2 + ","
    #if debug: print(" graphnode2: " + graphnode)
    servername2 = servername
    num = num + 1

for graphnode in graphnodelist:
    nodelist = []
    linklist = []
    str3list = []
    graphnode3 = ""
    print("*******graphnode_final****:"+graphnode)
    server = graphnode.split(',')
    node2 = ""
    for node in server:
        if node.rfind('servername') != -1 :
            nodelist.append(opts.GraphNode(name=node, symbol_size=35))
        elif node.rfind('VIOS') != -1 :
            nodelist.append(opts.GraphNode(name=node, symbol_size=30))
        elif node.rfind('pdName') != -1 :
            nodelist.append(opts.GraphNode(name=node, symbol_size=25))
        elif node.rfind('SEA') != -1 :
            nodelist.append(opts.GraphNode(name=node, symbol_size=20))
        elif node.rfind('vdName') != -1 :
            nodelist.append(opts.GraphNode(name=node, symbol_size=15))
        else:
            nodelist.append(opts.GraphNode(name=node, symbol_size=10))
    for link in alljsonlist_new :
        jsondata = json.loads(link)
        items = jsondata.items()
        servername = 'servername:'+jsondata['servername']
        linknode=""
        linknode2=""
        string1=server[0].split('\n')[0]
        #print("link-server:"+servername+","+string1)
        #print("**--**link:" + link)
        tempstr =""
        if servername == string1 :
            for key, value in items:
                string3 = key + ':' + value
                str3list.append(string3)
            for str2 in str3list:
                if str2.rfind('servername') != -1 or str2.rfind('serversn') != -1  or str2.rfind('vdName') != -1 or str2.rfind('pdName') != -1 or str2.rfind('ethernetAdpter') != -1 or str2.rfind('VIOC') != -1:
                    graphnode3 = graphnode3 + str2 + "\n"
                else:
                    graphnode3 = graphnode3 + str2 + ","
            tempstr = graphnode3.split(',')
        #print("**--**tempstr:"+graphnode3)
        servernamenum = 0
        for linknode in tempstr :
            #print("**--**linnode:"+linknode+",linknode2:" + linknode2.split('\n')[0] + ",server:"+server[0].split('\n')[0])
            if (linknode.split('\n')[0] == server[0].split('\n')[0]) and servernamenum != 0:
                linknode2 = linknode
                continue
            if (linknode.split('\n')[0] == server[0].split('\n')[0]) and servernamenum == 0 : servernamenum = servernamenum + 1
            if (linknode != linknode2 and linknode2 != "") :
                #print("linknode:" + linknode + ",linknode2:" + linknode2)
                linklist.append(opts.GraphLink(source= linknode2, target=linknode,value=linknode.split(':')[0]))
            linknode2 = linknode
        node2 = node

    c = (
        Graph()
              .add("", nodelist, linklist, repulsion=4000,
                   edge_label=opts.LabelOpts(is_show=True, position="middle", formatter="{c}")
                         )
              .set_global_opts(title_opts=opts.TitleOpts(title="Graph-GraphNode-GraphLink"))
               .render("SEA_" + server[0].split('\n')[1].split(':')[1] + ".html")
    )

###VSCSI
vscsigraphnode = ""
servername = ""
servername2 = ""
vscsigraphnodelist = []
strlist = []
num = 0

storage_key = ""
storage_value = ""
storage_str = ""
storage_list = []
vscsi_server = ""
for vscsijson in vscsijsonlist_new:
    if debug: print("---vscsijson---: " + vscsijson)
    length = len(vscsijsonlist_new)-1
    jsondata = json.loads(vscsijson)
    servername = jsondata['servername']
    items = jsondata.items()

    string = ""
    if debug: print(
        " -->servername: " + servername + ",servername2:" + servername2 + ",num:" + str(num) + ",len:" + str(length))
    if (servername != servername2 and servername2 != "") or num == length:
        if debug: print("-->vscsigraphnode: " + vscsigraphnode)
        vscsigraphnodelist.append(vscsigraphnode[:len(vscsigraphnode)-1])
        strlist = []
        vscsigraphnode = ""
        storage_key = ""
        storage_value = ""
        storage_str = ""
        storage_list = []
        temp_key = ""
        temp_value = ""
        storage_list = []

    vscsigraphnodetemp = ""
    for key,value in items:
        string = key + ':'+ value
        if key == 'VSCSI_Server' :
            vscsi_server = value
        if key == 'Disk':
            storage_key = key
            storage_value = value
            storage_str = storage_key + ':' + storage_value
            storage_list.append(storage_value)
            # if storage_value not in storage_list:
            #     storage_list.append(storage_value+":"+0)
            # print("--------------storage_list--------")
            # print(storage_list)
            # print("-----------------------------")
            # else :
            #     storage_list.find(storage_value)
        if  key == 'targetDevice' :
            for storage in storage_list:
                print("----storage:"+storage+",count:"+str(storage_list.count(temp_value))+",key:"+key +",value:"+value+" ------------------------")
                if temp_value == storage and storage_list.count(temp_value) != 1:
                    strlist.append(storage_str)
                    break
        if string not in strlist:
            strlist.append(string)
        temp_key = key
        temp_value = value
    # print("--------------strlist--------")
    # print(strlist)
    # print("-----------------------------")


    vscsigraphnode = ""
    for str2 in strlist:
        if str2.rfind('servername') != -1 or str2.rfind('serversn') != -1 or str2.rfind('VIOC') != -1 or str2.rfind('Disk') != -1:
            vscsigraphnode = vscsigraphnode + str2 + "\n"
        else:
            vscsigraphnode = vscsigraphnode + str2 + ","
        vscsigraphnodetemp = str2
    if debug: print(" vscsigraphnode2: " + vscsigraphnode)
    servername2 = servername
    num = num + 1

for vscsigraphnode in vscsigraphnodelist:
    vscsinodelist = []
    vscsilinklist = []
    str3list = []
    graphnode3 = ""
    print("*******vscsi_graphnode_final****:"+vscsigraphnode)
    vscsinode = vscsigraphnode.split(',')
    node2 = ""
    for node in vscsinode:
        if node.rfind('servername') != -1 :
            vscsinodelist.append(opts.GraphNode(name=node, symbol_size=35))
        elif node.rfind('VIOS') != -1 :
            vscsinodelist.append(opts.GraphNode(name=node, symbol_size=25))
        elif node.rfind('VSCSI_Server') != -1 :
            vscsinodelist.append(opts.GraphNode(name=node, symbol_size=20))
        elif node.rfind('Disk') != -1 :
            vscsinodelist.append(opts.GraphNode(name=node, symbol_size=15))
        else:
            vscsinodelist.append(opts.GraphNode(name=node, symbol_size=10))
    for link in vscsijsonlist_new :
        jsondata = json.loads(link)
        items = jsondata.items()
        servername = 'servername:'+jsondata['servername']
        linknode=""
        linknode2=""
        string1=vscsinode[0].split('\n')[0]
        print("link-server:"+servername+","+string1)
        print("**--**link:" + link)
        tempstr =""
        storage = ""
        vscsi_server =""
        vscsigraphnodetemp =""
        if servername == string1 :
            for key, value in items:
                string3 = key + ':' + value
                str3list.append(string3)
            for str2 in str3list:
                if str2.rfind('servername') != -1 or str2.rfind('serversn') != -1  or str2.rfind('Disk') != -1 or str2.rfind('VIOC') != -1:
                    graphnode3 = graphnode3 + str2 + "\n"
                else:
                    graphnode3 = graphnode3 + str2 + ","
                vscsigraphnodetemp = str2
        print("**--**vscsitempstr:" + graphnode3)
        tempstr = graphnode3.split(',')
        servernamenum = 0
        for linknode in tempstr:
            print("**--**linnode:"+linknode+",linknode2:" + linknode2.split('\n')[0] + ",server:"+server[0].split('\n')[0])
            if (linknode.split('\n')[0] == vscsinode[0].split('\n')[0]) and servernamenum != 0:
                linknode2 = linknode
                continue
            if (linknode.split('\n')[0] == vscsinode[0].split('\n')[
                    0]) and servernamenum == 0: servernamenum = servernamenum + 1
            if (linknode != linknode2 and linknode2 != ""):
                # print("linknode:" + linknode + ",linknode2:" + linknode2)
                vscsilinklist.append(opts.GraphLink(source=linknode2, target=linknode,value=linknode.split(':')[0]))
            linknode2 = linknode
        node2 = node

        c = (
            Graph()
                .add("", vscsinodelist, vscsilinklist, repulsion=4000,
                     edge_label=opts.LabelOpts(is_show=True, position="middle", formatter="{c}")
                     )
                .set_global_opts(title_opts=opts.TitleOpts(title="Graph-GraphNode-GraphLink"))
                .render("VSCSI_" + vscsinode[0].split('\n')[1].split(':')[1] + ".html")
        )

###NPIV
npivgraphnode = ""
servername = ""
servername2 = ""
npivgraphnodelist = []
strlist = []
num = 0
for npivjson in npivjsonlist_new:
    if debug: print("vscsijson: " + npivjson)
    length = len(npivjsonlist_new)-1
    jsondata = json.loads(npivjson)
    servername = jsondata['servername']
    items = jsondata.items()

    string = ""
    if debug: print(
        " -->servername: " + servername + ",servername2:" + servername2 + ",num:" + str(num) + ",len:" + str(length))
    if (servername != servername2 and servername2 != "") or num == length:
        if debug: print("npivgraphnode: " + npivgraphnode)
        npivgraphnodelist.append(npivgraphnode[:len(npivgraphnode)-1])
        strlist = []
        npivgraphnode = ""
    for key,value in items:
        string = key + ':'+ value
        if string not in strlist:
            strlist.append(string)
    npivgraphnode=""
    for str2 in strlist:
        if str2.rfind('servername') != -1 or str2.rfind('serversn') != -1 or str2.rfind('portName') != -1 or str2.rfind('VIOC') != -1:
            npivgraphnode = npivgraphnode + str2 + "\n"
        else:
            npivgraphnode = npivgraphnode + str2 + ","
    if debug: print(" npivgraphnode2: " + npivgraphnode)
    servername2 = servername
    num = num + 1

for npivgraphnode in npivgraphnodelist:
    npivnodelist = []
    npivlinklist = []
    str3list = []
    graphnode3 = ""
    print("*******graphnode_final****:"+npivgraphnode)
    npivnode = npivgraphnode.split(',')
    node2 = ""
    for node in npivnode:
        if node.rfind('servername') != -1 :
            npivnodelist.append(opts.GraphNode(name=node, symbol_size=35))
        elif node.rfind('VIOS') != -1:
            npivnodelist.append(opts.GraphNode(name=node, symbol_size=25))
        elif node.rfind('portName') != -1:
            npivnodelist.append(opts.GraphNode(name=node, symbol_size=20))
        elif node.rfind('NPIV_Server') != -1 :
            npivnodelist.append(opts.GraphNode(name=node, symbol_size=15))
        else:
            npivnodelist.append(opts.GraphNode(name=node, symbol_size=10))
    for link in npivjsonlist_new :
        jsondata = json.loads(link)
        items = jsondata.items()
        servername = 'servername:'+jsondata['servername']
        linknode=""
        linknode2=""
        string1=npivnode[0].split('\n')[0]
        #print("link-server:"+servername+","+string1)
        if servername == string1 :
            for key, value in items:
                string3 = key + ':' + value
                str3list.append(string3)
            for str2 in str3list:
                if str2.rfind('servername') != -1 or str2.rfind('serversn') != -1 or str2.rfind('portName') != -1 or str2.rfind('VIOC') != -1:
                    graphnode3 = graphnode3 + str2 + "\n"
                else:
                    graphnode3 = graphnode3 + str2 + ","
        tempstr = graphnode3.split(',')
        servernamenum = 0
        for linknode in tempstr:
            #print("**--**linnode:"+linknode+",linknode2:" + linknode2.split('\n')[0] + ",server:"+server[0].split('\n')[0])
            if (linknode.split('\n')[0] == npivnode[0].split('\n')[0]) and servernamenum != 0:
                linknode2 = linknode
                continue
            if (linknode.split('\n')[0] == npivnode[0].split('\n')[
                    0]) and servernamenum == 0: servernamenum = servernamenum + 1
            if (linknode != linknode2 and linknode2 != ""):
                # print("linknode:" + linknode + ",linknode2:" + linknode2)
                npivlinklist.append(opts.GraphLink(source=linknode2, target=linknode,value=linknode.split(':')[0]))
            linknode2 = linknode
        node2 = node

    c = (
        Graph()
              .add("", npivnodelist, npivlinklist, repulsion=4000,
                   edge_label=opts.LabelOpts(is_show=True, position="middle", formatter="{c}")
                         )
              .set_global_opts(title_opts=opts.TitleOpts(title="Graph-GraphNode-GraphLink"))
              .render("NPIV_" + npivnode[0].split('\n')[1].split(':')[1]+ ".html")
    )




if saveJSON:
    JSONfile.close()

print("Logging off the HMC - found %d measures" % (measures))
hmc.logoff()
