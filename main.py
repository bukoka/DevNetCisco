




from netmiko import ConnectHandler
import yaml
from pprint import pprint
from datetime import datetime
import textfsm
import re


PATH = r'/home/python/PycharmProjects/DevNetCisco/'
SOURCE_NTP = '192.168.100.3'
LIST_OF_COMMANDS = ['clock timezone GMT +0', f'ntp server {SOURCE_NTP}']

def execute_command(device_dict,command):
    '''
    :param device_dict: Dictionary with parametrs of connection
    :param command: Command in string to execute
    :return: Tuple with resutl of  command (output) + hostname of device
    '''
    now = datetime.now().isoformat()
    with ConnectHandler(**device_dict) as ssh:
        ssh.enable()
        hostname = ssh.find_prompt()
        result = ssh.send_command(command)
    return result,hostname[:-1],now


def save_to_disk(path,output,hostname,timestamp):
    '''
    Save to disk function
    :param path: PATH to save file
    :param output:  data that should be written into file
    :param hostname:  one part of filename
    :param timestamp:  second part of filename
    :return: Boolean (True/False)
    '''
    try:
        with open(path+hostname+'_'+timestamp,'w') as file:
            file.write(output)
        return True
    except IOError:
        return False


def verify_cdp(output_cdp):
    '''
    Verify is CDP in run and count neighbors
    :param output_cdp: output of  "sh cdp  neihbors" to parse
    :return: Tuple with STATE and COUNT
    '''
    #Parse output with TextFsm
    with open('templates/cisco_ios_show_cdp_neighbors.textfsm') as t:
        parse = textfsm.TextFSM(t)
        result = parse.ParseText(output_cdp)

    #For cheking is CDP enabled - use re
    regex = re.compile(r'CDP is not enabled')
    match = regex.search(output_cdp)
    if match:
        state = 'OFF'
    else:
        state = 'ON'
    return state,len(result)

def verify_npe(output_sh_ver):
    '''
    Function fro checking is file image of IOS is PE/NPE
    :param output_sh_ver: string - output of sh_ver
    :return: (NPE or PE in string, version - string)
    '''
    #Parse output with TextFsm
    with open('templates/cisco_ios_show_version.textfsm') as t:
        parse = textfsm.TextFSM(t)
        result = parse.ParseText(output_sh_ver)
    #result[0][0] -- VERSION
    #result[0][6][0] -- HARDWARE
    # For cheking is NPE or not  - use re
    regex = re.compile(r'npe')
    match = regex.search(result[0][5].lower())
    if match:
        state = 'NPE'
    else:
        state = 'PE'
    return state,result[0][0],result[0][6][0]

def configure_command(device,list_of_command):
    '''
    Function for configuring several commands
    :param device: Dict  with device params
    :param list_of_command: list of commands
    :return: result  in string
    '''
    with ConnectHandler(**device) as ssh:
        ssh.enable()
        result = ssh.send_config_set(list_of_command)
    return result


if __name__=='__main__':
    #Read data from YAML file to python structure
    with open('devices.yaml') as file:
        devices = yaml.safe_load(file)

    flag = {} # For matching Sync / Not sync
    list_report = [] # For finally construction report
    for device in devices:
         hostname = execute_command(device,'sh users')[1] # Bring hostname

         save_to_disk(PATH, *execute_command(device, 'sh run')) # First requirement from  Homework will be done here

         state_cdp,count_cdp = verify_cdp(execute_command(device, 'sh cdp neighbors')[0])# Second reqiurement from Homework will be done here

         state_npe,version,hardware = verify_npe(execute_command(device, 'sh version')[0]) # Third  requirement  in Homework will be done here

         match = re.search(r'Success rate is 0 percent', execute_command(device,f'ping {SOURCE_NTP}')[0])
         if match:
             print(f'For device {device["ip"]} address of NTP server is not reachable')
             flag[hostname] = 'Clock not Sync'
             continue
         else:
             print(f'Commands with NTP will be executed for device {device["ip"]}')
             pprint(configure_command(device,LIST_OF_COMMANDS))
             flag[hostname] = 'Clock in Sync'

         list_report.append(f'{hostname} |{hardware} |{version} |{state_npe} |CDP is {state_cdp},{count_cdp} peers |{flag[hostname]}')

    ########Finaly report output ########
    print('-*'*10)
    for line in list_report:
        print(line)

