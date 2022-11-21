import json
import os
import uuid
from datetime import datetime
from pathlib import Path

import requests
import socket

from workbench_utils import WorkbenchSettings, WorkbenchUtils
from workbench_hwdata import HardwareData


class WorkbenchCore:
    """ Create a snapshot of your computer with hardware data and submit the information to a server.
        You must run this software as root / sudo.
    """

    def __init__(self):
        if os.geteuid() != 0:
            raise EnvironmentError('[ERROR] Execute Workbench as root / sudo.')
        self.timestamp = datetime.now()
        self.type = 'Snapshot'
        self.snapshot_uuid = uuid.uuid4()
        self.software = 'Workbench'
        self.version = '2022.11.1-beta'
        self.schema_api = '1.0.0'
        # Generate SID as an alternative id to the DHID when no internet 
        self.sid = self.generate_sid()
        self.dh_url = WorkbenchSettings.DH_URL
        self.dh_token = WorkbenchSettings.DH_TOKEN
        self.snapshots_path = WorkbenchSettings.SNAPSHOT_PATH or os.getcwd()
        self.settings_version = WorkbenchSettings.VERSION or 'No Settings Version (NaN)'

    def generate_sid(self):
            return str(self.snapshot_uuid.time_mid).rjust(5, '0')

    def generate_snapshot(self):
        """ Getting hardware data and generate snapshot object."""

        snapshot_data = {}
        snapshot_data.update({'lshw': HardwareData.get_lshw_data()})
        snapshot_data.update({'dmidecode': HardwareData.get_dmi_data()})
        snapshot_data.update({'lspci': HardwareData.get_lspci_data()})
        # 2022-9-8: hwinfo is slow, it is in the stage of deprecation and it is not tested
        #   hence, don't run hwinfo on test situation
        #   info: disabling it reduces the process time from 17 to 2 seconds
        if(not os.environ.get("DISABLE_HWINFO")):
          snapshot_data.update({'hwinfo': HardwareData.get_hwinfo_data()})
        else:
          snapshot_data.update({'hwinfo': ''})
        snapshot_data.update({'smart': HardwareData.get_smart_data()})

        # Generate snapshot
        snapshot = {
            'timestamp': self.timestamp.isoformat(),
            'type': self.type,
            'uuid': str(self.snapshot_uuid),
            'sid': self.sid,
            'software': self.software,
            'version': self.version,
            'schema_api': self.schema_api,
            'settings_version': self.settings_version,
            'data': snapshot_data
        }

        print('[INFO] Snapshot generated properly.')
        return snapshot

    def save_snapshot(self, snapshot):
        """ Save snapshot like JSON file on local storage."""
        try:
            json_file = '{date}_{sid}_snapshot.json'.format(date=self.timestamp.strftime("%Y-%m-%d_%Hh%Mm%Ss"),
                                                            sid=self.sid)
            # Create snapshots folder
            snapshot_folder=self.snapshots_path + '/snapshots/'
            Path(snapshot_folder).mkdir(parents=True, exist_ok=True)
            # Saving snapshot
            with open(snapshot_folder + json_file, 'w+') as file:
                json.dump(snapshot, file)
            print('[INFO] Snapshot successfully saved on', snapshot_folder)
            print('[SNAPSHOT]', json_file)
            return json_file
        except Exception as e:
            print('[EXCEPTION] Save snapshot:', e)
            return None

    def post_snapshot(self, snapshot):
        """ Upload snapshot to server."""
        if WorkbenchUtils.internet():
            if self.dh_url and self.dh_token:
                post_headers = {'Authorization': 'Basic ' + self.dh_token, 'Content-type': 'application/json'}

                try:
                    response = requests.post(self.dh_url, headers=post_headers, data=json.dumps(snapshot))
                    r = response.json()
                    if response.status_code == 201:
                        print('[INFO] Snapshot JSON successfully uploaded.')
                        print('[DHID]', r['dhid'])
                        print('[DH_URL]', r['url'])
                    elif response.status_code == 400:
                        print('[ERROR] We could not auto-upload the device.', response.status_code, response.reason)
                        print('Response error:', r)
                    else:
                        print('[WARNING] We could not auto-upload the device.', r['code'], r['type'])
                        print('Response:', r['message'])
                    return response
                except Exception as e:
                    print('[EXCEPTION] POST snapshot exception:', e)
                    return False
            else:
                print('[WARNING] We could not auto-upload the device. Settings URL or TOKEN are empty.')
                return False
    
    def print_summary(self, json_file, response):
        print('[VERSION]', self.version)
        print('[SETTINGS]', self.settings_version)
        print('[SID]', self.sid)
        print('[SNAPSHOT]', json_file)

        if response:
            r = response.json()
            if response.status_code == 201:
                print('[DH_URL]', r['url'])
                print('[DHID]', r['dhid'])
                print('[DEVICE_URL]', r['public_url'])
            else:
                print('[WARNING] We could not auto-upload the device.', r['code'], r['type'])
                print('Response:', r['message'])


if '__main__' == __name__:
    workbench = WorkbenchCore()

    print('[INIT] ====== Starting Workbench ======')
    print('[VERSION]', workbench.version)
    print('[SETTINGS]', workbench.settings_version)
    print('[SID]', workbench.sid)

    print('[STEP 1] ---- Generating Snapshot ----')
    snapshot = workbench.generate_snapshot()

    print('[STEP 2] ---- Saving Snapshot ----')
    json_file = workbench.save_snapshot(snapshot)

    print('[STEP 3] ---- Uploading Snapshot ----')
    response = workbench.post_snapshot(snapshot)

    print('[EXIT] ====== Workbench finished ======')

    print('-------------- [SUMMARY] --------------')
    workbench.print_summary(json_file, response)
