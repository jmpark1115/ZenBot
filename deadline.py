import requests
import datetime

url = 'http://worldclockapi.com/api/json/utc/now'

def isDeadline():

    deadline = datetime.datetime(2020, 9, 13)
    print(deadline)

    status = 'ERROR'
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            content = resp.json()
            current = content.get('currentDateTime', '')
            if current:
                cur_list = current.split('-')
                print(cur_list)

                remote   = datetime.datetime(int(cur_list[0]), int(cur_list[1]), int(cur_list[2][:2]))
                print('remote {} >= deadline {}' .format(remote, deadline))

                if remote >= deadline :
                    print('stop')
                    return 'NG'
                else:
                    print('go')
                    return 'OK'
        return status
    except Exception as ex:
        return status