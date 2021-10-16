import subprocess
from flask import Flask, request
import yaml

SETTINGS_FILE="settings.yaml"

with open(SETTINGS_FILE, 'r') as f:
    settings = yaml.load(f)

app = Flask(__name__)

@app.route('/unlock/<device_name>', methods=['GET', 'POST']) #device_name is the name of the device in configuration.yaml
def unlock_luks_device(device_name):
    key = request.args.get('key')
    device_settings = settings["devices"][device_name]

    with open(f"/tmp/{device_name}.key", 'w') as f:
        f.write(key)

    cryptsetup_result = subprocess.run(["cryptsetup", "luksOpen", device_settings.get('path'), device_settings.get('name'), "-d", f"/tmp/{device_name}.key"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    cryptsetup_output = cryptsetup_result.stdout.decode("utf-8")
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
