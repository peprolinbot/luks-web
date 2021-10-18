import subprocess
import os
from flask import Flask, request,render_template
import yaml

SETTINGS_FILE="settings.yaml"

with open(SETTINGS_FILE, 'r') as f:
    settings = yaml.load(f)

app = Flask(__name__)

@app.route('/')
def unlock_page():
    password_forms = []
    for device_id, device in settings["devices"].items():
        password_forms.append(f"""
        <form id={device_id}_form action="/unlock/{device_id}" method="POST" target="hidden-form">
            <label for="{device_id}">Passphrase for {device.get("name")}:</label>
            <input type="password" id="{device_id}" name="{device_id}" value="">
            <label for="{device_id}" id="{device_id}_status">❌</label>
            <input type="submit" id="{device_id}_submit" value="Submit">
            <script>
                function reqListener () {{
                    const response = JSON.parse(this.responseText);
                    if ( response.status == "unlocked" ) {{
                        {device_id}.disabled = true;
                        {device_id}_submit.style.display = "none";
                        {device_id}_status.innerHTML = "✅";
                    }}
                }}

                function checkUnlocked() {{
                    var target = '/check_unlocked/{device_id}';
                    var xhr = new XMLHttpRequest();
                    xhr.addEventListener("load", reqListener);
                    xhr.open('GET', target);
                    xhr.send();
                }}

                checkUnlocked();
                setInterval(checkUnlocked, 5000);
            </script>
        </form>
        """) # Double curlies are for escaping
    password_forms_str = "\n".join(password_forms)
    return render_template('unlock.html',
                           password_forms=password_forms_str)

@app.route('/unlock/<device_id>', methods=['GET', 'POST']) #device_id is the id of the device in settings.yaml
def unlock_luks_device(device_id):
    device_settings = settings["devices"][device_id]
    key =  request.form.get(device_id) or request.args.get('key')
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


@app.route('/check_unlocked/<device_id>', methods=['GET']) #device_id is the id of the device in settings.yaml
def check_unlocked_luks_device(device_id):
    device_settings = settings["devices"][device_id]

    if os.path.exists(f"/dev/mapper/{device_settings.get('name')}"):
        return {"status": "unlocked"}
    else:
        return {"status": "locked"}

if __name__ == '__main__':
    app.run(host='0.0.0.0')
