from nanolib import Block, get_account_id
import json
import requests

#Convert IP address to valid url format
def toURL(address):
    if not address.startswith("http"):
        return "http://" + address
    else:
        return address

#Import config
with open('worker_config.json') as worker_config:
    data = json.load(worker_config)
worker = {
    "account": data['reward_account'].replace("xrb_", "nano_"),
    "private_key": data['private_key'],
    "representative": data['representative'].replace("xrb_", "nano_"),
    "fee": data['fee'],
    "node": toURL(data['node']),
    "worker_node": toURL(data['worker']),
    "use_active_difficulty": data['use_active_difficulty'],
    "max_multiplier": data['max_multiplier'],
    "service_port": data['port'],
}


with open('register_config.json') as register_config:
    data_register = json.load(register_config)
register_config = {
    "account": data_register['registration_account'].replace("xrb_", "nano_"),
    "sign_new_ip_code": int(data_register['sign_new_ip_code']),
    "sign_new_account_code": int(data_register['sign_new_account_code']),
    "get_ip": toURL(data_register['get_ip'])
}

#Read transaction Block
def block_create(block_type, account, representative, previous, link_as_account, balance, signature):
    try:
        block = Block(
            block_type=block_type,
            account=account,
            representative=representative,
            previous=previous,
            link_as_account=link_as_account,
            balance=balance,
        )
    except:
        return "invalid"
    else:
        if signature is not None:
            try:
                block.signature = signature
            except:
                return "invalid"
        return block

#check if the account has the balance
def balance(account):
    resp = requests.post(worker["node"], json={"action": "account_balance", "account": account})
    return int(resp.json()['balance'])

#account history
def check_history(account, destination):
    request = requests.post(worker["node"], json={"action": "account_history", "account": account, "count": -1})
    history = request.json()["history"]
    for b in history:
        if destination == b["account"].replace("xrb_", "nano_"):
            return b
    return (None)

#check if block already exists
def frontier(account):
     request = requests.post(worker["node"], json={"action": "accounts_frontiers", "accounts": [account]})
     if account in request.json()["frontiers"]:
        return request.json()["frontiers"][account]
     else:
        request = requests.post(worker["node"], json={ "action": "account_key", "account" : account })
        return request.json()["key"]

#active difficulty network
def get_difficulty():
     request = requests.post(worker["node"], json={"action": "active_difficulty", "include_trend": "true"})
     return float(request.json()["multiplier"])

#solve work
def solve_work (hash, multiplier):
     request = requests.post(worker["node"], json={"action": "work_generate", "hash": hash, "multiplier": multiplier })
     return request.json()["work"]

#broadcast transaction
def broadcast(transaction):
    request = requests.post(worker["node"], json={"action": "process", "json_block": "true", "block": json.loads(transaction)})
    return request.json()

#Find pending transactions and return those that complete the required amount.
def pending_filter (account, threshold):
    request = requests.post(worker["node"], json={"action": "pending", "account": account, "count": 1, "threshold": threshold})
    blocks = request.json()["blocks"]
    if blocks != "":
        return blocks
    else:
        request = requests.post(worker["node"], json={"action": "pending", "account": account, "threshold": 1})
        blocks = request.json()["blocks"]
        if blocks == "":
            return None
        else:
            for key in blocks:
                    blocks[key] = int(blocks[key])
            sorted_blocks = dict(sorted(blocks.items(), key=lambda kv: kv[1], reverse=True))
            receive_blocks = {}; acumulated = 0
            for key in sorted_blocks:
                receive_blocks[key] = sorted_blocks[key]
                acumulated += sorted_blocks[key]
                if acumulated >= threshold:
                    return receive_blocks
            return None

#Receive pending transactions
def receive(account, private_key, representative, amount, link, difficulty):
     request = requests.post(worker["node"], json={"action": "accounts_frontiers", "accounts": [account]})
     if account in request.json()["frontiers"]:
        previous = request.json()["frontiers"][account]
     else:
         previous = "0000000000000000000000000000000000000000000000000000000000000000"
     block = Block(
        block_type="state",
        account=account,
        representative=representative,
        previous=previous,
        balance=balance(worker["account"]) + amount,
        link=link
     )
     block.work = solve_work(frontier(account), difficulty)
     block.sign(private_key)
     r = broadcast(block.json())
     return r

#Send transactions (Used in the registration process)
def send (account, representative, previous, link_as_account, amount, difficulty):
    block = block_create("state", account, representative, previous, link_as_account, balance(worker["account"]) - amount, None)
    block.sign(worker["private_key"])
    block.work = solve_work(block.previous, difficulty)
    r = broadcast(block.json())
    return r

#Get external IPv4 or IPv6
def get_my_ip():
    myIP = requests.get(register_config["get_ip"])
    return myIP.text

#encode IPv4 or IPv6 into Nano Account format
def encode_ip (ip):
    ip_as_bytes = bytes(map(int, ip.split('.'))) #convert to bytes
    ip_as_bytes += (32 - len(ip_as_bytes)) * b'\0' #padding
    ip_account =  get_account_id(public_key=ip_as_bytes.hex(), prefix="nano_") ##convert to nano account format
    return ip_account

#Registration Function. This process uses Nano transactions to save worker IP and account and associate it with the main registration account
def register (account, representative, previous, register_account, code, multiplier):
    if code == register_config["sign_new_account_code"]:
        what = "your worker account"
    if code == register_config["sign_new_ip_code"]:
        what = "your IP address"
    if balance(account) >= code:
        print ("You have sufficient funds to register " + what)
        print ("Registering " + what + " now")
        r = send(account, representative, previous, register_account, code, multiplier)
        if 'hash' in r:
            print ("Successfully registred " + what + " Block: " + r["hash"])
        else:
            print ("Register transaction fail. Details: " + json.dumps(r))
    else:
        print ("Insufficient funds, checking for unpocketed transactions...")
        pending = pending_filter(account, code)
        if pending == None:
            print ("You have not sufficient funds to register " + what + "! Please send at least " + str((register_config["sign_new_account_code"] + register_config["sign_new_ip_code"])) + " raws to your worker account")
            return False
        else:
            for block in pending:
                print ("Receiving pending block: " + str(pending[block]) + " raws")
                r = receive(account, worker["private_key"], representative, int(pending[block]), block, multiplier)
                if 'hash' in r:
                    print ("Transaction received!" + "! Block: " + r["hash"])
                else:
                    print ("Transaction receiving fail. Details: " + json.dumps(r))
            print ("Ok, registering " + what + " now")
            r = send(account, representative, frontier(account), register_account, code, multiplier)
            if 'hash' in r:
                print ("Successfully registred " + what + "! Block: " + r["hash"])
            else:
                print ("Register transaction fail. Details: " + json.dumps(r))
