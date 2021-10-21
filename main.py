import subprocess
import os
from flask import Flask, request, render_template, redirect, url_for
import yaml

SETTINGS_FILE=os.environ.get('LW_SETTINGS_FILE', "settings.yaml")

with open(SETTINGS_FILE, 'r') as f:
    settings = yaml.load(f, Loader=yaml.CLoader)

STOP_CMD=os.environ.get('LW_STOP_CMD') or settings["stop_cmd"]

app = Flask(__name__)

@app.route('/')
def unlock_page():
    password_forms = []
    for device_id, device in settings["devices"].items():
        password_forms.append(f"""
        <form id={device_id}_form action="/unlock/{device_id}" method="POST" target="hidden-form">
            <label for="{device_id}_password">Passphrase for {device.get("name")}:</label>
            <input type="password" id="{device_id}_password" name="{device_id}_password" value="">
            <label for="{device_id}_password" id="{device_id}_status">❌</label>
            <input type="submit" id="{device_id}_submit" value="Submit">
            <script>
                function {device_id}_reqListener () {{
                    const response = JSON.parse(this.responseText);
                    if ( response.status == "unlocked" ) {{
                        clearInterval({device_id}_checkUnlockedInterval);
                        {device_id}_password.disabled = true;
                        {device_id}_submit.style.display = "none";
                        {device_id}_status.innerHTML = "✅";
                        encryptedDevices -= 1;
                        if ( encryptedDevices <= 0 ) {{
                            setTimeout("window.location.href = '/unlocked'", 2000);
                        }}
                    }}
                }}

                function {device_id}_checkUnlocked() {{
                    var target = '/check_unlocked/{device_id}';
                    var xhr = new XMLHttpRequest();
                    xhr.addEventListener("load", {device_id}_reqListener);
                    xhr.open('GET', target);
                    xhr.send();
                }}

                {device_id}_checkUnlocked();
                var {device_id}_checkUnlockedInterval = setInterval({device_id}_checkUnlocked, 5000);
            </script>
        </form>
        """) # Double curlies are for escaping
    password_forms_str = "\n".join(password_forms)
    return render_template('unlock.html',
                           password_forms=password_forms_str,
                           encrypted_devices=len(password_forms))

@app.route('/unlocked')
def unlocked_page():
    devices = settings["devices"]

    all_unlocked = True
    for device_id, device in devices.items():
        if not os.path.exists(f"/dev/mapper/{device.get('name')}"):
            all_unlocked = False
    if all_unlocked:
        return render_template('unlocked.html')
    else:
        return redirect(url_for('unlock_page'))

@app.route('/unlock/<device_id>', methods=['GET', 'POST']) #device_id is the id of the device in settings.yaml
def unlock_luks_device(device_id):
    device_settings = settings["devices"][device_id]
    key =  request.form.get(f"{device_id}_password") or request.args.get('key')
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

@app.route('/kill', methods=['GET', 'POST'])
def kill():
    devices = settings["devices"]

    all_unlocked = True
    for device_id, device in devices.items():
        if not os.path.exists(f"/dev/mapper/{device.get('name')}"):
            all_unlocked = False
    if all_unlocked:
        return {"exit_code": os.system(STOP_CMD)}
    else:
        return {"message": "You can't do that until you unlock all the devices"}

if __name__ == '__main__':
    app.run(host='0.0.0.0')
