import subprocess
from flask import Flask, request
import yaml

SETTINGS_FILE="settings.yaml"

with open(SETTINGS_FILE, 'r') as f:
    settings = yaml.load(f)

app = Flask(__name__)

@app.route('/unlock/<device_id>', methods=['GET', 'POST']) #device_id is the id of the device in settings.yaml
def unlock_luks_device(device_id):
    device_settings = settings["devices"][device_id]
    key = request.args.get('key')
    key_file = f"/tmp/{device_settings.get('name')}.key"

    with open(f"/tmp/{device_settings.get('name')}.key", 'w') as f:
        f.write(key)

    cryptsetup_result = subprocess.run(["cryptsetup", "luksOpen", device_settings.get('path'), device_settings.get('name'), "-d", key_file], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    cryptsetup_output = cryptsetup_result.stdout.decode("utf-8")

    subprocess.run(["rm", key_file])

    mount_result = subprocess.run(["mount", f"/dev/mapper/{device_settings.get('name')}", device_settings.get('mount')], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    mount_output = mount_result.stdout.decode("utf-8")
    if cryptsetup_result.returncode == 0 and mount_result.returncode == 0:
        return {"status": "succesful",
                "cryptsetup_exit_code": cryptsetup_result.returncode,
                "cryptsetup_output": cryptsetup_output,
                "mount_exit_code": mount_result.returncode,
                "mount_output": mount_output}
    else:
        return {"status": "error",
                "cryptsetup_exit_code": cryptsetup_result.returncode,
                "cryptsetup_output": cryptsetup_output,
                "mount_exit_code": mount_result.returncode,
                "mount_output": mount_output}




if __name__ == '__main__':
    app.run(host='0.0.0.0')
